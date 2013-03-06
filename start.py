#!/usr/bin/env python
# -*- coding: utf-8 -*-
#############################################################################
##
## OnAirScreen Analog
## Copyright (C) 2013 Sascha Ludwig
## All rights reserved.
##
## start.py
## This file is part of OnAirScreen
##
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
#############################################################################

import atexit
import os
import sys
import re
from datetime import datetime
from PyQt4.QtGui import QApplication, QWidget, QCursor, QPalette, QColorDialog, QColor, QShortcut, QKeySequence, QDialog, QLineEdit, QVBoxLayout, QLabel, QIcon, QPixmap
from PyQt4.QtCore import SIGNAL, QSettings, QCoreApplication, QTimer, QObject, QVariant, QDate
from PyQt4.QtNetwork import QUdpSocket, QHostAddress, QHostInfo, QNetworkInterface
from mainscreen import Ui_MainScreen
from locale import LC_TIME, setlocale
import ntplib
import signal
import socket
from settings_functions import Settings

class MainScreen(QWidget, Ui_MainScreen):
    def __init__(self):
        QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        self.settings = Settings()
        self.restoreSettingsFromConfig()
        # quit app from settings window
        self.settings.sigExitOAS.connect(self.exitOAS)
        self.settings.sigRebootHost.connect(self.reboot_host)
        self.settings.sigShutdownHost.connect(self.shutdown_host)
        self.settings.sigConfigFinished.connect(self.configFinished)

        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True).toBool():
            self.showFullScreen()
            app.setOverrideCursor( QCursor( 10 ) );
        settings.endGroup()

        self.labelWarning.hide()

        # add hotkey bindings
        QShortcut(QKeySequence("Ctrl+F"), self, self.toggleFullScreen )
        QShortcut(QKeySequence("F"), self, self.toggleFullScreen )
        QShortcut(QKeySequence(16777429), self, self.toggleFullScreen ) # 'Display' Key on OAS USB Keyboard
        QShortcut(QKeySequence("Ctrl+Q"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("Q"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("Ctrl+C"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("ESC"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("Ctrl+S"), self, self.showsettings )
        QShortcut(QKeySequence("Ctrl+,"), self, self.showsettings )
        QShortcut(QKeySequence(" "), self, self.radioTimerStartStop )
        QShortcut(QKeySequence("0"), self, self.radioTimerStartStop )
        QShortcut(QKeySequence("."), self, self.radioTimerReset )
        QShortcut(QKeySequence(","), self, self.radioTimerReset )
        QShortcut(QKeySequence("R"), self, self.radioTimerReset )
        QShortcut(QKeySequence("1"), self, self.toggleLED1 )
        QShortcut(QKeySequence("2"), self, self.toggleLED2 )
        QShortcut(QKeySequence("3"), self, self.toggleLED3 )
        QShortcut(QKeySequence("4"), self, self.toggleLED4 )
        QShortcut(QKeySequence("M"), self, self.toggleAIR1 )
        QShortcut(QKeySequence("/"), self, self.toggleAIR1 )
        QShortcut(QKeySequence("P"), self, self.toggleAIR2 )
        QShortcut(QKeySequence("*"), self, self.toggleAIR2 )
        QShortcut(QKeySequence("Enter"), self, self.getTimerDialog )
        QShortcut(QKeySequence("Return"), self, self.getTimerDialog )

        # Setup and start timers
        self.ctimer = QTimer()
        QObject.connect(self.ctimer, SIGNAL("timeout()"), self.constantUpdate)
        self.ctimer.start(100)
        # LED timers
        self.timerLED1 = QTimer()
        QObject.connect(self.timerLED1, SIGNAL("timeout()"), self.toggleLED1)
        self.timerLED2 = QTimer()
        QObject.connect(self.timerLED2, SIGNAL("timeout()"), self.toggleLED2)
        self.timerLED3 = QTimer()
        QObject.connect(self.timerLED3, SIGNAL("timeout()"), self.toggleLED3)
        self.timerLED4 = QTimer()
        QObject.connect(self.timerLED4, SIGNAL("timeout()"), self.toggleLED4)

        # Setup OnAir Timers
        self.timerAIR1 = QTimer()
        QObject.connect(self.timerAIR1, SIGNAL("timeout()"), self.updateAIR1Seconds)
        self.Air1Seconds = 0
        self.statusAIR1 = False

        self.timerAIR2 = QTimer()
        QObject.connect(self.timerAIR2, SIGNAL("timeout()"), self.updateAIR2Seconds)
        self.Air2Seconds = 0
        self.statusAIR2 = False

        self.timerAIR3 = QTimer()
        QObject.connect(self.timerAIR3, SIGNAL("timeout()"), self.updateAIR3Seconds)
        self.Air3Seconds = 0
        self.statusAIR3 = False
        self.radioTimerMode = 0 #count up mode

        # Setup check NTP Timer
        self.timerNTP = QTimer()
        QObject.connect(self.timerNTP, SIGNAL("timeout()"), self.checkNTPOffset)
        # initial check
        self.timerNTP.start(5000)

        # Setup UDP Socket
        self.udpsock = QUdpSocket()
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        (port, foo) = settings.value('udpport', 3310).toInt()
        settings.endGroup()
        self.udpsock.bind(port, QUdpSocket.ShareAddress)
        self.udpsock.readyRead.connect(self.cmdHandler)

        # diplay all host adresses
        self.displayAllHostaddresses()

        # set NTP warning
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        if settings.value('ntpcheck', True).toBool():
            self.showWarning("Clock NTP status unknown")
        settings.endGroup()

    def radioTimerStartStop(self):
        self.startStopAIR3()

    def radioTimerReset(self):
        self.resetAIR3()
        self.radioTimerMode = 0 #count up mode

    def radioTimerSet(self, seconds):
        self.Air3Seconds = seconds
        self.radioTimerMode = 1 #count down mode
        self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds/60, self.Air3Seconds%60) )

    def getTimerDialog(self):
        # generate and display timer input window
        self.getTimeWindow = QDialog()
        self.getTimeWindow.resize(200,100)
        self.getTimeWindow.setWindowTitle("Please enter timer")
        self.getTimeWindow.timeEdit = QLineEdit("Enter timer here")
        self.getTimeWindow.timeEdit.selectAll()
        self.getTimeWindow.infoLabel = QLabel("Examples:\nenter 2,10 for 2:10 minutes\nenter 30 for 30 seconds")
        layout = QVBoxLayout()
        layout.addWidget(self.getTimeWindow.infoLabel)
        layout.addWidget(self.getTimeWindow.timeEdit)
        self.getTimeWindow.setLayout(layout)
        self.getTimeWindow.timeEdit.setFocus()
        self.getTimeWindow.timeEdit.returnPressed.connect(self.parseTimerInput)
        self.getTimeWindow.show()

    def parseTimerInput(self):
        minutes = 0
        seconds = 0
        # hide input window
        self.sender().parent().hide()
        # get timestring
        text = str(self.sender().text())
        if re.match('^[0-9]*,[0-9]*$', text):
            (minutes, seconds) = text.split(",")
            minutes = int(minutes)
            seconds = int(seconds)
        elif re.match('^[0-9]*\.[0-9]*$', text):
            (minutes, seconds) = text.split(".")
            minutes = int(minutes)
            seconds = int(seconds)
        elif re.match('^[0-9]*$', text):
            seconds = int(text)
        seconds = (minutes*60)+seconds
        self.radioTimerSet(seconds)

    def showsettings(self):
        global app
        # un-hide mousecursor
        app.setOverrideCursor( QCursor( 0 ) );
        self.settings.showsettings()

    def displayAllHostaddresses(self):
        v4addrs = list()
        v6addrs = list()
        for address in QNetworkInterface().allAddresses():
            if address.protocol() == 0:
                v4addrs.append(address.toString())
            #if address.protocol() == 1:
            #    v6addrs.append(address.toString())

        self.setCurrentSongText(", ".join(["%s" % (addr) for addr in v4addrs]))
        self.setNewsText(", ".join(["%s" % (addr) for addr in v6addrs]))

    def cmdHandler(self):
        while self.udpsock.hasPendingDatagrams():
            data, host, port = self.udpsock.readDatagram(self.udpsock.pendingDatagramSize())
            print "DATA: ", data
            lines = data.splitlines()
            for line in lines:
                (command, value) = line.split(':',1)
                print "command: '" + command + "'"
                print "value: '" + value + "'"
                if command == "NOW":
                    self.setCurrentSongText(value)
                if command == "NEXT":
                    self.setNewsText("Next: %s" % value)
                if command == "LED1":
                    if value == "OFF":
                        self.ledLogic(1, False)
                    else:
                        self.ledLogic(1, True)
                if command == "LED2":
                    if value == "OFF":
                        self.ledLogic(2, False)
                    else:
                        self.ledLogic(2, True)
                if command == "LED3":
                    if value == "OFF":
                        self.ledLogic(3, False)
                    else:
                        self.ledLogic(3, True)
                if command == "LED4":
                    if value == "OFF":
                        self.ledLogic(4, False)
                    else:
                        self.ledLogic(4, True)
                if command == "WARN":
                    if value:
                        self.showWarning(value)
                    else:
                        self.hideWarning()

                if command == "AIR1":
                    if value == "OFF":
                        self.setAIR1(False)
                    else:
                        self.setAIR1(True)

                if command == "AIR2":
                    if value == "OFF":
                        self.setAIR2(False)
                    else:
                        self.setAIR2(True)

                if command == "CMD":
                        if value == "REBOOT":
                            self.reboot_host()
                        if value == "SHUTDOWN":
                            self.shutdown_host()
                        if value == "QUIT":
                            QApplication.quit()

                if command == "CONF":
                    #split group, config and values and apply them
                    (group, paramvalue) = value.split(':',1)
                    (param, content) = paramvalue.split('=',1)
                    print "CONF:", param, content
                    if group == "General":
                        if param == "stationname":
                            self.settings.StationName.setText(content)
                        if param == "slogan":
                            self.settings.Slogan.setText(content)
                        if param == "stationcolor":
                            self.settings.setStationNameColor(self.settings.getColorFromName(content))
                        if param == "slogancolor":
                            self.settings.setSloganColor(self.settings.getColorFromName(content))

                    if group == "LED1":
                        if param == "used":
                            self.settings.LED1.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED1Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED1BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED1FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED1Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED1Timedflash.setChecked(QVariant(content).toBool())

                    if group == "LED2":
                        if param == "used":
                            self.settings.LED2.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED2Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED2BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED2FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED2Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED2Timedflash.setChecked(QVariant(content).toBool())

                    if group == "LED3":
                        if param == "used":
                            self.settings.LED3.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED3Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED3BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED3FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED3Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED3Timedflash.setChecked(QVariant(content).toBool())

                    if group == "LED4":
                        if param == "used":
                            self.settings.LED4.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED4Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED4BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED4FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED4Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED4Timedflash.setChecked(QVariant(content).toBool())

                    if group == "Clock":
                        if param == "digital":
                            if content == "True":
                                self.settings.clockDigital.setChecked(QVariant(content).toBool())
                                self.settings.clockAnalog.setChecked(not QVariant(content).toBool())
                            if content == "False":
                                self.settings.clockAnalog.setChecked(QVariant(content).toBool())
                                self.settings.clockDigital.setChecked(not QVariant(content).toBool())
                        if param == "digitalhourcolor":
                            self.settings.setDigitalHourColor(self.settings.getColorFromName(content))
                        if param == "digitalsecondcolor":
                            self.settings.setDigitalSecondColor(self.settings.getColorFromName(content))
                        if param == "digitaldigitcolor":
                            self.settings.setDigitalDigitColor(self.settings.getColorFromName(content))

                    if group == "Network":
                        if param == "udpport":
                            self.settings.udpport.setText(content)
                        if param == "tcpport":
                            self.settings.tcpport.setText(content)

                    # apply and save settings
                    self.settings.applySettings()

    def toggleLED1(self):
        if self.statusLED1:
            self.setLED1(False)
        else:
            self.setLED1(True)
    def toggleLED2(self):
        if self.statusLED2:
            self.setLED2(False)
        else:
            self.setLED2(True)
    def toggleLED3(self):
        if self.statusLED3:
            self.setLED3(False)
        else:
            self.setLED3(True)
    def toggleLED4(self):
        if self.statusLED4:
            self.setLED4(False)
        else:
            self.setLED4(True)

    def toggleAIR1(self):
        if self.statusAIR1:
            self.setAIR1(False)
        else:
            self.setAIR1(True)

    def toggleAIR2(self):
        if self.statusAIR2:
            self.setAIR2(False)
        else:
            self.setAIR2(True)

    def unsetLED1(self):
        self.ledLogic(1, False)
    def unsetLED2(self):
        self.ledLogic(2, False)
    def unsetLED3(self):
        self.ledLogic(3, False)
    def unsetLED4(self):
        self.ledLogic(4, False)

    def ledLogic(self, led, state):
        if state == True:
            if led == 1:
                if self.settings.LED1Autoflash.isChecked():
                    self.timerLED1.start(500)
                if self.settings.LED1Timedflash.isChecked():
                    self.timerLED1.start(500)
                    QTimer.singleShot(10000, self.unsetLED1)
                self.setLED1(state)
            if led == 2:
                if self.settings.LED2Autoflash.isChecked():
                    self.timerLED2.start(500)
                if self.settings.LED2Timedflash.isChecked():
                    self.timerLED2.start(500)
                    QTimer.singleShot(10000, self.unsetLED2)
                self.setLED2(state)
            if led == 3:
                if self.settings.LED3Autoflash.isChecked():
                    self.timerLED3.start(500)
                if self.settings.LED3Timedflash.isChecked():
                    self.timerLED3.start(500)
                    QTimer.singleShot(10000, self.unsetLED3)
                self.setLED3(state)
            if led == 4:
                if self.settings.LED4Autoflash.isChecked():
                    self.timerLED4.start(500)
                if self.settings.LED4Timedflash.isChecked():
                    self.timerLED4.start(500)
                    QTimer.singleShot(10000, self.unsetLED4)
                self.setLED4(state)

        if state == False:
            if led == 1:
                self.setLED1(state)
                self.timerLED1.stop()
            if led == 2:
                self.setLED2(state)
                self.timerLED2.stop()
            if led == 3:
                self.setLED3(state)
                self.timerLED3.stop()
            if led == 4:
                self.setLED4(state)
                self.timerLED4.stop()

    def setStationColor(self, newcolor):
        palette = self.labelStation.palette()
        palette.setColor(QPalette.WindowText, newcolor)
        self.labelStation.setPalette(palette)

    def setSloganColor(self, newcolor):
        palette = self.labelSlogan.palette()
        palette.setColor(QPalette.WindowText, newcolor)
        self.labelSlogan.setPalette(palette)

    def restoreSettingsFromConfig(self):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        self.labelStation.setText(settings.value('stationname', 'Radio Eriwan').toString())
        self.labelSlogan.setText(settings.value('slogan', 'Your question is our motivation').toString())
        self.setStationColor(self.settings.getColorFromName(settings.value('stationcolor', '#FFAA00').toString()))
        self.setSloganColor(self.settings.getColorFromName(settings.value('slogancolor', '#FFAA00').toString()))
        settings.endGroup()

        settings.beginGroup("LED1")
        self.setLED1Text(settings.value('text', 'ON AIR').toString())
        settings.endGroup()

        settings.beginGroup("LED2")
        self.setLED2Text(settings.value('text', 'PHONE').toString())
        settings.endGroup()

        settings.beginGroup("LED3")
        self.setLED3Text(settings.value('text', 'DOORBELL').toString())
        settings.endGroup()

        settings.beginGroup("LED4")
        self.setLED4Text(settings.value('text', 'ARI').toString())
        settings.endGroup()

        settings.beginGroup("Clock")
        self.clockWidget.setClockMode( settings.value('digital', True).toBool() )

        self.clockWidget.setDigiHourColor(self.settings.getColorFromName(settings.value('digitalhourcolor', '#3232FF').toString()))
        self.clockWidget.setDigiSecondColor(self.settings.getColorFromName(settings.value('digitalsecondcolor', '#FF9900').toString()))
        self.clockWidget.setDigiDigitColor(self.settings.getColorFromName(settings.value('digitaldigitcolor', '#3232FF').toString()))

        self.clockWidget.setLogo( settings.value('logopath', ':/astrastudio_logo/astrastudio_transparent.png').toString() )
        settings.endGroup()

    def constantUpdate(self):
        # slot for constant timer timeout
        self.updateDate()
        self.updateBacktimingText()
        self.updateBacktimingSeconds()
        if self.settings.configChanged == True:
            self.restoreSettingsFromConfig()
            self.settings.configChanged = False

    def updateDate(self):
        now = datetime.now()
        self.setLeftText( QDate.currentDate().toString("dddd, dd. MMMM yyyy") )

    def updateBacktimingText(self):
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second
        remain_min = 60-minute
        if hour > 12:
            hour -= 12

        if minute >= 0 and minute < 15:
            string = "%d Minute%s nach %d" % (minute, 'n' if minute>1 else '', hour)

        if minute >= 15 and minute < 30:
            string = "%d Minute%s vor halb %d" % (remain_min-30, 'n' if remain_min-30>1 else '', hour+1)

        if minute >= 30 and minute < 45:
            string = "%d Minute%s nach halb %d" % (30-remain_min, 'n' if 30-remain_min>1 else '', hour)

        if minute >= 45 and minute <= 59:
            string = "%d Minute%s vor %d" % (remain_min, 'n' if remain_min>1 else '', hour+1)

        if minute == 30:
           string = "halb %d" % (hour+1)

        self.setRightText( string )

    def updateBacktimingSeconds(self):
        now = datetime.now()
        second = now.second
        remain_seconds = 60-second
        self.setBacktimingSecs(remain_seconds)

    def toggleFullScreen(self):
        global app
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if not settings.value('fullscreen', 'True').toBool():
            self.showFullScreen()
            app.setOverrideCursor( QCursor( 10 ) );
            settings.setValue('fullscreen', True)
        else:
            self.showNormal()
            app.setOverrideCursor( QCursor( 0 ) );
            settings.setValue('fullscreen', False)
        settings.endGroup()

    def setAIR1(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.Air1Seconds = 0
            self.AirLabel_1.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_1.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_1.setText("Mic\n%d:%02d" % (self.Air1Seconds/60, self.Air1Seconds%60) )
            self.statusAIR1 = True
            # AIR1 timer
            self.timerAIR1.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_1.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            self.AirLabel_1.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusAIR1 = False
            self.timerAIR1.stop()

    def updateAIR1Seconds(self):
        self.Air1Seconds += 1
        self.AirLabel_1.setText("Mic\n%d:%02d" % (self.Air1Seconds/60, self.Air1Seconds%60) )

    def setAIR2(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.Air2Seconds = 0
            self.AirLabel_2.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_2.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_2.setText("Phone\n%d:%02d" % (self.Air2Seconds/60, self.Air2Seconds%60) )
            self.statusAIR2 = True
            # AIR2 timer
            self.timerAIR2.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_2.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            self.AirLabel_2.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusAIR2 = False
            self.timerAIR2.stop()

    def updateAIR2Seconds(self):
        self.Air2Seconds += 1
        self.AirLabel_2.setText("Phone\n%d:%02d" % (self.Air2Seconds/60, self.Air2Seconds%60) )

    def resetAIR3(self):
        self.timerAIR3.stop()
        self.Air3Seconds = 0
        self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds/60, self.Air3Seconds%60) )
        if self.statusAIR3 == True:
            self.timerAIR3.start(1000)

    def setAIR3(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.AirLabel_3.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_3.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds/60, self.Air3Seconds%60) )
            self.statusAIR3 = True
            # substract initial second on countdown with display update
            if self.radioTimerMode == 1 and self.Air3Seconds > 1:
                self.updateAIR3Seconds()
            # AIR3 timer
            self.timerAIR3.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_3.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            self.AirLabel_3.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusAIR3 = False
            self.timerAIR3.stop()

    def startStopAIR3(self):
        if self.statusAIR3 == False:
            self.startAIR3()
        else:
            self.stopAIR3()

    def startAIR3(self):
        self.setAIR3(True)

    def stopAIR3(self):
        self.setAIR3(False)

    def updateAIR3Seconds(self):
        if self.radioTimerMode == 0: #count up mode
            self.Air3Seconds += 1
        else:
            self.Air3Seconds -= 1
            if self.Air3Seconds < 1:
                self.stopAIR3()
                self.radioTimerMode = 0
        self.AirLabel_3.setText("Timer\n%d:%02d" % (self.Air3Seconds/60, self.Air3Seconds%60) )

    def checkNTPOffset(self):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("NTP")
        ntpcheck = settings.value('ntpcheck', True).toBool()
        settings.endGroup()
        if not ntpcheck:
            return
        self.timerNTP.stop()
        max_deviation = 0.2
        c = ntplib.NTPClient()
        try:
            response = c.request('ptbtime1.ptb.de', version=3)
            if response.offset > max_deviation or response.offset < -max_deviation:
                print "offset too big: %f" % response.offset
                self.showWarning("Clock not NTP synchronized: offset too big")
            else:
                self.hideWarning()
        except socket.timeout:
            print "timeout checking NTP"
            self.showWarning("Clock not NTP synchronized")
        except socket.gaierror:
            print "error checking NTP"
            self.showWarning("Clock not NTP synchronized")
        except:
            print "general error checking NTP"
            self.showWarning("Clock not NTP synchronized")
        self.timerNTP.start(30000)

    def setLED1(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED1")
            self.buttonLED1.setStyleSheet("color:"+settings.value('activetextcolor', '#FFFFFF').toString()+";background-color:"+settings.value('activebgcolor', '#FF0000').toString())
            settings.endGroup()
            self.statusLED1 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED1.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusLED1 = False

    def setLED2(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED2")
            self.buttonLED2.setStyleSheet("color:"+settings.value('activetextcolor', '#FFFFFF').toString()+";background-color:"+settings.value('activebgcolor', '#FF0000').toString())
            settings.endGroup()
            self.statusLED2 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED2.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusLED2 = False

    def setLED3(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED3")
            self.buttonLED3.setStyleSheet("color:"+settings.value('activetextcolor', '#FFFFFF').toString()+";background-color:"+settings.value('activebgcolor', '#FF0000').toString())
            settings.endGroup()
            self.statusLED3 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED3.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusLED3 = False

    def setLED4(self, action):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED4")
            self.buttonLED4.setStyleSheet("color:"+settings.value('activetextcolor', '#FFFFFF').toString()+";background-color:"+settings.value('activebgcolor', '#FF0000').toString())
            settings.endGroup()
            self.statusLED4 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED4.setStyleSheet("color:"+settings.value('inactivetextcolor', '#555555').toString()+";background-color:"+settings.value('inactivebgcolor', '#222222').toString())
            settings.endGroup()
            self.statusLED4 = False

    def setStation(self, text):
        self.labelStation.setText(text)

    def setSlogan(self, text):
        self.labelSlogan.setText(text)

    def setLeftText(self, text):
        self.labelTextLeft.setText(text)

    def setRightText(self, text):
        self.labelTextRight.setText(text)

    def setLED1Text(self, text):
        self.buttonLED1.setText(text)

    def setLED2Text(self, text):
        self.buttonLED2.setText(text)

    def setLED3Text(self, text):
        self.buttonLED3.setText(text)

    def setLED4Text(self, text):
        self.buttonLED4.setText(text)

    def setCurrentSongText(self, text):
        self.labelCurrentSong.setText(text)

    def setNewsText(self, text):
        self.labelNews.setText(text)

    def setBacktimingSecs(self, value):
        pass
        #self.labelSeconds.setText( str(value) )

    def showWarning(self, text):
        self.labelCurrentSong.hide()
        self.labelNews.hide()
        self.labelWarning.setText( text )
        font = self.labelWarning.font()
        font.setPointSize(45)
        self.labelWarning.setFont(font)
        self.labelWarning.show()

    def hideWarning(self):
        self.labelWarning.hide()
        self.labelCurrentSong.show()
        self.labelNews.show()
        self.labelWarning.setText( "" )
        self.labelWarning.hide()

    def exitOAS(self):
        global app
        app.exit()

    def configFinished(self):
        global app
        # hide mousecursor if in fullscreen mode
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', 'True').toBool():
            app.setOverrideCursor( QCursor( 10 ) );
        settings.endGroup()

    def reboot_host(self):
        if os.name == "posix":
            cmd = "sudo reboot"
            os.system(cmd)
        if os.name == "nt":
            cmd = "shutdown -f -r -t 0"
            pass

    def shutdown_host(self):
        if os.name == "posix":
            cmd = "sudo halt"
            os.system(cmd)
        if os.name == "nt":
            cmd = "shutdown -f -t 0"
            pass


###################################
## App SIGINT handler
###################################
def sigint_handler(*args):
    # Handler for SIGINT signal
    sys.stderr.write("\n")
    QApplication.quit()

###################################
## App Init
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

    mainscreen = MainScreen()
    mainscreen.setWindowIcon(icon)


    for i in range(1,5):
        mainscreen.ledLogic(i, False)

    mainscreen.setAIR1(False)
    mainscreen.setAIR2(False)
    mainscreen.setAIR3(False)

    mainscreen.show()

    sys.exit(app.exec_())
