#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2020 Sascha Ludwig, astrastudio.de
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
from PyQt5.QtWidgets import QWidget, QColorDialog, QFileDialog, QErrorMessage, QMessageBox, QPushButton
from PyQt5.QtCore import QSettings, QVariant, pyqtSignal, QUrl, QUrlQuery
import PyQt5.QtNetwork as QtNetwork
from settings import Ui_Settings
from collections import defaultdict
import json
import textwrap
from uuid import getnode
from weatherwidget import WeatherWidget as ww
from utils import TimerUpdateMessageBox
try:
    from distribution import distributionString
except ModuleNotFoundError:
    distributionString = "OpenSource"

versionString = "0.9.2"


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
    sigCheckForUpdate = pyqtSignal()

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
        # set update check mode
        self.manual_update_check = False
        self.sigCheckForUpdate.connect(self.check_for_updates)

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
        self.LED4BGColor.clicked.connect(self.setLED4BGColor)
        self.LED4FGColor.clicked.connect(self.setLED4FGColor)
        self.ResetSettingsButton.clicked.connect(self.resetSettings)

        self.DigitalHourColorButton.clicked.connect(self.setDigitalHourColor)
        self.DigitalSecondColorButton.clicked.connect(self.setDigitalSecondColor)
        self.DigitalDigitColorButton.clicked.connect(self.setDigitalDigitColor)
        self.logoButton.clicked.connect(self.openLogoPathSelector)
        self.resetLogoButton.clicked.connect(self.resetLogo)

        self.StationNameColor.clicked.connect(self.setStationNameColor)
        self.SloganColor.clicked.connect(self.setSloganColor)

        self.owmTestAPI.clicked.connect(self.makeOWMTestCall)
        self.updateCheckNowButton.clicked.connect(self.trigger_manual_check_for_updates)

    #        self.triggered.connect(self.closeEvent)

    # special OAS Settings from OAC functions

    def readConfigFromJson(self, row, config):
        # remember which row we are
        self.row = row
        conf_dict = json.loads(config)
        for group, content in conf_dict.items():
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

        # polulate text clock languages
        self.textClockLanguage.clear()
        self.textClockLanguage.addItems(self.textClockLanguages)

        # populate owm widget languages
        self.owmLanguage.clear()
        self.owmLanguage.addItems(ww.owm_languages.keys())

        # populate owm units
        self.owmUnit.clear()
        self.owmUnit.addItems(ww.owm_units.keys())

        settings.beginGroup("General")
        self.StationName.setText(settings.value('stationname', 'Radio Eriwan'))
        self.Slogan.setText(settings.value('slogan', 'Your question is our motivation'))
        self.setStationNameColor(self.getColorFromName(settings.value('stationcolor', '#FFAA00')))
        self.setSloganColor(self.getColorFromName(settings.value('slogancolor', '#FFAA00')))
        self.checkBox_UpdateCheck.setChecked(settings.value('updatecheck', False, type=bool))
        self.updateKey.setEnabled(settings.value('updatecheck', False, type=bool))
        self.label_28.setEnabled(settings.value('updatecheck', False, type=bool))
        self.updateCheckNowButton.setEnabled(settings.value('updatecheck', False, type=bool))
        self.checkBox_IncludeBetaVersions.setEnabled(settings.value('updatecheck', False, type=bool))
        self.updateKey.setText(settings.value('updatekey', ''))
        self.checkBox_IncludeBetaVersions.setChecked(settings.value('updateincludebeta', False, type=bool))
        settings.endGroup()

        settings.beginGroup("NTP")
        self.checkBox_NTPCheck.setChecked(settings.value('ntpcheck', True, type=bool))
        self.NTPCheckServer.setText(settings.value('ntpcheckserver', 'pool.ntp.org'))
        settings.endGroup()

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

        settings.beginGroup("LED4")
        self.LED4.setChecked(settings.value('used', True, type=bool))
        self.LED4Text.setText(settings.value('text', 'ARI'))
        self.LED4Demo.setText(settings.value('text', 'ARI'))
        self.setLED4BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF00FF')))
        self.setLED4FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF')))
        self.LED4Autoflash.setChecked(settings.value('autoflash', False, type=bool))
        self.LED4Timedflash.setChecked(settings.value('timedflash', False, type=bool))
        settings.endGroup()

        settings.beginGroup("Clock")
        self.clockDigital.setChecked(settings.value('digital', True, type=bool))
        self.clockAnalog.setChecked(not settings.value('digital', True, type=bool))
        self.showSeconds.setChecked(settings.value('showSeconds', False, type=bool))
        self.staticColon.setChecked(settings.value('staticColon', False, type=bool))
        self.setDigitalHourColor(self.getColorFromName(settings.value('digitalhourcolor', '#3232FF')))
        self.setDigitalSecondColor(self.getColorFromName(settings.value('digitalsecondcolor', '#FF9900')))
        self.setDigitalDigitColor(self.getColorFromName(settings.value('digitaldigitcolor', '#3232FF')))
        self.logoPath.setText(
            settings.value('logopath', ':/astrastudio_logo/images/astrastudio_transparent.png'))
        settings.endGroup()

        settings.beginGroup("Network")
        self.udpport.setText(settings.value('udpport', '3310'))
        self.httpport.setText(settings.value('httpport', '8010'))
        settings.endGroup()

        settings.beginGroup("Formatting")
        self.dateFormat.setText(settings.value('dateFormat', 'dddd, dd. MMMM yyyy'))
        self.textClockLanguage.setCurrentIndex(self.textClockLanguage.findText(settings.value('textClockLanguage', 'English')))
        self.time_am_pm.setChecked(settings.value('isAmPm', False, type=bool))
        self.time_24h.setChecked(not settings.value('isAmPm', False, type=bool))
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
        if self.oacmode:
            settings = self.settings
        else:
            settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        settings.setValue('stationname', self.StationName.displayText())
        settings.setValue('slogan', self.Slogan.displayText())
        settings.setValue('stationcolor', self.getStationNameColor().name())
        settings.setValue('slogancolor', self.getSloganColor().name())
        settings.setValue('updatecheck', self.checkBox_UpdateCheck.isChecked())
        settings.setValue('updatekey', self.updateKey.displayText())
        settings.setValue('updateincludebeta', self.checkBox_IncludeBetaVersions.isChecked())
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
        settings.setValue('showSeconds', self.showSeconds.isChecked())
        settings.setValue('staticColon', self.staticColon.isChecked())
        settings.setValue('digitalhourcolor', self.getDigitalHourColor().name())
        settings.setValue('digitalsecondcolor', self.getDigitalSecondColor().name())
        settings.setValue('digitaldigitcolor', self.getDigitalDigitColor().name())
        settings.setValue('logopath', self.logoPath.text())
        settings.endGroup()

        settings.beginGroup("Network")
        settings.setValue('udpport', self.udpport.displayText())
        settings.setValue('httpport', self.httpport.displayText())
        settings.endGroup()

        settings.beginGroup("Formatting")
        settings.setValue('dateFormat', self.dateFormat.displayText())
        settings.setValue('textClockLanguage', self.textClockLanguage.currentText())
        settings.setValue('isAmPm', self.time_am_pm.isChecked())
        settings.endGroup()

        settings.beginGroup("WeatherWidget")
        settings.setValue('owmWidgetEnabled', self.owmWidgetEnabled.isChecked())
        settings.setValue('owmAPIKey', self.owmAPIKey.displayText())
        settings.setValue('owmCityID', self.owmCityID.displayText())
        settings.setValue('owmLanguage', self.owmLanguage.currentText())
        settings.setValue('owmUnit', self.owmUnit.currentText())
        settings.endGroup()

        if self.oacmode:
            # send oac a signal the the config has changed
            self.sigConfigChanged.emit(self.row, self.readJsonFromConfig())

    def applySettings(self):
        # apply settings button pressed
        self.getSettingsFromDialog()
        self.sigConfigFinished.emit()

    def closeSettings(self):
        # close settings button pressed
        self.restoreSettingsFromConfig()

    @staticmethod
    def get_mac():
        mac1 = getnode()
        mac2 = getnode()
        if mac1 == mac2:
            mac = ":".join(textwrap.wrap(format(mac1, 'x').zfill(12).upper(), 2))
        else:
            print("ERROR: Could not get a valid mac address")
            mac = "00:00:00:00:00:00"
        return mac

    def trigger_manual_check_for_updates(self):
        self.manual_update_check = True
        self.check_for_updates()

    def check_for_updates(self):
        if self.checkBox_UpdateCheck.isChecked():
            print("check for updates")
            update_key = self.updateKey.displayText()
            if len(update_key) == 50:
                url = "https://customer.astrastudio.de/updatemanager/c"
                data = QUrlQuery()
                data.addQueryItem("update_key", update_key)
                data.addQueryItem("product", "OnAirScreen")
                data.addQueryItem("current_version", versionString)
                data.addQueryItem("distribution", distributionString)
                data.addQueryItem("mac", self.get_mac())
                data.addQueryItem("include_beta", f'{self.checkBox_IncludeBetaVersions.isChecked()}')
                req = QtNetwork.QNetworkRequest(QUrl(url))
                req.setHeader(QtNetwork.QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
                self.nam_update_check = QtNetwork.QNetworkAccessManager()
                self.nam_update_check.finished.connect(self.handle_update_check_response)
                self.nam_update_check.post(req, data.toString(QUrl.FullyEncoded).encode("UTF-8"))
            else:
                print("error, update key in wrong format")
                self.error_dialog = QErrorMessage()
                self.error_dialog.setWindowTitle("Update Check Error")
                self.error_dialog.showMessage('Update key is in the wrong format!', 'UpdateKeyError')

    def handle_update_check_response(self, reply):
        er = reply.error()
        if er == QtNetwork.QNetworkReply.NoError:
            bytes_string = reply.readAll()
            reply_string = str(bytes_string, 'utf-8')
            json_reply = json.loads(reply_string)

            if json_reply['Status'] == "UPDATE":
                self.timer_message_box = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
                self.timer_message_box.exec_()

            if json_reply['Status'] == "OK" and self.manual_update_check:
                self.message_box = QMessageBox()
                self.message_box.setIcon(QMessageBox.Information)
                self.message_box.setWindowTitle("OnAirScreen Update Check")
                self.message_box.setText("OnAirScreen Update Check")
                self.message_box.setInformativeText(f"{json_reply['Message']}")
                self.message_box.setStandardButtons(QMessageBox.Ok)
                self.message_box.show()
                self.manual_update_check = False

            if json_reply['Status'] == "ERROR" and self.manual_update_check:
                self.message_box = QMessageBox()
                self.message_box.setIcon(QMessageBox.Critical)
                self.message_box.setWindowTitle("OnAirScreen Update Check")
                self.message_box.setText("OnAirScreen Update Check")
                self.message_box.setInformativeText(f"{json_reply['Message']}")
                self.message_box.setStandardButtons(QMessageBox.Ok)
                self.message_box.show()
                self.manual_update_check = False

        elif self.manual_update_check:
            error_string = "Error occurred: {}, {}".format(er, reply.errorString())
            self.error_dialog = QErrorMessage()
            self.error_dialog.setWindowTitle("Update Check Error")
            self.error_dialog.showMessage(error_string, 'UpdateCheckError')

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
            errorString = "Error occurred: {}, {}".format(er, reply.errorString())
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

    def setLED4BGColor(self, newcolor=False):
        palette = self.LED4Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.LED4Demo.setPalette(palette)

    def setLED4FGColor(self, newcolor=False):
        palette = self.LED4Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.LED4Demo.setPalette(palette)

    def setStationNameColor(self, newcolor=False):
        palette = self.StationNameDemo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.StationNameDemo.setPalette(palette)

    def setSloganColor(self, newcolor=False):
        palette = self.SloganDemo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.WindowText, newcolor)
        self.SloganDemo.setPalette(palette)

    def getStationNameColor(self):
        palette = self.StationNameDemo.palette()
        color = palette.windowText().color()
        return color

    def getSloganColor(self):
        palette = self.SloganDemo.palette()
        color = palette.windowText().color()
        return color

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

    def getLED4BGColor(self):
        palette = self.LED4Demo.palette()
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

    def getLED4FGColor(self):
        palette = self.LED4Demo.palette()
        color = palette.windowText().color()
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
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalHourColor.setPalette(palette)

    def setDigitalSecondColor(self, newcolor=False):
        palette = self.DigitalSecondColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalSecondColor.setPalette(palette)

    def setDigitalDigitColor(self, newcolor=False):
        palette = self.DigitalDigitColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
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
        color.setNamedColor(colorname)
        return color

    def openLogoPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)")[0]
        if filename:
            self.logoPath.setText(filename)

    def resetLogo(self):
        self.logoPath.setText(":/astrastudio_logo/images/astrastudio_transparent.png")

    def setLogoPath(self, path):
        self.logoPath.setText(path)
