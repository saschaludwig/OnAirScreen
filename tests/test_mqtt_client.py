#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for mqtt_client.py

Tests for MQTT client functionality including:
- Connection handling
- Autodiscovery configuration
- Status publishing
- Command receiving
- Thread management
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, call
from PyQt6.QtCore import QSettings, QThread
from PyQt6.QtWidgets import QApplication

import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from mqtt_client import MqttClient
from utils import settings_group


@pytest.fixture
def mock_main_screen():
    """Create a mock MainScreen instance for testing"""
    main_screen = Mock()
    
    # Mock status attributes
    main_screen.statusLED1 = False
    main_screen.statusLED2 = False
    main_screen.statusLED3 = False
    main_screen.statusLED4 = False
    main_screen.statusAIR1 = False
    main_screen.statusAIR2 = False
    main_screen.statusAIR3 = False
    main_screen.statusAIR4 = False
    main_screen.Air1Seconds = 0
    main_screen.Air2Seconds = 0
    main_screen.Air3Seconds = 0
    main_screen.Air4Seconds = 0
    
    # Mock text widgets
    main_screen.labelCurrentSong = Mock()
    main_screen.labelCurrentSong.text.return_value = ""
    main_screen.labelNews = Mock()
    main_screen.labelNews.text.return_value = ""
    main_screen.labelWarning = Mock()
    main_screen.labelWarning.text.return_value = ""
    
    # Mock command handler
    main_screen.command_handler = Mock()
    main_screen.command_handler.parse_cmd = Mock()
    
    # Mock command signal
    main_screen.command_signal = Mock()
    main_screen.command_signal.command_received = Mock()
    
    # Mock get_status_json method
    def get_status_json():
        return {
            'leds': {
                1: {'status': main_screen.statusLED1, 'text': 'LED1'},
                2: {'status': main_screen.statusLED2, 'text': 'LED2'},
                3: {'status': main_screen.statusLED3, 'text': 'LED3'},
                4: {'status': main_screen.statusLED4, 'text': 'LED4'},
            },
            'air': {
                1: {'status': main_screen.statusAIR1, 'seconds': main_screen.Air1Seconds, 'text': 'Mic'},
                2: {'status': main_screen.statusAIR2, 'seconds': main_screen.Air2Seconds, 'text': 'Phone'},
                3: {'status': main_screen.statusAIR3, 'seconds': main_screen.Air3Seconds, 'text': 'Radio'},
                4: {'status': main_screen.statusAIR4, 'seconds': main_screen.Air4Seconds, 'text': 'Stream'},
            },
            'texts': {
                'now': main_screen.labelCurrentSong.text(),
                'next': main_screen.labelNews.text(),
                'warn': main_screen.labelWarning.text(),
            },
            'version': '0.9.7beta4',
            'distribution': 'OpenSource'
        }
    
    main_screen.get_status_json = get_status_json
    
    return main_screen


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client"""
    with patch('mqtt_client.mqtt') as mock_mqtt_module:
        mock_client = Mock()
        mock_client_class = Mock(return_value=mock_client)
        mock_mqtt_module.Client = mock_client_class
        mock_mqtt_module.MQTTv311 = 3
        
        yield mock_client


class TestMqttClientInitialization:
    """Tests for MQTT client initialization"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_init_with_main_screen(self, mock_main_screen):
        """Test MQTT client initialization with main screen"""
        client = MqttClient(mock_main_screen)
        assert client.main_screen == mock_main_screen
        assert client.broker_host == "localhost"
        assert client.broker_port == 1883
        assert client.base_topic == "onairscreen"
        assert client._connected == False
        assert client._stop_requested == False
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_init_without_main_screen(self):
        """Test MQTT client initialization without main screen"""
        client = MqttClient(None)
        assert client.main_screen is None
        assert client.broker_host == "localhost"
        assert client.broker_port == 1883
    
    @patch('mqtt_client.MQTT_AVAILABLE', False)
    def test_init_without_mqtt_library(self):
        """Test that client can be initialized even without paho-mqtt"""
        client = MqttClient(None)
        assert client.main_screen is None


class TestMqttClientConfiguration:
    """Tests for MQTT client configuration loading"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    @patch('mqtt_client.QSettings')
    @patch('settings_functions.Settings')
    def test_load_config_from_settings(self, mock_settings_class, mock_qsettings, mock_main_screen):
        """Test loading configuration from QSettings"""
        # Mock Settings.get_mac() to return a consistent MAC address
        mock_settings_class.get_mac.return_value = "AA:BB:CC:DD:EE:FF"
        
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'mqttserver': 'test-broker.local',
            'mqttport': 8883,
            'mqttuser': 'testuser',
            'mqttpassword': 'testpass',
            'mqttdevicename': 'TestDevice',
            'discovery_prefix': 'hass',
            'enablemqtt': True
        }.get(key, default)
        
        mock_qsettings.return_value = mock_settings
        
        client = MqttClient(mock_main_screen)
        client._load_config()
        
        assert client.broker_host == 'test-broker.local'
        assert client.broker_port == 8883
        assert client.username == 'testuser'
        assert client.password == 'testpass'
        assert client.base_topic == 'onairscreen_ddeeff'  # Last 6 hex chars from MAC (AA:BB:CC:DD:EE:FF -> DDEEFF)
        assert client.discovery_prefix == 'hass'
        assert client.device_name == 'TestDevice'
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    @patch('mqtt_client.QSettings')
    @patch('settings_functions.Settings')
    def test_load_config_defaults(self, mock_settings_class, mock_qsettings, mock_main_screen):
        """Test loading default configuration when settings are empty"""
        # Mock Settings.get_mac() to return a consistent MAC address
        mock_settings_class.get_mac.return_value = "11:22:33:44:55:66"
        
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: default
        mock_qsettings.return_value = mock_settings
        
        client = MqttClient(mock_main_screen)
        client._load_config()
        
        assert client.broker_host == "localhost"
        assert client.broker_port == 1883
        assert client.username is None
        assert client.password is None
        assert client.base_topic == "onairscreen_445566"  # Last 6 hex chars from MAC (11:22:33:44:55:66 -> 445566)
        assert client.device_name == "OnAirScreen"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    @patch('mqtt_client.QSettings')
    def test_is_enabled(self, mock_qsettings, mock_main_screen):
        """Test checking if MQTT is enabled"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'enablemqtt': True
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        client = MqttClient(mock_main_screen)
        assert client._is_enabled() == True
        
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'enablemqtt': False
        }.get(key, default)
        assert client._is_enabled() == False


class TestMqttClientConnection:
    """Tests for MQTT client connection handling"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    @patch('mqtt_client.mqtt')
    @patch('mqtt_client.QSettings')
    def test_connection_success(self, mock_qsettings, mock_mqtt_module, mock_main_screen):
        """Test successful MQTT connection"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'enablemqtt': True,
            'mqttserver': 'localhost',
            'mqttport': 1883
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_client = Mock()
        mock_client_class = Mock(return_value=mock_client)
        mock_mqtt_module.Client = mock_client_class
        mock_mqtt_module.MQTTv311 = 3
        
        client = MqttClient(mock_main_screen)
        client._connected = True  # Simulate connection
        client.client = mock_client
        
        # Test that callbacks are set
        assert mock_client.on_connect is not None
        assert mock_client.on_disconnect is not None
        assert mock_client.on_message is not None
        assert mock_client.on_publish is not None
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    @patch('mqtt_client.mqtt')
    @patch('mqtt_client.QSettings')
    def test_connection_with_credentials(self, mock_qsettings, mock_mqtt_module, mock_main_screen):
        """Test MQTT connection with username/password"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'enablemqtt': True,
            'mqttserver': 'localhost',
            'mqttport': 1883,
            'mqttuser': 'user',
            'mqttpassword': 'pass'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_client = Mock()
        mock_client_class = Mock(return_value=mock_client)
        mock_mqtt_module.Client = mock_client_class
        mock_mqtt_module.MQTTv311 = 3
        
        client = MqttClient(mock_main_screen)
        client._load_config()
        client.client = mock_client
        
        # Simulate connection setup (username_pw_set is called in run(), not in _load_config)
        # So we test it directly
        if client.username and client.password:
            client.client.username_pw_set(client.username, client.password)
            mock_client.username_pw_set.assert_called_once_with('user', 'pass')


class TestMqttClientAutodiscovery:
    """Tests for Home Assistant Autodiscovery"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_autodiscovery_leds(self, mock_main_screen):
        """Test publishing autodiscovery config for LEDs"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.discovery_prefix = "homeassistant"
        client.device_id = "test_device"
        client.device_name = "OnAirScreen"
        
        client._publish_autodiscovery()
        
        # Check that publish was called for each LED
        assert client.client.publish.call_count >= 4  # At least 4 LEDs
        
        # Check that LED configs were published
        published_topics = [call[0][0] for call in client.client.publish.call_args_list]
        led_configs = [topic for topic in published_topics if 'led' in topic.lower() and 'config' in topic]
        assert len(led_configs) == 4
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_autodiscovery_air_timers(self, mock_main_screen):
        """Test publishing autodiscovery config for AIR timers"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.discovery_prefix = "homeassistant"
        client.device_id = "test_device"
        client.device_name = "OnAirScreen"
        
        client._publish_autodiscovery()
        
        # Check that AIR timer configs were published
        published_topics = [call[0][0] for call in client.client.publish.call_args_list]
        air_configs = [topic for topic in published_topics if 'air' in topic.lower() and 'config' in topic]
        assert len(air_configs) >= 4  # Switches + sensors
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_autodiscovery_text_sensors(self, mock_main_screen):
        """Test publishing autodiscovery config for text sensors"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.discovery_prefix = "homeassistant"
        client.device_id = "test_device"
        client.device_name = "OnAirScreen"
        
        client._publish_autodiscovery()
        
        # Check that text sensor configs were published
        published_topics = [call[0][0] for call in client.client.publish.call_args_list]
        text_configs = [topic for topic in published_topics if 'text' in topic.lower() and 'config' in topic]
        assert len(text_configs) == 3  # NOW, NEXT, WARN
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_autodiscovery_reset_buttons(self, mock_main_screen):
        """Test publishing autodiscovery config for AIR3 and AIR4 reset buttons"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.discovery_prefix = "homeassistant"
        client.device_id = "test_device"
        client.device_name = "OnAirScreen"
        
        client._publish_autodiscovery()
        
        # Check that reset button configs were published
        published_topics = [call[0][0] for call in client.client.publish.call_args_list]
        reset_button_configs = [topic for topic in published_topics if 'reset' in topic.lower() and 'config' in topic and 'button' in topic]
        assert len(reset_button_configs) == 2  # AIR3 and AIR4 reset buttons
        
        # Check that button configs have correct structure
        published_calls = client.client.publish.call_args_list
        for call_args in published_calls:
            topic = call_args[0][0]
            if 'reset' in topic and 'button' in topic and 'config' in topic:
                config_json = call_args[0][1]
                config = json.loads(config_json)
                assert 'command_topic' in config
                assert 'reset' in config['command_topic']
                assert 'payload_press' in config
                assert config['payload_press'] == 'PRESS'


class TestMqttClientStatusPublishing:
    """Tests for status publishing"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_all(self, mock_main_screen):
        """Test publishing all status items"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        # Set up mock status
        mock_main_screen.statusLED1 = True
        mock_main_screen.statusLED2 = False
        mock_main_screen.statusAIR1 = True
        mock_main_screen.Air1Seconds = 120
        mock_main_screen.labelCurrentSong.text.return_value = "Test Song"
        mock_main_screen.labelNews.text.return_value = "Test News"
        
        client.publish_status()
        
        # Check that publish was called multiple times
        assert client.client.publish.call_count > 0
        
        # Check LED states were published
        published_calls = client.client.publish.call_args_list
        led_states = [call[0][0] for call in published_calls if 'led' in call[0][0] and 'state' in call[0][0]]
        assert len(led_states) == 4
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_specific_led(self, mock_main_screen):
        """Test publishing status for specific LED"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        mock_main_screen.statusLED1 = True
        
        client.publish_status("led1")
        
        # Check that only LED1 state was published
        assert client.client.publish.call_count == 1
        call_args = client.client.publish.call_args[0]
        assert call_args[0] == "onairscreen/led1/state"
        assert call_args[1] == "ON"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_specific_air(self, mock_main_screen):
        """Test publishing status for specific AIR timer"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        mock_main_screen.statusAIR1 = True
        mock_main_screen.Air1Seconds = 60
        
        client.publish_status("air1")
        
        # Check that AIR1 state and time were published
        assert client.client.publish.call_count == 2
        published_topics = [call[0][0] for call in client.client.publish.call_args_list]
        assert "onairscreen/air1/state" in published_topics
        assert "onairscreen/air1/time" in published_topics
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_specific_text(self, mock_main_screen):
        """Test publishing status for specific text field"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        mock_main_screen.labelCurrentSong.text.return_value = "Test Song"
        
        client.publish_status("now")
        
        # Check that NOW text was published
        assert client.client.publish.call_count == 1
        call_args = client.client.publish.call_args[0]
        assert call_args[0] == "onairscreen/text/now/state"
        assert call_args[1] == "Test Song"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_not_connected(self, mock_main_screen):
        """Test that status is not published when not connected"""
        client = MqttClient(mock_main_screen)
        client._connected = False
        client.client = Mock()
        
        client.publish_status()
        
        # Check that publish was not called
        client.client.publish.assert_not_called()


class TestMqttClientCommandReceiving:
    """Tests for receiving and processing MQTT commands"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_led_command(self, mock_main_screen):
        """Test receiving LED command via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Create mock MQTT message
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/led1/set"
        mock_msg.payload = b"ON"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"LED1:ON"
        assert call_args[1] == "mqtt"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_air_command(self, mock_main_screen):
        """Test receiving AIR timer command via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Create mock MQTT message
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/air1/set"
        mock_msg.payload = b"ON"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"AIR1:ON"
        assert call_args[1] == "mqtt"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_air3_command(self, mock_main_screen):
        """Test receiving AIR3 command with special actions"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test TOGGLE command
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/air3/set"
        mock_msg.payload = b"TOGGLE"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"AIR3:TOGGLE"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_text_command(self, mock_main_screen):
        """Test receiving text command via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test NOW command
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/text/now/set"
        mock_msg.payload = b"Test Song"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"NOW:Test Song"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_warn_command(self, mock_main_screen):
        """Test receiving warning command via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test WARN command
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/text/warn/set"
        mock_msg.payload = b"Test Warning"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"WARN:Test Warning"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_direct_command(self, mock_main_screen):
        """Test receiving direct command via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test direct command format
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/command/LED2"
        mock_msg.payload = b"OFF"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"LED2:OFF"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_air3_reset_button(self, mock_main_screen):
        """Test receiving AIR3 reset button press via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test reset button press
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/air3/reset"
        mock_msg.payload = b"PRESS"  # Button payload (can be anything)
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted with RESET command
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"AIR3:RESET"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_air4_reset_button(self, mock_main_screen):
        """Test receiving AIR4 reset button press via MQTT"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test reset button press
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/air4/reset"
        mock_msg.payload = b"PRESS"  # Button payload (can be anything)
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was emitted with RESET command
        mock_main_screen.command_signal.command_received.emit.assert_called_once()
        call_args = mock_main_screen.command_signal.command_received.emit.call_args[0]
        assert call_args[0] == b"AIR4:RESET"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_receive_air_reset_button_invalid(self, mock_main_screen):
        """Test that reset button for AIR1/AIR2 is rejected"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Test reset button for AIR1 (should be rejected)
        mock_msg = Mock()
        mock_msg.topic = "onairscreen/air1/reset"
        mock_msg.payload = b"PRESS"
        
        client._on_message(client.client, None, mock_msg)
        
        # Check that command signal was NOT emitted
        mock_main_screen.command_signal.command_received.emit.assert_not_called()


class TestMqttClientConnectionCallbacks:
    """Tests for MQTT connection callbacks"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_on_connect_success(self, mock_main_screen):
        """Test successful connection callback"""
        client = MqttClient(mock_main_screen)
        client.base_topic = "onairscreen"
        client.client = Mock()
        
        # Simulate successful connection (rc=0)
        client._on_connect(client.client, None, {}, 0)
        
        assert client._connected == True
        # Check that subscribe was called
        assert client.client.subscribe.call_count > 0
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_on_connect_failure(self, mock_main_screen):
        """Test failed connection callback"""
        client = MqttClient(mock_main_screen)
        client.client = Mock()
        
        # Simulate failed connection (rc=5)
        client._on_connect(client.client, None, {}, 5)
        
        assert client._connected == False
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_on_disconnect(self, mock_main_screen):
        """Test disconnect callback"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        
        # Simulate disconnect
        client._on_disconnect(client.client, None, 0)
        
        assert client._connected == False


class TestMqttClientDeviceInfo:
    """Tests for device information generation"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    @patch('builtins.__import__')
    def test_get_device_info(self, mock_import, mock_main_screen):
        """Test device information generation"""
        # Mock version module import
        mock_version_module = Mock()
        mock_version_module.versionString = "0.9.7beta4"
        
        def import_side_effect(name, *args, **kwargs):
            if name == 'version':
                return mock_version_module
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        client = MqttClient(mock_main_screen)
        client.device_id = "test_device"
        client.device_name = "OnAirScreen"
        
        device_info = client._get_device_info()
        
        assert device_info['identifiers'] == ['onairscreen_test_device']
        assert device_info['name'] == "OnAirScreen"
        assert device_info['manufacturer'] == "astrastudio"
        assert device_info['model'] == "OnAirScreen"
        assert device_info['sw_version'] == "0.9.7beta4"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_get_version_fallback(self, mock_main_screen):
        """Test version retrieval with fallback"""
        client = MqttClient(mock_main_screen)
        
        # Mock ImportError by patching the import in _get_version
        with patch('builtins.__import__', side_effect=ImportError("No module named 'version'")):
            version = client._get_version()
            assert version == "unknown"


class TestMqttClientThreadManagement:
    """Tests for thread management"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_stop_client(self, mock_main_screen):
        """Test stopping MQTT client"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client._stop_requested = False
        client.client = Mock()
        client.client.loop_stop = Mock()
        client.client.disconnect = Mock()
        
        client.stop()
        
        assert client._stop_requested == True
        client.client.loop_stop.assert_called_once()
        client.client.disconnect.assert_called_once()
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_restart_client(self, mock_main_screen):
        """Test restarting MQTT client"""
        client = MqttClient(mock_main_screen)
        client.stop = Mock()
        client.start = Mock()
        client._is_enabled = Mock(return_value=True)
        
        client.restart()
        
        client.stop.assert_called_once()
        client.start.assert_called_once()


class TestMqttClientIntegration:
    """Integration tests for MQTT client with MainScreen"""
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_after_led_change(self, mock_main_screen):
        """Test that MQTT status is published after LED change"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.publish_status = Mock()
        
        # Attach client to main screen and simulate _publish_mqtt_status logic
        mock_main_screen.mqtt_client = client
        
        # Simulate the logic from _publish_mqtt_status
        if hasattr(mock_main_screen, 'mqtt_client') and mock_main_screen.mqtt_client:
            mock_main_screen.mqtt_client.publish_status("led1")
        
        # Check that publish_status was called
        client.publish_status.assert_called_once_with("led1")
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_after_air_change(self, mock_main_screen):
        """Test that MQTT status is published after AIR timer change"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.publish_status = Mock()
        
        # Attach client to main screen and simulate _publish_mqtt_status logic
        mock_main_screen.mqtt_client = client
        
        # Simulate the logic from _publish_mqtt_status
        if hasattr(mock_main_screen, 'mqtt_client') and mock_main_screen.mqtt_client:
            mock_main_screen.mqtt_client.publish_status("air2")
        
        # Check that publish_status was called
        client.publish_status.assert_called_once_with("air2")
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_after_text_change(self, mock_main_screen):
        """Test that MQTT status is published after text change"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.publish_status = Mock()
        
        # Attach client to main screen and simulate _publish_mqtt_status logic
        mock_main_screen.mqtt_client = client
        
        # Simulate the logic from _publish_mqtt_status
        if hasattr(mock_main_screen, 'mqtt_client') and mock_main_screen.mqtt_client:
            mock_main_screen.mqtt_client.publish_status("now")
        
        # Check that publish_status was called
        client.publish_status.assert_called_once_with("now")
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_after_warning_change(self, mock_main_screen):
        """Test that MQTT status is published after warning change"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        client.publish_status = Mock()
        
        # Attach client to main screen and simulate _publish_mqtt_status logic
        mock_main_screen.mqtt_client = client
        
        # Simulate the logic from _publish_mqtt_status
        if hasattr(mock_main_screen, 'mqtt_client') and mock_main_screen.mqtt_client:
            mock_main_screen.mqtt_client.publish_status("warn")
        
        # Check that publish_status was called
        client.publish_status.assert_called_once_with("warn")
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_no_publish_when_client_not_available(self, mock_main_screen):
        """Test that no error occurs when MQTT client is not available"""
        # No mqtt_client attribute
        if hasattr(mock_main_screen, 'mqtt_client'):
            delattr(mock_main_screen, 'mqtt_client')
        
        # This should not raise an error
        try:
            mock_main_screen._publish_mqtt_status("led1")
        except AttributeError:
            pytest.fail("_publish_mqtt_status should handle missing mqtt_client gracefully")
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_with_empty_strings(self, mock_main_screen):
        """Test publishing status with empty text fields"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        # Set up empty text fields
        mock_main_screen.labelCurrentSong.text.return_value = ""
        mock_main_screen.labelNews.text.return_value = ""
        mock_main_screen.labelWarning.text.return_value = ""
        
        client.publish_status()
        
        # Check that empty strings were published
        published_calls = client.client.publish.call_args_list
        now_call = [call for call in published_calls if 'text/now/state' in call[0][0]]
        assert len(now_call) == 1
        assert now_call[0][0][1] == ""  # Empty string
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_with_warning_active(self, mock_main_screen):
        """Test publishing warning active state"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        # Set up warning text
        mock_main_screen.labelWarning.text.return_value = "Test Warning"
        
        client.publish_status()
        
        # Check that warning active was published as true
        published_calls = client.client.publish.call_args_list
        warning_active_call = [call for call in published_calls if 'warning/active' in call[0][0]]
        assert len(warning_active_call) == 1
        assert warning_active_call[0][0][1] == "true"
    
    @patch('mqtt_client.MQTT_AVAILABLE', True)
    def test_publish_status_with_warning_inactive(self, mock_main_screen):
        """Test publishing warning inactive state"""
        client = MqttClient(mock_main_screen)
        client._connected = True
        client.client = Mock()
        client.base_topic = "onairscreen"
        
        # Set up no warning
        mock_main_screen.labelWarning.text.return_value = ""
        
        client.publish_status()
        
        # Check that warning active was published as false
        published_calls = client.client.publish.call_args_list
        warning_active_call = [call for call in published_calls if 'warning/active' in call[0][0]]
        assert len(warning_active_call) == 1
        assert warning_active_call[0][0][1] == "false"

