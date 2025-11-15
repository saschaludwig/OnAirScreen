#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
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

import logging
import os
import re
import signal
import socket
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote_plus

import ntplib
from PyQt6.QtCore import Qt, QSettings, QCoreApplication, QTimer, QDate, QLocale, QThread
from PyQt6.QtGui import QCursor, QPalette, QKeySequence, QIcon, QPixmap, QFont, QShortcut, QFontDatabase
from PyQt6.QtNetwork import QUdpSocket, QNetworkInterface, QHostAddress
from PyQt6.QtWidgets import QApplication, QWidget, QDialog, QLineEdit, QVBoxLayout, QLabel, QMessageBox

# Import resources FIRST to register them with Qt before UI files are loaded
import resources_rc  # noqa: F401
from mainscreen import Ui_MainScreen
from settings_functions import Settings, versionString

HOST = '0.0.0.0'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MainScreen(QWidget, Ui_MainScreen):
    """
    Main application window for OnAirScreen
    
    This class handles the main UI, timer management, LED/AIR controls,
    network communication (UDP/HTTP), and settings management.
    """
    getTimeWindow: QDialog
    ntpHadWarning: bool
    ntpWarnMessage: str
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
        # quit app from settings window
        self.settings.sigExitOAS.connect(self.exit_oas)
        self.settings.sigRebootHost.connect(self.reboot_host)
        self.settings.sigShutdownHost.connect(self.shutdown_host)
        self.settings.sigConfigFinished.connect(self.config_finished)
        self.settings.sigConfigClosed.connect(self.config_closed)

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True, type=bool):
            self.showFullScreen()
            app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
        settings.endGroup()
        logger.info(f"Loaded settings from: {settings.fileName()}")

        self.labelWarning.hide()

        # init warning prio array (0-2
        self.warnings = ["", "", ""]

        # add hotkey bindings
        QShortcut(QKeySequence("Ctrl+F"), self, self.toggle_full_screen)
        QShortcut(QKeySequence("F"), self, self.toggle_full_screen)
        QShortcut(QKeySequence(16777429), self, self.toggle_full_screen)  # 'Display' Key on OAS USB Keyboard
        QShortcut(QKeySequence(16777379), self, self.shutdown_host)  # 'Calculator' Key on OAS USB Keyboard
        QShortcut(QKeySequence("Ctrl+Q"), self, self.quit_oas)
        QShortcut(QKeySequence("Q"), self, self.quit_oas)
        QShortcut(QKeySequence("Ctrl+C"), self, self.quit_oas)
        QShortcut(QKeySequence("ESC"), self, self.quit_oas)
        QShortcut(QKeySequence("Ctrl+S"), self, self.show_settings)
        QShortcut(QKeySequence("Ctrl+,"), self, self.show_settings)
        QShortcut(QKeySequence(" "), self, self.radio_timer_start_stop)
        QShortcut(QKeySequence(","), self, self.radio_timer_start_stop)
        QShortcut(QKeySequence("."), self, self.radio_timer_start_stop)
        QShortcut(QKeySequence("0"), self, self.radio_timer_reset)
        QShortcut(QKeySequence("R"), self, self.radio_timer_reset)
        QShortcut(QKeySequence("1"), self, self.manual_toggle_led1)
        QShortcut(QKeySequence("2"), self, self.manual_toggle_led2)
        QShortcut(QKeySequence("3"), self, self.manual_toggle_led3)
        QShortcut(QKeySequence("4"), self, self.manual_toggle_led4)
        QShortcut(QKeySequence("M"), self, self.toggle_air1)
        QShortcut(QKeySequence("/"), self, self.toggle_air1)
        QShortcut(QKeySequence("P"), self, self.toggle_air2)
        QShortcut(QKeySequence("*"), self, self.toggle_air2)
        QShortcut(QKeySequence("S"), self, self.toggle_air4)
        QShortcut(QKeySequence("I"), self, self.display_ips)
        QShortcut(QKeySequence("Alt+S"), self, self.stream_timer_reset)

        QShortcut(QKeySequence("Enter"), self, self.get_timer_dialog)
        QShortcut(QKeySequence("Return"), self, self.get_timer_dialog)

        self.statusLED1 = False
        self.statusLED2 = False
        self.statusLED3 = False
        self.statusLED4 = False

        self.LED1on = False
        self.LED2on = False
        self.LED3on = False
        self.LED4on = False

        # Setup and start timers
        self.ctimer = QTimer()
        self.ctimer.timeout.connect(self.constant_update)
        self.ctimer.start(100)
        # LED timers
        self.timerLED1 = QTimer()
        self.timerLED1.timeout.connect(self.toggle_led1)
        self.timerLED2 = QTimer()
        self.timerLED2.timeout.connect(self.toggle_led2)
        self.timerLED3 = QTimer()
        self.timerLED3.timeout.connect(self.toggle_led3)
        self.timerLED4 = QTimer()
        self.timerLED4.timeout.connect(self.toggle_led4)

        # Setup OnAir Timers
        self.timerAIR1 = QTimer()
        self.timerAIR1.timeout.connect(self.update_air1_seconds)
        self.Air1Seconds = 0
        self.statusAIR1 = False

        self.timerAIR2 = QTimer()
        self.timerAIR2.timeout.connect(self.update_air2_seconds)
        self.Air2Seconds = 0
        self.statusAIR2 = False

        self.timerAIR3 = QTimer()
        self.timerAIR3.timeout.connect(self.update_air3_seconds)
        self.Air3Seconds = 0
        self.statusAIR3 = False
        self.radioTimerMode = 0  # count up mode

        self.timerAIR4 = QTimer()
        self.timerAIR4.timeout.connect(self.update_air4_seconds)
        self.Air4Seconds = 0
        self.statusAIR4 = False
        self.streamTimerMode = 0  # count up mode

        # Setup NTP Check Thread
        self.checkNTPOffset = CheckNTPOffsetThread(self)

        # Setup check NTP Timer
        self.ntpHadWarning = True
        self.ntpWarnMessage = ""
        self.timerNTP = QTimer()
        self.timerNTP.timeout.connect(self.trigger_ntp_check)
        # initial check
        self.timerNTP.start(1000)

        self.replacenowTimer = QTimer()
        self.replacenowTimer.timeout.connect(self.replace_now_next)

        # Setup UDP Socket and join Multicast Group
        self.udpsock = QUdpSocket()
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        try:
            port = int(settings.value('udpport', "3310"))
        except ValueError:
            port = "3310"
            settings.setValue('udpport', "3310")
        multicast_address = settings.value('multicast_address', "239.194.0.1")
        if not QHostAddress(multicast_address).isMulticast():
            multicast_address = "239.194.0.1"
            settings.setValue('multicast_address', "239.194.0.1")
        settings.endGroup()

        self.udpsock.bind(QHostAddress.SpecialAddress.AnyIPv4, int(port), QUdpSocket.BindFlag.ShareAddress)
        if QHostAddress(multicast_address).isMulticast():
            logger.info(f"{multicast_address} is Multicast, joining multicast group")
            self.udpsock.joinMulticastGroup(QHostAddress(multicast_address))
        self.udpsock.readyRead.connect(self.udp_cmd_handler)

        # Setup HTTP Server
        self.httpd = HttpDaemon(self)
        self.httpd.start()

        # display all host addresses
        self.display_all_hostaddresses()

        # set NTP warning
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        if settings.value('ntpcheck', True, type=bool):
            self.ntpHadWarning = True
            self.ntpWarnMessage = "waiting for NTP status check"
        settings.endGroup()

        # do initial update check
        self.settings.sigCheckForUpdate.emit()

    def quit_oas(self):
        # do cleanup here
        logger.info("Quitting, cleaning up...")
        self.checkNTPOffset.stop()
        self.httpd.stop()
        QCoreApplication.instance().quit()

    def radio_timer_start_stop(self):
        self.start_stop_air3()

    def radio_timer_reset(self):
        self.reset_air3()
        self.radioTimerMode = 0  # count up mode

    def radio_timer_set(self, seconds):
        self.Air3Seconds = seconds
        if seconds > 0:
            self.radioTimerMode = 1  # count down mode
        else:
            self.radioTimerMode = 0  # count up mode
        self.AirLabel_3.setText(f"Timer\n{int(self.Air3Seconds / 60)}:{int(self.Air3Seconds % 60):02d}")

    def get_timer_dialog(self):
        # generate and display timer input window
        self.getTimeWindow = QDialog()
        self.getTimeWindow.resize(200, 100)
        self.getTimeWindow.setWindowTitle("Please enter timer")
        self.getTimeWindow.timeEdit = QLineEdit("Enter timer here")
        self.getTimeWindow.timeEdit.selectAll()
        self.getTimeWindow.infoLabel = QLabel("Examples:\nenter 2,10 for 2:10 minutes\nenter 30 for 30 seconds")
        layout = QVBoxLayout()
        layout.addWidget(self.getTimeWindow.infoLabel)
        layout.addWidget(self.getTimeWindow.timeEdit)
        self.getTimeWindow.setLayout(layout)
        self.getTimeWindow.timeEdit.setFocus()
        self.getTimeWindow.timeEdit.returnPressed.connect(self.parse_timer_input)
        self.getTimeWindow.show()

    def parse_timer_input(self):
        minutes = 0
        seconds = 0
        # hide input window
        self.sender().parent().hide()
        # get time string
        text = str(self.sender().text())
        if re.match('^[0-9]*,[0-9]*$', text):
            (minutes, seconds) = text.split(",")
            minutes = int(minutes)
            seconds = int(seconds)
        elif re.match(r'^[0-9]*\.[0-9]*$', text):
            (minutes, seconds) = text.split(".")
            minutes = int(minutes)
            seconds = int(seconds)
        elif re.match('^[0-9]*$', text):
            seconds = int(text)
        seconds = (minutes * 60) + seconds
        self.radio_timer_set(seconds)

    def stream_timer_start_stop(self):
        self.start_stop_air4()

    def stream_timer_reset(self):
        self.reset_air4()
        self.streamTimerMode = 0  # count up mode

    def _ensure_air_icons_are_set(self) -> None:
        """Helper method to ensure all AIR icons are set correctly"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("AIR")
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
        settings.endGroup()

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
        
        config = air_configs[air_num]
        label_widget = getattr(self, config['label_widget'])
        icon_widget = getattr(self, config['icon_widget'])
        seconds_attr = config['seconds_attr']
        status_attr = config['status_attr']
        timer_attr = config['timer_attr']
        
        if action:
            settings.beginGroup("Timers")
            if config.get('reset_seconds', False):
                setattr(self, seconds_attr, 0)
            
            # Set active styles
            active_text_color = settings.value(config['active_text_color'], '#FFFFFF')
            active_bg_color = settings.value(config['active_bg_color'], '#FF0000')
            label_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
            
            # Set icon with active styles
            settings.beginGroup("AIR")
            icon_path = settings.value(config['icon_key'], config['icon_default'])
            if icon_path:
                pixmap = QPixmap(icon_path)
                icon_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
                icon_widget.setPixmap(pixmap)
                icon_widget.update()
            settings.endGroup()
            
            # Set label text
            label_text = settings.value(config['label'], config['label_default'])
            seconds = getattr(self, seconds_attr)
            label_widget.setText(f"{label_text}\n{int(seconds/60)}:{seconds%60:02d}")
            
            # Set status and start timer
            setattr(self, status_attr, True)
            timer = getattr(self, timer_attr)
            timer.start(1000)
            
            # Special handling for AIR3 and AIR4 countdown mode
            if 'special_mode' in config:
                mode_attr = config['special_mode']
                mode = getattr(self, mode_attr, 0)
                if mode == 1 and seconds > 1:
                    update_method = getattr(self, f'update_air{air_num}_seconds')
                    update_method()
            
            settings.endGroup()
        else:
            settings.beginGroup("LEDS")
            inactive_text_color = settings.value('inactivetextcolor', '#555555')
            inactive_bg_color = settings.value('inactivebgcolor', '#222222')
            
            # Save icon before setStyleSheet to prevent flickering
            settings.beginGroup("AIR")
            icon_path = settings.value(config['icon_key'], config['icon_default'])
            icon_pixmap = QPixmap(icon_path) if icon_path else None
            settings.endGroup()
            
            # Set inactive styles
            label_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
            icon_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
            settings.endGroup()
            
            # Restore icon immediately after styleSheet change to prevent flickering
            if icon_pixmap and not icon_pixmap.isNull():
                icon_widget.setPixmap(icon_pixmap)
                icon_widget.update()
            
            # Set status and stop timer
            setattr(self, status_attr, False)
            timer = getattr(self, timer_attr)
            timer.stop()

    def _update_air_seconds(self, air_num: int) -> None:
        """
        Generic method to update AIR seconds display
        
        Args:
            air_num: AIR number (1-4)
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Timers")
        
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
        label_text = settings.value(config['label'], config['label_default'])
        seconds = getattr(self, seconds_attr)
        label_widget.setText(f"{label_text}\n{int(seconds/60)}:{seconds%60:02d}")
        
        settings.endGroup()

    def show_settings(self):
        global app
        # un-hide mouse cursor
        app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
        # Set icons BEFORE opening dialog to prevent flickering
        self._ensure_air_icons_are_set()
        self.settings.show_settings()

    def display_all_hostaddresses(self):
        v4addrs = list()
        v6addrs = list()
        for address in QNetworkInterface().allAddresses():
            if address.protocol() == 0:
                if address.toString()[:3] != '127':
                    v4addrs.append(address.toString())
            # if address.protocol() == 1:
            #    v6addrs.append(address.toString())

        self.set_current_song_text(", ".join([str(addr) for addr in v4addrs]))
        self.set_news_text(", ".join([str(addr) for addr in v6addrs]))

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('replacenow', True, type=bool):
            self.replacenowTimer.setSingleShot(True)
            self.replacenowTimer.start(10000)
        settings.endGroup()

    def parse_cmd(self, data: bytes) -> bool:
        """
        Parse and execute a command from UDP/HTTP input
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            
        Returns:
            True if command was parsed successfully, False otherwise
        """
        try:
            (command, value) = data.decode('utf_8').split(':', 1)
        except ValueError:
            return False

        command = str(command)
        value = str(value)
        
        # Use command dispatch map for simple commands
        handler = self._get_command_handler(command)
        if handler:
            handler(value)
            return True
        
        # Handle complex commands
        if command == "CONF":
            return self._handle_conf_command(value)
        
        # Unknown command
        logger.warning(f"Unknown command: {command}")
        return False

    def _get_command_handler(self, command: str):
        """
        Get command handler function for a given command
        
        Args:
            command: Command name
            
        Returns:
            Handler function or None if command not found
        """
        command_handlers = {
            "NOW": lambda v: self.set_current_song_text(v),
            "NEXT": lambda v: self.set_news_text(v),
            "LED1": lambda v: self._handle_led_command(1, v),
            "LED2": lambda v: self._handle_led_command(2, v),
            "LED3": lambda v: self._handle_led_command(3, v),
            "LED4": lambda v: self._handle_led_command(4, v),
            "WARN": lambda v: self._handle_warn_command(v),
            "AIR1": lambda v: self._handle_air_simple_command(1, v),
            "AIR2": lambda v: self._handle_air_simple_command(2, v),
            "AIR3": lambda v: self._handle_air3_command(v),
            "AIR3TIME": lambda v: self._handle_air3time_command(v),
            "AIR4": lambda v: self._handle_air4_command(v),
            "CMD": lambda v: self._handle_cmd_command(v),
        }
        return command_handlers.get(command)

    def _handle_led_command(self, led_num: int, value: str) -> None:
        """Handle LED command (LED1-4)"""
        self.led_logic(led_num, value != "OFF")

    def _handle_warn_command(self, value: str) -> None:
        """Handle WARN command"""
        if value:
            self.add_warning(value, 1)
        else:
            self.remove_warning(1)

    def _handle_air_simple_command(self, air_num: int, value: str) -> None:
        """Handle simple AIR command (AIR1, AIR2)"""
        if value == "OFF":
            getattr(self, f"set_air{air_num}")(False)
        else:
            getattr(self, f"set_air{air_num}")(True)

    def _handle_air3_command(self, value: str) -> None:
        """Handle AIR3 command with multiple actions"""
        if value == "OFF":
            self.stop_air3()
        elif value == "ON":
            self.start_air3()
        elif value == "RESET":
            self.radio_timer_reset()
        elif value == "TOGGLE":
            self.radio_timer_start_stop()

    def _handle_air3time_command(self, value: str) -> None:
        """Handle AIR3TIME command"""
        try:
            self.radio_timer_set(int(value))
        except ValueError as e:
            logger.error(f"ERROR: invalid value: {e}")

    def _handle_air4_command(self, value: str) -> None:
        """Handle AIR4 command"""
        if value == "OFF":
            self.set_air4(False)
        elif value == "ON":
            self.set_air4(True)
        elif value == "RESET":
            self.stream_timer_reset()

    def _handle_cmd_command(self, value: str) -> None:
        """Handle CMD command"""
        if value == "REBOOT":
            self.reboot_host()
        elif value == "SHUTDOWN":
            self.shutdown_host()
        elif value == "QUIT":
            self.quit_oas()

    def _handle_conf_command(self, value: str) -> bool:
        """
        Handle CONF command (configuration updates)
        
        Args:
            value: Configuration string in format "GROUP:PARAM=VALUE"
            
        Returns:
            True if command was handled successfully, False otherwise
        """
        try:
            (group, paramvalue) = value.split(':', 1)
            (param, content) = paramvalue.split('=', 1)
        except ValueError:
            return False

        group_handlers = {
            "General": self._handle_conf_general,
            "LED1": lambda p, c: self._handle_conf_led(1, p, c),
            "LED2": lambda p, c: self._handle_conf_led(2, p, c),
            "LED3": lambda p, c: self._handle_conf_led(3, p, c),
            "LED4": lambda p, c: self._handle_conf_led(4, p, c),
            "Timers": self._handle_conf_timers,
            "Clock": self._handle_conf_clock,
            "Network": self._handle_conf_network,
            "CONF": self._handle_conf_apply,
        }
        
        handler = group_handlers.get(group)
        if handler:
            handler(param, content)
            return True
        
        logger.warning(f"Unknown CONF group: {group}")
        return False

    def _handle_conf_general(self, param: str, content: str) -> None:
        """Handle CONF General group"""
        handlers = {
            "stationname": lambda c: self.settings.StationName.setText(c),
            "slogan": lambda c: self.settings.Slogan.setText(c),
            "stationcolor": lambda c: self.settings.setStationNameColor(
                self.settings.getColorFromName(c.replace("0x", "#"))),
            "slogancolor": lambda c: self.settings.setSloganColor(
                self.settings.getColorFromName(c.replace("0x", "#"))),
            "replacenow": lambda c: self.settings.replaceNOW.setChecked(c == "True"),
            "replacenowtext": lambda c: self.settings.replaceNOWText.setText(c),
        }
        handler = handlers.get(param)
        if handler:
            handler(content)

    def _handle_conf_led(self, led_num: int, param: str, content: str) -> None:
        """Handle CONF LED group (LED1-4)"""
        handlers = {
            "used": lambda c: getattr(self.settings, f"LED{led_num}").setChecked(c == "True"),
            "text": lambda c: getattr(self.settings, f"LED{led_num}Text").setText(c),
            "activebgcolor": lambda c: getattr(self.settings, f"setLED{led_num}BGColor")(
                self.settings.getColorFromName(c.replace("0x", "#"))),
            "activetextcolor": lambda c: getattr(self.settings, f"setLED{led_num}FGColor")(
                self.settings.getColorFromName(c.replace("0x", "#"))),
            "autoflash": lambda c: getattr(self.settings, f"LED{led_num}Autoflash").setChecked(c == "True"),
            "timedflash": lambda c: getattr(self.settings, f"LED{led_num}Timedflash").setChecked(c == "True"),
        }
        handler = handlers.get(param)
        if handler:
            handler(content)

    def _handle_conf_timers(self, param: str, content: str) -> None:
        """Handle CONF Timers group"""
        # Handle AIR enabled flags
        for air_num in range(1, 5):
            if param == f"TimerAIR{air_num}Enabled":
                getattr(self.settings, f"enableAIR{air_num}").setChecked(content == "True")
                return
        
        # Handle AIR text
        for air_num in range(1, 5):
            if param == f"TimerAIR{air_num}Text":
                getattr(self.settings, f"AIR{air_num}Text").setText(content)
                return
        
        # Handle AIR colors
        for air_num in range(1, 5):
            if param == f"AIR{air_num}activebgcolor":
                getattr(self.settings, f"setAIR{air_num}BGColor")(
                    self.settings.getColorFromName(content.replace("0x", "#")))
                return
            if param == f"AIR{air_num}activetextcolor":
                getattr(self.settings, f"setAIR{air_num}FGColor")(
                    self.settings.getColorFromName(content.replace("0x", "#")))
                return
        
        # Handle AIR icon paths
        for air_num in range(1, 5):
            if param == f"AIR{air_num}iconpath":
                getattr(self.settings, f"setAIR{air_num}IconPath")(content)
                return
        
        # Handle TimerAIRMinWidth
        if param == "TimerAIRMinWidth":
            self.settings.AIRMinWidth.setValue(int(content))

    def _handle_conf_clock(self, param: str, content: str) -> None:
        """Handle CONF Clock group"""
        if param == "digital":
            if content == "True":
                self.settings.clockDigital.setChecked(True)
                self.settings.clockAnalog.setChecked(False)
            elif content == "False":
                self.settings.clockAnalog.setChecked(False)
                self.settings.clockDigital.setChecked(True)
        elif param == "showseconds":
            if content == "True":
                self.settings.showSeconds.setChecked(True)
                self.settings.seconds_in_one_line.setChecked(False)
                self.settings.seconds_separate.setChecked(True)
            elif content == "False":
                self.settings.showSeconds.setChecked(False)
                self.settings.seconds_in_one_line.setChecked(False)
                self.settings.seconds_separate.setChecked(True)
        elif param == "secondsinoneline":
            if content == "True":
                self.settings.showSeconds.setChecked(True)
                self.settings.seconds_in_one_line.setChecked(True)
                self.settings.seconds_separate.setChecked(False)
            elif content == "False":
                self.settings.showSeconds.setChecked(False)
                self.settings.seconds_in_one_line.setChecked(False)
                self.settings.seconds_separate.setChecked(True)
        elif param == "staticcolon":
            self.settings.staticColon.setChecked(content == "True")
        elif param == "digitalhourcolor":
            self.settings.setDigitalHourColor(self.settings.getColorFromName(content.replace("0x", "#")))
        elif param == "digitalsecondcolor":
            self.settings.setDigitalSecondColor(self.settings.getColorFromName(content.replace("0x", "#")))
        elif param == "digitaldigitcolor":
            self.settings.setDigitalDigitColor(self.settings.getColorFromName(content.replace("0x", "#")))
        elif param == "logopath":
            self.settings.setLogoPath(content)
        elif param == "logoupper":
            self.settings.setLogoUpper(content == "True")

    def _handle_conf_network(self, param: str, content: str) -> None:
        """Handle CONF Network group"""
        if param == "udpport":
            self.settings.udpport.setText(content)

    def _handle_conf_apply(self, param: str, content: str) -> None:
        """Handle CONF APPLY command"""
        if param == "APPLY" and content == "TRUE":
            self.settings.applySettings()

    def udp_cmd_handler(self) -> None:
        """Handle incoming UDP commands"""
        while self.udpsock.hasPendingDatagrams():
            data, host, port = self.udpsock.readDatagram(self.udpsock.pendingDatagramSize())
            lines = data.splitlines()
            for line in lines:
                self.parse_cmd(line)

    def manual_toggle_led1(self):
        if self.LED1on:
            self.led_logic(1, False)
        else:
            self.led_logic(1, True)

    def manual_toggle_led2(self):
        if self.LED2on:
            self.led_logic(2, False)
        else:
            self.led_logic(2, True)

    def manual_toggle_led3(self):
        if self.LED3on:
            self.led_logic(3, False)
        else:
            self.led_logic(3, True)

    def manual_toggle_led4(self):
        if self.LED4on:
            self.led_logic(4, False)
        else:
            self.led_logic(4, True)

    def toggle_led1(self):
        if self.statusLED1:
            self.set_led1(False)
        else:
            self.set_led1(True)

    def toggle_led2(self):
        if self.statusLED2:
            self.set_led2(False)
        else:
            self.set_led2(True)

    def toggle_led3(self):
        if self.statusLED3:
            self.set_led3(False)
        else:
            self.set_led3(True)

    def toggle_led4(self):
        if self.statusLED4:
            self.set_led4(False)
        else:
            self.set_led4(True)

    def toggle_air1(self):
        if self.statusAIR1:
            self.set_air1(False)
        else:
            self.set_air1(True)

    def toggle_air2(self):
        if self.statusAIR2:
            self.set_air2(False)
        else:
            self.set_air2(True)

    def toggle_air4(self):
        if self.statusAIR4:
            self.set_air4(False)
        else:
            self.set_air4(True)

    def display_ips(self):
        self.display_all_hostaddresses()
        self.replacenowTimer.setSingleShot(True)
        self.replacenowTimer.start(10000)

    def unset_led1(self):
        self.led_logic(1, False)

    def unset_led2(self):
        self.led_logic(2, False)

    def unset_led3(self):
        self.led_logic(3, False)

    def unset_led4(self):
        self.led_logic(4, False)

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

    def set_station_color(self, newcolor):
        palette = self.labelStation.palette()
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.labelStation.setPalette(palette)

    def set_slogan_color(self, newcolor):
        palette = self.labelSlogan.palette()
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.labelSlogan.setPalette(palette)

    def restore_settings_from_config(self) -> None:
        """Restore all settings from configuration"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        self._restore_general_settings(settings)
        self._restore_led_settings(settings)
        self._restore_clock_settings(settings)
        self._restore_formatting_settings(settings)
        self._restore_weather_settings(settings)
        self._restore_timer_settings(settings)
        self._restore_font_settings(settings)

    def _restore_general_settings(self, settings: QSettings) -> None:
        """Restore general settings (station name, slogan, colors)"""
        settings.beginGroup("General")
        self.labelStation.setText(settings.value('stationname', 'Radio Eriwan'))
        self.labelSlogan.setText(settings.value('slogan', 'Your question is our motivation'))
        self.set_station_color(self.settings.getColorFromName(settings.value('stationcolor', '#FFAA00')))
        self.set_slogan_color(self.settings.getColorFromName(settings.value('slogancolor', '#FFAA00')))
        settings.endGroup()

    def _restore_led_settings(self, settings: QSettings) -> None:
        """Restore LED settings (text, visibility)"""
        led_configs = [
            (1, 'ON AIR'),
            (2, 'PHONE'),
            (3, 'DOORBELL'),
            (4, 'EAS ACTIVE'),
        ]
        
        for led_num, default_text in led_configs:
            settings.beginGroup(f"LED{led_num}")
            getattr(self, f'set_led{led_num}_text')(settings.value('text', default_text))
            getattr(self, f'buttonLED{led_num}').setVisible(settings.value('used', True, type=bool))
            settings.endGroup()

    def _restore_clock_settings(self, settings: QSettings) -> None:
        """Restore clock widget settings"""
        settings.beginGroup("Clock")
        self.clockWidget.set_clock_mode(settings.value('digital', True, type=bool))
        self.clockWidget.set_digi_hour_color(
            self.settings.getColorFromName(settings.value('digitalhourcolor', '#3232FF')))
        self.clockWidget.set_digi_second_color(
            self.settings.getColorFromName(settings.value('digitalsecondcolor', '#FF9900')))
        self.clockWidget.set_digi_digit_color(
            self.settings.getColorFromName(settings.value('digitaldigitcolor', '#3232FF')))
        self.clockWidget.set_logo(
            settings.value('logopath', ':/astrastudio_logo/images/astrastudio_transparent.png'))
        self.clockWidget.set_show_seconds(settings.value('showSeconds', False, type=bool))
        self.clockWidget.set_one_line_time(settings.value('showSecondsInOneLine', False, type=bool) &
                                           settings.value('showSeconds', False, type=bool))
        self.clockWidget.set_static_colon(settings.value('staticColon', False, type=bool))
        self.clockWidget.set_logo_upper(settings.value('logoUpper', False, type=bool))
        self.labelTextRight.setVisible(settings.value('useTextClock', True, type=bool))
        settings.endGroup()

    def _restore_formatting_settings(self, settings: QSettings) -> None:
        """Restore formatting settings (AM/PM, text clock language)"""
        settings.beginGroup("Formatting")
        self.clockWidget.set_am_pm(settings.value('isAmPm', False, type=bool))
        self.textLocale = settings.value('textClockLanguage', 'English')
        settings.endGroup()

    def _restore_weather_settings(self, settings: QSettings) -> None:
        """Restore weather widget settings"""
        settings.beginGroup("WeatherWidget")
        if settings.value('owmWidgetEnabled', False, type=bool):
            self.weatherWidget.show()
        else:
            self.weatherWidget.hide()
        settings.endGroup()

    def _restore_timer_settings(self, settings: QSettings) -> None:
        """Restore timer/AIR settings"""
        settings.beginGroup("Timers")
        # Configuration for each AIR timer
        air_timer_configs = [
            (1, 'TimerAIR1Enabled', 'TimerAIR1Text', 'Mic', 'air1iconpath', ':/mic_icon/images/mic_icon.png'),
            (2, 'TimerAIR2Enabled', 'TimerAIR2Text', 'Phone', 'air2iconpath', ':/phone_icon/images/phone_icon.png'),
            (3, 'TimerAIR3Enabled', 'TimerAIR3Text', 'Timer', 'air3iconpath', ':/timer_icon/images/timer_icon.png'),
            (4, 'TimerAIR4Enabled', 'TimerAIR4Text', 'Stream', 'air4iconpath', ':/stream_icon/images/antenna2.png')
        ]
        
        for air_num, enabled_key, text_key, text_default, icon_key, icon_default in air_timer_configs:
            if not settings.value(enabled_key, True, type=bool):
                led_widget = getattr(self, f'AirLED_{air_num}')
                led_widget.hide()
            else:
                label_text = settings.value(text_key, text_default)
                label_widget = getattr(self, f'AirLabel_{air_num}')
                icon_widget = getattr(self, f'AirIcon_{air_num}')
                led_widget = getattr(self, f'AirLED_{air_num}')
                
                label_widget.setText(f"{label_text}\n0:00")
                inactive_text_color = settings.value('inactivetextcolor', '#555555')
                inactive_bg_color = settings.value('inactivebgcolor', '#222222')
                
                # Save icon before setStyleSheet to prevent flickering
                settings.beginGroup("AIR")
                icon_path = settings.value(icon_key, icon_default)
                icon_pixmap = QPixmap(icon_path) if icon_path else None
                settings.endGroup()
                
                # Set inactive styles
                label_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
                icon_widget.setStyleSheet(f"color:{inactive_text_color};background-color:{inactive_bg_color}")
                
                # Restore icon immediately after styleSheet change to prevent flickering
                if icon_pixmap and not icon_pixmap.isNull():
                    icon_widget.setPixmap(icon_pixmap)
                    icon_widget.update()
                
                led_widget.show()
        
        # Set minimum left LED width
        min_width = settings.value('TimerAIRMinWidth', 200, type=int)
        for air_num in range(1, 5):
            led_widget = getattr(self, f'AirLED_{air_num}')
            led_widget.setMinimumWidth(min_width)
        
        settings.endGroup()

    def _restore_font_settings(self, settings: QSettings) -> None:
        """Restore font settings for all widgets"""
        settings.beginGroup("Fonts")
        # Font configuration for widgets
        font_configs = [
            ('LED1', 'buttonLED1'),
            ('LED2', 'buttonLED2'),
            ('LED3', 'buttonLED3'),
            ('LED4', 'buttonLED4'),
            ('AIR1', 'AirLabel_1'),
            ('AIR2', 'AirLabel_2'),
            ('AIR3', 'AirLabel_3'),
            ('AIR4', 'AirLabel_4'),
            ('StationName', 'labelStation'),
            ('Slogan', 'labelSlogan'),
        ]
        
        for font_prefix, widget_name in font_configs:
            widget = getattr(self, widget_name)
            font_name = settings.value(f'{font_prefix}FontName', "FreeSans")
            font_size = settings.value(f'{font_prefix}FontSize', 24, type=int)
            font_weight = settings.value(f'{font_prefix}FontWeight', QFont.Weight.Bold, type=int)
            widget.setFont(QFont(font_name, font_size, font_weight))
        
        settings.endGroup()

    def constant_update(self):
        # slot for constant timer timeout
        self.update_date()
        self.update_backtiming_text()
        self.update_backtiming_seconds()
        self.update_ntp_status()
        self.process_warnings()

    def update_date(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Formatting")
        set_language = settings.value('textClockLanguage', 'English')
        lang = QLocale(self.languages[set_language] if set_language in self.languages else QLocale().name())
        self.set_left_text(lang.toString(QDate.currentDate(), settings.value('dateFormat', 'dddd, dd. MMMM yyyy')))
        settings.endGroup()

    def update_backtiming_text(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Formatting")
        text_clock_language = settings.value('textClockLanguage', 'English')
        is_am_pm = settings.value('isAmPm', False, type=bool)
        settings.endGroup()

        string = ""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        remain_min = 60 - minute

        if text_clock_language == "German":
            # german textclock
            if hour > 12:
                hour -= 12
            if 0 < minute < 25:
                string = F"{minute} Minute{'n' if minute>1 else ''} nach {hour}"
            if 25 <= minute < 30:
                string = F"{remain_min-30} Minute{'n' if remain_min-30>1 else ''} vor halb {1 if hour==12 else hour+1}"
            if 31 <= minute <= 39:
                string = F"{30-remain_min} Minute{'n' if 30-remain_min>1 else ''} nach halb {1 if hour==12 else hour+1}"
            if 40 <= minute <= 59:
                string = F"{remain_min} Minute{'n' if remain_min>1 else ''} vor {1 if hour==12 else hour+1}"
            if minute == 30:
                string = F"halb {1 if hour==12 else hour+1}"
            if minute == 0:
                string = F"{hour} Uhr"

        elif text_clock_language == "Dutch":
            # Dutch textclock
            if is_am_pm:
                if hour > 12:
                    hour -= 12
            if minute == 0:
                string = F"Het is {hour} uur"
            if (1 <= minute <= 14) or (16 <= minute <= 29):
                string = F"Het is {minute} minu{'ten' if minute>1 else 'ut'} over {hour}"
            if minute == 15:
                string = F"Het is kwart over {hour}"
            if minute == 30:
                string = F"Het is half {1 if hour==12 else hour+1}"
            if minute == 45:
                string = F"Het is kwart voor {1 if hour==12 else hour+1}"
            if (31 <= minute <= 44) or (46 <= minute <= 59):
                string = F"Het is {remain_min} minu{'ten' if minute>1 else 'ut'} voor {1 if hour==12 else hour+1}"

        elif text_clock_language == "French":
            # French textclock
            if hour > 12:
                hour -= 12
            if 0 < minute < 60:
                string = F"{hour} {'heures' if hour > 1 else 'heure'} {minute}"
            if minute == 0:
                string = F"{hour} {'heures' if hour > 1 else 'heure'}"
            if minute == 15:
                string = F"{hour} {'heures' if hour > 1 else 'heure'} et quart"
            if minute == 30:
                string = F"{hour} {'heures' if hour > 1 else 'heure'} et demie"
            if hour == 0:
                if 0 < minute < 59:
                    string = F"minuit {minute}"
                if minute == 0:
                    string = F"minuit"
                if minute == 15:
                    string = F"minuit et quart"
                if minute == 30:
                    string = F"minuit et demie"

        else:
            # english textclock
            if is_am_pm:
                if hour > 12:
                    hour -= 12
            if minute == 0:
                string = f"it's {hour} o'clock"
            if (0 < minute < 15) or (16 <= minute <= 29):
                string = f"it's {minute} minute{'s' if minute > 1 else ''} past {hour}"
            if minute == 15:
                string = f"it's a quarter past {hour}"
            if minute == 30:
                string = f"it's half past {hour}"
            if minute == 45:
                string = f"it's a quarter to {hour + 1}"
            if (31 <= minute <= 44) or (46 <= minute <= 59):
                string = f"it's {remain_min} minute{'s' if remain_min > 1 else ''} to {1 if hour == 12 else hour + 1}"

        self.set_right_text(string)

    def update_backtiming_seconds(self):
        now = datetime.now()
        second = now.second
        remain_seconds = 60 - second
        self.set_backtiming_secs(remain_seconds)

    def update_ntp_status(self):
        if self.ntpHadWarning and len(self.ntpWarnMessage):
            self.add_warning(self.ntpWarnMessage, 0)
        else:
            self.ntpWarnMessage = ""
            self.remove_warning(0)

    def toggle_full_screen(self):
        global app
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if not settings.value('fullscreen', True, type=bool):
            self.showFullScreen()
            app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
            settings.setValue('fullscreen', True)
        else:
            self.showNormal()
            app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
            settings.setValue('fullscreen', False)
        settings.endGroup()

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

    def reset_air3(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Timers")
        self.timerAIR3.stop()
        self.Air3Seconds = 0
        label_text = settings.value('TimerAIR3Text', 'Timer')
        self.AirLabel_3.setText(F"{label_text}\n{int(self.Air3Seconds/60)}:{self.Air3Seconds%60:02d}")
        if self.statusAIR3:
            self.timerAIR3.start(1000)
        settings.endGroup()

    def set_air3(self, action: bool) -> None:
        """Set AIR3 state (active/inactive)"""
        self._set_air_state(3, action)

    def start_stop_air3(self):
        if not self.statusAIR3:
            self.start_air3()
        else:
            self.stop_air3()

    def start_air3(self):
        self.set_air3(True)

    def stop_air3(self):
        self.set_air3(False)

    def update_air3_seconds(self) -> None:
        """Update AIR3 seconds display"""
        self._update_air_seconds(3)

    def reset_air4(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Timers")
        self.timerAIR4.stop()
        self.Air4Seconds = 0
        label_text = settings.value('TimerAIR4Text', 'Stream')
        self.AirLabel_4.setText(F"{label_text}\n{int(self.Air4Seconds/60)}:{self.Air4Seconds%60:02d}")
        if self.statusAIR4:
            self.timerAIR4.start(1000)
        settings.endGroup()

    def set_air4(self, action: bool) -> None:
        """Set AIR4 state (active/inactive)"""
        self._set_air_state(4, action)

    def start_stop_air4(self):
        if not self.statusAIR4:
            self.start_air4()
        else:
            self.stop_air4()

    def start_air4(self):
        self.set_air4(True)

    def stop_air4(self):
        self.set_air4(False)

    def update_air4_seconds(self) -> None:
        """Update AIR4 seconds display"""
        self._update_air_seconds(4)

    def replace_now_next(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        self.set_current_song_text(settings.value('replacenowtext', ""))
        self.set_news_text("")
        settings.endGroup()

    def trigger_ntp_check(self):
        logger.debug("NTP Check triggered")
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        ntp_check = settings.value('ntpcheck', True, type=bool)
        settings.endGroup()
        if not ntp_check:
            self.timerNTP.stop()
            return
        else:
            self.timerNTP.stop()
            self.checkNTPOffset.start()
            self.timerNTP.start(60000)

    def set_led1(self, action):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED1")
            self.buttonLED1.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#FF0000'))
            settings.endGroup()
            self.statusLED1 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED1.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED1 = False

    def set_led2(self, action):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED2")
            self.buttonLED2.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#DCDC00'))
            settings.endGroup()
            self.statusLED2 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED2.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED2 = False

    def set_led3(self, action):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED3")
            self.buttonLED3.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#00C8C8'))
            settings.endGroup()
            self.statusLED3 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED3.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED3 = False

    def set_led4(self, action):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED4")
            self.buttonLED4.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#FF00FF'))
            settings.endGroup()
            self.statusLED4 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED4.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED4 = False

    def set_station(self, text):
        self.labelStation.setText(text)

    def set_slogan(self, text):
        self.labelSlogan.setText(text)

    def set_left_text(self, text):
        self.labelTextLeft.setText(text)

    def set_right_text(self, text):
        self.labelTextRight.setText(text)

    def set_led1_text(self, text):
        self.buttonLED1.setText(text)

    def set_led2_text(self, text):
        self.buttonLED2.setText(text)

    def set_led3_text(self, text):
        self.buttonLED3.setText(text)

    def set_led4_text(self, text):
        self.buttonLED4.setText(text)

    def set_current_song_text(self, text):
        self.labelCurrentSong.setText(text)

    def set_news_text(self, text):
        self.labelNews.setText(text)

    def set_backtiming_secs(self, value):
        pass
        # self.labelSeconds.setText( str(value) )

    def add_warning(self, text, priority=0):
        self.warnings[priority] = text

    def remove_warning(self, priority=0):
        self.warnings[priority] = ""

    def process_warnings(self):
        warning_available = False
        last_warning = None

        for warning in self.warnings:
            if len(warning) > 0:
                last_warning = warning
                warning_available = True
        if warning_available:
            self.show_warning(last_warning)
        else:
            self.hide_warning()

    def show_warning(self, text):
        self.labelCurrentSong.hide()
        self.labelNews.hide()
        self.labelWarning.setText(text)
        font = self.labelWarning.font()
        font.setPointSize(45)
        self.labelWarning.setFont(font)
        self.labelWarning.show()

    def hide_warning(self, priority=0):
        self.labelWarning.hide()
        self.labelCurrentSong.show()
        self.labelNews.show()
        self.labelWarning.setText("")
        self.labelWarning.hide()

    @staticmethod
    def exit_oas():
        global app
        app.exit()

    def config_closed(self):
        global app
        # hide mouse cursor if in fullscreen mode
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True, type=bool):
            app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
        settings.endGroup()
        # Ensure icons are still set after dialog is closed
        self._ensure_air_icons_are_set()

    def config_finished(self):
        self.restore_settings_from_config()
        self.weatherWidget.readConfig()
        self.weatherWidget.makeOWMApiCall()
        # Ensure icons are still set after config is finished
        # Icons are already set in restore_settings_from_config() after each setStyleSheet()
        # No need to set them again here to prevent flickering

    def reboot_host(self):
        self.add_warning("SYSTEM REBOOT IN PROGRESS", 2)
        if os.name == "posix":
            cmd = "sudo reboot"
            os.system(cmd)
        if os.name == "nt":
            cmd = "shutdown -f -r -t 0"
            os.system(cmd)

    def shutdown_host(self):
        self.add_warning("SYSTEM SHUTDOWN IN PROGRESS", 2)
        if os.name == "posix":
            cmd = "sudo halt"
            os.system(cmd)
        if os.name == "nt":
            cmd = "shutdown -f -t 0"
            os.system(cmd)

    def closeEvent(self, event):
        self.httpd.stop()
        self.checkNTPOffset.stop()


class CheckNTPOffsetThread(QThread):
    """
    Thread for checking NTP time synchronization offset
    
    Periodically checks the system clock against an NTP server
    and warns if the offset is too large.
    """

    def __init__(self, oas):
        self.oas = oas
        QThread.__init__(self)
        self._initialized = True  # Mark that __init__ was called

    def __del__(self):
        try:
            # Only call wait() if the thread was properly initialized
            # This prevents errors when the object is created with __new__() in tests
            if hasattr(self, '_initialized') and self._initialized:
                self.wait()
        except (RuntimeError, AttributeError):
            # Thread was never initialized or already destroyed
            pass

    def run(self):
        logger.debug("entered CheckNTPOffsetThread.run")
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        ntp_server = str(settings.value('ntpcheckserver', 'pool.ntp.org'))
        settings.endGroup()
        max_deviation = 0.3
        c = ntplib.NTPClient()
        try:
            response = c.request(ntp_server)
            if response.offset > max_deviation or response.offset < -max_deviation:
                logger.warning(f"offset too big: {response.offset} while checking {ntp_server}")
                self.oas.ntpWarnMessage = "Clock not NTP synchronized: offset too big"
                self.oas.ntpHadWarning = True
            else:
                if self.oas.ntpHadWarning:
                    self.oas.ntpHadWarning = False
        except socket.timeout:
            logger.error(f"NTP error: timeout while checking NTP {ntp_server}")
            self.oas.ntpWarnMessage = "Clock not NTP synchronized"
            self.oas.ntpHadWarning = True
        except socket.gaierror:
            logger.error(f"NTP error: socket error while checking NTP {ntp_server}")
            self.oas.ntpWarnMessage = "Clock not NTP synchronized"
            self.oas.ntpHadWarning = True
        except ntplib.NTPException as e:
            logger.error(f"NTP error: {e}")
            self.oas.ntpWarnMessage = str(e)
            self.oas.ntpHadWarning = True

    def stop(self):
        self.quit()


class HttpDaemon(QThread):
    """
    HTTP server thread for handling HTTP-based commands
    
    Runs a simple HTTP server that accepts GET requests with commands
    and forwards them to the UDP command handler.
    """
    def run(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        try:
            port = int(settings.value('httpport', "8010"))
        except ValueError:
            port = 8010
            settings.setValue("httpport", "8010")
        settings.endGroup()

        try:
            handler = OASHTTPRequestHandler
            self._server = HTTPServer((HOST, port), handler)
            self._server.serve_forever()
        except OSError as error:
            logger.error(f"ERROR: Starting HTTP Server on port {port}: {error}")

    def stop(self):
        self._server.shutdown()
        self._server.socket.close()
        self.wait()


class OASHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for OnAirScreen commands
    
    Handles GET requests with command parameters and forwards them
    to the UDP command handler.
    """
    server_version = f"OnAirScreen/{versionString}"

    # handle HEAD request
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

    # handle GET command
    def do_GET(self):
        logger.debug(f"HTTP request path: {self.path}")
        if self.path.startswith('/?cmd'):
            try:
                # Parse the query string: /?cmd=COMMAND:VALUE
                # First split to get cmd=COMMAND:VALUE
                query_string = str(self.path)[5:]  # Remove '/?cmd'
                if '=' in query_string:
                    cmd, message = query_string.split("=", 1)
                    # URL-decode the message part (value after =)
                    # unquote_plus also decodes + signs to spaces
                    message = unquote_plus(message)
                else:
                    self.send_error(400, 'no command was given')
                    return
            except ValueError:
                self.send_error(400, 'no command was given')
                return

            if len(message) > 0:
                self.send_response(200)

                # send header first
                self.send_header('Content-type', 'text-html; charset=utf-8')
                self.end_headers()

                settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
                settings.beginGroup("Network")
                port = int(settings.value('udpport', "3310"))
                settings.endGroup()

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(message.encode(), ("127.0.0.1", port))

                # send file content to client
                self.wfile.write(message.encode())
                self.wfile.write("\n".encode())
                return
            else:
                self.send_error(400, 'no command was given')
                return

        self.send_error(404, 'file not found')


###################################
# Load fonts from fonts directory
###################################
def load_fonts() -> None:
    """Load fonts from the fonts/ directory"""
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    if os.path.exists(font_dir):
        font_files = [
            "FreeSans.otf",
            "FreeSansBold.otf",
            "FreeSansBoldOblique.otf",
            "FreeSansOblique.otf"
        ]
        for font_file in font_files:
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    logger.info(f"Loaded font: {font_file} -> {families}")
                else:
                    logger.warning(f"Failed to load font: {font_file}")


###################################
# App SIGINT handler
###################################
def sigint_handler(*args) -> None:
    """
    Handler for SIGINT signal (Ctrl+C)
    
    Gracefully quits the application when interrupted.
    """
    sys.stderr.write("\n")
    QApplication.quit()


###################################
# App Init
###################################
if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QApplication(sys.argv)
    
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

    main_screen.set_air1(False)
    main_screen.set_air2(False)
    main_screen.set_air3(False)
    main_screen.set_air4(False)

    main_screen.show()

    sys.exit(app.exec())
