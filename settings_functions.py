#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
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

import json
import logging
import textwrap
from collections import defaultdict
from uuid import getnode

import PyQt6.QtNetwork as QtNetwork
from PyQt6.QtCore import QSettings, QVariant, pyqtSignal, QUrl, QUrlQuery
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QWidget, QColorDialog, QFileDialog, QErrorMessage, QMessageBox, QFontDialog

from settings import Ui_Settings
from utils import TimerUpdateMessageBox
from version import versionString
from weatherwidget import WeatherWidget as ww

try:
    from distribution import distributionString, update_url
except ModuleNotFoundError:
    distributionString = "OpenSource"
    update_url = "https://customer.astrastudio.de/updatemanager/c"

# Configure logging
logger = logging.getLogger(__name__)


def validate_color_value(color_str: str) -> tuple[bool, str]:
    """
    Validate a color value string
    
    Supports formats:
    - Hex format: #RRGGBB or #RGB
    - Hex format with 0x prefix: 0xRRGGBB or 0xRGB
    - Named colors (Qt color names)
    
    Args:
        color_str: Color string to validate
        
    Returns:
        Tuple of (is_valid, normalized_color_string)
        If invalid, normalized_color_string will be empty string
    """
    if not color_str or not isinstance(color_str, str):
        return False, ""
    
    color_str = color_str.strip()
    
    # Handle 0x prefix (convert to #)
    if color_str.startswith("0x") or color_str.startswith("0X"):
        color_str = "#" + color_str[2:]
    
    # Validate hex format: #RRGGBB or #RGB
    if color_str.startswith("#"):
        hex_part = color_str[1:]
        # Check if it's a valid hex string (3 or 6 digits)
        if len(hex_part) == 3:
            # Short format #RGB
            if all(c in '0123456789ABCDEFabcdef' for c in hex_part):
                return True, color_str.upper()
        elif len(hex_part) == 6:
            # Long format #RRGGBB
            if all(c in '0123456789ABCDEFabcdef' for c in hex_part):
                return True, color_str.upper()
        # Invalid hex format
        return False, ""
    
    # Check if it's a valid Qt named color
    # Qt supports many named colors, we'll let QColor validate it
    test_color = QColor()
    test_color.setNamedColor(color_str)
    if test_color.isValid():
        return True, color_str
    
    # Invalid color
    return False, ""


# class OASSettings for use from OAC
class OASSettings:
    """
    Settings class for OAC (OnAirScreen Control) mode
    
    Provides a QSettings-like interface for in-memory configuration
    storage when running in OAC mode.
    """
    def __init__(self) -> None:
        """Initialize OASSettings with empty configuration"""
        self.config: dict = defaultdict(dict)
        self.currentgroup: str | None = None

    def beginGroup(self, group: str) -> None:
        """Begin a settings group"""
        self.currentgroup = group

    def endGroup(self) -> None:
        """End the current settings group"""
        self.currentgroup = None

    def setValue(self, name: str, value) -> None:
        """Set a value in the current group"""
        if self.currentgroup:
            self.config[self.currentgroup][name] = value

    def value(self, name: str, default=None) -> QVariant:
        """Get a value from the current group"""
        try:
            return QVariant(self.config[self.currentgroup][name])
        except KeyError:
            return QVariant(default)

    def fileName(self) -> str:
        """Return the settings file name (for compatibility)"""
        return "OAC Mode"


class Settings(QWidget, Ui_Settings):
    """
    Settings dialog for OnAirScreen
    
    Provides a comprehensive settings interface for configuring
    all aspects of the OnAirScreen application.
    """
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

    def __init__(self, oacmode: bool = False) -> None:
        """
        Initialize the Settings dialog
        
        Args:
            oacmode: If True, run in OAC (OnAirScreen Control) mode
        """
        self.settingsPath = None
        self.row = -1
        QWidget.__init__(self)
        Ui_Settings.__init__(self)

        # available text clock languages
        self.textClockLanguages = ["English", "German", "Dutch", "French"]

        # available Weather Widget languages
        # self.owmLanguages = {"Arabic": "ar", "Bulgarian": "bg", "Catalan": "ca", "Czech": "cz", "German": "de",
        #                     "Greek": "el", "English": "en", "Persian (Farsi)": "fa", "Finnish": "fi", "French": "fr",
        #                     "Galician": "gl", "Croatian": "hr", "Hungarian": "hu", "Italian": "it", "Japanese": "ja",
        #                     "Korean": "kr", "Latvian": "la", "Lithuanian": "lt", "Macedonian": "mk", "Dutch": "nl",
        #                     "Polish": "pl", "Portuguese": "pt", "Romanian": "ro", "Russian": "ru", "Swedish": "se",
        #                     "Slovak": "sk", "Slovenian": "sl", "Spanish": "es", "Turkish": "tr", "Ukrainian": "ua",
        #                     "Vietnamese": "vi", "Chinese Simplified": "zh_cn", "Chinese Traditional": "zh_tw."}
        # self.owmUnits = {"Kelvin": "", "Celsius": "metric", "Fahrenheit": "imperial"}

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
        self.versionLabel.setText(f"Version: {versionString}")
        # set distribution string
        self.distributionLabel.setText(f"Distribution: {distributionString}")
        # set settings path
        self.settingspathLabel.setText(f"Settings Path: {self.settingsPath}")
        # set update check mode
        self.manual_update_check = False
        self.sigCheckForUpdate.connect(self.check_for_updates)
        
        # Set tooltips for all settings widgets
        self._setup_tooltips()

    def show_settings(self):
        self.restoreSettingsFromConfig()
        self.sigConfigFinished.emit()
        self.show()

    def closeEvent(self, event):
        # emit config finished signal
        self.sigConfigFinished.emit()
        self.sigConfigClosed.emit()

    def exit_on_air_screen(self):
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
        resetSettings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        resetSettings.clear()
        self.sigConfigFinished.emit()
        self.close()

    def _connectSlots(self):
        self.ApplyButton.clicked.connect(self.applySettings)
        self.CloseButton.clicked.connect(self.closeSettings)
        self.ExitButton.clicked.connect(self.exit_on_air_screen)
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
        self.AIR1BGColor.clicked.connect(self.setAIR1BGColor)
        self.AIR1FGColor.clicked.connect(self.setAIR1FGColor)
        self.AIR2BGColor.clicked.connect(self.setAIR2BGColor)
        self.AIR2FGColor.clicked.connect(self.setAIR2FGColor)
        self.AIR3BGColor.clicked.connect(self.setAIR3BGColor)
        self.AIR3FGColor.clicked.connect(self.setAIR3FGColor)
        self.AIR4BGColor.clicked.connect(self.setAIR4BGColor)
        self.AIR4FGColor.clicked.connect(self.setAIR4FGColor)
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

        self.SetFont_LED1.clicked.connect(self.setOASFontLED1)
        self.SetFont_LED2.clicked.connect(self.setOASFontLED2)
        self.SetFont_LED3.clicked.connect(self.setOASFontLED3)
        self.SetFont_LED4.clicked.connect(self.setOASFontLED4)
        self.SetFont_AIR1.clicked.connect(self.setOASFontAIR1)
        self.SetFont_AIR2.clicked.connect(self.setOASFontAIR2)
        self.SetFont_AIR3.clicked.connect(self.setOASFontAIR3)
        self.SetFont_AIR4.clicked.connect(self.setOASFontAIR4)

        self.AIR1IconSelectButton.clicked.connect(self.openAIR1IconPathSelector)
        self.AIR1IconResetButton.clicked.connect(self.resetAIR1Icon)
        self.AIR2IconSelectButton.clicked.connect(self.openAIR2IconPathSelector)
        self.AIR2IconResetButton.clicked.connect(self.resetAIR2Icon)
        self.AIR3IconSelectButton.clicked.connect(self.openAIR3IconPathSelector)
        self.AIR3IconResetButton.clicked.connect(self.resetAIR3Icon)
        self.AIR4IconSelectButton.clicked.connect(self.openAIR4IconPathSelector)
        self.AIR4IconResetButton.clicked.connect(self.resetAIR4Icon)

        self.SetFont_StationName.clicked.connect(self.setOASFontStationName)
        self.SetFont_Slogan.clicked.connect(self.setOASFontSlogan)

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
        if self.oacmode:
            settings = self.settings
        else:
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            
        self.settingsPath = settings.fileName()

        # populate text clock languages
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
        self.replaceNOW.setChecked(settings.value('replacenow', False, type=bool))
        self.replaceNOWText.setText(settings.value('replacenowtext', ''))
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
        self.LED4Text.setText(settings.value('text', 'EAS ACTIVE'))
        self.LED4Demo.setText(settings.value('text', 'EAS ACTIVE'))
        self.setLED4BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF00FF')))
        self.setLED4FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF')))
        self.LED4Autoflash.setChecked(settings.value('autoflash', False, type=bool))
        self.LED4Timedflash.setChecked(settings.value('timedflash', False, type=bool))
        settings.endGroup()

        settings.beginGroup("Clock")
        self.clockDigital.setChecked(settings.value('digital', True, type=bool))
        self.clockAnalog.setChecked(not settings.value('digital', True, type=bool))
        self.showSeconds.setChecked(settings.value('showSeconds', False, type=bool))
        self.seconds_in_one_line.setChecked(settings.value('showSecondsInOneLine', False, type=bool))
        if not settings.value('showSeconds', False, type=bool):
            self.seconds_in_one_line.setDisabled(True)
            self.seconds_separate.setDisabled(True)
        self.staticColon.setChecked(settings.value('staticColon', False, type=bool))
        self.useTextclock.setChecked(settings.value('useTextClock', True, type=bool))
        self.setDigitalHourColor(self.getColorFromName(settings.value('digitalhourcolor', '#3232FF')))
        self.setDigitalSecondColor(self.getColorFromName(settings.value('digitalsecondcolor', '#FF9900')))
        self.setDigitalDigitColor(self.getColorFromName(settings.value('digitaldigitcolor', '#3232FF')))
        self.logoPath.setText(
            settings.value('logopath', ':/astrastudio_logo/images/astrastudio_transparent.png'))
        if settings.value('logoUpper', False, type=bool):
            self.radioButton_logo_upper.setChecked(True)
            self.radioButton_logo_lower.setChecked(False)
        else:
            self.radioButton_logo_upper.setChecked(False)
            self.radioButton_logo_lower.setChecked(True)
        settings.endGroup()

        settings.beginGroup("Network")
        self.udpport.setText(str(settings.value('udpport', '3310')))
        self.httpport.setText(str(settings.value('httpport', '8010')))
        self.multicast_group.setText(settings.value('multicast_address', "239.194.0.1"))
        settings.endGroup()

        settings.beginGroup("Formatting")
        self.dateFormat.setText(settings.value('dateFormat', 'dddd, dd. MMMM yyyy'))
        self.textClockLanguage.setCurrentIndex(
            self.textClockLanguage.findText(settings.value('textClockLanguage', 'English')))
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

        settings.beginGroup("Timers")
        self.enableAIR1.setChecked(settings.value('TimerAIR1Enabled', True, type=bool))
        self.enableAIR2.setChecked(settings.value('TimerAIR2Enabled', True, type=bool))
        self.enableAIR3.setChecked(settings.value('TimerAIR3Enabled', True, type=bool))
        self.enableAIR4.setChecked(settings.value('TimerAIR4Enabled', True, type=bool))
        self.AIR1Text.setText(settings.value('TimerAIR1Text', 'Mic'))
        self.AIR2Text.setText(settings.value('TimerAIR2Text', 'Phone'))
        self.AIR3Text.setText(settings.value('TimerAIR3Text', 'Timer'))
        self.AIR4Text.setText(settings.value('TimerAIR4Text', 'Stream'))
        self.setAIR1BGColor(self.getColorFromName(settings.value('AIR1activebgcolor', '#FF0000')))
        self.setAIR1FGColor(self.getColorFromName(settings.value('AIR1activetextcolor', '#FFFFFF')))
        self.setAIR2BGColor(self.getColorFromName(settings.value('AIR2activebgcolor', '#FF0000')))
        self.setAIR2FGColor(self.getColorFromName(settings.value('AIR2activetextcolor', '#FFFFFF')))
        self.setAIR3BGColor(self.getColorFromName(settings.value('AIR3activebgcolor', '#FF0000')))
        self.setAIR3FGColor(self.getColorFromName(settings.value('AIR3activetextcolor', '#FFFFFF')))
        self.setAIR4BGColor(self.getColorFromName(settings.value('AIR4activebgcolor', '#FF0000')))
        self.setAIR4FGColor(self.getColorFromName(settings.value('AIR4activetextcolor', '#FFFFFF')))

        self.AIR1IconPath.setText(settings.value('air1iconpath', ':/mic_icon/images/mic_icon.png'))
        self.AIR2IconPath.setText(settings.value('air2iconpath', ':/phone_icon/images/phone_icon.png'))
        self.AIR3IconPath.setText(settings.value('air3iconpath', ':/timer_icon/images/timer_icon.png'))
        self.AIR4IconPath.setText(settings.value('air4iconpath', ':/stream_icon/images/antenna2.png'))

        self.AIRMinWidth.setValue(settings.value('TimerAIRMinWidth', 200, type=int))
        settings.endGroup()

        settings.beginGroup("Fonts")
        self.ExampleFont_LED1.setFont(QFont(settings.value('LED1FontName', "FreeSans"),
                                            settings.value('LED1FontSize', 24, type=int),
                                            settings.value('LED1FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_LED2.setFont(QFont(settings.value('LED2FontName', "FreeSans"),
                                            settings.value('LED2FontSize', 24, type=int),
                                            settings.value('LED2FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_LED3.setFont(QFont(settings.value('LED3FontName', "FreeSans"),
                                            settings.value('LED3FontSize', 24, type=int),
                                            settings.value('LED3FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_LED4.setFont(QFont(settings.value('LED4FontName', "FreeSans"),
                                            settings.value('LED4FontSize', 24, type=int),
                                            settings.value('LED4FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_AIR1.setFont(QFont(settings.value('AIR1FontName', "FreeSans"),
                                            settings.value('AIR1FontSize', 24, type=int),
                                            settings.value('AIR1FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_AIR2.setFont(QFont(settings.value('AIR2FontName', "FreeSans"),
                                            settings.value('AIR2FontSize', 24, type=int),
                                            settings.value('AIR2FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_AIR3.setFont(QFont(settings.value('AIR3FontName', "FreeSans"),
                                            settings.value('AIR3FontSize', 24, type=int),
                                            settings.value('AIR3FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_AIR4.setFont(QFont(settings.value('AIR4FontName', "FreeSans"),
                                            settings.value('AIR4FontSize', 24, type=int),
                                            settings.value('AIR4FontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_StationName.setFont(QFont(settings.value('StationNameFontName', "FreeSans"),
                                                   settings.value('StationNameFontSize', 24, type=int),
                                                   settings.value('StationNameFontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_Slogan.setFont(QFont(settings.value('SloganFontName', "FreeSans"),
                                              settings.value('SloganFontSize', 18, type=int),
                                              settings.value('SloganFontWeight', QFont.Weight.Bold, type=int)))
        self.ExampleFont_LED1.setText(f"{settings.value('LED1FontName', 'FreeSans')}, "
                                      f"{settings.value('LED1FontSize', 24, type=int)}pt")
        self.ExampleFont_LED2.setText(f"{settings.value('LED2FontName', 'FreeSans')}, "
                                      f"{settings.value('LED2FontSize', 24, type=int)}pt")
        self.ExampleFont_LED3.setText(f"{settings.value('LED3FontName', 'FreeSans')}, "
                                      f"{settings.value('LED3FontSize', 24, type=int)}pt")
        self.ExampleFont_LED4.setText(f"{settings.value('LED4FontName', 'FreeSans')}, "
                                      f"{settings.value('LED4FontSize', 24, type=int)}pt")
        self.ExampleFont_AIR1.setText(f"{settings.value('AIR1FontName', 'FreeSans')}, "
                                      f"{settings.value('AIR1FontSize', 24, type=int)}pt")
        self.ExampleFont_AIR2.setText(f"{settings.value('AIR2FontName', 'FreeSans')}, "
                                      f"{settings.value('AIR2FontSize', 24, type=int)}pt")
        self.ExampleFont_AIR3.setText(f"{settings.value('AIR3FontName', 'FreeSans')}, "
                                      f"{settings.value('AIR3FontSize', 24, type=int)}pt")
        self.ExampleFont_AIR4.setText(f"{settings.value('AIR4FontName', 'FreeSans')}, "
                                      f"{settings.value('AIR4FontSize', 24, type=int)}pt")
        self.ExampleFont_StationName.setText(f"{settings.value('StationNameFontName', 'FreeSans')}, "
                                             f"{settings.value('StationNameFontSize', 24, type=int)}pt")
        self.ExampleFont_Slogan.setText(f"{settings.value('SloganFontName', 'FreeSans')}, "
                                        f"{settings.value('SloganFontSize', 18, type=int)}pt")
        settings.endGroup()

    def getSettingsFromDialog(self):
        if self.oacmode:
            settings = self.settings
        else:
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        settings.setValue('stationname', self.StationName.displayText())
        settings.setValue('slogan', self.Slogan.displayText())
        settings.setValue('stationcolor', self.getStationNameColor().name())
        settings.setValue('slogancolor', self.getSloganColor().name())
        settings.setValue('updatecheck', self.checkBox_UpdateCheck.isChecked())
        settings.setValue('updatekey', self.updateKey.displayText())
        settings.setValue('updateincludebeta', self.checkBox_IncludeBetaVersions.isChecked())
        settings.setValue('replacenow', self.replaceNOW.isChecked())
        settings.setValue('replacenowtext', self.replaceNOWText.displayText())
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
        settings.setValue('showSecondsInOneLine', self.seconds_in_one_line.isChecked())
        settings.setValue('staticColon', self.staticColon.isChecked())
        settings.setValue('useTextClock', self.useTextclock.isChecked())
        settings.setValue('digitalhourcolor', self.getDigitalHourColor().name())
        settings.setValue('digitalsecondcolor', self.getDigitalSecondColor().name())
        settings.setValue('digitaldigitcolor', self.getDigitalDigitColor().name())
        settings.setValue('logopath', self.logoPath.text())
        settings.setValue('logoUpper', self.radioButton_logo_upper.isChecked())
        settings.endGroup()

        settings.beginGroup("Network")
        settings.setValue('udpport', self.udpport.displayText())
        settings.setValue('httpport', self.httpport.displayText())
        settings.setValue('multicast_address', self.multicast_group.displayText())
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

        settings.beginGroup("Timers")
        settings.setValue('TimerAIR1Enabled', self.enableAIR1.isChecked())
        settings.setValue('TimerAIR2Enabled', self.enableAIR2.isChecked())
        settings.setValue('TimerAIR3Enabled', self.enableAIR3.isChecked())
        settings.setValue('TimerAIR4Enabled', self.enableAIR4.isChecked())
        settings.setValue('TimerAIR1Text', self.AIR1Text.text())
        settings.setValue('TimerAIR2Text', self.AIR2Text.text())
        settings.setValue('TimerAIR3Text', self.AIR3Text.text())
        settings.setValue('TimerAIR4Text', self.AIR4Text.text())
        settings.setValue('AIR1activebgcolor', self.getAIR1BGColor().name())
        settings.setValue('AIR1activetextcolor', self.getAIR1FGColor().name())
        settings.setValue('AIR2activebgcolor', self.getAIR2BGColor().name())
        settings.setValue('AIR2activetextcolor', self.getAIR2FGColor().name())
        settings.setValue('AIR3activebgcolor', self.getAIR3BGColor().name())
        settings.setValue('AIR3activetextcolor', self.getAIR3FGColor().name())
        settings.setValue('AIR4activebgcolor', self.getAIR4BGColor().name())
        settings.setValue('AIR4activetextcolor', self.getAIR4FGColor().name())

        settings.setValue('air1iconpath', self.AIR1IconPath.text())
        settings.setValue('air2iconpath', self.AIR2IconPath.text())
        settings.setValue('air3iconpath', self.AIR3IconPath.text())
        settings.setValue('air4iconpath', self.AIR4IconPath.text())

        settings.setValue('TimerAIRMinWidth', self.AIRMinWidth.value())
        settings.endGroup()

        settings.beginGroup("Fonts")
        settings.setValue("LED1FontName", self.ExampleFont_LED1.font().family())
        settings.setValue("LED1FontSize", self.ExampleFont_LED1.font().pointSize())
        settings.setValue("LED1FontWeight", self.ExampleFont_LED1.font().weight())
        settings.setValue("LED2FontName", self.ExampleFont_LED2.font().family())
        settings.setValue("LED2FontSize", self.ExampleFont_LED2.font().pointSize())
        settings.setValue("LED2FontWeight", self.ExampleFont_LED2.font().weight())
        settings.setValue("LED3FontName", self.ExampleFont_LED3.font().family())
        settings.setValue("LED3FontSize", self.ExampleFont_LED3.font().pointSize())
        settings.setValue("LED3FontWeight", self.ExampleFont_LED3.font().weight())
        settings.setValue("LED4FontName", self.ExampleFont_LED4.font().family())
        settings.setValue("LED4FontSize", self.ExampleFont_LED4.font().pointSize())
        settings.setValue("LED4FontWeight", self.ExampleFont_LED4.font().weight())
        settings.setValue("AIR1FontName", self.ExampleFont_AIR1.font().family())
        settings.setValue("AIR1FontSize", self.ExampleFont_AIR1.font().pointSize())
        settings.setValue("AIR1FontWeight", self.ExampleFont_AIR1.font().weight())
        settings.setValue("AIR2FontName", self.ExampleFont_AIR2.font().family())
        settings.setValue("AIR2FontSize", self.ExampleFont_AIR2.font().pointSize())
        settings.setValue("AIR2FontWeight", self.ExampleFont_AIR2.font().weight())
        settings.setValue("AIR3FontName", self.ExampleFont_AIR3.font().family())
        settings.setValue("AIR3FontSize", self.ExampleFont_AIR3.font().pointSize())
        settings.setValue("AIR3FontWeight", self.ExampleFont_AIR3.font().weight())
        settings.setValue("AIR4FontName", self.ExampleFont_AIR4.font().family())
        settings.setValue("AIR4FontSize", self.ExampleFont_AIR4.font().pointSize())
        settings.setValue("AIR4FontWeight", self.ExampleFont_AIR4.font().weight())
        settings.setValue("StationNameFontName", self.ExampleFont_StationName.font().family())
        settings.setValue("StationNameFontSize", self.ExampleFont_StationName.font().pointSize())
        settings.setValue("StationNameFontWeight", self.ExampleFont_StationName.font().weight())
        settings.setValue("SloganFontName", self.ExampleFont_Slogan.font().family())
        settings.setValue("SloganFontSize", self.ExampleFont_Slogan.font().pointSize())
        settings.setValue("SloganFontWeight", self.ExampleFont_Slogan.font().weight())
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
            logger.error("ERROR: Could not get a valid mac address")
            mac = "00:00:00:00:00:00"
        return mac

    def trigger_manual_check_for_updates(self):
        self.manual_update_check = True
        self.check_for_updates()

    def check_for_updates(self):
        if self.checkBox_UpdateCheck.isChecked():
            logger.debug("check for updates")
            update_key = self.updateKey.displayText()
            if len(update_key) == 50:
                data = QUrlQuery()
                data.addQueryItem("update_key", update_key)
                data.addQueryItem("product", "OnAirScreen")
                data.addQueryItem("current_version", versionString)
                data.addQueryItem("distribution", distributionString)
                data.addQueryItem("mac", self.get_mac())
                data.addQueryItem("include_beta", f'{self.checkBox_IncludeBetaVersions.isChecked()}')
                req = QtNetwork.QNetworkRequest(QUrl(update_url))
                req.setHeader(QtNetwork.QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
                self.nam_update_check = QtNetwork.QNetworkAccessManager()
                self.nam_update_check.finished.connect(self.handle_update_check_response)
                self.nam_update_check.post(req, data.toString(QUrl.FullyEncoded).encode("UTF-8"))
            else:
                logger.error("error, update key in wrong format")
                self.error_dialog = QErrorMessage()
                self.error_dialog.setWindowTitle("Update Check Error")
                self.error_dialog.showMessage('Update key is in the wrong format!', 'UpdateKeyError')

    def handle_update_check_response(self, reply):
        er = reply.error()
        if er == QtNetwork.QNetworkReply.NetworkError.NoError:
            bytes_string = reply.readAll()
            reply_string = str(bytes_string, 'utf-8')
            json_reply = json.loads(reply_string)

            if json_reply['Status'] == "UPDATE":
                self.timer_message_box = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
                self.timer_message_box.exec()

            if json_reply['Status'] == "OK" and self.manual_update_check:
                self.message_box = QMessageBox()
                self.message_box.setIcon(QMessageBox.Icon.Information)
                self.message_box.setWindowTitle("OnAirScreen Update Check")
                self.message_box.setText("OnAirScreen Update Check")
                self.message_box.setInformativeText(f"{json_reply['Message']}")
                self.message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                self.message_box.show()
                self.manual_update_check = False

            if json_reply['Status'] == "ERROR" and self.manual_update_check:
                self.message_box = QMessageBox()
                self.message_box.setIcon(QMessageBox.Icon.Critical)
                self.message_box.setWindowTitle("OnAirScreen Update Check")
                self.message_box.setText("OnAirScreen Update Check")
                self.message_box.setInformativeText(f"{json_reply['Message']}")
                self.message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
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

        if er == QtNetwork.QNetworkReply.NetworkError.NoError:
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
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.LED1Demo.setPalette(palette)

    def setLEDInactiveBGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLEDInactiveFGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLED1FGColor(self, newcolor=False):
        palette = self.LED1Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.LED1Demo.setPalette(palette)

    def setLED2BGColor(self, newcolor=False):
        palette = self.LED2Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.LED2Demo.setPalette(palette)

    def setLED2FGColor(self, newcolor=False):
        palette = self.LED2Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.LED2Demo.setPalette(palette)

    def setLED3BGColor(self, newcolor=False):
        palette = self.LED3Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.LED3Demo.setPalette(palette)

    def setLED3FGColor(self, newcolor=False):
        palette = self.LED3Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.LED3Demo.setPalette(palette)

    def setLED4BGColor(self, newcolor=False):
        palette = self.LED4Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.LED4Demo.setPalette(palette)

    def setLED4FGColor(self, newcolor=False):
        palette = self.LED4Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.LED4Demo.setPalette(palette)

    def setAIR1FGColor(self, newcolor=False):
        palette = self.AIR1Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.AIR1Demo.setPalette(palette)

    def setAIR2FGColor(self, newcolor=False):
        palette = self.AIR2Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.AIR2Demo.setPalette(palette)

    def setAIR3FGColor(self, newcolor=False):
        palette = self.AIR3Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.AIR3Demo.setPalette(palette)

    def setAIR4FGColor(self, newcolor=False):
        palette = self.AIR4Demo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.AIR4Demo.setPalette(palette)

    def setAIR1BGColor(self, newcolor=False):
        palette = self.AIR1Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.AIR1Demo.setPalette(palette)

    def setAIR2BGColor(self, newcolor=False):
        palette = self.AIR2Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.AIR2Demo.setPalette(palette)

    def setAIR3BGColor(self, newcolor=False):
        palette = self.AIR3Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.AIR3Demo.setPalette(palette)

    def setAIR4BGColor(self, newcolor=False):
        palette = self.AIR4Demo.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.AIR4Demo.setPalette(palette)

    def setStationNameColor(self, newcolor=False):
        palette = self.StationNameDemo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
        self.StationNameDemo.setPalette(palette)

    def setSloganColor(self, newcolor=False):
        palette = self.SloganDemo.palette()
        oldcolor = palette.windowText().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.WindowText, newcolor)
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

    def getAIR1FGColor(self):
        palette = self.AIR1Demo.palette()
        color = palette.windowText().color()
        return color

    def getAIR2FGColor(self):
        palette = self.AIR2Demo.palette()
        color = palette.windowText().color()
        return color

    def getAIR3FGColor(self):
        palette = self.AIR3Demo.palette()
        color = palette.windowText().color()
        return color

    def getAIR4FGColor(self):
        palette = self.AIR4Demo.palette()
        color = palette.windowText().color()
        return color

    def getAIR1BGColor(self):
        palette = self.AIR1Demo.palette()
        color = palette.window().color()
        return color

    def getAIR2BGColor(self):
        palette = self.AIR2Demo.palette()
        color = palette.window().color()
        return color

    def getAIR3BGColor(self):
        palette = self.AIR3Demo.palette()
        color = palette.window().color()
        return color

    def getAIR4BGColor(self):
        palette = self.AIR4Demo.palette()
        color = palette.window().color()
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
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.DigitalHourColor.setPalette(palette)

    def setDigitalSecondColor(self, newcolor=False):
        palette = self.DigitalSecondColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.DigitalSecondColor.setPalette(palette)

    def setDigitalDigitColor(self, newcolor=False):
        palette = self.DigitalDigitColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        palette.setColor(QPalette.ColorRole.Window, newcolor)
        self.DigitalDigitColor.setPalette(palette)

    def openColorDialog(self, initcolor):
        colordialog = QColorDialog()
        selectedcolor = colordialog.getColor(initcolor, None, 'Please select a color')
        if selectedcolor.isValid():
            return selectedcolor
        else:
            return initcolor

    def getColorFromName(self, colorname):
        """
        Get QColor from color name string with validation
        
        Args:
            colorname: Color string (hex format #RRGGBB, 0xRRGGBB, or named color)
            
        Returns:
            QColor object, or invalid QColor if color string is invalid
        """
        if not colorname:
            logger.warning("getColorFromName: Empty color name provided")
            return QColor()  # Return invalid color
        
        # Validate color value
        is_valid, normalized_color = validate_color_value(colorname)
        if not is_valid:
            logger.warning(f"getColorFromName: Invalid color value '{colorname}', using default black")
            return QColor(0, 0, 0)  # Return black as fallback
        
        # Create color from validated string
        color = QColor()
        color.setNamedColor(normalized_color)
        
        # Double-check that QColor accepted it
        if not color.isValid():
            logger.warning(f"getColorFromName: QColor rejected color '{normalized_color}', using default black")
            return QColor(0, 0, 0)  # Return black as fallback
        
        return color

    def openLogoPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)")[0]
        if filename:
            self.logoPath.setText(filename)

    def resetLogo(self):
        self.logoPath.setText(":/astrastudio_logo/images/astrastudio_transparent.png")

    def setLogoPath(self, path):
        self.logoPath.setText(path)

    def setLogoUpper(self, state):
        self.radioButton_logo_upper.setChecked(state)
        self.radioButton_logo_lower.setChecked(not state)

    def _set_font_for_widget(self, widget_name: str) -> None:
        """
        Generic method to set font for a widget
        
        Args:
            widget_name: Name of the widget (e.g., 'ExampleFont_LED1')
        """
        widget = getattr(self, widget_name)
        current_font = widget.font()
        new_font, ok = QFontDialog.getFont(current_font)
        if ok:
            widget.setFont(new_font)
            widget.setText(f"{new_font.family()}, {new_font.pointSize()}pt")

    def setOASFontLED1(self):
        """Set font for LED1"""
        self._set_font_for_widget('ExampleFont_LED1')

    def setOASFontLED2(self):
        """Set font for LED2"""
        self._set_font_for_widget('ExampleFont_LED2')

    def setOASFontLED3(self):
        """Set font for LED3"""
        self._set_font_for_widget('ExampleFont_LED3')

    def setOASFontLED4(self):
        """Set font for LED4"""
        self._set_font_for_widget('ExampleFont_LED4')

    def setOASFontAIR1(self):
        """Set font for AIR1"""
        self._set_font_for_widget('ExampleFont_AIR1')

    def setOASFontAIR2(self):
        """Set font for AIR2"""
        self._set_font_for_widget('ExampleFont_AIR2')

    def setOASFontAIR3(self):
        """Set font for AIR3"""
        self._set_font_for_widget('ExampleFont_AIR3')

    def setOASFontAIR4(self):
        """Set font for AIR4"""
        self._set_font_for_widget('ExampleFont_AIR4')

    def setOASFontStationName(self):
        """Set font for Station Name"""
        self._set_font_for_widget('ExampleFont_StationName')

    def setOASFontSlogan(self):
        """Set font for Slogan"""
        self._set_font_for_widget('ExampleFont_Slogan')

    def openAIR1IconPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)")[0]
        if filename:
            self.AIR1IconPath.setText(filename)

    def resetAIR1Icon(self):
        self.AIR1IconPath.setText(":/mic_icon/images/mic_icon.png")

    def setAIR1IconPath(self, path):
        self.AIR1IconPath.setText(path)

    def openAIR2IconPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)")[0]
        if filename:
            self.AIR2IconPath.setText(filename)

    def resetAIR2Icon(self):
        self.AIR2IconPath.setText(":/phone_icon/images/phone_icon.png")

    def setAIR2IconPath(self, path):
        self.AIR2IconPath.setText(path)

    def openAIR3IconPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)")[0]
        if filename:
            self.AIR3IconPath.setText(filename)

    def resetAIR3Icon(self):
        self.AIR3IconPath.setText(":/timer_icon/images/timer_icon.png")

    def setAIR3IconPath(self, path):
        self.AIR3IconPath.setText(path)

    def openAIR4IconPathSelector(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png)")[0]
        if filename:
            self.AIR4IconPath.setText(filename)

    def resetAIR4Icon(self):
        self.AIR4IconPath.setText(":/stream_icon/images/antenna2.png")

    def setAIR4IconPath(self, path):
        self.AIR4IconPath.setText(path)
    
    def _setup_tooltips(self) -> None:
        """
        Setup tooltips for all settings widgets
        
        This method sets helpful tooltips for all configuration options
        in the settings dialog to improve user experience.
        """
        # General settings
        self.StationName.setToolTip("Enter the name of your radio station")
        self.Slogan.setToolTip("Enter your station's slogan or tagline")
        self.StationNameColor.setToolTip("Click to select the color for the station name")
        self.SloganColor.setToolTip("Click to select the color for the slogan")
        self.checkBox_UpdateCheck.setToolTip("Enable automatic update checking on startup")
        self.updateKey.setToolTip("Enter your update key for automatic updates (if applicable)")
        self.checkBox_IncludeBetaVersions.setToolTip("Include beta versions when checking for updates")
        self.updateCheckNowButton.setToolTip("Manually check for updates now")
        self.replaceNOW.setToolTip("Replace the 'NOW' text with custom text after 10 seconds")
        self.replaceNOWText.setToolTip("Custom text to display after IP addresses are shown")
        
        # NTP settings
        self.checkBox_NTPCheck.setToolTip("Enable NTP (Network Time Protocol) synchronization check")
        self.NTPCheckServer.setToolTip("NTP server address to check time synchronization against")
        
        # LED settings (inactive)
        self.LEDInactiveBGColor.setToolTip("Background color for inactive LEDs")
        self.LEDInactiveFGColor.setToolTip("Text color for inactive LEDs")
        
        # LED1-4 settings
        for led_num in range(1, 5):
            getattr(self, f'LED{led_num}').setToolTip(f"Enable or disable LED{led_num} display")
            getattr(self, f'LED{led_num}Text').setToolTip(f"Text to display on LED{led_num}")
            getattr(self, f'LED{led_num}BGColor').setToolTip(f"Background color for LED{led_num} when active")
            getattr(self, f'LED{led_num}FGColor').setToolTip(f"Text color for LED{led_num} when active")
            getattr(self, f'LED{led_num}Autoflash').setToolTip(f"Enable automatic flashing for LED{led_num} (blinks every 500ms)")
            getattr(self, f'LED{led_num}Timedflash').setToolTip(f"Enable timed flash for LED{led_num} (flashes for 20 seconds then turns off)")
        
        # Clock settings
        self.clockDigital.setToolTip("Display digital clock (HH:MM format)")
        self.clockAnalog.setToolTip("Display analog clock (traditional clock face)")
        self.showSeconds.setToolTip("Show seconds in the clock display")
        self.seconds_in_one_line.setToolTip("Display seconds on the same line as hours and minutes")
        self.seconds_separate.setToolTip("Display seconds separately below the main time")
        self.staticColon.setToolTip("Use static colon (:) instead of blinking colon in digital clock")
        self.useTextclock.setToolTip("Enable text-based clock display (e.g., 'it's 3 o'clock')")
        self.DigitalHourColorButton.setToolTip("Color for the hour digits in digital clock")
        self.DigitalSecondColorButton.setToolTip("Color for the seconds display in digital clock")
        self.DigitalDigitColorButton.setToolTip("Color for all digits in digital clock")
        self.logoPath.setToolTip("Path to the logo image file")
        self.logoButton.setToolTip("Browse for a logo image file")
        self.resetLogoButton.setToolTip("Reset logo to default")
        self.radioButton_logo_upper.setToolTip("Display logo in the upper part of the clock")
        self.radioButton_logo_lower.setToolTip("Display logo in the lower part of the clock")
        
        # Network settings
        self.udpport.setToolTip("UDP port for receiving commands (default: 3310)")
        self.httpport.setToolTip("HTTP port for receiving commands (default: 8010)")
        self.multicast_group.setToolTip("Multicast address for UDP commands (default: 239.194.0.1)")
        
        # Formatting settings
        self.dateFormat.setToolTip("Date format string (e.g., 'dddd, dd. MMMM yyyy' for 'Monday, 01. January 2024')")
        self.textClockLanguage.setToolTip("Language for text-based clock display")
        self.time_am_pm.setToolTip("Use 12-hour format with AM/PM")
        self.time_24h.setToolTip("Use 24-hour format")
        
        # Weather Widget settings
        self.owmWidgetEnabled.setToolTip("Enable the weather widget display")
        self.owmAPIKey.setToolTip("OpenWeatherMap API key (get one at openweathermap.org)")
        self.owmCityID.setToolTip("OpenWeatherMap City ID (find your city ID on openweathermap.org)")
        self.owmLanguage.setToolTip("Language for weather descriptions")
        self.owmUnit.setToolTip("Temperature unit (Celsius, Fahrenheit, or Kelvin)")
        self.owmTestAPI.setToolTip("Test the OpenWeatherMap API connection with current settings")
        
        # Timer/AIR settings
        for air_num in range(1, 5):
            getattr(self, f'enableAIR{air_num}').setToolTip(f"Enable or disable AIR{air_num} timer display")
            getattr(self, f'AIR{air_num}Text').setToolTip(f"Text label for AIR{air_num} timer")
            getattr(self, f'AIR{air_num}BGColor').setToolTip(f"Background color for AIR{air_num} when active")
            getattr(self, f'AIR{air_num}FGColor').setToolTip(f"Text color for AIR{air_num} when active")
            getattr(self, f'AIR{air_num}IconPath').setToolTip(f"Path to icon image for AIR{air_num}")
            getattr(self, f'AIR{air_num}IconSelectButton').setToolTip(f"Browse for an icon image for AIR{air_num}")
            getattr(self, f'AIR{air_num}IconResetButton').setToolTip(f"Reset AIR{air_num} icon to default")
        
        self.AIRMinWidth.setToolTip("Minimum width for AIR timer displays (in pixels)")
        
        # Font settings
        self.SetFont_LED1.setToolTip("Set font for LED1 text")
        self.SetFont_LED2.setToolTip("Set font for LED2 text")
        self.SetFont_LED3.setToolTip("Set font for LED3 text")
        self.SetFont_LED4.setToolTip("Set font for LED4 text")
        self.SetFont_AIR1.setToolTip("Set font for AIR1 timer text")
        self.SetFont_AIR2.setToolTip("Set font for AIR2 timer text")
        self.SetFont_AIR3.setToolTip("Set font for AIR3 timer text")
        self.SetFont_AIR4.setToolTip("Set font for AIR4 timer text")
        self.SetFont_StationName.setToolTip("Set font for station name")
        self.SetFont_Slogan.setToolTip("Set font for slogan")
        
        # Action buttons
        self.ApplyButton.setToolTip("Apply all settings and close the dialog")
        self.CloseButton.setToolTip("Close the settings dialog without applying changes")
        self.ExitButton.setToolTip("Exit OnAirScreen application")
        self.RebootButton.setToolTip("Reboot the host system")
        self.ShutdownButton.setToolTip("Shutdown the host system")
        self.ResetSettingsButton.setToolTip("Reset all settings to default values (this cannot be undone)")

