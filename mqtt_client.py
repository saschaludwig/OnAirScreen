#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# mqtt_client.py
# This file is part of OnAirScreen
#
# MQTT Client with Home Assistant Autodiscovery support
#
#############################################################################

"""
MQTT Client for OnAirScreen with Home Assistant Autodiscovery

This module provides MQTT integration for OnAirScreen, allowing it to:
- Publish status updates via MQTT
- Receive commands via MQTT
- Auto-discover in Home Assistant using MQTT Discovery
"""

import json
import logging
import socket
from typing import Optional, TYPE_CHECKING, Dict, Any
import sys
from PyQt6.QtCore import QThread, QSettings

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None  # type: ignore
    logging.getLogger(__name__).warning("paho-mqtt library not available. MQTT support will be disabled.")

from utils import settings_group
from exceptions import MqttError, log_exception

if TYPE_CHECKING:
    from start import MainScreen
    from settings_functions import Settings

logger = logging.getLogger(__name__)


class MqttClient(QThread):
    """
    MQTT Client thread for OnAirScreen with Home Assistant Autodiscovery
    
    Handles MQTT connection, publishing status updates, receiving commands,
    and Home Assistant MQTT Discovery configuration.
    """
    
    def __init__(self, main_screen: Optional["MainScreen"] = None) -> None:
        """
        Initialize MQTT client
        
        Args:
            main_screen: Reference to MainScreen instance for status queries and commands
        """
        super().__init__()
        self.main_screen = main_screen
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        self._stop_requested = False
        
        # MQTT configuration (will be loaded from settings)
        self.broker_host = "localhost"
        self.broker_port = 1883
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.client_id = f"onairscreen_{socket.gethostname()}"
        self.base_topic = "onairscreen"
        self.discovery_prefix = "homeassistant"
        self.device_name = "OnAirScreen"
        self.device_id = socket.gethostname().lower().replace(" ", "_").replace(".", "_")
    
    def _get_unique_id_from_mac(self) -> str:
        """
        Get unique ID from MAC address (last 6 hex characters)
        
        Returns:
            Unique ID string (6 hex characters, lowercase)
        """
        try:
            from settings_functions import Settings
            mac = Settings.get_mac()
            # Extract last 6 hex characters (remove colons and take last 6)
            mac_clean = mac.replace(":", "").upper()
            if len(mac_clean) >= 6:
                unique_id = mac_clean[-6:].lower()
            else:
                # Fallback if MAC address is invalid
                logger.warning(f"Invalid MAC address format: {mac}, using fallback")
                unique_id = "000000"
            return unique_id
        except Exception as e:
            logger.error(f"Error getting unique ID from MAC address: {e}")
            return "000000"
    
    def _load_config(self) -> None:
        """Load MQTT configuration from QSettings"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "MQTT"):
            self.broker_host = settings.value('mqttserver', "localhost", type=str)
            try:
                self.broker_port = int(settings.value('mqttport', 1883, type=int))
            except (ValueError, TypeError):
                self.broker_port = 1883
            self.username = settings.value('mqttuser', None, type=str)
            if not self.username:
                self.username = None
            self.password = settings.value('mqttpassword', None, type=str)
            if not self.password:
                self.password = None
            self.discovery_prefix = settings.value('discovery_prefix', "homeassistant", type=str)
            self.device_name = settings.value('mqttdevicename', "OnAirScreen", type=str)
            if not self.device_name:
                self.device_name = "OnAirScreen"
            # Generate base_topic automatically from "onairscreen" + unique ID from MAC
            unique_id = self._get_unique_id_from_mac()
            self.base_topic = f"onairscreen_{unique_id}"
    
    def _is_enabled(self) -> bool:
        """Check if MQTT is enabled in settings"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "MQTT"):
            return settings.value('enablemqtt', False, type=bool)
    
    def run(self) -> None:
        """Start MQTT client in a separate thread"""
        if not MQTT_AVAILABLE:
            logger.warning("MQTT support not available, skipping MQTT client startup")
            return
        
        if not self._is_enabled():
            logger.info("MQTT is disabled in settings")
            return
        
        self._load_config()
        
        try:
            # Create MQTT client
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311
            )
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            
            # Set credentials if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            try:
                self.client.connect(self.broker_host, self.broker_port, 60)
            except Exception as e:
                error = MqttError(f"Failed to connect to MQTT broker: {e}")
                log_exception(logger, error)
                return
            
            # Start network loop (this runs in a separate thread)
            self.client.loop_start()
            
            # Wait for connection
            import time
            connection_wait_timeout = 10
            for _ in range(connection_wait_timeout):  # Wait up to 5 seconds
                if self._connected:
                    break
                time.sleep(0.5)
            
            if not self._connected:
                logger.error("Failed to establish MQTT connection within timeout")
                self.client.loop_stop()
                return
            
            # Give the connection a moment to stabilize
            time.sleep(0.5)
            
            # Publish autodiscovery configuration
            self._publish_autodiscovery()
            
            # Give time for autodiscovery messages to be sent
            time.sleep(0.5)
            
            # Publish initial status
            logger.debug("Publishing initial status after autodiscovery")
            self.publish_status()
            logger.debug("Initial status published, entering main loop")
            
            # Keep thread alive and publish status periodically
            last_publish_time = time.time()
            loop_iteration = 0
            while not self._stop_requested:
                loop_iteration += 1
                if loop_iteration % 60 == 0:  # Log every 60 seconds
                    logger.debug(f"MQTT client main loop running, connected={self._connected}, stop_requested={self._stop_requested}")
                time.sleep(1)
                # Check if still connected
                if not self._connected:
                    logger.warning("MQTT connection lost, attempting to reconnect...")
                    # Try to reconnect
                    try:
                        self.client.reconnect()
                        # Wait for reconnection
                        for _ in range(10):
                            if self._connected:
                                break
                            time.sleep(0.5)
                        if self._connected:
                            logger.info("MQTT reconnected successfully")
                            # Re-publish autodiscovery after reconnection
                            self._publish_autodiscovery()
                            time.sleep(0.5)
                        else:
                            logger.error("Failed to reconnect to MQTT broker")
                            time.sleep(5)  # Wait before next reconnect attempt
                            continue
                    except Exception as reconnect_error:
                        error = MqttError(f"Error during MQTT reconnect: {reconnect_error}")
                        log_exception(logger, error)
                        time.sleep(5)  # Wait before next reconnect attempt
                        continue
                
                # Publish status every 5 seconds
                current_time = time.time()
                if current_time - last_publish_time >= 5.0:
                    self.publish_status()
                    last_publish_time = current_time
                
        except Exception as e:
            from exceptions import OnAirScreenError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = MqttError(f"Error in MQTT client thread: {e}")
                log_exception(logger, error)
        except KeyboardInterrupt:
            logger.debug("MQTT client thread interrupted")
        finally:
            logger.debug("MQTT client thread entering finally block")
            if self.client:
                logger.debug("Stopping MQTT client loop and disconnecting")
                self._stop_requested = True
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                    logger.debug("MQTT client stopped")
                except Exception as e:
                    from exceptions import OnAirScreenError
                    if isinstance(e, OnAirScreenError):
                        log_exception(logger, e)
                    else:
                        error = MqttError(f"Error during MQTT client cleanup: {e}")
                        log_exception(logger, error)
            logger.debug("MQTT client thread finished")
    
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, int], rc: int) -> None:
        """Callback when MQTT client connects"""
        if rc == 0:
            self._connected = True
            logger.info("MQTT client connected successfully")
            
            # Subscribe to command topics
            command_topic = f"{self.base_topic}/command/+"
            client.subscribe(command_topic)
            logger.info(f"Subscribed to MQTT topic: {command_topic}")
            
            # Subscribe to set topics for Home Assistant
            for led_num in range(1, 5):
                set_topic = f"{self.base_topic}/led{led_num}/set"
                client.subscribe(set_topic)
            for air_num in range(1, 5):
                set_topic = f"{self.base_topic}/air{air_num}/set"
                client.subscribe(set_topic)
            # Subscribe to reset topics for AIR3 and AIR4
            for air_num in [3, 4]:
                reset_topic = f"{self.base_topic}/air{air_num}/reset"
                client.subscribe(reset_topic)
            set_topic = f"{self.base_topic}/text/now/set"
            client.subscribe(set_topic)
            set_topic = f"{self.base_topic}/text/next/set"
            client.subscribe(set_topic)
            set_topic = f"{self.base_topic}/text/warn/set"
            client.subscribe(set_topic)
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self._connected = False
    
    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Callback when MQTT client disconnects"""
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT client disconnected unexpectedly (rc={rc}), stop_requested={self._stop_requested}")
        else:
            logger.debug(f"MQTT client disconnected (rc={rc}), stop_requested={self._stop_requested}")
    
    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback when MQTT message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"Received MQTT message: {topic} = {payload}")
            
            # Build command string
            command = None
            
            # Parse topic and build command
            if topic.startswith(f"{self.base_topic}/command/"):
                # Direct command format: onairscreen/command/LED1:ON
                command = f"{topic.split('/')[-1]}:{payload}"
            
            elif topic.startswith(f"{self.base_topic}/led"):
                # LED command: onairscreen/led1/set -> payload: ON or OFF
                led_num = int(topic.split("/")[1][3:])  # Extract number from "led1"
                command = f"LED{led_num}:{payload.upper()}"
            
            elif topic.startswith(f"{self.base_topic}/air"):
                # AIR timer command: onairscreen/air1/set -> payload: ON, OFF, RESET, TOGGLE
                # or: onairscreen/air3/reset -> payload: (any, button press)
                topic_parts = topic.split("/")
                air_num = int(topic_parts[1][3:])  # Extract number from "air1"
                
                # Check if this is a reset button topic
                if len(topic_parts) > 2 and topic_parts[2] == "reset":
                    # Reset button pressed for AIR3 or AIR4
                    if air_num == 3:
                        command = "AIR3:RESET"
                    elif air_num == 4:
                        command = "AIR4:RESET"
                    else:
                        logger.warning(f"Reset button only available for AIR3 and AIR4, not AIR{air_num}")
                        return
                else:
                    # Regular set command
                    if air_num == 3:
                        command = f"AIR3:{payload.upper()}"
                    elif air_num == 4:
                        command = f"AIR4:{payload.upper()}"
                    else:
                        command = f"AIR{air_num}:{payload.upper()}"
            
            elif topic.startswith(f"{self.base_topic}/text/"):
                # Text command: onairscreen/text/now/set -> payload: text content
                text_type = topic.split("/")[2]  # now, next, or warn
                if text_type == "warn":
                    # Check if payload contains priority (format: "priority:text" or just "text")
                    if ":" in payload and payload.split(":")[0].isdigit():
                        # Already in correct format
                        command = f"WARN:{payload}"
                    else:
                        command = f"WARN:{payload}"
                else:
                    command = f"{text_type.upper()}:{payload}"
            
            # Execute command in GUI thread using signal (thread-safe)
            if command and self.main_screen:
                command_bytes = command.encode('utf-8')
                # Use command_signal if available (thread-safe execution in GUI thread)
                if hasattr(self.main_screen, 'command_signal') and self.main_screen.command_signal:
                    self.main_screen.command_signal.command_received.emit(command_bytes, "mqtt")
                elif hasattr(self.main_screen, 'command_handler'):
                    # Fallback: direct call (may not work for timers if not in GUI thread)
                    logger.warning("MQTT command executed without signal - may not work correctly for timers")
                    self.main_screen.command_handler.parse_cmd(command_bytes)
                else:
                    logger.error("No command handler available for MQTT command")
                    
        except Exception as e:
            from exceptions import OnAirScreenError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = MqttError(f"Error processing MQTT message: {e}")
                log_exception(logger, error)
    
    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int) -> None:
        """Callback when message is published (optional, for debugging)"""
        logger.debug(f"MQTT message published (mid={mid})")
    
    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information for Home Assistant discovery"""
        return {
            "identifiers": [f"onairscreen_{self.device_id}"],
            "name": self.device_name,
            "manufacturer": "astrastudio",
            "model": "OnAirScreen",
            "sw_version": self._get_version(),
        }
    
    def _get_version(self) -> str:
        """Get OnAirScreen version"""
        try:
            from version import versionString
            return versionString
        except ImportError:
            return "unknown"
    
    def _publish_autodiscovery(self) -> None:
        """Publish Home Assistant MQTT Discovery configuration"""
        if not self._connected or not self.client:
            return
        
        device_info = self._get_device_info()
        
        # Publish LED switches
        for led_num in range(1, 5):
            config = {
                "name": f"{self.device_name} LED{led_num}",
                "unique_id": f"onairscreen_led{led_num}_{self.device_id}",
                "state_topic": f"{self.base_topic}/led{led_num}/state",
                "command_topic": f"{self.base_topic}/led{led_num}/set",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device_class": "switch",
                "device": device_info,
            }
            topic = f"{self.discovery_prefix}/switch/onairscreen_led{led_num}_{self.device_id}/config"
            self.client.publish(topic, json.dumps(config), retain=True)
            logger.info(f"Published autodiscovery config for LED{led_num}")
        
        # Publish AIR timer switches
        for air_num in range(1, 5):
            air_name = f"AIR{air_num}"
            config = {
                "name": f"{self.device_name} {air_name}",
                "unique_id": f"onairscreen_air{air_num}_{self.device_id}",
                "state_topic": f"{self.base_topic}/air{air_num}/state",
                "command_topic": f"{self.base_topic}/air{air_num}/set",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device_class": "switch",
                "device": device_info,
            }
            topic = f"{self.discovery_prefix}/switch/onairscreen_air{air_num}_{self.device_id}/config"
            self.client.publish(topic, json.dumps(config), retain=True)
            logger.info(f"Published autodiscovery config for {air_name}")
        
        # Publish AIR timer sensors (for elapsed time)
        for air_num in range(1, 5):
            air_name = f"AIR{air_num}"
            config = {
                "name": f"{self.device_name} {air_name} Time",
                "unique_id": f"onairscreen_air{air_num}_time_{self.device_id}",
                "state_topic": f"{self.base_topic}/air{air_num}/time",
                "unit_of_measurement": "s",
                "device_class": "duration",
                "device": device_info,
            }
            topic = f"{self.discovery_prefix}/sensor/onairscreen_air{air_num}_time_{self.device_id}/config"
            self.client.publish(topic, json.dumps(config), retain=True)
            logger.info(f"Published autodiscovery config for {air_name} Time")
        
        # Publish Reset buttons for AIR3 and AIR4
        for air_num in [3, 4]:
            air_name = f"AIR{air_num}"
            config = {
                "name": f"{self.device_name} {air_name} Reset",
                "unique_id": f"onairscreen_air{air_num}_reset_{self.device_id}",
                "command_topic": f"{self.base_topic}/air{air_num}/reset",
                "payload_press": "PRESS",
                "device": device_info,
            }
            topic = f"{self.discovery_prefix}/button/onairscreen_air{air_num}_reset_{self.device_id}/config"
            self.client.publish(topic, json.dumps(config), retain=True)
            logger.info(f"Published autodiscovery config for {air_name} Reset button")
        
        # Publish text sensors (Home Assistant uses "text" not "text_sensor")
        for text_type in ["now", "next", "warn"]:
            config = {
                "name": f"{self.device_name} {text_type.upper()}",
                "unique_id": f"onairscreen_text_{text_type}_{self.device_id}",
                "state_topic": f"{self.base_topic}/text/{text_type}/state",
                "command_topic": f"{self.base_topic}/text/{text_type}/set",
                "device": device_info,
            }
            topic = f"{self.discovery_prefix}/text/onairscreen_text_{text_type}_{self.device_id}/config"
            self.client.publish(topic, json.dumps(config), retain=True)
            logger.info(f"Published autodiscovery config for {text_type.upper()} text")
        
        # Publish binary sensor for warnings (active/inactive)
        config = {
            "name": f"{self.device_name} Warning Active",
            "unique_id": f"onairscreen_warning_active_{self.device_id}",
            "state_topic": f"{self.base_topic}/warning/active",
            "payload_on": "true",
            "payload_off": "false",
            "device_class": "problem",
            "device": device_info,
        }
        topic = f"{self.discovery_prefix}/binary_sensor/onairscreen_warning_active_{self.device_id}/config"
        self.client.publish(topic, json.dumps(config), retain=True)
        logger.info("Published autodiscovery config for Warning Active")
    
    def publish_status(self, specific_item: str | None = None) -> None:
        """
        Publish current status to MQTT
        
        Args:
            specific_item: Optional specific item to publish (e.g., 'led1', 'air2', 'now', 'next', 'warn')
                          If None, publishes all status items
        """
        if not self._connected or not self.client or not self.main_screen:
            return
        
        try:
            status = self.main_screen.get_status_json()
            
            if specific_item is None:
                # Publish all status items
                # Publish LED states
                for led_num in range(1, 5):
                    led_status = "ON" if status['leds'][led_num]['status'] else "OFF"
                    topic = f"{self.base_topic}/led{led_num}/state"
                    self.client.publish(topic, led_status, retain=True)
                
                # Publish AIR timer states
                for air_num in range(1, 5):
                    air_status = "ON" if status['air'][air_num]['status'] else "OFF"
                    topic = f"{self.base_topic}/air{air_num}/state"
                    self.client.publish(topic, air_status, retain=True)
                    
                    # Publish elapsed time
                    time_topic = f"{self.base_topic}/air{air_num}/time"
                    self.client.publish(time_topic, str(status['air'][air_num]['seconds']), retain=True)
                
                # Publish text fields
                self.client.publish(f"{self.base_topic}/text/now/state", status['texts']['now'], retain=True)
                self.client.publish(f"{self.base_topic}/text/next/state", status['texts']['next'], retain=True)
                self.client.publish(f"{self.base_topic}/text/warn/state", status['texts']['warn'], retain=True)
                
                # Publish warning active state
                warning_active = "true" if status['texts']['warn'] else "false"
                self.client.publish(f"{self.base_topic}/warning/active", warning_active, retain=True)
                
                logger.debug("Published all status to MQTT")
            else:
                # Publish specific item only
                if specific_item.startswith('led'):
                    led_num = int(specific_item[3:])
                    led_status = "ON" if status['leds'][led_num]['status'] else "OFF"
                    topic = f"{self.base_topic}/led{led_num}/state"
                    self.client.publish(topic, led_status, retain=True)
                    logger.debug(f"Published LED{led_num} status to MQTT: {led_status}")
                
                elif specific_item.startswith('air'):
                    air_num = int(specific_item[3:])
                    air_status = "ON" if status['air'][air_num]['status'] else "OFF"
                    topic = f"{self.base_topic}/air{air_num}/state"
                    self.client.publish(topic, air_status, retain=True)
                    time_topic = f"{self.base_topic}/air{air_num}/time"
                    self.client.publish(time_topic, str(status['air'][air_num]['seconds']), retain=True)
                    logger.debug(f"Published AIR{air_num} status to MQTT: {air_status}")
                
                elif specific_item in ['now', 'next', 'warn']:
                    text_value = status['texts'][specific_item]
                    self.client.publish(f"{self.base_topic}/text/{specific_item}/state", text_value, retain=True)
                    if specific_item == 'warn':
                        warning_active = "true" if text_value else "false"
                        self.client.publish(f"{self.base_topic}/warning/active", warning_active, retain=True)
                    logger.debug(f"Published {specific_item.upper()} text to MQTT: {text_value}")
            
        except Exception as e:
            from exceptions import OnAirScreenError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = MqttError(f"Error publishing status to MQTT: {e}")
                log_exception(logger, error)
    
    def restart(self) -> None:
        """Restart MQTT client (stop and start again)"""
        logger.debug("Restarting MQTT client...")
        self.stop()
        # Wait for thread to fully stop before starting a new one
        if self.isRunning():
            logger.debug("Waiting for MQTT client thread to stop...")
            if not self.wait(3000):  # Wait up to 3 seconds
                logger.warning("MQTT client thread did not stop within timeout, forcing termination")
                self.terminate()
                self.wait(1000)  # Wait additional second after termination
        
        # Reset stop flag for new start
        self._stop_requested = False
        self._connected = False
        
        if self._is_enabled():
            logger.debug("Starting new MQTT client thread...")
            self.start()
        else:
            logger.debug("MQTT is disabled, not restarting client")
    
    def stop(self) -> None:
        """Stop MQTT client gracefully"""
        logger.debug("Stopping MQTT client...")
        self._stop_requested = True
        if self.client and self._connected:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                logger.warning(f"Error stopping MQTT client: {e}")
        self.wait(3000)  # Wait up to 3 seconds

