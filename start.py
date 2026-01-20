#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# start.py
# This file is part of OnAirScreen
#
# You may use this file under the terms of the BSD license as follows:
#
# "Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
#
#############################################################################

import argparse
import logging
import re
import sys

from PyQt6.QtCore import Qt, QSettings, QCoreApplication, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QCursor, QPalette, QIcon, QPixmap, QFont, QColor
from PyQt6.QtNetwork import QNetworkInterface
from PyQt6.QtWidgets import QApplication, QWidget, QDialog, QLineEdit, QVBoxLayout, QLabel, QMessageBox

# Import resources FIRST to register them with Qt before UI files are loaded
import resources_rc  # noqa: F401
from mainscreen import Ui_MainScreen
from settings_functions import Settings, versionString, distributionString
from command_handler import CommandHandler
from network import UdpServer, HttpDaemon, WebSocketDaemon
from timer_manager import TimerManager
from event_logger import EventLogger
from warning_manager import WarningManager
from settings_functions import SettingsRestorer
from timer_input import TimerInputDialog
from ntp_manager import NTPManager
from font_loader import load_fonts
from signal_handlers import setup_signal_handlers
from system_operations import SystemOperations
from status_exporter import StatusExporter
from ui_updater import UIUpdater
from hotkey_manager import HotkeyManager
from logging_config import set_log_level, get_command_line_log_level, set_command_line_log_level
from utils import settings_group
from defaults import *  # noqa: F403, F405
from exceptions import WidgetAccessError, log_exception

# Logging will be configured after QApplication initialization and settings loading
logger = logging.getLogger(__name__)


class CommandSignal(QObject):
    """Signal object for thread-safe command execution"""
    command_received = pyqtSignal(bytes, str)


class MainScreen(QWidget, Ui_MainScreen):
    """
    Main application window for OnAirScreen
    
    This class handles the main UI, timer management, LED/AIR controls,
    network communication (UDP/HTTP), and settings management.
    
    The class delegates specific responsibilities to specialized manager classes:
    - NTPManager: NTP time synchronization checking
    - UIUpdater: Periodic UI updates (date, time, backtiming)
    - SystemOperations: System operations (reboot, shutdown, exit)
    - StatusExporter: Status data export for API
    - HotkeyManager: Keyboard shortcut management
    - TimerManager: Timer object management
    - WarningManager: Warning system management
    """
    getTimeWindow: QDialog
    textLocale: str  # for text language
    languages = {"English": 'en_US',
                 "German": 'de_DE',
                 "Dutch": 'nl_NL',
                 "French": 'fr_FR'}

    def __init__(self) -> None:
        """Initialize the main screen and load settings"""
        QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        self.settings = Settings()
        self.restore_settings_from_config()
        
        # Initialize event logger (needed for system operations)
        self.event_logger = EventLogger()
        
        # Initialize system operations (needed for signal connections)
        self.system_operations = SystemOperations(self)
        
        # quit app from settings window
        self.settings.sigExitOAS.connect(self.system_operations.exit_oas)
        self.settings.sigRebootHost.connect(self.system_operations.reboot_host)
        self.settings.sigShutdownHost.connect(self.system_operations.shutdown_host)
        self.settings.sigConfigFinished.connect(self.config_finished)
        self.settings.sigConfigClosed.connect(self.config_closed)
        
        # Store MQTT settings when settings dialog opens to compare on apply
        self._mqtt_settings_before_edit = {}

        # Initialize command handler
        self.command_handler = CommandHandler(self)
        
        # Initialize event logger
        self.event_logger = EventLogger()
        
        # Initialize status exporter
        self.status_exporter = StatusExporter(self)

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('fullscreen', True, type=bool):
                self.showFullScreen()
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
        logger.info(f"Loaded settings from: {settings.fileName()}")

        self.labelWarning.hide()

        # Initialize warning manager
        self.warning_manager = WarningManager(
            self.labelWarning,
            self.labelCurrentSong,
            self.labelNews,
            self.event_logger,
            self._publish_mqtt_status
        )
        # Keep warnings attribute for backward compatibility (used in get_status_json)
        self.warnings = self.warning_manager.warnings

        # Initialize hotkey manager
        self.hotkey_manager = HotkeyManager(self)

        self.statusLED1 = False
        self.statusLED2 = False
        self.statusLED3 = False
        self.statusLED4 = False

        self.LED1on = False
        self.LED2on = False
        self.LED3on = False
        self.LED4on = False

        # Initialize UI updater
        self.ui_updater = UIUpdater(self)
        
        # Setup and start constant update timer
        self.ctimer = QTimer()
        self.ctimer.timeout.connect(self.ui_updater.constant_update)
        self.ctimer.start(100)
        
        # Initialize timer manager
        self.timer_manager = TimerManager(self)
        
        # AIR timer state
        self.Air1Seconds = 0
        self.statusAIR1 = False
        self.Air2Seconds = 0
        self.statusAIR2 = False
        self.Air3Seconds = 0
        self.statusAIR3 = False
        self.radioTimerMode = 0  # count up mode
        self.Air4Seconds = 0
        self.statusAIR4 = False
        self.streamTimerMode = 0  # count up mode
        
        # Expose timer objects for backward compatibility
        self.timerLED1 = self.timer_manager.timerLED1
        self.timerLED2 = self.timer_manager.timerLED2
        self.timerLED3 = self.timer_manager.timerLED3
        self.timerLED4 = self.timer_manager.timerLED4
        self.timerAIR1 = self.timer_manager.timerAIR1
        self.timerAIR2 = self.timer_manager.timerAIR2
        self.timerAIR3 = self.timer_manager.timerAIR3
        self.timerAIR4 = self.timer_manager.timerAIR4

        # Initialize NTP manager
        self.ntp_manager = NTPManager(self)

        self.replacenowTimer = QTimer()
        self.replacenowTimer.timeout.connect(self.replace_now_next)

        # Setup command signal for thread-safe HTTP command execution
        self.command_signal = CommandSignal()
        self.command_signal.command_received.connect(self._parse_cmd_with_source)
        
        # Setup UDP Server with source tracking
        def udp_command_callback(data: bytes) -> None:
            self._parse_cmd_with_source(data, "udp")
        
        self.udp_server = UdpServer(udp_command_callback)

        # Setup HTTP Server with reference to MainScreen for status API and command signal
        self.httpd = HttpDaemon(self, self.command_signal)
        self.httpd.start()
        
        # Setup WebSocket Server for real-time status updates
        self.wsd = WebSocketDaemon(self)
        self.wsd.start()
        
        # Setup MQTT Client
        try:
            from mqtt_client import MqttClient
            self.mqtt_client = MqttClient(self)
            self.mqtt_client.start()
        except Exception as e:
            logger.warning(f"Failed to initialize MQTT client: {e}")
            self.mqtt_client = None
        
        # Log application start
        self.event_logger.log_system_event("Application started")

        # display all host addresses
        self.display_all_hostaddresses()

        # NTP warning is already initialized in NTPManager

        # do initial update check
        self.settings.sigCheckForUpdate.emit()

    def quit_oas(self) -> None:
        """
        Quit the application with cleanup
        
        Stops NTP check thread, HTTP server, and quits the application.
        """
        logger.info("Quitting, cleaning up...")
        self.event_logger.log_system_event("Application quit")
        self.ntp_manager.stop()
        self.httpd.stop()
        if hasattr(self, 'wsd') and self.wsd:
            self.wsd.stop()
        if hasattr(self, 'mqtt_client') and self.mqtt_client:
            self.mqtt_client.stop()
        QCoreApplication.instance().quit()

    def radio_timer_start_stop(self) -> None:
        """
        Start or stop the radio timer (AIR3)
        
        Toggles the radio timer between running and stopped states.
        """
        self.start_stop_air3()

    def radio_timer_reset(self) -> None:
        """Reset radio timer"""
        self._reset_timer('radio', 3)

    def _reset_timer(self, timer_type: str, air_num: int) -> None:
        """
        Generic method to reset timer
        
        Args:
            timer_type: Type of timer ('radio' or 'stream')
            air_num: AIR number (3 or 4)
        """
        if timer_type == 'radio':
            self.reset_air3()
            self.radioTimerMode = 0  # count up mode
        elif timer_type == 'stream':
            self.reset_air4()
            self.streamTimerMode = 0  # count up mode
        else:
            logger.warning(f"Invalid timer type: {timer_type}")

    def radio_timer_set(self, seconds: int) -> None:
        """
        Set radio timer duration in seconds
        
        Args:
            seconds: Timer duration in seconds (0 for count-up mode, >0 for count-down mode)
        """
        self.Air3Seconds = seconds
        if seconds > 0:
            self.radioTimerMode = 1  # count down mode
            mode = "count_down"
        else:
            self.radioTimerMode = 0  # count up mode
            mode = "count_up"
        self.AirLabel_3.setText(f"Timer\n{int(self.Air3Seconds / 60)}:{int(self.Air3Seconds % 60):02d}")
        
        # Log timer set event
        self.event_logger.log_timer_set(3, seconds, mode)

    def get_timer_dialog(self) -> None:
        """
        Generate and display timer input dialog window
        
        Creates a dialog window for entering timer values in formats:
        - "2,10" or "2.10" for 2 minutes 10 seconds
        - "30" for 30 seconds only
        """
        if not hasattr(self, 'timer_input_dialog') or self.timer_input_dialog is None:
            self.timer_input_dialog = TimerInputDialog(self)
            self.timer_input_dialog.timer_set.connect(self.radio_timer_set)
        self.timer_input_dialog.show()

    def stream_timer_start_stop(self) -> None:
        """
        Start or stop the stream timer (AIR4)
        
        Toggles the stream timer between running and stopped states.
        """
        self.start_stop_air4()

    def stream_timer_reset(self) -> None:
        """
        Reset stream timer (AIR4)
        
        Resets the stream timer to 0 and sets it to count-up mode.
        """
        self._reset_timer('stream', 4)

    def _ensure_air_icons_are_set(self) -> None:
        """Helper method to ensure all AIR icons are set correctly"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "AIR"):
            air_configs = [
                (1, 'air1iconpath', ':/mic_icon/images/mic_icon.png'),
                (2, 'air2iconpath', ':/phone_icon/images/phone_icon.png'),
                (3, 'air3iconpath', ':/timer_icon/images/timer_icon.png'),
                (4, 'air4iconpath', ':/stream_icon/images/antenna2.png')
            ]
            for air_num, icon_key, default_path in air_configs:
                icon_path = settings.value(icon_key, default_path)
                if icon_path:
                    pixmap = QPixmap(icon_path)
                    icon_widget = getattr(self, f'AirIcon_{air_num}')
                    icon_widget.setPixmap(pixmap)
                    icon_widget.update()

    def _set_air_state(self, air_num: int, action: bool) -> None:
        """
        Generic method to set AIR state (active/inactive)
        
        Args:
            air_num: AIR number (1-4)
            action: True for active, False for inactive
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        air_configs = {
            1: {
                'label': 'TimerAIR1Text',
                'label_default': 'Mic',
                'icon_key': 'air1iconpath',
                'icon_default': ':/mic_icon/images/mic_icon.png',
                'active_text_color': 'AIR1activetextcolor',
                'active_bg_color': 'AIR1activebgcolor',
                'seconds_attr': 'Air1Seconds',
                'status_attr': 'statusAIR1',
                'timer_attr': 'timerAIR1',
                'label_widget': 'AirLabel_1',
                'icon_widget': 'AirIcon_1',
                'reset_seconds': True
            },
            2: {
                'label': 'TimerAIR2Text',
                'label_default': 'Phone',
                'icon_key': 'air2iconpath',
                'icon_default': ':/phone_icon/images/phone_icon.png',
                'active_text_color': 'AIR2activetextcolor',
                'active_bg_color': 'AIR2activebgcolor',
                'seconds_attr': 'Air2Seconds',
                'status_attr': 'statusAIR2',
                'timer_attr': 'timerAIR2',
                'label_widget': 'AirLabel_2',
                'icon_widget': 'AirIcon_2',
                'reset_seconds': True
            },
            3: {
                'label': 'TimerAIR3Text',
                'label_default': 'Timer',
                'icon_key': 'air3iconpath',
                'icon_default': ':/timer_icon/images/timer_icon.png',
                'active_text_color': 'AIR3activetextcolor',
                'active_bg_color': 'AIR3activebgcolor',
                'seconds_attr': 'Air3Seconds',
                'status_attr': 'statusAIR3',
                'timer_attr': 'timerAIR3',
                'label_widget': 'AirLabel_3',
                'icon_widget': 'AirIcon_3',
                'reset_seconds': False,
                'special_mode': 'radioTimerMode'
            },
            4: {
                'label': 'TimerAIR4Text',
                'label_default': 'Stream',
                'icon_key': 'air4iconpath',
                'icon_default': ':/stream_icon/images/antenna2.png',
                'active_text_color': 'AIR4activetextcolor',
                'active_bg_color': 'AIR4activebgcolor',
                'seconds_attr': 'Air4Seconds',
                'status_attr': 'statusAIR4',
                'timer_attr': 'timerAIR4',
                'label_widget': 'AirLabel_4',
                'icon_widget': 'AirIcon_4',
                'reset_seconds': False,
                'special_mode': 'streamTimerMode'
            }
        }
        
        if air_num not in air_configs:
            logger.warning(f"Invalid AIR number: {air_num}, must be 1-4")
            return
        
        config = air_configs[air_num]
        label_widget = getattr(self, config['label_widget'])
        icon_widget = getattr(self, config['icon_widget'])
        seconds_attr = config['seconds_attr']
        status_attr = config['status_attr']
        timer_attr = config['timer_attr']
        
        if action:
            with settings_group(settings, "Timers"):
                if config.get('reset_seconds', False):
                    setattr(self, seconds_attr, 0)
                
                # Set active styles
                active_text_color = settings.value(config['active_text_color'], DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR)
                active_bg_color = settings.value(config['active_bg_color'], DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR)
                label_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
                
                # Set icon with active styles
                with settings_group(settings, "AIR"):
                    icon_path = settings.value(config['icon_key'], config['icon_default'])
                    if icon_path:
                        pixmap = QPixmap(icon_path)
                        icon_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
                        icon_widget.setPixmap(pixmap)
                        icon_widget.update()
                
                # Set label text
                label_text = settings.value(config['label'], config['label_default'])
                seconds = getattr(self, seconds_attr)
                label_widget.setText(f"{label_text}\n{int(seconds/60)}:{seconds%60:02d}")
                
                # Set status and start timer
                setattr(self, status_attr, True)
                timer = getattr(self, timer_attr)
                timer.start(1000)
                
                # Log AIR started event
                self.event_logger.log_air_started(air_num, "manual")
                
                # Publish MQTT status immediately after AIR start
                self._publish_mqtt_status(f"air{air_num}")
                
                # Special handling for AIR3 and AIR4 countdown mode
                if 'special_mode' in config:
                    mode_attr = config['special_mode']
                    mode = getattr(self, mode_attr, 0)
                    if mode == 1 and seconds > 1:
                        update_method = getattr(self, f'update_air{air_num}_seconds')
                        update_method()
        else:
            with settings_group(settings, "LEDS"):
                inactive_text_color = settings.value('inactivetextcolor', '#555555')
                inactive_bg_color = settings.value('inactivebgcolor', '#222222')
                
                # Save icon before setStyleSheet to prevent flickering
                with settings_group(settings, "AIR"):
                    icon_path = settings.value(config['icon_key'], config['icon_default'])
                    icon_pixmap = QPixmap(icon_path) if icon_path else None
                
                # Set inactive styles
                label_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
                icon_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
            
            # Restore icon immediately after styleSheet change to prevent flickering
            if icon_pixmap and not icon_pixmap.isNull():
                icon_widget.setPixmap(icon_pixmap)
                icon_widget.update()
            
            # Set status and stop timer
            setattr(self, status_attr, False)
            timer = getattr(self, timer_attr)
            timer.stop()
            
            # Log AIR stopped event
            self.event_logger.log_air_stopped(air_num, "manual")
        
        # Publish MQTT status immediately after AIR state change
        self._publish_mqtt_status(f"air{air_num}")

    def _update_air_seconds(self, air_num: int) -> None:
        """
        Generic method to update AIR seconds display
        
        Args:
            air_num: AIR number (1-4)
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        
        air_configs = {
            1: {'label': 'TimerAIR1Text', 'label_default': 'Mic', 'seconds_attr': 'Air1Seconds', 'label_widget': 'AirLabel_1'},
            2: {'label': 'TimerAIR2Text', 'label_default': 'Phone', 'seconds_attr': 'Air2Seconds', 'label_widget': 'AirLabel_2'},
            3: {'label': 'TimerAIR3Text', 'label_default': 'Timer', 'seconds_attr': 'Air3Seconds', 'label_widget': 'AirLabel_3', 'mode_attr': 'radioTimerMode'},
            4: {'label': 'TimerAIR4Text', 'label_default': 'Stream', 'seconds_attr': 'Air4Seconds', 'label_widget': 'AirLabel_4', 'mode_attr': 'streamTimerMode'}
        }
        
        config = air_configs[air_num]
        seconds_attr = config['seconds_attr']
        label_widget = getattr(self, config['label_widget'])
        
        # Handle countdown mode for AIR3 and AIR4
        if 'mode_attr' in config:
            mode_attr = config['mode_attr']
            mode = getattr(self, mode_attr, 0)
            if mode == 0:  # count up mode
                setattr(self, seconds_attr, getattr(self, seconds_attr) + 1)
            else:  # countdown mode
                current_seconds = getattr(self, seconds_attr)
                setattr(self, seconds_attr, current_seconds - 1)
                if getattr(self, seconds_attr) < 1:
                    stop_method = getattr(self, f'stop_air{air_num}')
                    stop_method()
                    # Reset the correct mode attribute
                    setattr(self, mode_attr, 0)
        else:
            # Simple count up for AIR1 and AIR2
            setattr(self, seconds_attr, getattr(self, seconds_attr) + 1)
        
        # Update label text
        with settings_group(settings, "Timers"):
            label_text = settings.value(config['label'], config['label_default'])
            seconds = getattr(self, seconds_attr)
            label_widget.setText(f"{label_text}\n{int(seconds/60)}:{seconds%60:02d}")

    def show_settings(self) -> None:
        """
        Show settings dialog window
        
        Restores mouse cursor, ensures AIR icons are set, and displays settings window.
        """
        global app
        # un-hide mouse cursor
        app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
        # Set icons BEFORE opening dialog to prevent flickering
        self._ensure_air_icons_are_set()
        self.settings.show_settings()

    def display_all_hostaddresses(self) -> None:
        """
        Display all local network IP addresses in NOW and NEXT text fields
        
        Retrieves all non-loopback IPv4 and IPv6 addresses from network interfaces
        and displays them in the UI. Starts a timer to replace with configured text
        after 10 seconds if replacenow setting is enabled.
        """
        v4addrs = list()
        v6addrs = list()
        
        # Get all network interfaces
        for interface in QNetworkInterface.allInterfaces():
            # Skip loopback interfaces
            if interface.flags() & QNetworkInterface.InterfaceFlag.IsLoopBack:
                continue
            
            # Get all address entries for this interface
            for entry in interface.addressEntries():
                address = entry.ip()
                addr_str = address.toString()
                
                # Check if it's IPv4 or IPv6 using toIPv4Address/toIPv6Address
                # Both methods return a tuple: (address_value, is_valid) for IPv4, (16 bytes) for IPv6
                ipv4_result = address.toIPv4Address()
                ipv6_result = address.toIPv6Address()
                
                if len(ipv4_result) == 2 and ipv4_result[1]:  # IPv4 and valid
                    # Skip localhost addresses
                    if not addr_str.startswith('127.'):
                        v4addrs.append(addr_str)
                elif len(ipv6_result) == 16:  # IPv6 (returns 16-byte tuple)
                    # Skip IPv6 localhost (::1) and link-local addresses (fe80::)
                    if addr_str != '::1' and not addr_str.startswith('fe80::'):
                        v6addrs.append(addr_str)

        self.set_current_song_text(", ".join([str(addr) for addr in v4addrs]))
        self.set_news_text(", ".join([str(addr) for addr in v6addrs]))

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('replacenow', True, type=bool):
                self.replacenowTimer.setSingleShot(True)
                self.replacenowTimer.start(10000)

    def _parse_cmd_with_source(self, data: bytes, source: str = "udp") -> None:
        """
        Parse and execute a command with source tracking
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            source: Source of command ('udp' or 'http')
        """
        try:
            command_str = data.decode('utf-8') if isinstance(data, bytes) else str(data)
            if ':' in command_str:
                command, value = command_str.split(':', 1)
                # Log command received event with source
                self.event_logger.log_command_received(command, value, source)
        except (UnicodeDecodeError, ValueError, AttributeError):
            pass
        
        # Forward to actual command handler
        self.command_handler.parse_cmd(data if isinstance(data, bytes) else data.encode())
    
    def parse_cmd(self, data: bytes) -> bool:
        """
        Parse and execute a command from UDP/HTTP input
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            
        Returns:
            True if command was parsed successfully, False otherwise
        """
        # Default to unknown source for backward compatibility
        self._parse_cmd_with_source(data, "unknown")
        return True


    def manual_toggle_led1(self) -> None:
        """Toggle LED1 using led_logic (manual toggle)"""
        self._manual_toggle_led(1)

    def manual_toggle_led2(self) -> None:
        """Toggle LED2 using led_logic (manual toggle)"""
        self._manual_toggle_led(2)

    def manual_toggle_led3(self) -> None:
        """Toggle LED3 using led_logic (manual toggle)"""
        self._manual_toggle_led(3)

    def manual_toggle_led4(self) -> None:
        """Toggle LED4 using led_logic (manual toggle)"""
        self._manual_toggle_led(4)

    def _manual_toggle_led(self, led_num: int) -> None:
        """Generic method to toggle LED using led_logic"""
        led_on_attr = f'LED{led_num}on'
        current_state = getattr(self, led_on_attr, False)
        self.led_logic(led_num, not current_state)

    def toggle_led1(self) -> None:
        """Toggle LED1 using set_led1"""
        self._toggle_led(1)

    def toggle_led2(self) -> None:
        """Toggle LED2 using set_led2"""
        self._toggle_led(2)

    def toggle_led3(self) -> None:
        """Toggle LED3 using set_led3"""
        self._toggle_led(3)

    def toggle_led4(self) -> None:
        """Toggle LED4 using set_led4"""
        self._toggle_led(4)

    def _toggle_led(self, led_num: int) -> None:
        """Generic method to toggle LED using led_logic"""
        # Use LED{num}on for logical status, not statusLED{num} which is the visual blinking state
        led_on_attr = f'LED{led_num}on'
        current_state = getattr(self, led_on_attr, False)
        self.led_logic(led_num, not current_state)

    def toggle_air1(self) -> None:
        """Toggle AIR1"""
        self._toggle_air(1)

    def toggle_air2(self) -> None:
        """Toggle AIR2"""
        self._toggle_air(2)

    def toggle_air4(self) -> None:
        """Toggle AIR4"""
        self._toggle_air(4)

    def _toggle_air(self, air_num: int) -> None:
        """Generic method to toggle AIR"""
        status_attr = f'statusAIR{air_num}'
        current_state = getattr(self, status_attr, False)
        set_air_method = getattr(self, f'set_air{air_num}')
        set_air_method(not current_state)

    def display_ips(self) -> None:
        """Display all host IP addresses"""
        self.display_all_hostaddresses()
        self.replacenowTimer.setSingleShot(True)
        self.replacenowTimer.start(10000)

    def unset_led1(self) -> None:
        """Turn off LED1"""
        self._unset_led(1)

    def unset_led2(self) -> None:
        """Turn off LED2"""
        self._unset_led(2)

    def unset_led3(self) -> None:
        """Turn off LED3"""
        self._unset_led(3)

    def unset_led4(self) -> None:
        """Turn off LED4"""
        self._unset_led(4)

    def _unset_led(self, led_num: int) -> None:
        """Generic method to turn off LED"""
        self.led_logic(led_num, False)

    def led_logic(self, led: int, state: bool) -> None:
        """
        Handle LED logic (on/off, autoflash, timedflash)
        
        Args:
            led: LED number (1-4)
            state: True to turn on, False to turn off
        """
        if led < 1 or led > 4:
            logger.warning(f"Invalid LED number: {led}")
            return
        
        # Get LED-specific attributes
        timer_attr = f'timerLED{led}'
        set_led_attr = f'set_led{led}'
        unset_led_attr = f'unset_led{led}'
        led_on_attr = f'LED{led}on'
        autoflash_attr = f'LED{led}Autoflash'
        timedflash_attr = f'LED{led}Timedflash'
        
        # Determine source for logging
        source = "manual"
        if state:
            timer = getattr(self, timer_attr)
            autoflash = getattr(self.settings, autoflash_attr)
            timedflash = getattr(self.settings, timedflash_attr)
            
            if autoflash.isChecked() and timer.isActive():
                source = "autoflash"
            elif timedflash.isChecked():
                source = "timedflash"
        
        if state:
            # Turn LED on
            timer = getattr(self, timer_attr)
            autoflash = getattr(self.settings, autoflash_attr)
            timedflash = getattr(self.settings, timedflash_attr)
            
            if autoflash.isChecked():
                timer.start(500)
            if timedflash.isChecked():
                timer.start(500)
                QTimer.singleShot(20000, getattr(self, unset_led_attr))
            
            set_led_method = getattr(self, set_led_attr)
            set_led_method(state)
            setattr(self, led_on_attr, state)
        else:
            # Turn LED off
            set_led_method = getattr(self, set_led_attr)
            set_led_method(state)
            timer = getattr(self, timer_attr)
            timer.stop()
            setattr(self, led_on_attr, state)
        
        # Log LED change event
        self.event_logger.log_led_changed(led, state, source)
        
        # Publish MQTT status immediately after LED change
        self._publish_mqtt_status(f"led{led}")
        
        # Broadcast WebSocket status immediately after LED change
        self._broadcast_web_status()

    def set_station_color(self, newcolor: QColor) -> None:
        """
        Set the station label color
        
        Args:
            newcolor: QColor object for the station name label
        """
        self._set_label_color(self.labelStation, newcolor)

    def set_slogan_color(self, newcolor: QColor) -> None:
        """
        Set the slogan label color
        
        Args:
            newcolor: QColor object for the slogan label
        """
        self._set_label_color(self.labelSlogan, newcolor)

    def _set_label_color(self, widget: QLabel, color: QColor) -> None:
        """
        Generic method to set label color
        
        Args:
            widget: The label widget to set color for
            color: QColor object to set as text color
        """
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.WindowText, color)
        widget.setPalette(palette)

    def restore_settings_from_config(self) -> None:
        """Restore all settings from configuration"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings_restorer = SettingsRestorer(self, self.settings)
        settings_restorer.restore_all(settings)

    def constant_update(self):
        """Slot for constant timer timeout - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.constant_update()
        except (AttributeError, RuntimeError):
            # Fallback if ui_updater not yet initialized
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.constant_update()

    def update_date(self):
        """Update the date display - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.update_date()
        except (AttributeError, RuntimeError):
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.update_date()

    def update_backtiming_text(self) -> None:
        """Update the text clock display - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.update_backtiming_text()
        except (AttributeError, RuntimeError):
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.update_backtiming_text()

    def update_backtiming_seconds(self):
        """Update backtiming seconds - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.update_backtiming_seconds()
        except (AttributeError, RuntimeError):
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.update_backtiming_seconds()

    def update_ntp_status(self):
        """Update NTP status warning (priority -1)"""
        try:
            if self.ntp_manager:
                self.ntp_manager.update_ntp_status()
        except (AttributeError, RuntimeError):
            # Fallback if ntp_manager not yet initialized
            from ntp_manager import NTPManager
            self.ntp_manager = NTPManager(self)
            self.ntp_manager.update_ntp_status()

    def toggle_full_screen(self):
        global app
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if not settings.value('fullscreen', True, type=bool):
                self.showFullScreen()
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
                settings.setValue('fullscreen', True)
            else:
                self.showNormal()
                app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
                settings.setValue('fullscreen', False)

    def set_air1(self, action: bool) -> None:
        """Set AIR1 state (active/inactive)"""
        self._set_air_state(1, action)

    def update_air1_seconds(self) -> None:
        """Update AIR1 seconds display"""
        self._update_air_seconds(1)

    def set_air2(self, action: bool) -> None:
        """Set AIR2 state (active/inactive)"""
        self._set_air_state(2, action)

    def update_air2_seconds(self) -> None:
        """Update AIR2 seconds display"""
        self._update_air_seconds(2)

    def reset_air3(self) -> None:
        """Reset AIR3 timer"""
        self._reset_air(3)

    def _reset_air(self, air_num: int) -> None:
        """
        Generic method to reset AIR timer
        
        Args:
            air_num: AIR number (3 or 4)
        """
        if air_num not in [3, 4]:
            logger.warning(f"Invalid AIR number for reset: {air_num}")
            return
        
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Timers"):
            timer_attr = f'timerAIR{air_num}'
            seconds_attr = f'Air{air_num}Seconds'
            status_attr = f'statusAIR{air_num}'
            label_attr = f'AirLabel_{air_num}'
            
            default_texts = {3: 'Timer', 4: 'Stream'}
            text_key = f'TimerAIR{air_num}Text'
            
            timer = getattr(self, timer_attr)
            timer.stop()
            setattr(self, seconds_attr, 0)
            
            label_text = settings.value(text_key, default_texts[air_num])
            label_widget = getattr(self, label_attr)
            seconds = getattr(self, seconds_attr)
            label_widget.setText(f"{label_text}\n{int(seconds/60)}:{seconds%60:02d}")
            
            # Log AIR reset event
            self.event_logger.log_air_reset(air_num, "manual")
            
            if getattr(self, status_attr):
                timer.start(1000)

    def set_air3(self, action: bool) -> None:
        """Set AIR3 state (active/inactive)"""
        self._set_air_state(3, action)

    def start_stop_air3(self) -> None:
        """Toggle AIR3 start/stop"""
        self._start_stop_air(3)

    def _start_stop_air(self, air_num: int) -> None:
        """
        Generic method to toggle AIR start/stop
        
        Args:
            air_num: AIR number (3 or 4)
        """
        if air_num not in [3, 4]:
            logger.warning(f"Invalid AIR number for start_stop: {air_num}")
            return
        
        status_attr = f'statusAIR{air_num}'
        current_state = getattr(self, status_attr, False)
        
        if not current_state:
            getattr(self, f'start_air{air_num}')()
        else:
            getattr(self, f'stop_air{air_num}')()

    def start_air3(self) -> None:
        """Start AIR3"""
        self.set_air3(True)

    def stop_air3(self) -> None:
        """Stop AIR3"""
        self.set_air3(False)

    def update_air3_seconds(self) -> None:
        """Update AIR3 seconds display"""
        self._update_air_seconds(3)

    def reset_air4(self) -> None:
        """Reset AIR4 timer"""
        self._reset_air(4)

    def set_air4(self, action: bool) -> None:
        """Set AIR4 state (active/inactive)"""
        self._set_air_state(4, action)

    def start_stop_air4(self) -> None:
        """Toggle AIR4 start/stop"""
        self._start_stop_air(4)

    def start_air4(self) -> None:
        """Start AIR4"""
        self.set_air4(True)

    def stop_air4(self) -> None:
        """Stop AIR4"""
        self.set_air4(False)

    def update_air4_seconds(self) -> None:
        """Update AIR4 seconds display"""
        self._update_air_seconds(4)

    def replace_now_next(self) -> None:
        """
        Replace NOW and NEXT text fields with configured replacement text
        
        Called by timer after displaying IP addresses. Replaces NOW field with
        configured replacement text and clears NEXT field.
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            self.set_current_song_text(settings.value('replacenowtext', DEFAULT_REPLACE_NOW_TEXT))
            self.set_news_text("")

    def trigger_ntp_check(self) -> None:
        """
        Trigger NTP offset check
        
        Checks if NTP checking is enabled and triggers NTP offset check.
        """
        try:
            if self.ntp_manager:
                self.ntp_manager.trigger_ntp_check()
        except (AttributeError, RuntimeError):
            # Fallback if ntp_manager not yet initialized
            from ntp_manager import NTPManager
            self.ntp_manager = NTPManager(self)
            self.ntp_manager.trigger_ntp_check()

    def set_led1(self, action: bool) -> None:
        """Set LED1 state (active/inactive)"""
        self._set_led(1, action)

    def set_led2(self, action: bool) -> None:
        """Set LED2 state (active/inactive)"""
        self._set_led(2, action)

    def set_led3(self, action: bool) -> None:
        """Set LED3 state (active/inactive)"""
        self._set_led(3, action)

    def set_led4(self, action: bool) -> None:
        """Set LED4 state (active/inactive)"""
        self._set_led(4, action)

    def _set_led(self, led_num: int, action: bool) -> None:
        """
        Generic method to set LED state (active/inactive)
        
        Args:
            led_num: LED number (1-4)
            action: True for active, False for inactive
        """
        if led_num < 1 or led_num > 4:
            logger.warning(f"Invalid LED number: {led_num}")
            return
        
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        button_widget = getattr(self, f'buttonLED{led_num}')
        status_attr = f'statusLED{led_num}'
        
        # Default active background colors for each LED
        default_active_colors = {
            1: '#FF0000',  # Red
            2: '#DCDC00',  # Yellow
            3: '#00C8C8',  # Cyan
            4: '#FF00FF',  # Magenta
        }
        
        if action:
            with settings_group(settings, f"LED{led_num}"):
                active_text_color = settings.value('activetextcolor', DEFAULT_LED_ACTIVE_TEXT_COLOR)
                active_bg_color = settings.value('activebgcolor', default_active_colors[led_num])
                button_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
            setattr(self, status_attr, True)
        else:
            with settings_group(settings, "LEDS"):
                inactive_text_color = settings.value('inactivetextcolor', DEFAULT_LED_INACTIVE_TEXT_COLOR)
                inactive_bg_color = settings.value('inactivebgcolor', DEFAULT_LED_INACTIVE_BG_COLOR)
                button_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
            setattr(self, status_attr, False)

    def set_station(self, text: str) -> None:
        """Set station name text"""
        self._set_text('labelStation', text)

    def set_slogan(self, text: str) -> None:
        """Set slogan text"""
        self._set_text('labelSlogan', text)

    def set_left_text(self, text: str) -> None:
        """Set left text label"""
        self._set_text('labelTextLeft', text)

    def set_right_text(self, text: str) -> None:
        """Set right text label"""
        self._set_text('labelTextRight', text)

    def set_led1_text(self, text: str) -> None:
        """Set LED1 button text"""
        self._set_text('buttonLED1', text)

    def set_led2_text(self, text: str) -> None:
        """Set LED2 button text"""
        self._set_text('buttonLED2', text)

    def set_led3_text(self, text: str) -> None:
        """Set LED3 button text"""
        self._set_text('buttonLED3', text)

    def set_led4_text(self, text: str) -> None:
        """Set LED4 button text"""
        self._set_text('buttonLED4', text)

    def set_current_song_text(self, text: str) -> None:
        """Set current song text"""
        self._set_text('labelCurrentSong', text)
        # Publish MQTT status immediately after NOW text change
        self._publish_mqtt_status("now")

    def set_news_text(self, text: str) -> None:
        """Set news text"""
        self._set_text('labelNews', text)
        # Publish MQTT status immediately after NEXT text change
        self._publish_mqtt_status("next")

    def _publish_mqtt_status(self, specific_item: str | None = None) -> None:
        """
        Publish MQTT status immediately after status change
        
        Args:
            specific_item: Optional specific item to publish (e.g., 'led1', 'air2', 'now', 'next', 'warn')
                          If None, publishes all status items
        """
        try:
            mqtt_client = getattr(self, 'mqtt_client', None)
            if mqtt_client:
                try:
                    mqtt_client.publish_status(specific_item)
                except Exception as e:
                    logger.warning(f"Failed to publish MQTT status: {e}")
        except (RuntimeError, AttributeError) as e:
            # Ignore errors when object is not fully initialized (e.g., in tests)
            # Log but don't raise - this is expected in test scenarios
            error = WidgetAccessError(
                f"Error accessing MQTT client (object may not be initialized): {e}",
                widget_name="mqtt_client",
                attribute="publish_status"
            )
            log_exception(logger, error, use_exc_info=False)
            pass
    
    def _broadcast_web_status(self) -> None:
        """
        Broadcast WebSocket status immediately after status change
        
        Triggers immediate status update to all connected WebSocket clients
        instead of waiting for the periodic broadcast.
        """
        try:
            wsd = getattr(self, 'wsd', None)
            if wsd:
                try:
                    wsd.broadcast_status()
                except Exception as e:
                    logger.warning(f"Failed to broadcast WebSocket status: {e}")
        except (RuntimeError, AttributeError) as e:
            # Ignore errors when object is not fully initialized (e.g., in tests)
            # Log but don't raise - this is expected in test scenarios
            error = WidgetAccessError(
                f"Error accessing WebSocket daemon (object may not be initialized): {e}",
                widget_name="wsd",
                attribute="broadcast_status"
            )
            log_exception(logger, error, use_exc_info=False)
            pass

    def _set_text(self, widget_name: str, text: str) -> None:
        """
        Generic method to set text on a widget
        
        Args:
            widget_name: Name of the widget attribute
            text: Text to set
        """
        widget = getattr(self, widget_name, None)
        if widget:
            widget.setText(text)
        else:
            logger.warning(f"Widget '{widget_name}' not found for set_text")

    def set_backtiming_secs(self, value: int) -> None:
        """
        Set backtiming seconds (currently not implemented)
        
        Args:
            value: Seconds value (not currently used)
        """
        pass
        # self.labelSeconds.setText( str(value) )

    def add_warning(self, text: str, priority: int = 0) -> None:
        """
        Add a warning message to the warning system
        
        Args:
            text: Warning message text
            priority: Warning priority level (-1=NTP, 0=normal/legacy, 1=medium, 2=high, default: 0)
        """
        self.warning_manager.add_warning(text, priority)

    def remove_warning(self, priority: int = 0) -> None:
        """
        Remove warning message from the warning system
        
        Args:
            priority: Warning priority level (-1=NTP, 0=normal/legacy, 1=medium, 2=high, default: 0)
        """
        self.warning_manager.remove_warning(priority)

    def process_warnings(self) -> None:
        """
        Process all warnings and display the highest priority warning
        
        Checks all warning priority levels and displays the highest priority
        warning found (excluding NTP warnings if other warnings exist),
        or hides the warning label if no warnings are present.
        
        Priority order: 2 (high) > 1 (medium) > 0 (normal) > -1 (NTP)
        NTP warnings are only shown if no other warnings exist.
        """
        self.warning_manager.process_warnings()

    def show_warning(self, text: str) -> None:
        """
        Show warning message in the UI
        
        Hides current song and news labels and displays warning text with large font.
        
        Args:
            text: Warning message text to display
        """
        self.warning_manager.show_warning(text)

    def hide_warning(self, priority: int = 0) -> None:
        """
        Hide warning message and restore normal UI
        
        Args:
            priority: Warning priority level (0-2, default: 0, currently unused)
        """
        self.warning_manager.hide_warning(priority)

    def config_closed(self) -> None:
        """
        Handle settings window closed event
        
        Restores mouse cursor state and ensures AIR icons are set correctly.
        """
        global app
        # hide mouse cursor if in fullscreen mode
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('fullscreen', True, type=bool):
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
        # Ensure icons are still set after dialog is closed
        self._ensure_air_icons_are_set()

    def config_finished(self) -> None:
        """
        Handle settings applied event
        
        Restores settings from configuration, updates weather widget config,
        and triggers weather update.
        """
        # IMPORTANT: Check command-line log level FIRST, before restoring settings
        # Command-line log level ALWAYS overrides settings and must not be changed
        import sys as sys_module
        
        # If command-line log level is set, use it and ignore settings completely
        # This check MUST happen BEFORE restoring settings to prevent settings from overriding
        command_line_log_level = get_command_line_log_level()
        if command_line_log_level is not None:
            # Command-line log level always overrides settings - do not change it
            log_level = command_line_log_level
            set_log_level(log_level)
            # Always print log level change, regardless of current log level
            print(f"Log level (from command-line, ignoring settings): {log_level}", file=sys_module.stderr)
            # Restore other settings (but keep command-line log level - do NOT read log level from settings)
            self.restore_settings_from_config()
            self.weatherWidget.readConfig()
            self.weatherWidget.updateWeather()
            # Note: We do NOT read or apply log level from settings when command-line level is set
        else:
            # No command-line level set, restore all settings including log level
            self.restore_settings_from_config()
            self.weatherWidget.readConfig()
            self.weatherWidget.updateWeather()
            
            # Apply log level from settings
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "General"):
                log_level = settings.value('loglevel', DEFAULT_LOG_LEVEL, type=str)
            set_log_level(log_level)
            # Always print log level change, regardless of current log level
            print(f"Log level updated to: {log_level}", file=sys_module.stderr)
        
        # Always restart MQTT client when settings are applied (applySettings was called)
        # The client will check if settings changed and only reconnect if needed
        if hasattr(self, 'mqtt_client') and self.mqtt_client:
            logger.debug("Settings applied, restarting MQTT client to apply any changes...")
            self.mqtt_client.restart()

    def reboot_host(self):
        """Reboot the host system safely using subprocess"""
        self.system_operations.reboot_host()

    def shutdown_host(self):
        """Shutdown the host system safely using subprocess"""
        self.system_operations.shutdown_host()

    def get_status_json(self) -> dict:
        """
        Get current status as JSON-serializable dictionary
        
        Returns:
            Dictionary containing current LED, AIR timer status, and text fields
        """
        try:
            if self.status_exporter:
                return self.status_exporter.get_status_json()
        except (AttributeError, RuntimeError):
            # Fallback if status_exporter not yet initialized
            from status_exporter import StatusExporter
            self.status_exporter = StatusExporter(self)
            return self.status_exporter.get_status_json()
    
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            if hasattr(self, 'httpd') and self.httpd:
                self.httpd.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping HTTP daemon: {e}")
                log_exception(logger, error)
        
        try:
            if hasattr(self, 'wsd') and self.wsd:
                self.wsd.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping WebSocket daemon: {e}")
                log_exception(logger, error)
        
        try:
            if hasattr(self, 'ntp_manager') and self.ntp_manager:
                self.ntp_manager.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping NTP check: {e}")
                log_exception(logger, error)


###################################
# App Init
###################################
if __name__ == "__main__":
    setup_signal_handlers()
    
    # Parse command-line arguments before QApplication initialization
    parser = argparse.ArgumentParser(description='OnAirScreen')
    parser.add_argument('-l', '--loglevel', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set log level (overrides settings, but does not save)')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    
    # Initialize logging: load from settings first, then override with command-line if provided
    settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
    with settings_group(settings, "General"):
        log_level = settings.value('loglevel', DEFAULT_LOG_LEVEL, type=str)
    
    # Command-line argument overrides settings (temporarily, not saved)
    if args.loglevel:
        # Set module-level variable to remember command-line log level (for settings dialog)
        set_command_line_log_level(args.loglevel)
        log_level = args.loglevel
    else:
        # Clear command-line log level
        set_command_line_log_level(None)
    
    # Configure logging with determined level
    set_log_level(log_level)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Always print log level change, regardless of current log level
    print(f"Log level set to: {log_level}", file=sys.stderr)
    
    # Load fonts from fonts/ directory before creating UI
    load_fonts()
    
    icon = QIcon()
    icon.addPixmap(QPixmap(":/oas_icon/images/oas_icon.png"), QIcon.Mode.Normal, QIcon.State.Off)
    app.setWindowIcon(icon)

    timer = QTimer()
    timer.start(100)
    timer.timeout.connect(lambda: None)

    main_screen = MainScreen()
    main_screen.setWindowIcon(icon)

    for i in range(1, 5):
        main_screen.led_logic(i, False)
        main_screen._set_air_state(i, False)

    main_screen.show()

    sys.exit(app.exec())
