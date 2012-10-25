#!/usr/bin/env python
# -*- coding: utf-8 -*-

# OnAirScreen
# Copyright 2012, Sascha Ludwig <sascha@astrastudio.de>
# start.py
#
#    This file is part of OnAirScreen
#
#    OnAirScreen is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnAirScreen is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnAirScreen.  If not, see <http://www.gnu.org/licenses/>.
#

import os
from datetime import datetime
from PyQt4.QtGui import QApplication, QWidget, QCursor, QPalette, QColorDialog, QColor, QShortcut, QKeySequence
from PyQt4.QtCore import SIGNAL, QSettings, QCoreApplication, QTimer, QObject
from PyQt4.QtNetwork import QUdpSocket, QHostAddress, QHostInfo, QNetworkInterface
from mainscreen import Ui_MainScreen
from settings import Ui_Settings
from locale import LC_TIME, setlocale

versionString = "0.4"

class Settings(QWidget, Ui_Settings):
    def __init__(self):
        QWidget.__init__(self)
        Ui_Settings.__init__(self)
        self.setupUi(self)
        self._connectSlots()
        self.hide()
        # read the config, add missing values, save config and re-read config
        self.restoreSettingsFromConfig()
        self.configChanged = True
        # set version string
        self.versionLabel.setText("Version %s" % versionString)

    def showsettings(self):
        global app
        # un-hide mousecursor
        app.setOverrideCursor( QCursor( 0 ) );
        self.show()

    def hidesettings(self):
        global app
        # hide mousecursor if in fullscreen mode
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', 'True').toBool():
            app.setOverrideCursor( QCursor( 10 ) );
        settings.endGroup()

    def closeEvent(self, event):
        global app
        # hide mousecursor if in fullscreen mode
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', 'True').toBool():
            app.setOverrideCursor( QCursor( 10 ) );
        settings.endGroup()

    def exitOnAirScreen(self):
        global app
        app.exit()

    def _connectSlots(self):
        self.connect(self.ApplyButton, SIGNAL("clicked()"), self.applySettings )
        self.connect(self.CloseButton, SIGNAL("clicked()"), self.closeSettings )
        self.connect(self.ExitButton, SIGNAL("clicked()"), self.exitOnAirScreen )
        self.connect(self.LEDInactiveBGColor, SIGNAL("clicked()"), self.setLEDInactiveBGColor )
        self.connect(self.LEDInactiveFGColor, SIGNAL("clicked()"), self.setLEDInactiveFGColor )
        self.connect(self.LED1BGColor, SIGNAL("clicked()"), self.setLED1BGColor )
        self.connect(self.LED1FGColor, SIGNAL("clicked()"), self.setLED1FGColor )
        self.connect(self.LED2BGColor, SIGNAL("clicked()"), self.setLED2BGColor )
        self.connect(self.LED2FGColor, SIGNAL("clicked()"), self.setLED2FGColor )
        self.connect(self.LED3BGColor, SIGNAL("clicked()"), self.setLED3BGColor )
        self.connect(self.LED3FGColor, SIGNAL("clicked()"), self.setLED3FGColor )
        self.connect(self.LED4BGColor, SIGNAL("clicked()"), self.setLED4BGColor )
        self.connect(self.LED4FGColor, SIGNAL("clicked()"), self.setLED4FGColor )

        self.connect(self.StationNameColor, SIGNAL("clicked()"), self.setStationNameColor )
        self.connect(self.SloganColor, SIGNAL("clicked()"), self.setSloganColor )

        self.connect(self, SIGNAL("triggered()"), self.closeEvent )

    def restoreSettingsFromConfig(self):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        self.StationName.setText(settings.value('stationname', 'Radio Eriwan').toString())
        self.Slogan.setText(settings.value('slogan', 'Your question is our motivation').toString())
        self.setStationNameColor(self.getColorFromName(settings.value('stationcolor', '#FFAA00').toString()))
        self.setSloganColor(self.getColorFromName(settings.value('slogancolor', '#FFAA00').toString()))
        settings.endGroup()

        settings.beginGroup("VU")
        self.checkBox_VU.setChecked(settings.value('vumeters', False).toBool())
        self.checkBox_TooLoud.setChecked(settings.value('tooloud', True).toBool())
        self.TooLoudText.setText(settings.value('tooloudtext', 'TOO LOUD').toString())
        settings.endGroup()

        settings.beginGroup("LEDS")
        self.setLEDInactiveBGColor(self.getColorFromName(settings.value('inactivebgcolor', '#222222').toString()))
        self.setLEDInactiveFGColor(self.getColorFromName(settings.value('inactivetextcolor', '#555555').toString()))
        settings.endGroup()

        settings.beginGroup("LED1")
        self.LED1.setChecked(settings.value('used', True).toBool())
        self.LED1Text.setText(settings.value('text', 'ON AIR').toString())
        self.setLED1BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF0000').toString()))
        self.setLED1FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED1Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED1Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("LED2")
        self.LED2.setChecked(settings.value('used', True).toBool())
        self.LED2Text.setText(settings.value('text', 'PHONE').toString())
        self.setLED2BGColor(self.getColorFromName(settings.value('activebgcolor', '#DCDC00').toString()))
        self.setLED2FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED2Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED2Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("LED3")
        self.LED3.setChecked(settings.value('used', True).toBool())
        self.LED3Text.setText(settings.value('text', 'DOORBELL').toString())
        self.setLED3BGColor(self.getColorFromName(settings.value('activebgcolor', '#00C8C8').toString()))
        self.setLED3FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED3Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED3Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("LED4")
        self.LED4.setChecked(settings.value('used', True).toBool())
        self.LED4Text.setText(settings.value('text', 'ARI').toString())
        self.setLED4BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF00FF').toString()))
        self.setLED4FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED4Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED4Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("Network")
        self.udpport.setText(settings.value('udpport', '3310').toString())
        settings.endGroup()

    def getSettingsFromDialog(self):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        settings.setValue('stationname', self.StationName.displayText())
        settings.setValue('slogan', self.Slogan.displayText())
        settings.setValue('stationcolor', self.getStationNameColor().name())
        settings.setValue('slogancolor', self.getSloganColor().name())
        settings.endGroup()

        settings.beginGroup("VU")
        settings.setValue('vumeters', self.checkBox_VU.isChecked())
        settings.setValue('tooloud', self.checkBox_TooLoud.isChecked())
        settings.setValue('tooloudtext', self.TooLoudText.displayText())
        settings.endGroup()

        settings.beginGroup("LEDS")
        settings.setValue('inactivebgcolor', self.getLEDInactiveBGColor().name())
        settings.setValue('inactivetextcolor', self.getLEDInactiveFGColor().name())
        settings.endGroup()

        settings.beginGroup("LED1")
        settings.setValue('used', self.LED1.isChecked())
        settings.setValue('text', self.LED1Text.displayText())
        settings.setValue('activebgcolor', self.getLED1BGColor().name())
        settings.setValue('activetextcolor', self.getLED1FGColor().name())
        settings.setValue('autoflash', self.LED1Autoflash.isChecked())
        settings.setValue('timedflash', self.LED1Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("LED2")
        settings.setValue('used', self.LED2.isChecked())
        settings.setValue('text', self.LED2Text.displayText())
        settings.setValue('activebgcolor', self.getLED2BGColor().name())
        settings.setValue('activetextcolor', self.getLED2FGColor().name())
        settings.setValue('autoflash', self.LED2Autoflash.isChecked())
        settings.setValue('timedflash', self.LED2Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("LED3")
        settings.setValue('used', self.LED3.isChecked())
        settings.setValue('text', self.LED3Text.displayText())
        settings.setValue('activebgcolor', self.getLED3BGColor().name())
        settings.setValue('activetextcolor', self.getLED3FGColor().name())
        settings.setValue('autoflash', self.LED3Autoflash.isChecked())
        settings.setValue('timedflash', self.LED3Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("LED4")
        settings.setValue('used', self.LED4.isChecked())
        settings.setValue('text', self.LED4Text.displayText())
        settings.setValue('activebgcolor', self.getLED4BGColor().name())
        settings.setValue('activetextcolor', self.getLED4FGColor().name())
        settings.setValue('autoflash', self.LED4Autoflash.isChecked())
        settings.setValue('timedflash', self.LED4Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("Network")
        settings.setValue('udpport', self.udpport.displayText())
        settings.endGroup()

    def applySettings(self):
        #apply settings button pressed
        self.getSettingsFromDialog()
        self.configChanged = True

    def closeSettings(self):
        #close settings button pressed
        self.restoreSettingsFromConfig()
        self.hidesettings()

    def setLED1BGColor(self, newcolor=False):
        palette = self.LED1Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED1Text.setPalette(palette)

    def setLEDInactiveBGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLEDInactiveFGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLED1FGColor(self, newcolor=False):
        palette = self.LED1Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED1Text.setPalette(palette)

    def setLED2BGColor(self, newcolor=False):
        palette = self.LED2Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED2FGColor(self, newcolor=False):
        palette = self.LED2Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED3BGColor(self, newcolor=False):
        palette = self.LED3Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED3FGColor(self, newcolor=False):
        palette = self.LED3Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED4BGColor(self, newcolor=False):
        palette = self.LED4Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED4Text.setPalette(palette)

    def setLED4FGColor(self, newcolor=False):
        palette = self.LED4Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED4Text.setPalette(palette)

    def setStationNameColor(self, newcolor=False):
        palette = self.StationName.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.StationName.setPalette(palette)

    def setSloganColor(self, newcolor=False):
        palette = self.Slogan.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.Slogan.setPalette(palette)

    def getStationNameColor(self):
        palette = self.StationName.palette()
        color = palette.text().color()
        return color

    def getSloganColor(self):
        palette = self.Slogan.palette()
        color = palette.text().color()
        return color

    def getLEDInactiveBGColor(self):
        palette = self.LEDInactive.palette()
        color = palette.base().color()
        return color

    def getLEDInactiveFGColor(self):
        palette = self.LEDInactive.palette()
        color = palette.text().color()
        return color

    def getLED1BGColor(self):
        palette = self.LED1Text.palette()
        color = palette.base().color()
        return color

    def getLED2BGColor(self):
        palette = self.LED2Text.palette()
        color = palette.base().color()
        return color

    def getLED3BGColor(self):
        palette = self.LED3Text.palette()
        color = palette.base().color()
        return color

    def getLED4BGColor(self):
        palette = self.LED4Text.palette()
        color = palette.base().color()
        return color

    def getLED1FGColor(self):
        palette = self.LED1Text.palette()
        color = palette.text().color()
        return color

    def getLED2FGColor(self):
        palette = self.LED2Text.palette()
        color = palette.text().color()
        return color

    def getLED3FGColor(self):
        palette = self.LED3Text.palette()
        color = palette.text().color()
        return color

    def getLED4FGColor(self):
        palette = self.LED4Text.palette()
        color = palette.text().color()
        return color

    def openColorDialog(self, initcolor):
        colordialog = QColorDialog()
        selectedcolor = colordialog.getColor(initcolor, None, 'Please select a color')
        if selectedcolor.isValid():
            return selectedcolor
        else:
            return initcolor

    def getColorFromName(self, colorname):
        color = QColor()
        color.setNamedColor( colorname )
        return color

class MainScreen(QWidget, Ui_MainScreen):
    def __init__(self):
        QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        self.settings = Settings()
        self.restoreSettingsFromConfig()

        # set locale
        locale = 'de_DE.UTF-8'
        try:
            setlocale(LC_TIME, locale)
        except:
            print 'error: setting locale %s' % locale
            pass

        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True).toBool():
            self.showFullScreen()
        settings.endGroup()

        self.labelWarning.hide()

        # add hotkey bindings
        QShortcut(QKeySequence("Ctrl+F"), self, self.toggleFullScreen )
        QShortcut(QKeySequence("Ctrl+Q"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("Ctrl+C"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("ESC"), self, QCoreApplication.instance().quit )
        QShortcut(QKeySequence("Ctrl+S"), self, self.settings.showsettings )
        QShortcut(QKeySequence("Ctrl+,"), self, self.settings.showsettings )

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

        # Setup UDP Socket
        self.sock = QUdpSocket()
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        (port, foo) = settings.value('udpport', 3310).toInt()
        settings.endGroup()
        self.sock.bind(port, QUdpSocket.ShareAddress)
        self.sock.readyRead.connect(self.cmdHandler)

        # diplay all host adresses
        self.displayAllHostaddresses()

    def displayAllHostaddresses(self):
        v4addrs = list()
        v6addrs = list()
        for address in QNetworkInterface().allAddresses():
            if address.protocol() == 0:
                v4addrs.append(address.toString())
            if address.protocol() == 1:
                v6addrs.append(address.toString())

        self.setCurrentSongText(", ".join(["%s" % (addr) for addr in v4addrs]))
        self.setNewsText(", ".join(["%s" % (addr) for addr in v6addrs]))

    def cmdHandler(self):
        while self.sock.hasPendingDatagrams():
            data, host, port = self.sock.readDatagram(self.sock.pendingDatagramSize())
            print "DATA: "+ data
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
                if command == "CONF":
                    #split config values and apply them
                    (param, content) = value.split('=',1)
                    if param == "STATIONNAME":
                        self.settings.StationName.setText(content)
                    if param == "SLOGAN":
                        self.settings.Slogan.setText(content)
                    if param == "STATIONNAMECOLOR":
                        self.settings.setStationNameColor(self.settings.getColorFromName(content))
                    if param == "SLOGANCOLOR":
                        self.settings.setSloganColor(self.settings.getColorFromName(content))

                    if param == "LED1USED":
                        self.settings.LED1.setChecked(content)
                    if param == "LED1TEXT":
                        self.settings.LED1Text.setText(content)
                    if param == "LED1BGCOLOR":
                        self.settings.setLED1BGColor(self.settings.getColorFromName(content))
                    if param == "LED1TEXTCOLOR":
                        self.settings.setLED1FGColor(self.settings.getColorFromName(content))
                    if param == "LED1AUTOFLASH":
                        self.settings.LED1Autoflash.setChecked(content)
                    if param == "LED1TIMEDFLASH":
                        self.settings.LED1Timedflash.setChecked(content)

                    if param == "LED2USED":
                        self.settings.LED2.setChecked(content)
                    if param == "LED2TEXT":
                        self.settings.LED2Text.setText(content)
                    if param == "LED2BGCOLOR":
                        self.settings.setLED2BGColor(self.settings.getColorFromName(content))
                    if param == "LED2TEXTCOLOR":
                        self.settings.setLED2FGColor(self.settings.getColorFromName(content))
                    if param == "LED2AUTOFLASH":
                        self.settings.LED2Autoflash.setChecked(content)
                    if param == "LED2TIMEDFLASH":
                        self.settings.LED2Timedflash.setChecked(content)

                    if param == "LED3USED":
                        self.settings.LED3.setChecked(content)
                    if param == "LED3TEXT":
                        self.settings.LED3Text.setText(content)
                    if param == "LED3BGCOLOR":
                        self.settings.setLED3BGColor(self.settings.getColorFromName(content))
                    if param == "LED3TEXTCOLOR":
                        self.settings.setLED3FGColor(self.settings.getColorFromName(content))
                    if param == "LED3AUTOFLASH":
                        self.settings.LED3Autoflash.setChecked(content)
                    if param == "LED3TIMEDFLASH":
                        self.settings.LED3Timedflash.setChecked(content)

                    if param == "LED4USED":
                        self.settings.LED4.setChecked(content)
                    if param == "LED4TEXT":
                        self.settings.LED4Text.setText(content)
                    if param == "LED4BGCOLOR":
                        self.settings.setLED4BGColor(self.settings.getColorFromName(content))
                    if param == "LED4TEXTCOLOR":
                        self.settings.setLED4FGColor(self.settings.getColorFromName(content))
                    if param == "LED4AUTOFLASH":
                        self.settings.LED4Autoflash.setChecked(content)
                    if param == "LED4TIMEDFLASH":
                        self.settings.LED4Timedflash.setChecked(content)

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

    def constantUpdate(self):
        # slot for constant timer timeout
        self.updateClock()
        self.updateDate()
        self.updateBacktimingText()
        self.updateBacktimingSeconds()
        if self.settings.configChanged == True:
            self.restoreSettingsFromConfig()
            self.settings.configChanged = False

    def updateClock(self):
        now = datetime.now()
        self.setClock( now.strftime("%H:%M:%S") )

    def updateDate(self):
        now = datetime.now()
        self.setLeftText( now.strftime("%A, %d. %B %Y") )

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

    def setClock(self, text):
        self.labelClock.setText(text)

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

    def setVULeft(self, value):
        self.progressL.setValue(value)

    def setVURight(self, value):
        self.progressR.setValue(value)

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

if __name__ == "__main__":
    from sys import argv, exit

    app = QApplication(argv)
    mainscreen = MainScreen()

    mainscreen.setVULeft(0)
    mainscreen.setVURight(0)

    for i in range(1,5):
        mainscreen.ledLogic(i, False)

    mainscreen.show()

    exit(app.exec_())
