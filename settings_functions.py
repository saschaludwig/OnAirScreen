#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2019 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# settings_functions.py
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

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QWidget, QColorDialog, QFileDialog
from PyQt5.QtCore import QSettings, QVariant, pyqtSignal, QUrl
import PyQt5.QtNetwork as QtNetwork
from settings import Ui_Settings
from collections import defaultdict
import json
from weatherwidget import WeatherWidget as ww

versionString = "0.9.2 (HLED Custom)"


# class OASSettings for use from OAC
class OASSettings:
    def __init__(self):
        self.config = defaultdict(dict)
        self.currentgroup = None

    def beginGroup(self, group):
        self.currentgroup = group

    def endGroup(self):
        self.currentgroup = None

    def setValue(self, name, value):
        if self.currentgroup:
            self.config[self.currentgroup][name] = value
        pass

    def value(self, name, default=None):
        try:
            return QVariant(self.config[self.currentgroup][name])
        except KeyError:
            return QVariant(default)


class Settings(QWidget, Ui_Settings):
    sigConfigChanged = pyqtSignal(int, str)
    sigExitOAS = pyqtSignal()
    sigRebootHost = pyqtSignal()
    sigShutdownHost = pyqtSignal()
    sigConfigFinished = pyqtSignal()
    sigConfigClosed = pyqtSignal()
    sigExitRemoteOAS = pyqtSignal(int)
    sigRebootRemoteHost = pyqtSignal(int)
    sigShutdownRemoteHost = pyqtSignal(int)

    def __init__(self, oacmode=False):
        self.row = -1
        QWidget.__init__(self)
        Ui_Settings.__init__(self)

        # available text clock languages
        self.textClockLanguages = ["English", "German"]

        # available Weather Widget languages
        #self.owmLanguages = {"Arabic": "ar", "Bulgarian": "bg", "Catalan": "ca", "Czech": "cz", "German": "de",
        #                     "Greek": "el", "English": "en", "Persian (Farsi)": "fa", "Finnish": "fi", "French": "fr",
        #                     "Galician": "gl", "Croatian": "hr", "Hungarian": "hu", "Italian": "it", "Japanese": "ja",
        #                     "Korean": "kr", "Latvian": "la", "Lithuanian": "lt", "Macedonian": "mk", "Dutch": "nl",
        #                     "Polish": "pl", "Portuguese": "pt", "Romanian": "ro", "Russian": "ru", "Swedish": "se",
        #                     "Slovak": "sk", "Slovenian": "sl", "Spanish": "es", "Turkish": "tr", "Ukrainian": "ua",
        #                     "Vietnamese": "vi", "Chinese Simplified": "zh_cn", "Chinese Traditional": "zh_tw."}
        #self.owmUnits = {"Kelvin": "", "Celsius": "metric", "Fahrenheit": "imperial"}

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
        # emit config finished signal
        self.sigConfigFinished.emit()
        self.sigConfigClosed.emit()

    def exitOnAirScreen(self):
        if not self.oacmode:
            # emit app close signal
            self.sigExitOAS.emit()
        else:
            self.sigExitRemoteOAS.emit(self.row)

    def rebootHost(self):
        if self.oacmode == False:
            # emit reboot host signal
            self.sigRebootHost.emit()
        else:
            self.sigRebootRemoteHost.emit(self.row)

    def shutdownHost(self):
        if self.oacmode == False:
            # emit shutdown host signal
            self.sigShutdownHost.emit()
        else:
            self.sigShutdownRemoteHost.emit(self.row)

    def resetSettings(self):
        resetSettings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        resetSettings.clear()
        self.sigConfigFinished.emit()
        self.close()

    def _connectSlots(self):
        self.ApplyButton.clicked.connect(self.applySettings)
        self.CloseButton.clicked.connect(self.closeSettings)
        self.ExitButton.clicked.connect(self.exitOnAirScreen)
        self.RebootButton.clicked.connect(self.rebootHost)
        self.ShutdownButton.clicked.connect(self.shutdownHost)
        self.LEDInactiveBGColor.clicked.connect(self.setLEDInactiveBGColor)
        self.LEDInactiveFGColor.clicked.connect(self.setLEDInactiveFGColor)
        self.LED1BGColor.clicked.connect(self.setLED1BGColor)
        self.LED1FGColor.clicked.connect(self.setLED1FGColor)
        self.LED2BGColor.clicked.connect(self.setLED2BGColor)
        self.LED2FGColor.clicked.connect(self.setLED2FGColor)
        self.LED3BGColor.clicked.connect(self.setLED3BGColor)
        self.LED3FGColor.clicked.connect(self.setLED3FGColor)
        self.ResetSettingsButton.clicked.connect(self.resetSettings)
        self.owmTestAPI.clicked.connect(self.makeOWMTestCall)

    # special OAS Settings from OAC functions

    def readConfigFromJson(self, row, config):
        # remember which row we are
        self.row = row
        confdict = json.loads(unicode(config))
        for group, content in confdict.items():
            self.settings.beginGroup(group)
            for key, value in content.items():
                self.settings.setValue(key, value)
            self.settings.endGroup()
        self.restoreSettingsFromConfig()

    def readJsonFromConfig(self):
        # return json representation of config
        return json.dumps(self.settings.config)

    def restoreSettingsFromConfig(self):
        if self.oacmode == True:
            settings = self.settings
        else:
            settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")

        # populate owm widget languages
        self.owmLanguage.clear()
        self.owmLanguage.addItems(ww.owm_languages.keys())

        # populate owm units
        self.owmUnit.clear()
        self.owmUnit.addItems(ww.owm_units.keys())

        settings.beginGroup("LEDS")
        self.setLEDInactiveBGColor(self.getColorFromName(settings.value('inactivebgcolor', '#222222')))
        self.setLEDInactiveFGColor(self.getColorFromName(settings.value('inactivetextcolor', '#555555')))
        settings.endGroup()

        settings.beginGroup("LED1")
        self.LED1.setChecked(settings.value('used', True, type=bool))
        self.LED1Text.setText(settings.value('text', 'ON AIR'))
        self.LED1Demo.setText(settings.value('text', 'ON AIR'))
        self.setLED1BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF0000')))
        self.setLED1FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF')))
        self.LED1Autoflash.setChecked(settings.value('autoflash', False, type=bool))
        self.LED1Timedflash.setChecked(settings.value('timedflash', False, type=bool))
        settings.endGroup()

        settings.beginGroup("LED2")
        self.LED2.setChecked(settings.value('used', True, type=bool))
        self.LED2Text.setText(settings.value('text', 'PHONE'))
        self.LED2Demo.setText(settings.value('text', 'PHONE'))
        self.setLED2BGColor(self.getColorFromName(settings.value('activebgcolor', '#DCDC00')))
        self.setLED2FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF')))
        self.LED2Autoflash.setChecked(settings.value('autoflash', False, type=bool))
        self.LED2Timedflash.setChecked(settings.value('timedflash', False, type=bool))
        settings.endGroup()

        settings.beginGroup("LED3")
        self.LED3.setChecked(settings.value('used', True, type=bool))
        self.LED3Text.setText(settings.value('text', 'DOORBELL'))
        self.LED3Demo.setText(settings.value('text', 'DOORBELL'))
        self.setLED3BGColor(self.getColorFromName(settings.value('activebgcolor', '#00C8C8')))
        self.setLED3FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF')))
        self.LED3Autoflash.setChecked(settings.value('autoflash', False, type=bool))
        self.LED3Timedflash.setChecked(settings.value('timedflash', False, type=bool))
        settings.endGroup()

        settings.beginGroup("Network")
        self.udpport.setText(settings.value('udpport', '3310'))
        self.httpport.setText(settings.value('httpport', '8010'))
        settings.endGroup()

        settings.beginGroup("WeatherWidget")
        self.owmWidgetEnabled.setChecked(settings.value('owmWidgetEnabled', False, type=bool))
        self.owmAPIKey.setText(settings.value('owmAPIKey', ""))
        self.owmCityID.setText(settings.value('owmCityID', "2643743"))
        self.owmLanguage.setCurrentIndex(self.owmLanguage.findText(settings.value('owmLanguage', "English")))
        self.owmUnit.setCurrentIndex(self.owmUnit.findText(settings.value('owmUnit', "Celsius")))
        self.owmAPIKey.setEnabled(settings.value('owmWidgetEnabled', False, type=bool))
        self.owmCityID.setEnabled(settings.value('owmWidgetEnabled', False, type=bool))
        self.owmLanguage.setEnabled(settings.value('owmWidgetEnabled', False, type=bool))
        self.owmUnit.setEnabled(settings.value('owmWidgetEnabled', False, type=bool))
        self.owmTestAPI.setEnabled(settings.value('owmWidgetEnabled', False, type=bool))
        self.owmTestOutput.setEnabled(settings.value('owmWidgetEnabled', False, type=bool))
        settings.endGroup()

    def getSettingsFromDialog(self):
        if self.oacmode == True:
            settings = self.settings
        else:
            settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")

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

        settings.beginGroup("Network")
        settings.setValue('udpport', self.udpport.displayText())
        settings.setValue('httpport', self.httpport.displayText())
        settings.endGroup()

        settings.beginGroup("WeatherWidget")
        settings.setValue('owmWidgetEnabled', self.owmWidgetEnabled.isChecked())
        settings.setValue('owmAPIKey', self.owmAPIKey.displayText())
        settings.setValue('owmCityID', self.owmCityID.displayText())
        settings.setValue('owmLanguage', self.owmLanguage.currentText())
        settings.setValue('owmUnit', self.owmUnit.currentText())
        settings.endGroup()

        if self.oacmode == True:
            # send oac a signal the the config has changed
            self.sigConfigChanged.emit(self.row, self.readJsonFromConfig())

    def applySettings(self):
        # apply settings button pressed
        self.getSettingsFromDialog()
        self.sigConfigFinished.emit()

    def closeSettings(self):
        # close settings button pressed
        self.restoreSettingsFromConfig()

    def makeOWMTestCall(self):
        appid = self.owmAPIKey.displayText()
        cityID = self.owmCityID.displayText()
        units = ww.owm_units.get(self.owmUnit.currentText())
        lang = ww.owm_languages.get(self.owmLanguage.currentText())
        url = "http://api.openweathermap.org/data/2.5/weather?id=" + cityID + "&units=" + units + "&lang=" + lang + "&appid=" + appid

        req = QtNetwork.QNetworkRequest(QUrl(url))
        self.nam = QtNetwork.QNetworkAccessManager()
        self.nam.finished.connect(self.handleOWMResponse)
        self.nam.get(req)

    def handleOWMResponse(self, reply):
        er = reply.error()

        if er == QtNetwork.QNetworkReply.NoError:
            bytes_string = reply.readAll()
            replyString = str(bytes_string, 'utf-8')
            self.owmTestOutput.setPlainText(replyString)
        else:
            errorString = "Error occured: {}, {}".format(er, reply.errorString())
            self.owmTestOutput.setPlainText(errorString)

    def setLED1BGColor(self, newcolor=False):
        palette = self.LED1Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.LED1Demo.setPalette(palette)

    def setLEDInactiveBGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLEDInactiveFGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLED1FGColor(self, newcolor=False):
        palette = self.LED1Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.LED1Demo.setPalette(palette)

    def setLED2BGColor(self, newcolor=False):
        palette = self.LED2Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.LED2Demo.setPalette(palette)

    def setLED2FGColor(self, newcolor=False):
        palette = self.LED2Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.LED2Demo.setPalette(palette)

    def setLED3BGColor(self, newcolor=False):
        palette = self.LED3Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.LED3Demo.setPalette(palette)

    def setLED3FGColor(self, newcolor=False):
        palette = self.LED3Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.LED3Demo.setPalette(palette)

    def getLEDInactiveBGColor(self):
        palette = self.LEDInactive.palette()
        color = palette.window().color()
        return color

    def getLEDInactiveFGColor(self):
        palette = self.LEDInactive.palette()
        color = palette.windowText().color()
        return color

    def getLED1BGColor(self):
        palette = self.LED1Demo.palette()
        color = palette.window().color()
        return color

    def getLED2BGColor(self):
        palette = self.LED2Demo.palette()
        color = palette.window().color()
        return color

    def getLED3BGColor(self):
        palette = self.LED3Demo.palette()
        color = palette.window().color()
        return color

    def getLED1FGColor(self):
        palette = self.LED1Demo.palette()
        color = palette.windowText().color()
        return color

    def getLED2FGColor(self):
        palette = self.LED2Demo.palette()
        color = palette.windowText().color()
        return color

    def getLED3FGColor(self):
        palette = self.LED3Demo.palette()
        color = palette.windowText().color()
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
        color.setNamedColor(colorname)
        return color
