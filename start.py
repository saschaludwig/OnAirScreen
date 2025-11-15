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

import ntplib
from PyQt6.QtCore import Qt, QSettings, QCoreApplication, QTimer, QDate, QLocale, QThread
from PyQt6.QtGui import QCursor, QPalette, QKeySequence, QIcon, QPixmap, QFont, QShortcut, QFontDatabase
from PyQt6.QtNetwork import QNetworkInterface
from PyQt6.QtWidgets import QApplication, QWidget, QDialog, QLineEdit, QVBoxLayout, QLabel, QMessageBox

# Import resources FIRST to register them with Qt before UI files are loaded
import resources_rc  # noqa: F401
from mainscreen import Ui_MainScreen
from settings_functions import Settings, versionString
from command_handler import CommandHandler
from network import UdpServer, HttpDaemon
from timer_manager import TimerManager
from utils import settings_group

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

        # Initialize command handler
        self.command_handler = CommandHandler(self)

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('fullscreen', True, type=bool):
                self.showFullScreen()
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
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

        # Setup and start constant update timer
        self.ctimer = QTimer()
        self.ctimer.timeout.connect(self.constant_update)
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

        # Setup UDP Server
        self.udp_server = UdpServer(self.parse_cmd)

        # Setup HTTP Server
        self.httpd = HttpDaemon()
        self.httpd.start()

        # display all host addresses
        self.display_all_hostaddresses()

        # set NTP warning
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            if settings.value('ntpcheck', True, type=bool):
                self.ntpHadWarning = True
                self.ntpWarnMessage = "waiting for NTP status check"

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
        """Set radio timer seconds"""
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

    def stream_timer_reset(self) -> None:
        """Reset stream timer"""
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
                active_text_color = settings.value(config['active_text_color'], '#FFFFFF')
                active_bg_color = settings.value(config['active_bg_color'], '#FF0000')
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
        with settings_group(settings, "General"):
            if settings.value('replacenow', True, type=bool):
                self.replacenowTimer.setSingleShot(True)
                self.replacenowTimer.start(10000)

    def parse_cmd(self, data: bytes) -> bool:
        """
        Parse and execute a command from UDP/HTTP input
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            
        Returns:
            True if command was parsed successfully, False otherwise
        """
        return self.command_handler.parse_cmd(data)


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
        """Generic method to toggle LED using set_led"""
        status_attr = f'statusLED{led_num}'
        current_state = getattr(self, status_attr, False)
        set_led_method = getattr(self, f'set_led{led_num}')
        set_led_method(not current_state)

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

    def set_station_color(self, newcolor) -> None:
        """Set the station label color"""
        self._set_label_color(self.labelStation, newcolor)

    def set_slogan_color(self, newcolor) -> None:
        """Set the slogan label color"""
        self._set_label_color(self.labelSlogan, newcolor)

    def _set_label_color(self, widget, color) -> None:
        """
        Generic method to set label color
        
        Args:
            widget: The label widget to set color for
            color: The color to set
        """
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.WindowText, color)
        widget.setPalette(palette)

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
        with settings_group(settings, "General"):
            self.labelStation.setText(settings.value('stationname', 'Radio Eriwan'))
            self.labelSlogan.setText(settings.value('slogan', 'Your question is our motivation'))
            self.set_station_color(self.settings.getColorFromName(settings.value('stationcolor', '#FFAA00')))
            self.set_slogan_color(self.settings.getColorFromName(settings.value('slogancolor', '#FFAA00')))

    def _restore_led_settings(self, settings: QSettings) -> None:
        """Restore LED settings (text, visibility)"""
        led_configs = [
            (1, 'ON AIR'),
            (2, 'PHONE'),
            (3, 'DOORBELL'),
            (4, 'EAS ACTIVE'),
        ]
        
        for led_num, default_text in led_configs:
            with settings_group(settings, f"LED{led_num}"):
                getattr(self, f'set_led{led_num}_text')(settings.value('text', default_text))
                getattr(self, f'buttonLED{led_num}').setVisible(settings.value('used', True, type=bool))

    def _restore_clock_settings(self, settings: QSettings) -> None:
        """Restore clock widget settings"""
        with settings_group(settings, "Clock"):
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

    def _restore_formatting_settings(self, settings: QSettings) -> None:
        """Restore formatting settings (AM/PM, text clock language)"""
        with settings_group(settings, "Formatting"):
            self.clockWidget.set_am_pm(settings.value('isAmPm', False, type=bool))
            self.textLocale = settings.value('textClockLanguage', 'English')

    def _restore_weather_settings(self, settings: QSettings) -> None:
        """Restore weather widget settings"""
        with settings_group(settings, "WeatherWidget"):
            if settings.value('owmWidgetEnabled', False, type=bool):
                self.weatherWidget.show()
            else:
                self.weatherWidget.hide()

    def _restore_timer_settings(self, settings: QSettings) -> None:
        """Restore timer/AIR settings"""
        with settings_group(settings, "Timers"):
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
                    with settings_group(settings, "AIR"):
                        icon_path = settings.value(icon_key, icon_default)
                        icon_pixmap = QPixmap(icon_path) if icon_path else None
                    
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

    def _restore_font_settings(self, settings: QSettings) -> None:
        """Restore font settings for all widgets"""
        with settings_group(settings, "Fonts"):
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

    def constant_update(self):
        # slot for constant timer timeout
        self.update_date()
        self.update_backtiming_text()
        self.update_backtiming_seconds()
        self.update_ntp_status()
        self.process_warnings()

    def update_date(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Formatting"):
            set_language = settings.value('textClockLanguage', 'English')
        lang = QLocale(self.languages[set_language] if set_language in self.languages else QLocale().name())
        self.set_left_text(lang.toString(QDate.currentDate(), settings.value('dateFormat', 'dddd, dd. MMMM yyyy')))

    def update_backtiming_text(self) -> None:
        """Update the text clock display based on current time and language"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Formatting"):
            text_clock_language = settings.value('textClockLanguage', 'English')
            is_am_pm = settings.value('isAmPm', False, type=bool)

        now = datetime.now()
        hour = now.hour
        minute = now.minute
        remain_min = 60 - minute

        # Dispatch to language-specific formatters
        language_formatters = {
            "German": self._format_time_german,
            "Dutch": self._format_time_dutch,
            "French": self._format_time_french,
        }
        
        formatter = language_formatters.get(text_clock_language, self._format_time_english)
        string = formatter(hour, minute, remain_min, is_am_pm)
        
        self.set_right_text(string)

    def _format_time_german(self, hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in German text clock style"""
        if hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"{hour} Uhr"
        elif minute == 30:
            return f"halb {1 if hour == 12 else hour + 1}"
        elif 0 < minute < 25:
            return f"{minute} Minute{'n' if minute > 1 else ''} nach {hour}"
        elif 25 <= minute < 30:
            return f"{remain_min - 30} Minute{'n' if remain_min - 30 > 1 else ''} vor halb {1 if hour == 12 else hour + 1}"
        elif 31 <= minute <= 39:
            return f"{30 - remain_min} Minute{'n' if 30 - remain_min > 1 else ''} nach halb {1 if hour == 12 else hour + 1}"
        elif 40 <= minute <= 59:
            return f"{remain_min} Minute{'n' if remain_min > 1 else ''} vor {1 if hour == 12 else hour + 1}"
        else:
            return f"{hour} Uhr"

    def _format_time_dutch(self, hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in Dutch text clock style"""
        if is_am_pm and hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"Het is {hour} uur"
        elif minute == 15:
            return f"Het is kwart over {hour}"
        elif minute == 30:
            return f"Het is half {1 if hour == 12 else hour + 1}"
        elif minute == 45:
            return f"Het is kwart voor {1 if hour == 12 else hour + 1}"
        elif (1 <= minute <= 14) or (16 <= minute <= 29):
            return f"Het is {minute} minu{'ten' if minute > 1 else 'ut'} over {hour}"
        elif (31 <= minute <= 44) or (46 <= minute <= 59):
            return f"Het is {remain_min} minu{'ten' if minute > 1 else 'ut'} voor {1 if hour == 12 else hour + 1}"
        else:
            return f"Het is {hour} uur"

    def _format_time_french(self, hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in French text clock style"""
        if hour > 12:
            hour -= 12
        
        if hour == 0:
            if minute == 0:
                return "minuit"
            elif minute == 15:
                return "minuit et quart"
            elif minute == 30:
                return "minuit et demie"
            elif 0 < minute < 59:
                return f"minuit {minute}"
        
        if minute == 0:
            return f"{hour} {'heures' if hour > 1 else 'heure'}"
        elif minute == 15:
            return f"{hour} {'heures' if hour > 1 else 'heure'} et quart"
        elif minute == 30:
            return f"{hour} {'heures' if hour > 1 else 'heure'} et demie"
        elif 0 < minute < 60:
            return f"{hour} {'heures' if hour > 1 else 'heure'} {minute}"
        else:
            return f"{hour} {'heures' if hour > 1 else 'heure'}"

    def _format_time_english(self, hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in English text clock style"""
        if is_am_pm and hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"it's {hour} o'clock"
        elif minute == 15:
            return f"it's a quarter past {hour}"
        elif minute == 30:
            return f"it's half past {hour}"
        elif minute == 45:
            return f"it's a quarter to {hour + 1}"
        elif (0 < minute < 15) or (16 <= minute <= 29):
            return f"it's {minute} minute{'s' if minute > 1 else ''} past {hour}"
        elif (31 <= minute <= 44) or (46 <= minute <= 59):
            return f"it's {remain_min} minute{'s' if remain_min > 1 else ''} to {1 if hour == 12 else hour + 1}"
        else:
            return f"it's {hour} o'clock"

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

    def replace_now_next(self):
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            self.set_current_song_text(settings.value('replacenowtext', ""))
            self.set_news_text("")

    def trigger_ntp_check(self):
        logger.debug("NTP Check triggered")
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            ntp_check = settings.value('ntpcheck', True, type=bool)
        if not ntp_check:
            self.timerNTP.stop()
            return
        else:
            self.timerNTP.stop()
            self.checkNTPOffset.start()
            self.timerNTP.start(60000)

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
                active_text_color = settings.value('activetextcolor', '#FFFFFF')
                active_bg_color = settings.value('activebgcolor', default_active_colors[led_num])
                button_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
            setattr(self, status_attr, True)
        else:
            with settings_group(settings, "LEDS"):
                inactive_text_color = settings.value('inactivetextcolor', '#555555')
                inactive_bg_color = settings.value('inactivebgcolor', '#222222')
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

    def set_news_text(self, text: str) -> None:
        """Set news text"""
        self._set_text('labelNews', text)

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
        with settings_group(settings, "General"):
            if settings.value('fullscreen', True, type=bool):
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
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
        with settings_group(settings, "NTP"):
            ntp_server = str(settings.value('ntpcheckserver', 'pool.ntp.org'))
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
