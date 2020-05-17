#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2020 Sascha Ludwig, astrastudio.de
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

import os
import re
import signal
import socket
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

import ntplib
from PyQt5.QtCore import Qt, QSettings, QCoreApplication, QTimer, QVariant, QDate, QThread
from PyQt5.QtGui import QCursor, QPalette, QKeySequence, QIcon, QPixmap
from PyQt5.QtNetwork import QUdpSocket, QNetworkInterface
from PyQt5.QtWidgets import QApplication, QWidget, QShortcut, QDialog, QLineEdit, QVBoxLayout, QLabel

from mainscreen import Ui_MainScreen
from settings_functions import Settings, versionString

HOST = '0.0.0.0'


class MainScreen(QWidget, Ui_MainScreen):
    getTimeWindow: QDialog
    ntpHadWarning: bool
    ntpWarnMessage: str

    def __init__(self):
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

        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True, type=bool):
            self.showFullScreen()
            app.setOverrideCursor(QCursor(Qt.BlankCursor))
        settings.endGroup()
        print("Loading Settings from: ", settings.fileName())

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

        # Setup UDP Socket
        self.udpsock = QUdpSocket()
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        port = int(settings.value('udpport', 3310))
        settings.endGroup()
        self.udpsock.bind(port, QUdpSocket.ShareAddress)
        self.udpsock.readyRead.connect(self.udp_cmd_handler)

        # Setup HTTP Server
        self.httpd = HttpDaemon(self)
        self.httpd.start()

        # display all host addresses
        self.display_all_hostaddresses()

        # set NTP warning
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        if settings.value('ntpcheck', True, type=bool):
            self.ntpHadWarning = True
            self.ntpWarnMessage = "waiting for NTP status check"
        settings.endGroup()

        # do initial update check
        self.settings.sigCheckForUpdate.emit()

    def quit_oas(self):
        # do cleanup here
        print("Quitting, cleaning up...")
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
        self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds / 60, self.Air3Seconds % 60))

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

    def show_settings(self):
        global app
        # un-hide mouse cursor
        app.setOverrideCursor(QCursor(Qt.ArrowCursor))
        self.settings.showsettings()

    def display_all_hostaddresses(self):
        v4addrs = list()
        v6addrs = list()
        for address in QNetworkInterface().allAddresses():
            if address.protocol() == 0:
                v4addrs.append(address.toString())
            # if address.protocol() == 1:
            #    v6addrs.append(address.toString())

        self.set_current_song_text(", ".join(["%s" % addr for addr in v4addrs]))
        self.set_news_text(", ".join(["%s" % addr for addr in v6addrs]))

    def parse_cmd(self, data):
        try:
            (command, value) = data.decode('utf_8').split(':', 1)
        except ValueError:
            return False

        command = str(command)
        value = str(value)
        # print("command: >" + command + "<")
        # print("value: >" + value + "<")
        if command == "NOW":
            self.set_current_song_text(value)
        elif command == "NEXT":
            self.set_news_text(value)
        elif command == "LED1":
            if value == "OFF":
                self.led_logic(1, False)
            else:
                self.led_logic(1, True)
        elif command == "LED2":
            if value == "OFF":
                self.led_logic(2, False)
            else:
                self.led_logic(2, True)
        elif command == "LED3":
            if value == "OFF":
                self.led_logic(3, False)
            else:
                self.led_logic(3, True)
        elif command == "LED4":
            if value == "OFF":
                self.led_logic(4, False)
            else:
                self.led_logic(4, True)
        elif command == "WARN":
            if value:
                self.add_warning(value, 1)
            else:
                self.remove_warning(1)

        elif command == "AIR1":
            if value == "OFF":
                self.set_air1(False)
            else:
                self.set_air1(True)

        elif command == "AIR2":
            if value == "OFF":
                self.set_air2(False)
            else:
                self.set_air2(True)

        elif command == "AIR3":
            if value == "OFF":
                self.stop_air3()
            if value == "ON":
                self.start_air3()
            if value == "RESET":
                self.radio_timer_reset()
            if value == "TOGGLE":
                self.radio_timer_start_stop()

        elif command == "AIR3TIME":
            self.radio_timer_set(int(value))

        elif command == "AIR4":
            if value == "OFF":
                self.set_air4(False)
            if value == "ON":
                self.set_air4(True)
            if value == "RESET":
                self.stream_timer_reset()

        elif command == "CMD":
            if value == "REBOOT":
                self.reboot_host()
            if value == "SHUTDOWN":
                self.shutdown_host()
            if value == "QUIT":
                self.quit_oas()

        elif command == "CONF":
            # split group, config and values and apply them
            try:
                (group, paramvalue) = value.split(':', 1)
                (param, content) = paramvalue.split('=', 1)
                # print "CONF:", param, content
            except ValueError:
                return

            if group == "General":
                if param == "stationname":
                    self.settings.StationName.setText(content)
                elif param == "slogan":
                    self.settings.Slogan.setText(content)
                elif param == "stationcolor":
                    self.settings.setStationNameColor(self.settings.getColorFromName(content))
                elif param == "slogancolor":
                    self.settings.setSloganColor(self.settings.getColorFromName(content))

            elif group == "LED1":
                if param == "used":
                    self.settings.LED1.setChecked(QVariant(content).toBool())
                elif param == "text":
                    self.settings.LED1Text.setText(content)
                elif param == "activebgcolor":
                    self.settings.setLED1BGColor(self.settings.getColorFromName(content))
                elif param == "activetextcolor":
                    self.settings.setLED1FGColor(self.settings.getColorFromName(content))
                elif param == "autoflash":
                    self.settings.LED1Autoflash.setChecked(QVariant(content).toBool())
                elif param == "timedflash":
                    self.settings.LED1Timedflash.setChecked(QVariant(content).toBool())

            elif group == "LED2":
                if param == "used":
                    self.settings.LED2.setChecked(QVariant(content).toBool())
                elif param == "text":
                    self.settings.LED2Text.setText(content)
                elif param == "activebgcolor":
                    self.settings.setLED2BGColor(self.settings.getColorFromName(content))
                elif param == "activetextcolor":
                    self.settings.setLED2FGColor(self.settings.getColorFromName(content))
                elif param == "autoflash":
                    self.settings.LED2Autoflash.setChecked(QVariant(content).toBool())
                elif param == "timedflash":
                    self.settings.LED2Timedflash.setChecked(QVariant(content).toBool())

            elif group == "LED3":
                if param == "used":
                    self.settings.LED3.setChecked(QVariant(content).toBool())
                elif param == "text":
                    self.settings.LED3Text.setText(content)
                elif param == "activebgcolor":
                    self.settings.setLED3BGColor(self.settings.getColorFromName(content))
                elif param == "activetextcolor":
                    self.settings.setLED3FGColor(self.settings.getColorFromName(content))
                elif param == "autoflash":
                    self.settings.LED3Autoflash.setChecked(QVariant(content).toBool())
                elif param == "timedflash":
                    self.settings.LED3Timedflash.setChecked(QVariant(content).toBool())

            elif group == "LED4":
                if param == "used":
                    self.settings.LED4.setChecked(QVariant(content).toBool())
                elif param == "text":
                    self.settings.LED4Text.setText(content)
                elif param == "activebgcolor":
                    self.settings.setLED4BGColor(self.settings.getColorFromName(content))
                elif param == "activetextcolor":
                    self.settings.setLED4FGColor(self.settings.getColorFromName(content))
                elif param == "autoflash":
                    self.settings.LED4Autoflash.setChecked(QVariant(content).toBool())
                elif param == "timedflash":
                    self.settings.LED4Timedflash.setChecked(QVariant(content).toBool())

            elif group == "Clock":
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
                    elif content == "False":
                        self.settings.showSeconds.setChecked(False)
                elif param == "staticcolon":
                    if content == "True":
                        self.settings.staticColon.setChecked(True)
                    elif content == "False":
                        self.settings.staticColon.setChecked(False)
                elif param == "digitalhourcolor":
                    self.settings.setDigitalHourColor(self.settings.getColorFromName(content))
                elif param == "digitalsecondcolor":
                    self.settings.setDigitalSecondColor(self.settings.getColorFromName(content))
                elif param == "digitaldigitcolor":
                    self.settings.setDigitalDigitColor(self.settings.getColorFromName(content))
                elif param == "logopath":
                    self.settings.setLogoPath(content)

            elif group == "Network":
                if param == "udpport":
                    self.settings.udpport.setText(content)

            elif group == "CONF":
                if param == "APPLY":
                    if content == "TRUE":
                        # apply and save settings
                        self.settings.applySettings()

    def udp_cmd_handler(self):
        while self.udpsock.hasPendingDatagrams():
            data, host, port = self.udpsock.readDatagram(self.udpsock.pendingDatagramSize())
            # print("DATA: ", data)
            lines = data.splitlines()
            for line in lines:
                # print("Line:", line)
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

    def unset_led1(self):
        self.led_logic(1, False)

    def unset_led2(self):
        self.led_logic(2, False)

    def unset_led3(self):
        self.led_logic(3, False)

    def unset_led4(self):
        self.led_logic(4, False)

    def led_logic(self, led, state):
        if state:
            if led == 1:
                if self.settings.LED1Autoflash.isChecked():
                    self.timerLED1.start(500)
                if self.settings.LED1Timedflash.isChecked():
                    self.timerLED1.start(500)
                    QTimer.singleShot(20000, self.unset_led1)
                self.set_led1(state)
                self.LED1on = state
            if led == 2:
                if self.settings.LED2Autoflash.isChecked():
                    self.timerLED2.start(500)
                if self.settings.LED2Timedflash.isChecked():
                    self.timerLED2.start(500)
                    QTimer.singleShot(20000, self.unset_led2)
                self.set_led2(state)
                self.LED2on = state
            if led == 3:
                if self.settings.LED3Autoflash.isChecked():
                    self.timerLED3.start(500)
                if self.settings.LED3Timedflash.isChecked():
                    self.timerLED3.start(500)
                    QTimer.singleShot(20000, self.unset_led3)
                self.set_led3(state)
                self.LED3on = state
            if led == 4:
                if self.settings.LED4Autoflash.isChecked():
                    self.timerLED4.start(500)
                if self.settings.LED4Timedflash.isChecked():
                    self.timerLED4.start(500)
                    QTimer.singleShot(20000, self.unset_led4)
                self.set_led4(state)
                self.LED4on = state

        if not state:
            if led == 1:
                self.set_led1(state)
                self.timerLED1.stop()
                self.LED1on = state
            if led == 2:
                self.set_led2(state)
                self.timerLED2.stop()
                self.LED2on = state
            if led == 3:
                self.set_led3(state)
                self.timerLED3.stop()
                self.LED3on = state
            if led == 4:
                self.set_led4(state)
                self.timerLED4.stop()
                self.LED4on = state

    def set_station_color(self, newcolor):
        palette = self.labelStation.palette()
        palette.setColor(QPalette.WindowText, newcolor)
        self.labelStation.setPalette(palette)

    def set_slogan_color(self, newcolor):
        palette = self.labelSlogan.palette()
        palette.setColor(QPalette.WindowText, newcolor)
        self.labelSlogan.setPalette(palette)

    def restore_settings_from_config(self):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        self.labelStation.setText(settings.value('stationname', 'Radio Eriwan'))
        self.labelSlogan.setText(settings.value('slogan', 'Your question is our motivation'))
        self.set_station_color(self.settings.getColorFromName(settings.value('stationcolor', '#FFAA00')))
        self.set_slogan_color(self.settings.getColorFromName(settings.value('slogancolor', '#FFAA00')))
        settings.endGroup()

        settings.beginGroup("LED1")
        self.set_led1_text(settings.value('text', 'ON AIR'))
        settings.endGroup()

        settings.beginGroup("LED2")
        self.set_led2_text(settings.value('text', 'PHONE'))
        settings.endGroup()

        settings.beginGroup("LED3")
        self.set_led3_text(settings.value('text', 'DOORBELL'))
        settings.endGroup()

        settings.beginGroup("LED4")
        self.set_led4_text(settings.value('text', 'ARI'))
        settings.endGroup()

        settings.beginGroup("Clock")
        self.clockWidget.setClockMode(settings.value('digital', True, type=bool))
        self.clockWidget.setDigiHourColor(
            self.settings.getColorFromName(settings.value('digitalhourcolor', '#3232FF')))
        self.clockWidget.setDigiSecondColor(
            self.settings.getColorFromName(settings.value('digitalsecondcolor', '#FF9900')))
        self.clockWidget.setDigiDigitColor(
            self.settings.getColorFromName(settings.value('digitaldigitcolor', '#3232FF')))
        self.clockWidget.setLogo(
            settings.value('logopath', ':/astrastudio_logo/images/astrastudio_transparent.png'))
        self.clockWidget.setShowSeconds(settings.value('showSeconds', False, type=bool))
        self.clockWidget.setStaticColon(settings.value('staticColon', False, type=bool))
        settings.endGroup()

        settings.beginGroup("Formatting")
        self.clockWidget.setAmPm(settings.value('isAmPm', False, type=bool))
        settings.endGroup()

        settings.beginGroup("WeatherWidget")
        if settings.value('owmWidgetEnabled', False, type=bool):
            pass
            self.weatherWidget.show()
        else:
            self.weatherWidget.hide()

        settings.endGroup()

    def constant_update(self):
        # slot for constant timer timeout
        self.update_date()
        self.update_backtiming_text()
        self.update_backtiming_seconds()
        self.update_ntp_status()
        self.process_warnings()

    def update_date(self):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Formatting")
        self.set_left_text(QDate.currentDate().toString(settings.value('dateFormat', 'dddd, dd. MMMM yyyy')))
        settings.endGroup()

    def update_backtiming_text(self):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
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
                string = '%d Minute%s nach %d:00' % (minute, 'n' if minute > 1 else '', hour)
            if 25 <= minute < 30:
                string = '%d Minute%s vor halb %d:00' % (remain_min - 30, 'n' if remain_min - 30 > 1 else '', hour + 1)
            if 30 <= minute <= 39:
                string = '%d Minute%s nach halb %d:00' % (30 - remain_min, 'n' if 30 - remain_min > 1 else '', hour + 1)
            if 40 <= minute <= 59:
                string = '%d Minute%s vor %d:00' % (remain_min, 'n' if remain_min > 1 else '', hour + 1)
            if minute == 30:
                string = 'halb %d:00' % (hour + 1)
            if minute == 0:
                string = '%d:00 Uhr' % hour

        else:
            # english textclock
            if is_am_pm:
                if hour > 12:
                    hour -= 12
            if minute == 0:
                string = "it's %d o'clock" % hour
            if (0 < minute < 15) or (16 <= minute <= 29):
                string = "it's %d minute%s past %d:00" % (minute, 's' if minute > 1 else '', hour)
            if minute == 15:
                string = "it's a quarter past %d:00" % hour
            if minute == 30:
                string = "it's half past %d:00" % hour
            if minute == 45:
                string = "it's a quarter to %d:00" % hour
            if (31 <= minute <= 44) or (46 <= minute <= 59):
                string = "it's %d minute%s to %d:00" % (
                    remain_min, 's' if remain_min > 1 else '', 1 if hour == 12 else hour + 1)

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
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if not settings.value('fullscreen', True, type=bool):
            self.showFullScreen()
            app.setOverrideCursor(QCursor(Qt.BlankCursor))
            settings.setValue('fullscreen', True)
        else:
            self.showNormal()
            app.setOverrideCursor(QCursor(Qt.ArrowCursor))
            settings.setValue('fullscreen', False)
        settings.endGroup()

    def set_air1(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.Air1Seconds = 0
            self.AirLabel_1.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_1.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_1.setText("Mic\n%d:%02d" % (self.Air1Seconds / 60, self.Air1Seconds % 60))
            self.statusAIR1 = True
            # AIR1 timer
            self.timerAIR1.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_1.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                   '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            self.AirLabel_1.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusAIR1 = False
            self.timerAIR1.stop()

    def update_air1_seconds(self):
        self.Air1Seconds += 1
        self.AirLabel_1.setText("Mic\n%d:%02d" % (self.Air1Seconds / 60, self.Air1Seconds % 60))

    def set_air2(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.Air2Seconds = 0
            self.AirLabel_2.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_2.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_2.setText("Phone\n%d:%02d" % (self.Air2Seconds / 60, self.Air2Seconds % 60))
            self.statusAIR2 = True
            # AIR2 timer
            self.timerAIR2.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_2.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                   '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            self.AirLabel_2.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusAIR2 = False
            self.timerAIR2.stop()

    def update_air2_seconds(self):
        self.Air2Seconds += 1
        self.AirLabel_2.setText("Phone\n%d:%02d" % (self.Air2Seconds / 60, self.Air2Seconds % 60))

    def reset_air3(self):
        self.timerAIR3.stop()
        self.Air3Seconds = 0
        self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds / 60, self.Air3Seconds % 60))
        if self.statusAIR3:
            self.timerAIR3.start(1000)

    def set_air3(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.AirLabel_3.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_3.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds / 60, self.Air3Seconds % 60))
            self.statusAIR3 = True
            # subtract initial second on countdown with display update
            if self.radioTimerMode == 1 and self.Air3Seconds > 1:
                self.update_air3_seconds()
            # AIR3 timer
            self.timerAIR3.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_3.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                   '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            self.AirLabel_3.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusAIR3 = False
            self.timerAIR3.stop()

    def start_stop_air3(self):
        if not self.statusAIR3:
            self.start_air3()
        else:
            self.stop_air3()

    def start_air3(self):
        self.set_air3(True)

    def stop_air3(self):
        self.set_air3(False)

    def update_air3_seconds(self):
        if self.radioTimerMode == 0:  # count up mode
            self.Air3Seconds += 1
        else:
            self.Air3Seconds -= 1
            if self.Air3Seconds < 1:
                self.stop_air3()
                self.radioTimerMode = 0
        self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds / 60, self.Air3Seconds % 60))

    def reset_air4(self):
        self.timerAIR4.stop()
        self.Air4Seconds = 0
        self.AirLabel_4.setText("Stream\n%d:%02d" % (self.Air4Seconds / 60, self.Air4Seconds % 60))
        if self.statusAIR4:
            self.timerAIR4.start(1000)

    def set_air4(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.AirLabel_4.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_4.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_4.setText("Stream\n%d:%02d" % (self.Air4Seconds / 60, self.Air4Seconds % 60))
            self.statusAIR4 = True
            # substract initial second on countdown with display update
            if self.streamTimerMode == 1 and self.Air4Seconds > 1:
                self.update_air4_seconds()
            # AIR4 timer
            self.timerAIR4.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_4.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                   '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            self.AirLabel_4.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusAIR4 = False
            self.timerAIR4.stop()

    def start_stop_air4(self):
        if not self.statusAIR4:
            self.start_air4()
        else:
            self.stop_air4()

    def start_air4(self):
        self.set_air4(True)

    def stop_air4(self):
        self.set_air4(False)

    def update_air4_seconds(self):
        if self.streamTimerMode == 0:  # count up mode
            self.Air4Seconds += 1
        else:
            self.Air4Seconds -= 1
            if self.Air4Seconds < 1:
                self.stop_air4()
                self.radioTimerMode = 0
        self.AirLabel_4.setText("Stream\n%d:%02d" % (self.Air4Seconds / 60, self.Air4Seconds % 60))

    def trigger_ntp_check(self):
        print("NTP Check triggered")
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
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
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
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
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
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
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
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
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
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
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True, type=bool):
            app.setOverrideCursor(QCursor(Qt.BlankCursor))
        settings.endGroup()

    def config_finished(self):
        self.restore_settings_from_config()
        self.weatherWidget.readConfig()
        self.weatherWidget.makeOWMApiCall()

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

    def __init__(self, oas):
        self.oas = oas
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        print("entered CheckNTPOffsetThread.run")
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        ntp_server = str(settings.value('ntpcheckserver', 'pool.ntp.org'))
        settings.endGroup()
        max_deviation = 0.3
        c = ntplib.NTPClient()
        try:
            response = c.request(ntp_server)
            if response.offset > max_deviation or response.offset < -max_deviation:
                print("offset too big: %f while checking %s" % (response.offset, ntp_server))
                self.oas.ntpWarnMessage = "Clock not NTP synchronized: offset too big"
                self.oas.ntpHadWarning = True
            else:
                if self.oas.ntpHadWarning:
                    self.oas.ntpHadWarning = False
        except socket.timeout:
            print("NTP error: timeout while checking NTP %s" % ntp_server)
            self.oas.ntpWarnMessage = "Clock not NTP synchronized"
            self.oas.ntpHadWarning = True
        except socket.gaierror:
            print("NTP error: socket error while checking NTP %s" % ntp_server)
            self.oas.ntpWarnMessage = "Clock not NTP synchronized"
            self.oas.ntpHadWarning = True
        except ntplib.NTPException as e:
            print("NTP error:", e)
            self.oas.ntpWarnMessage = str(e)
            self.oas.ntpHadWarning = True

    def stop(self):
        self.quit()


class HttpDaemon(QThread):
    def run(self):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        port = int(settings.value('httpport', 8010))
        settings.endGroup()

        try:
            handler = OASHTTPRequestHandler
            self._server = HTTPServer((HOST, port), handler)
            self._server.serve_forever()
        except OSError as error:
            print("ERROR: Starting HTTP Sever on port", port, error)

    def stop(self):
        self._server.shutdown()
        self._server.socket.close()
        self.wait()


class OASHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "OnAirScreen/%s" % versionString

    # handle HEAD request
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

    # handle GET command
    def do_GET(self):
        print(self.path)
        if self.path.startswith('/?cmd'):
            try:
                cmd, message = unquote(str(self.path)[5:]).split("=", 1)
            except ValueError:
                self.send_error(400, 'no command was given')
                return

            if len(message) > 0:
                self.send_response(200)

                # send header first
                self.send_header('Content-type', 'text-html; charset=utf-8')
                self.end_headers()

                settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
                settings.beginGroup("Network")
                port = int(settings.value('udpport', 3310))
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
# App SIGINT handler
###################################
def sigint_handler(*args):
    # Handler for SIGINT signal
    sys.stderr.write("\n")
    QApplication.quit()


###################################
# App Init
###################################
if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QApplication(sys.argv)
    icon = QIcon()
    icon.addPixmap(QPixmap(":/oas_icon/oas_icon.png"), QIcon.Normal, QIcon.Off)
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

    sys.exit(app.exec_())
