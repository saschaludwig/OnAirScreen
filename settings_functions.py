#!/usr/bin/env python
# -*- coding: utf-8 -*-
#############################################################################
##
## OnAirScreen Analog
## Copyright (C) 2013 Sascha Ludwig
## All rights reserved.
##
## settings_functions.py
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

from PyQt4.QtGui import QApplication, QWidget, QCursor, QPalette, QColorDialog, QColor, QShortcut, QKeySequence, QFileDialog
from PyQt4.QtCore import SIGNAL, QSettings, QCoreApplication, QTimer, QObject, QVariant, pyqtSignal
from PyQt4.QtNetwork import QUdpSocket, QHostAddress, QHostInfo, QNetworkInterface
from settings import Ui_Settings
from collections import defaultdict
import json

versionString = "0.7"

# class OASSettings for use from OAC
class OASSettings():
    def __init__(self):
        self.config = defaultdict(dict)
        self.currentgroup = None

    def beginGroup(self, group):
        self.currentgroup = group

    def endGroup(self):
        self.currentgroup = None

    def setValue(self, name, value):
        if self.currentgroup:
            self.config[self.currentgroup][name] = unicode(value)
        pass

    def value(self, name, default=None):
        try:
            return QVariant(self.config[self.currentgroup][name])
        except KeyError:
            return QVariant(default)

class Settings(QWidget, Ui_Settings):
    sigConfigChanged = pyqtSignal(int, unicode)
    sigExitOAS = pyqtSignal()
    sigRebootHost = pyqtSignal()
    sigShutdownHost = pyqtSignal()
    sigConfigFinished = pyqtSignal()
    sigExitRemoteOAS = pyqtSignal(int)
    sigRebootRemoteHost = pyqtSignal(int)
    sigShutdownRemoteHost = pyqtSignal(int)
    def __init__(self, oacmode=False):
        self.row = -1
        QWidget.__init__(self)
        Ui_Settings.__init__(self)
        self.setupUi(self)
        self._connectSlots()
        self.hide()
        # create settings object for use with OAC
        self.settings = OASSettings()
        self.oacmode = oacmode

        # read the config, add missing values, save config and re-read config
        self.restoreSettingsFromConfig()
        self.sigConfigFinished.emit()

        # set version string
        self.versionLabel.setText("Version %s" % versionString)

    def showsettings(self):
        self.show()

    def closeEvent(self, event):
        #emit config finished signal
        self.sigConfigFinished.emit()

    def exitOnAirScreen(self):
        if self.oacmode == False:
            #emit app close signal
            self.sigExitOAS.emit()
        else:
            self.sigExitRemoteOAS.emit(self.row)

    def rebootHost(self):
        if self.oacmode == False:
            #emit reboot host signal
            self.sigRebootHost.emit()
        else:
            self.sigRebootRemoteHost.emit(self.row)

    def shutdownHost(self):
        if self.oacmode == False:
            #emit shutdown host signal
            self.sigShutdownHost.emit()
        else:
            self.sigShutdownRemoteHost.emit(self.row)

    def _connectSlots(self):
        self.connect(self.ApplyButton, SIGNAL("clicked()"), self.applySettings )
        self.connect(self.CloseButton, SIGNAL("clicked()"), self.closeSettings )
        self.connect(self.ExitButton, SIGNAL("clicked()"), self.exitOnAirScreen )
        self.connect(self.RebootButton, SIGNAL("clicked()"), self.rebootHost )
        self.connect(self.ShutdownButton, SIGNAL("clicked()"), self.shutdownHost )
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

        self.connect(self.DigitalHourColorButton, SIGNAL("clicked()"), self.setDigitalHourColor )
        self.connect(self.DigitalSecondColorButton, SIGNAL("clicked()"), self.setDigitalSecondColor )
        self.connect(self.DigitalDigitColorButton, SIGNAL("clicked()"), self.setDigitalDigitColor )
        self.connect(self.logoButton, SIGNAL("clicked()"), self.openLogoPathSelector )
        self.connect(self.resetLogoButton, SIGNAL("clicked()"), self.resetLogo )

        self.connect(self.StationNameColor, SIGNAL("clicked()"), self.setStationNameColor )
        self.connect(self.SloganColor, SIGNAL("clicked()"), self.setSloganColor )

        self.connect(self, SIGNAL("triggered()"), self.closeEvent )

    # special OAS Settings from OAC functions

    def readConfigFromJson(self, row, config):
        #remember which row we are
        self.row = row
        confdict = json.loads(unicode(config))
        for group, content in confdict.items():
            self.settings.beginGroup(group)
            for key, value in content.items():
                self.settings.setValue(key, value)
            self.settings.endGroup()
        self.restoreSettingsFromConfig()

    def readJsonFromConfig(self):
        #return json representation of config
        return json.dumps(self.settings.config)

    def restoreSettingsFromConfig(self):
        if self.oacmode == True:
            settings = self.settings
        else:
            settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        self.StationName.setText(settings.value('stationname', 'Radio Eriwan').toString())
        self.Slogan.setText(settings.value('slogan', 'Your question is our motivation').toString())
        self.setStationNameColor(self.getColorFromName(settings.value('stationcolor', '#FFAA00').toString()))
        self.setSloganColor(self.getColorFromName(settings.value('slogancolor', '#FFAA00').toString()))
        settings.endGroup()

        settings.beginGroup("NTP")
        self.checkBox_NTPCheck.setChecked(settings.value('ntpcheck', True).toBool())
        self.NTPCheckServer.setText(settings.value('ntpcheckserver', 'pool.ntp.org').toString())
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

        settings.beginGroup("Clock")
        self.clockDigital.setChecked(settings.value('digital', True).toBool())
        self.clockAnalog.setChecked(not settings.value('digital', True).toBool())
        self.setDigitalHourColor(self.getColorFromName(settings.value('digitalhourcolor', '#3232FF').toString()))
        self.setDigitalSecondColor(self.getColorFromName(settings.value('digitalsecondcolor', '#FF9900').toString()))
        self.setDigitalDigitColor(self.getColorFromName(settings.value('digitaldigitcolor', '#3232FF').toString()))
        self.logoPath.setText(settings.value('logopath', ':/astrastudio_logo/astrastudio_transparent.png').toString())
        settings.endGroup()

        settings.beginGroup("Network")
        self.udpport.setText(settings.value('udpport', '3310').toString())
        self.tcpport.setText(settings.value('tcpport', '3310').toString())
        settings.endGroup()

    def getSettingsFromDialog(self):
        if self.oacmode == True:
            settings = self.settings
        else:
            settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        settings.setValue('stationname', self.StationName.displayText())
        settings.setValue('slogan', self.Slogan.displayText())
        settings.setValue('stationcolor', self.getStationNameColor().name())
        settings.setValue('slogancolor', self.getSloganColor().name())
        settings.endGroup()

        settings.beginGroup("NTP")
        settings.setValue('ntpcheck', self.checkBox_NTPCheck.isChecked())
        settings.setValue('ntpcheckserver', self.NTPCheckServer.displayText())
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

        settings.beginGroup("Clock")
        settings.setValue('digital', self.clockDigital.isChecked())
        settings.setValue('digitalhourcolor', self.getDigitalHourColor().name())
        settings.setValue('digitalsecondcolor', self.getDigitalSecondColor().name())
        settings.setValue('digitaldigitcolor', self.getDigitalDigitColor().name())
        settings.setValue('logopath', self.logoPath.text())
        settings.endGroup()

        settings.beginGroup("Network")
        settings.setValue('udpport', self.udpport.displayText())
        settings.setValue('tcpport', self.tcpport.displayText())
        settings.endGroup()

        if self.oacmode == True:
            # send oac a signal the the config has changed
            self.sigConfigChanged.emit(self.row, self.readJsonFromConfig())


    def applySettings(self):
        #apply settings button pressed
        self.getSettingsFromDialog()
        self.sigConfigFinished.emit()

    def closeSettings(self):
        #close settings button pressed
        self.restoreSettingsFromConfig()

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

    def getDigitalHourColor(self):
        palette = self.DigitalHourColor.palette()
        color = palette.window().color()
        return color

    def getDigitalSecondColor(self):
        palette = self.DigitalSecondColor.palette()
        color = palette.window().color()
        return color

    def getDigitalDigitColor(self):
        palette = self.DigitalDigitColor.palette()
        color = palette.window().color()
        return color

    def setDigitalHourColor(self, newcolor=False):
        palette = self.DigitalHourColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalHourColor.setPalette(palette)

    def setDigitalSecondColor(self, newcolor=False):
        palette = self.DigitalSecondColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalSecondColor.setPalette(palette)

    def setDigitalDigitColor(self, newcolor=False):
        palette = self.DigitalDigitColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalDigitColor.setPalette(palette)

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

    def openLogoPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)" )
        if filename:
            self.logoPath.setText(filename)

    def resetLogo(self):
        self.logoPath.setText(":/astrastudio_logo/astrastudio_transparent.png")

