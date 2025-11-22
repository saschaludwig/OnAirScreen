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
import os
import textwrap
from collections import defaultdict
from pathlib import Path
from uuid import getnode

import PyQt6.QtNetwork as QtNetwork
from PyQt6.QtCore import QSettings, QVariant, pyqtSignal, QUrl, QUrlQuery
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtWidgets import (QWidget, QColorDialog, QFileDialog, QErrorMessage, QMessageBox,
                              QFontDialog, QInputDialog)

from settings import Ui_Settings
from utils import TimerUpdateMessageBox, settings_group
from version import versionString
from weatherwidget import WeatherWidget as ww
from defaults import *  # noqa: F403, F405
from exceptions import SettingsError, InvalidConfigValueError, log_exception
from PyQt6.QtGui import QPixmap

try:
    from distribution import distributionString, update_url # type: ignore
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
        
        # Connect preset management buttons (if they exist in UI)
        self._connect_preset_buttons()

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

        # MQTT checkbox connection
        self.enablemqtt.toggled.connect(self._on_mqtt_enabled_changed)

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
            with settings_group(self.settings, group):
                for key, value in content.items():
                    self.settings.setValue(key, value)
        self.restoreSettingsFromConfig()

    def readJsonFromConfig(self):
        # return json representation of config
        return json.dumps(self.settings.config)

    def _get_presets_directory(self) -> Path:
        """
        Get the directory where presets are stored
        
        Returns:
            Path object pointing to the presets directory
        """
        if self.oacmode:
            # In OAC mode, use a temporary directory
            presets_dir = Path.home() / ".onairscreen" / "presets"
        else:
            # Use QSettings to determine the appropriate directory
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            settings_file = Path(settings.fileName())
            # Presets directory is in the same location as settings file
            presets_dir = settings_file.parent / "presets"
        
        # Create directory if it doesn't exist
        presets_dir.mkdir(parents=True, exist_ok=True)
        return presets_dir

    def export_config_to_json(self) -> dict:
        """
        Export current QSettings configuration to a dictionary
        
        Returns:
            Dictionary containing all configuration groups and their values
        """
        if self.oacmode:
            # In OAC mode, use the in-memory settings
            return self.settings.config.copy()
        
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        config_dict = {}
        
        # List of all configuration groups
        groups = [
            "General", "NTP", "LEDS", "LED1", "LED2", "LED3", "LED4",
            "Clock", "Network", "Formatting", "WeatherWidget", "Timers", "Fonts"
        ]
        
        for group in groups:
            group_dict = {}
            # Get all keys in this group
            with settings_group(settings, group):
                # Get keys while in the group context
                # Note: allKeys() returns keys relative to current group
                keys = settings.allKeys()
                
                # Read each key's value
                for key in keys:
                    value = settings.value(key)
                    # Convert QVariant to Python type if needed
                    if isinstance(value, QVariant):
                        value = value.value()
                    group_dict[key] = value
            
            if group_dict:
                config_dict[group] = group_dict
        
        return config_dict

    def import_config_from_json(self, config_dict: dict) -> bool:
        """
        Import configuration from a dictionary into QSettings
        
        Args:
            config_dict: Dictionary containing configuration groups and values
            
        Returns:
            True if import was successful, False otherwise
        """
        if self.oacmode:
            # In OAC mode, update in-memory settings
            for group, content in config_dict.items():
                with settings_group(self.settings, group):
                    for key, value in content.items():
                        self.settings.setValue(key, value)
            self.restoreSettingsFromConfig()
            return True
        
        try:
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            
            for group, content in config_dict.items():
                with settings_group(settings, group):
                    for key, value in content.items():
                        settings.setValue(key, value)
            
            # Reload settings into the dialog
            self.restoreSettingsFromConfig()
            return True
        except Exception as e:
            if isinstance(e, (SettingsError, InvalidConfigValueError)):
                log_exception(logger, e, use_exc_info=False)
            else:
                error = SettingsError(f"Error importing configuration: {e}")
                log_exception(logger, error, use_exc_info=False)
            return False

    def save_preset(self, preset_name: str) -> bool:
        """
        Save current configuration as a preset
        
        Args:
            preset_name: Name of the preset (will be sanitized for filename)
            
        Returns:
            True if preset was saved successfully, False otherwise
        """
        if not preset_name or not preset_name.strip():
            logger.error("Preset name cannot be empty")
            return False
        
        # Sanitize preset name for filename
        safe_name = "".join(c for c in preset_name.strip() if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        if not safe_name:
            logger.error("Preset name contains no valid characters")
            return False
        
        try:
            presets_dir = self._get_presets_directory()
            preset_file = presets_dir / f"{safe_name}.json"
            
            # Export current configuration
            config_dict = self.export_config_to_json()
            
            # Add metadata
            preset_data = {
                "name": preset_name.strip(),
                "version": versionString,
                "config": config_dict
            }
            
            # Write to file
            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Preset '{preset_name}' saved to {preset_file}")
            return True
        except Exception as e:
            if isinstance(e, (SettingsError, InvalidConfigValueError)):
                log_exception(logger, e, use_exc_info=False)
            else:
                error = SettingsError(f"Error saving preset '{preset_name}': {e}")
                log_exception(logger, error, use_exc_info=False)
            return False

    def load_preset(self, preset_name: str) -> bool:
        """
        Load a preset configuration
        
        Args:
            preset_name: Name of the preset (filename without .json extension)
            
        Returns:
            True if preset was loaded successfully, False otherwise
        """
        try:
            presets_dir = self._get_presets_directory()
            preset_file = presets_dir / f"{preset_name}.json"
            
            if not preset_file.exists():
                logger.error(f"Preset file not found: {preset_file}")
                return False
            
            # Read preset file
            with open(preset_file, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            # Extract configuration
            if "config" in preset_data:
                config_dict = preset_data["config"]
            else:
                # Fallback: assume the whole file is the config
                config_dict = preset_data
            
            # Import configuration
            success = self.import_config_from_json(config_dict)
            
            if success:
                logger.info(f"Preset '{preset_name}' loaded successfully")
            
            return success
        except Exception as e:
            if isinstance(e, (SettingsError, InvalidConfigValueError)):
                log_exception(logger, e, use_exc_info=False)
            else:
                error = SettingsError(f"Error loading preset '{preset_name}': {e}")
                log_exception(logger, error, use_exc_info=False)
            return False

    def list_presets(self) -> list[dict]:
        """
        List all available presets
        
        Returns:
            List of dictionaries containing preset information (name, filename, version)
        """
        presets = []
        try:
            presets_dir = self._get_presets_directory()
            
            if not presets_dir.exists():
                return presets
            
            # Find all JSON files in presets directory
            for preset_file in presets_dir.glob("*.json"):
                try:
                    with open(preset_file, 'r', encoding='utf-8') as f:
                        preset_data = json.load(f)
                    
                    preset_info = {
                        "filename": preset_file.stem,
                        "name": preset_data.get("name", preset_file.stem),
                        "version": preset_data.get("version", "unknown")
                    }
                    presets.append(preset_info)
                except Exception as e:
                    logger.warning(f"Error reading preset file {preset_file}: {e}")
                    # Still include it with basic info
                    presets.append({
                        "filename": preset_file.stem,
                        "name": preset_file.stem,
                        "version": "unknown"
                    })
        except Exception as e:
            if isinstance(e, (SettingsError, InvalidConfigValueError)):
                log_exception(logger, e, use_exc_info=False)
            else:
                error = SettingsError(f"Error listing presets: {e}")
                log_exception(logger, error, use_exc_info=False)
        
        # Sort by name
        presets.sort(key=lambda x: x["name"].lower())
        return presets

    def delete_preset(self, preset_name: str) -> bool:
        """
        Delete a preset
        
        Args:
            preset_name: Name of the preset (filename without .json extension)
            
        Returns:
            True if preset was deleted successfully, False otherwise
        """
        try:
            presets_dir = self._get_presets_directory()
            preset_file = presets_dir / f"{preset_name}.json"
            
            if not preset_file.exists():
                logger.error(f"Preset file not found: {preset_file}")
                return False
            
            preset_file.unlink()
            logger.info(f"Preset '{preset_name}' deleted")
            return True
        except Exception as e:
            if isinstance(e, (SettingsError, InvalidConfigValueError)):
                log_exception(logger, e, use_exc_info=False)
            else:
                error = SettingsError(f"Error deleting preset '{preset_name}': {e}")
                log_exception(logger, error, use_exc_info=False)
            return False

    def restoreSettingsFromConfig(self):
        if self.oacmode:
            settings = self.settings
            # In OAC mode, we don't need to populate UI widgets
            # Just set the settings path and return
            self.settingsPath = settings.fileName()
            return
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

        with settings_group(settings, "General"):
            self.StationName.setText(settings.value('stationname', DEFAULT_STATION_NAME))
            self.Slogan.setText(settings.value('slogan', DEFAULT_SLOGAN))
            self.setStationNameColor(self.getColorFromName(settings.value('stationcolor', DEFAULT_STATION_COLOR)))
            self.setSloganColor(self.getColorFromName(settings.value('slogancolor', DEFAULT_SLOGAN_COLOR)))
            self.checkBox_UpdateCheck.setChecked(settings.value('updatecheck', DEFAULT_UPDATE_CHECK, type=bool))
            self.updateKey.setEnabled(settings.value('updatecheck', DEFAULT_UPDATE_CHECK, type=bool))
            self.label_28.setEnabled(settings.value('updatecheck', DEFAULT_UPDATE_CHECK, type=bool))
            self.updateCheckNowButton.setEnabled(settings.value('updatecheck', DEFAULT_UPDATE_CHECK, type=bool))
            self.checkBox_IncludeBetaVersions.setEnabled(settings.value('updatecheck', DEFAULT_UPDATE_CHECK, type=bool))
            self.updateKey.setText(settings.value('updatekey', DEFAULT_UPDATE_KEY))
            self.checkBox_IncludeBetaVersions.setChecked(settings.value('updateincludebeta', DEFAULT_UPDATE_INCLUDE_BETA, type=bool))
            self.replaceNOW.setChecked(settings.value('replacenow', DEFAULT_REPLACE_NOW, type=bool))
            self.replaceNOWText.setText(settings.value('replacenowtext', DEFAULT_REPLACE_NOW_TEXT))
            # Load log level and set ComboBox
            # Check if command-line log level is set (always overrides settings)
            try:
                import start
                if hasattr(start, '_command_line_log_level') and start._command_line_log_level:
                    log_level = start._command_line_log_level
                else:
                    log_level = settings.value('loglevel', DEFAULT_LOG_LEVEL, type=str)
            except (ImportError, AttributeError):
                # If import fails (e.g., in tests), use settings value
                log_level = settings.value('loglevel', DEFAULT_LOG_LEVEL, type=str)
            index = self.loglevelcombobox.findText(log_level)
            if index >= 0:
                self.loglevelcombobox.setCurrentIndex(index)
            else:
                # Fallback to default if value not found
                index = self.loglevelcombobox.findText(DEFAULT_LOG_LEVEL)
                if index >= 0:
                    self.loglevelcombobox.setCurrentIndex(index)

        with settings_group(settings, "NTP"):
            self.checkBox_NTPCheck.setChecked(settings.value('ntpcheck', DEFAULT_NTP_CHECK, type=bool))
            self.NTPCheckServer.setText(settings.value('ntpcheckserver', DEFAULT_NTP_CHECK_SERVER))

        with settings_group(settings, "LEDS"):
            self.setLEDInactiveBGColor(self.getColorFromName(settings.value('inactivebgcolor', DEFAULT_LED_INACTIVE_BG_COLOR)))
            self.setLEDInactiveFGColor(self.getColorFromName(settings.value('inactivetextcolor', DEFAULT_LED_INACTIVE_TEXT_COLOR)))

        # LED-specific default colors (different from general defaults)
        led_default_colors = {
            1: '#FF0000',  # Red
            2: '#DCDC00',  # Yellow
            3: '#00C8C8',  # Cyan
            4: '#FF00FF',  # Magenta
        }
        
        for led_num in range(1, 5):
            with settings_group(settings, f"LED{led_num}"):
                getattr(self, f'LED{led_num}').setChecked(settings.value('used', DEFAULT_LED_USED, type=bool))
                default_text = DEFAULT_LED_TEXTS.get(led_num, f'LED{led_num}')
                getattr(self, f'LED{led_num}Text').setText(settings.value('text', default_text))
                getattr(self, f'LED{led_num}Demo').setText(settings.value('text', default_text))
                default_bg_color = led_default_colors.get(led_num, DEFAULT_LED_ACTIVE_BG_COLOR)
                getattr(self, f'setLED{led_num}BGColor')(self.getColorFromName(settings.value('activebgcolor', default_bg_color)))
                getattr(self, f'setLED{led_num}FGColor')(self.getColorFromName(settings.value('activetextcolor', DEFAULT_LED_ACTIVE_TEXT_COLOR)))
                getattr(self, f'LED{led_num}Autoflash').setChecked(settings.value('autoflash', DEFAULT_LED_AUTOFLASH, type=bool))
                getattr(self, f'LED{led_num}Timedflash').setChecked(settings.value('timedflash', DEFAULT_LED_TIMEDFLASH, type=bool))

        with settings_group(settings, "Clock"):
            self.clockDigital.setChecked(settings.value('digital', DEFAULT_CLOCK_DIGITAL, type=bool))
            self.clockAnalog.setChecked(not settings.value('digital', DEFAULT_CLOCK_DIGITAL, type=bool))
            self.showSeconds.setChecked(settings.value('showSeconds', DEFAULT_CLOCK_SHOW_SECONDS, type=bool))
            self.seconds_in_one_line.setChecked(settings.value('showSecondsInOneLine', DEFAULT_CLOCK_SECONDS_IN_ONE_LINE, type=bool))
            if not settings.value('showSeconds', DEFAULT_CLOCK_SHOW_SECONDS, type=bool):
                self.seconds_in_one_line.setDisabled(True)
                self.seconds_separate.setDisabled(True)
            self.staticColon.setChecked(settings.value('staticColon', DEFAULT_CLOCK_STATIC_COLON, type=bool))
            self.useTextclock.setChecked(settings.value('useTextClock', DEFAULT_CLOCK_USE_TEXT_CLOCK, type=bool))
            self.setDigitalHourColor(self.getColorFromName(settings.value('digitalhourcolor', DEFAULT_CLOCK_DIGITAL_HOUR_COLOR)))
            self.setDigitalSecondColor(self.getColorFromName(settings.value('digitalsecondcolor', DEFAULT_CLOCK_DIGITAL_SECOND_COLOR)))
            self.setDigitalDigitColor(self.getColorFromName(settings.value('digitaldigitcolor', DEFAULT_CLOCK_DIGITAL_DIGIT_COLOR)))
            self.logoPath.setText(
                settings.value('logopath', DEFAULT_CLOCK_LOGO_PATH))
            if settings.value('logoUpper', DEFAULT_CLOCK_LOGO_UPPER, type=bool):
                self.radioButton_logo_upper.setChecked(True)
                self.radioButton_logo_lower.setChecked(False)
            else:
                self.radioButton_logo_upper.setChecked(False)
                self.radioButton_logo_lower.setChecked(True)

        with settings_group(settings, "Network"):
            self.udpport.setText(str(settings.value('udpport', str(DEFAULT_UDP_PORT))))
            self.httpport.setText(str(settings.value('httpport', str(DEFAULT_HTTP_PORT))))
            self.multicast_group.setText(settings.value('multicast_address', DEFAULT_MULTICAST_ADDRESS))

        with settings_group(settings, "MQTT"):
            self.enablemqtt.setChecked(settings.value('enablemqtt', False, type=bool))
            self.mqttserver.setText(settings.value('mqttserver', "localhost", type=str))
            self.mqttport.setText(str(settings.value('mqttport', 1883, type=int)))
            self.mqttuser.setText(settings.value('mqttuser', "", type=str))
            self.mqttpassword.setText(settings.value('mqttpassword', "", type=str))
            self.mqttbasetopic.setText(settings.value('mqttbasetopic', "onairscreen", type=str))
            # Enable/disable MQTT fields based on checkbox
            self.mqttserver.setEnabled(self.enablemqtt.isChecked())
            self.mqttport.setEnabled(self.enablemqtt.isChecked())
            self.mqttuser.setEnabled(self.enablemqtt.isChecked())
            self.mqttpassword.setEnabled(self.enablemqtt.isChecked())
            self.mqttbasetopic.setEnabled(self.enablemqtt.isChecked())

        with settings_group(settings, "Formatting"):
            self.dateFormat.setText(settings.value('dateFormat', DEFAULT_DATE_FORMAT))
            self.textClockLanguage.setCurrentIndex(
                self.textClockLanguage.findText(settings.value('textClockLanguage', DEFAULT_TEXT_CLOCK_LANGUAGE)))
            self.time_am_pm.setChecked(settings.value('isAmPm', DEFAULT_IS_AM_PM, type=bool))
            self.time_24h.setChecked(not settings.value('isAmPm', DEFAULT_IS_AM_PM, type=bool))

        with settings_group(settings, "WeatherWidget"):
            self.owmWidgetEnabled.setChecked(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))
            self.owmAPIKey.setText(settings.value('owmAPIKey', DEFAULT_WEATHER_API_KEY))
            self.owmCityID.setText(settings.value('owmCityID', DEFAULT_WEATHER_CITY_ID))
            self.owmLanguage.setCurrentIndex(self.owmLanguage.findText(settings.value('owmLanguage', DEFAULT_WEATHER_LANGUAGE)))
            self.owmUnit.setCurrentIndex(self.owmUnit.findText(settings.value('owmUnit', DEFAULT_WEATHER_UNIT)))
            self.owmAPIKey.setEnabled(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))
            self.owmCityID.setEnabled(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))
            self.owmLanguage.setEnabled(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))
            self.owmUnit.setEnabled(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))
            self.owmTestAPI.setEnabled(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))
            self.owmTestOutput.setEnabled(settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool))

        with settings_group(settings, "Timers"):
            self.enableAIR1.setChecked(settings.value('TimerAIR1Enabled', True, type=bool))
            self.enableAIR2.setChecked(settings.value('TimerAIR2Enabled', True, type=bool))
            self.enableAIR3.setChecked(settings.value('TimerAIR3Enabled', True, type=bool))
            self.enableAIR4.setChecked(settings.value('TimerAIR4Enabled', True, type=bool))
            self.AIR1Text.setText(settings.value('TimerAIR1Text', DEFAULT_TIMER_AIR_TEXTS.get(1, 'Mic')))
            self.AIR2Text.setText(settings.value('TimerAIR2Text', DEFAULT_TIMER_AIR_TEXTS.get(2, 'Phone')))
            self.AIR3Text.setText(settings.value('TimerAIR3Text', DEFAULT_TIMER_AIR_TEXTS.get(3, 'Timer')))
            self.AIR4Text.setText(settings.value('TimerAIR4Text', DEFAULT_TIMER_AIR_TEXTS.get(4, 'Stream')))
            self.setAIR1BGColor(self.getColorFromName(settings.value('AIR1activebgcolor', DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR)))
            self.setAIR1FGColor(self.getColorFromName(settings.value('AIR1activetextcolor', DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR)))
            self.setAIR2BGColor(self.getColorFromName(settings.value('AIR2activebgcolor', DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR)))
            self.setAIR2FGColor(self.getColorFromName(settings.value('AIR2activetextcolor', DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR)))
            self.setAIR3BGColor(self.getColorFromName(settings.value('AIR3activebgcolor', DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR)))
            self.setAIR3FGColor(self.getColorFromName(settings.value('AIR3activetextcolor', DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR)))
            self.setAIR4BGColor(self.getColorFromName(settings.value('AIR4activebgcolor', DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR)))
            self.setAIR4FGColor(self.getColorFromName(settings.value('AIR4activetextcolor', DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR)))

            self.AIR1IconPath.setText(settings.value('air1iconpath', DEFAULT_TIMER_AIR_ICON_PATHS.get(1, ':/mic_icon/images/mic_icon.png')))
            self.AIR2IconPath.setText(settings.value('air2iconpath', DEFAULT_TIMER_AIR_ICON_PATHS.get(2, ':/phone_icon/images/phone_icon.png')))
            self.AIR3IconPath.setText(settings.value('air3iconpath', DEFAULT_TIMER_AIR_ICON_PATHS.get(3, ':/timer_icon/images/timer_icon.png')))
            self.AIR4IconPath.setText(settings.value('air4iconpath', DEFAULT_TIMER_AIR_ICON_PATHS.get(4, ':/stream_icon/images/antenna2.png')))

            self.AIRMinWidth.setValue(settings.value('TimerAIRMinWidth', DEFAULT_TIMER_AIR_MIN_WIDTH, type=int))

        with settings_group(settings, "Fonts"):
            self.ExampleFont_LED1.setFont(QFont(settings.value('LED1FontName', DEFAULT_FONT_NAME),
                                                settings.value('LED1FontSize', DEFAULT_FONT_SIZE_LED, type=int),
                                                settings.value('LED1FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_LED2.setFont(QFont(settings.value('LED2FontName', DEFAULT_FONT_NAME),
                                                settings.value('LED2FontSize', DEFAULT_FONT_SIZE_LED, type=int),
                                                settings.value('LED2FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_LED3.setFont(QFont(settings.value('LED3FontName', DEFAULT_FONT_NAME),
                                                settings.value('LED3FontSize', DEFAULT_FONT_SIZE_LED, type=int),
                                                settings.value('LED3FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_LED4.setFont(QFont(settings.value('LED4FontName', DEFAULT_FONT_NAME),
                                                settings.value('LED4FontSize', DEFAULT_FONT_SIZE_LED, type=int),
                                                settings.value('LED4FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_AIR1.setFont(QFont(settings.value('AIR1FontName', DEFAULT_FONT_NAME),
                                                settings.value('AIR1FontSize', DEFAULT_FONT_SIZE_TIMER, type=int),
                                                settings.value('AIR1FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_AIR2.setFont(QFont(settings.value('AIR2FontName', DEFAULT_FONT_NAME),
                                                settings.value('AIR2FontSize', DEFAULT_FONT_SIZE_TIMER, type=int),
                                                settings.value('AIR2FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_AIR3.setFont(QFont(settings.value('AIR3FontName', DEFAULT_FONT_NAME),
                                                settings.value('AIR3FontSize', DEFAULT_FONT_SIZE_TIMER, type=int),
                                                settings.value('AIR3FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_AIR4.setFont(QFont(settings.value('AIR4FontName', DEFAULT_FONT_NAME),
                                                settings.value('AIR4FontSize', DEFAULT_FONT_SIZE_TIMER, type=int),
                                                settings.value('AIR4FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_StationName.setFont(QFont(settings.value('StationNameFontName', DEFAULT_FONT_NAME),
                                                       settings.value('StationNameFontSize', DEFAULT_FONT_SIZE_STATION, type=int),
                                                       settings.value('StationNameFontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_Slogan.setFont(QFont(settings.value('SloganFontName', DEFAULT_FONT_NAME),
                                                  settings.value('SloganFontSize', DEFAULT_FONT_SIZE_SLOGAN, type=int),
                                                  settings.value('SloganFontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)))
            self.ExampleFont_LED1.setText(f"{settings.value('LED1FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('LED1FontSize', DEFAULT_FONT_SIZE_LED, type=int)}pt")
            self.ExampleFont_LED2.setText(f"{settings.value('LED2FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('LED2FontSize', DEFAULT_FONT_SIZE_LED, type=int)}pt")
            self.ExampleFont_LED3.setText(f"{settings.value('LED3FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('LED3FontSize', DEFAULT_FONT_SIZE_LED, type=int)}pt")
            self.ExampleFont_LED4.setText(f"{settings.value('LED4FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('LED4FontSize', DEFAULT_FONT_SIZE_LED, type=int)}pt")
            self.ExampleFont_AIR1.setText(f"{settings.value('AIR1FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('AIR1FontSize', DEFAULT_FONT_SIZE_TIMER, type=int)}pt")
            self.ExampleFont_AIR2.setText(f"{settings.value('AIR2FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('AIR2FontSize', DEFAULT_FONT_SIZE_TIMER, type=int)}pt")
            self.ExampleFont_AIR3.setText(f"{settings.value('AIR3FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('AIR3FontSize', DEFAULT_FONT_SIZE_TIMER, type=int)}pt")
            self.ExampleFont_AIR4.setText(f"{settings.value('AIR4FontName', DEFAULT_FONT_NAME)}, "
                                          f"{settings.value('AIR4FontSize', DEFAULT_FONT_SIZE_TIMER, type=int)}pt")
            self.ExampleFont_StationName.setText(f"{settings.value('StationNameFontName', DEFAULT_FONT_NAME)}, "
                                                 f"{settings.value('StationNameFontSize', DEFAULT_FONT_SIZE_STATION, type=int)}pt")
            self.ExampleFont_Slogan.setText(f"{settings.value('SloganFontName', DEFAULT_FONT_NAME)}, "
                                            f"{settings.value('SloganFontSize', DEFAULT_FONT_SIZE_SLOGAN, type=int)}pt")

    def getSettingsFromDialog(self):
        if self.oacmode:
            settings = self.settings
        else:
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")

        with settings_group(settings, "General"):
            settings.setValue('stationname', self.StationName.displayText())
            settings.setValue('slogan', self.Slogan.displayText())
            settings.setValue('stationcolor', self.getStationNameColor().name())
            settings.setValue('slogancolor', self.getSloganColor().name())
            settings.setValue('updatecheck', self.checkBox_UpdateCheck.isChecked())
            settings.setValue('updatekey', self.updateKey.displayText())
            settings.setValue('updateincludebeta', self.checkBox_IncludeBetaVersions.isChecked())
            settings.setValue('replacenow', self.replaceNOW.isChecked())
            settings.setValue('replacenowtext', self.replaceNOWText.displayText())
            settings.setValue('loglevel', self.loglevelcombobox.currentText())

        with settings_group(settings, "NTP"):
            settings.setValue('ntpcheck', self.checkBox_NTPCheck.isChecked())
            settings.setValue('ntpcheckserver', self.NTPCheckServer.displayText())

        with settings_group(settings, "LEDS"):
            settings.setValue('inactivebgcolor', self.getLEDInactiveBGColor().name())
            settings.setValue('inactivetextcolor', self.getLEDInactiveFGColor().name())

        with settings_group(settings, "LED1"):
            settings.setValue('used', self.LED1.isChecked())
            settings.setValue('text', self.LED1Text.displayText())
            settings.setValue('activebgcolor', self.getLED1BGColor().name())
            settings.setValue('activetextcolor', self.getLED1FGColor().name())
            settings.setValue('autoflash', self.LED1Autoflash.isChecked())
            settings.setValue('timedflash', self.LED1Timedflash.isChecked())

        with settings_group(settings, "LED2"):
            settings.setValue('used', self.LED2.isChecked())
            settings.setValue('text', self.LED2Text.displayText())
            settings.setValue('activebgcolor', self.getLED2BGColor().name())
            settings.setValue('activetextcolor', self.getLED2FGColor().name())
            settings.setValue('autoflash', self.LED2Autoflash.isChecked())
            settings.setValue('timedflash', self.LED2Timedflash.isChecked())

        with settings_group(settings, "LED3"):
            settings.setValue('used', self.LED3.isChecked())
            settings.setValue('text', self.LED3Text.displayText())
            settings.setValue('activebgcolor', self.getLED3BGColor().name())
            settings.setValue('activetextcolor', self.getLED3FGColor().name())
            settings.setValue('autoflash', self.LED3Autoflash.isChecked())
            settings.setValue('timedflash', self.LED3Timedflash.isChecked())

        with settings_group(settings, "LED4"):
            settings.setValue('used', self.LED4.isChecked())
            settings.setValue('text', self.LED4Text.displayText())
            settings.setValue('activebgcolor', self.getLED4BGColor().name())
            settings.setValue('activetextcolor', self.getLED4FGColor().name())
            settings.setValue('autoflash', self.LED4Autoflash.isChecked())
            settings.setValue('timedflash', self.LED4Timedflash.isChecked())

        with settings_group(settings, "Clock"):
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

        with settings_group(settings, "Network"):
            settings.setValue('udpport', self.udpport.displayText())
            settings.setValue('httpport', self.httpport.displayText())
            settings.setValue('multicast_address', self.multicast_group.displayText())

        with settings_group(settings, "MQTT"):
            settings.setValue('enablemqtt', self.enablemqtt.isChecked())
            settings.setValue('mqttserver', self.mqttserver.displayText())
            settings.setValue('mqttport', self.mqttport.displayText())
            settings.setValue('mqttuser', self.mqttuser.displayText())
            settings.setValue('mqttpassword', self.mqttpassword.displayText())
            settings.setValue('mqttbasetopic', self.mqttbasetopic.displayText())

        with settings_group(settings, "Formatting"):
            settings.setValue('dateFormat', self.dateFormat.displayText())
            settings.setValue('textClockLanguage', self.textClockLanguage.currentText())
            settings.setValue('isAmPm', self.time_am_pm.isChecked())

        with settings_group(settings, "WeatherWidget"):
            settings.setValue('owmWidgetEnabled', self.owmWidgetEnabled.isChecked())
            settings.setValue('owmAPIKey', self.owmAPIKey.displayText())
            settings.setValue('owmCityID', self.owmCityID.displayText())
            settings.setValue('owmLanguage', self.owmLanguage.currentText())
            settings.setValue('owmUnit', self.owmUnit.currentText())

        with settings_group(settings, "Timers"):
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

        with settings_group(settings, "Fonts"):
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
        logger.info("Manual update check triggered")
        self.manual_update_check = True
        self.check_for_updates()

    def check_for_updates(self):
        if self.checkBox_UpdateCheck.isChecked():
            logger.info("Starting update check")
            update_key = self.updateKey.displayText()
            if len(update_key) == 50:
                logger.debug(f"Update check parameters: version={versionString}, distribution={distributionString}, include_beta={self.checkBox_IncludeBetaVersions.isChecked()}")
                data = QUrlQuery()
                data.addQueryItem("update_key", update_key)
                data.addQueryItem("product", "OnAirScreen")
                data.addQueryItem("current_version", versionString)
                data.addQueryItem("distribution", distributionString)
                data.addQueryItem("mac", self.get_mac())
                data.addQueryItem("include_beta", f'{self.checkBox_IncludeBetaVersions.isChecked()}')
                req = QtNetwork.QNetworkRequest(QUrl(update_url))
                req.setHeader(QtNetwork.QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/x-www-form-urlencoded")
                logger.debug(f"Sending update check request to: {update_url}")
                self.nam_update_check = QtNetwork.QNetworkAccessManager()
                self.nam_update_check.finished.connect(self.handle_update_check_response)
                self.nam_update_check.post(req, data.toString().encode("UTF-8"))
                logger.debug("Update check request sent successfully")
            else:
                logger.error(f"Update check failed: update key has wrong format (length: {len(update_key)}, expected: 50)")
                self.error_dialog = QErrorMessage()
                self.error_dialog.setWindowTitle("Update Check Error")
                self.error_dialog.showMessage('Update key is in the wrong format!', 'UpdateKeyError')
        else:
            logger.debug("Update check skipped: update check is disabled in settings")

    def handle_update_check_response(self, reply):
        er = reply.error()
        if er == QtNetwork.QNetworkReply.NetworkError.NoError:
            logger.info("Update check response received successfully")
            try:
                bytes_string = reply.readAll()
                reply_string = str(bytes_string, 'utf-8')
                logger.debug(f"Update check response body: {reply_string}")
                json_reply = json.loads(reply_string)
                status = json_reply.get('Status', 'UNKNOWN')
                logger.info(f"Update check response status: {status}")

                if json_reply['Status'] == "UPDATE":
                    logger.info(f"Update available: {json_reply.get('Message', 'No message')}")
                    self.timer_message_box = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
                    self.timer_message_box.exec()

                if json_reply['Status'] == "OK" and self.manual_update_check:
                    message = json_reply.get('Message', 'No message')
                    logger.info(f"Update check successful (no update available): {message}")
                    self.message_box = QMessageBox()
                    
                    # Set OnAirScreen app icon
                    icon = QIcon()
                    icon.addPixmap(QPixmap(":/oas_icon/images/oas_icon.png"), QIcon.Mode.Normal, QIcon.State.Off)
                    self.message_box.setWindowIcon(icon)
                    self.message_box.setIconPixmap(QPixmap(":/oas_icon/images/oas_icon.png"))
                    
                    self.message_box.setWindowTitle("OnAirScreen Update Check")
                    self.message_box.setText("OnAirScreen Update Check")
                    self.message_box.setInformativeText(f"{message}")
                    self.message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                    self.message_box.show()
                    self.manual_update_check = False

                if json_reply['Status'] == "ERROR" and self.manual_update_check:
                    message = json_reply.get('Message', 'No message')
                    logger.error(f"Update check returned error: {message}")
                    self.message_box = QMessageBox()
                    
                    # Set OnAirScreen app icon
                    icon = QIcon()
                    icon.addPixmap(QPixmap(":/oas_icon/images/oas_icon.png"), QIcon.Mode.Normal, QIcon.State.Off)
                    self.message_box.setWindowIcon(icon)
                    self.message_box.setIconPixmap(QPixmap(":/oas_icon/images/oas_icon.png"))
                    
                    self.message_box.setWindowTitle("OnAirScreen Update Check")
                    self.message_box.setText("OnAirScreen Update Check")
                    self.message_box.setInformativeText(f"{message}")
                    self.message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                    self.message_box.show()
                    self.manual_update_check = False

                if json_reply['Status'] not in ["UPDATE", "OK", "ERROR"]:
                    logger.warning(f"Update check returned unknown status: {status}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse update check response as JSON: {e}")
                if self.manual_update_check:
                    self.error_dialog = QErrorMessage()
                    self.error_dialog.setWindowTitle("Update Check Error")
                    self.error_dialog.showMessage('Invalid response from update server', 'UpdateCheckError')
            except Exception as e:
                if isinstance(e, (SettingsError, InvalidConfigValueError)):
                    log_exception(logger, e)
                else:
                    error = SettingsError(f"Unexpected error processing update check response: {e}")
                    log_exception(logger, error)
                if self.manual_update_check:
                    self.error_dialog = QErrorMessage()
                    self.error_dialog.setWindowTitle("Update Check Error")
                    self.error_dialog.showMessage(f'Error processing update check response: {str(e)}', 'UpdateCheckError')

        else:
            error_string = f"Error occurred: {er}, {reply.errorString()}"
            logger.error(f"Update check network error: {error_string}")
            if self.manual_update_check:
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
        
        # MQTT settings
        self.enablemqtt.setToolTip("Enable MQTT integration with Home Assistant Autodiscovery")
        self.mqttserver.setToolTip("MQTT broker hostname or IP address")
        self.mqttport.setToolTip("MQTT broker port (default: 1883)")
        self.mqttuser.setToolTip("MQTT username (optional)")
        self.mqttpassword.setToolTip("MQTT password (optional)")
        self.mqttbasetopic.setToolTip("Base MQTT topic prefix (default: onairscreen)")
        
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
        
    def _on_mqtt_enabled_changed(self, enabled: bool) -> None:
        """Handle MQTT enabled checkbox state change"""
        self.mqttserver.setEnabled(enabled)
        self.mqttport.setEnabled(enabled)
        self.mqttuser.setEnabled(enabled)
        self.mqttpassword.setEnabled(enabled)
        self.mqttbasetopic.setEnabled(enabled)
        
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
        self.ResetSettingsButton.setToolTip("Reset all settings to default values (this cannot be undone)")
        
        # Preset management tooltips
        self.SaveSettingsButton.setToolTip("Save current configuration as a preset")
        self.LoadSettingsButton.setToolTip("Load a saved preset configuration")
        self.DeleteSettingsButton.setToolTip("Delete a saved preset")

    def _connect_preset_buttons(self) -> None:
        """
        Connect preset management buttons from UI to their handlers
        """
        # Connect Save Settings button
        if hasattr(self, 'SaveSettingsButton'):
            self.SaveSettingsButton.clicked.connect(self.save_preset_dialog)
        else:
            logger.warning("SaveSettingsButton not found in UI")
        
        # Connect Load Settings button
        if hasattr(self, 'LoadSettingsButton'):
            self.LoadSettingsButton.clicked.connect(self.load_preset_dialog)
        else:
            logger.warning("LoadSettingsButton not found in UI")
        
        # Connect Delete Settings button
        if hasattr(self, 'DeleteSettingsButton'):
            self.DeleteSettingsButton.clicked.connect(self.delete_preset_dialog)
        else:
            logger.warning("DeleteSettingsButton not found in UI")

    def save_preset_dialog(self) -> None:
        """
        Show dialog to save current configuration as a preset
        """
        # First, save current dialog state to QSettings
        self.getSettingsFromDialog()
        
        # Get preset name from user
        preset_name, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter a name for this preset:",
            text=""
        )
        
        if not ok or not preset_name.strip():
            return
        
        # Check if preset already exists
        presets = self.list_presets()
        existing_preset = next((p for p in presets if p["name"].lower() == preset_name.strip().lower()), None)
        
        if existing_preset:
            reply = QMessageBox.question(
                self,
                "Preset Exists",
                f"A preset named '{preset_name}' already exists.\n\nDo you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Save preset
        success = self.save_preset(preset_name.strip())
        
        if success:
            QMessageBox.information(
                self,
                "Preset Saved",
                f"Preset '{preset_name}' has been saved successfully."
            )
        else:
            QMessageBox.warning(
                self,
                "Save Failed",
                f"Failed to save preset '{preset_name}'.\n\nPlease check the logs for details."
            )

    def load_preset_dialog(self) -> None:
        """
        Show dialog to load a preset configuration
        """
        # Get list of available presets
        presets = self.list_presets()
        
        if not presets:
            QMessageBox.information(
                self,
                "No Presets",
                "No presets are available.\n\nSave a preset first using 'Save Preset...'."
            )
            return
        
        # Create list of preset names for selection
        preset_names = [p["name"] for p in presets]
        
        # Show selection dialog
        preset_name, ok = QInputDialog.getItem(
            self,
            "Load Preset",
            "Select a preset to load:",
            preset_names,
            0,
            False
        )
        
        if not ok:
            return
        
        # Find the preset filename
        selected_preset = next((p for p in presets if p["name"] == preset_name), None)
        if not selected_preset:
            QMessageBox.warning(
                self,
                "Load Failed",
                f"Could not find preset '{preset_name}'."
            )
            return
        
        # Confirm loading (this will overwrite current settings)
        reply = QMessageBox.question(
            self,
            "Load Preset",
            f"Loading preset '{preset_name}' will overwrite your current settings.\n\nDo you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Load preset
        success = self.load_preset(selected_preset["filename"])
        
        if success:
            QMessageBox.information(
                self,
                "Preset Loaded",
                f"Preset '{preset_name}' has been loaded successfully.\n\nClick 'Apply' to apply the changes."
            )
        else:
            QMessageBox.warning(
                self,
                "Load Failed",
                f"Failed to load preset '{preset_name}'.\n\nPlease check the logs for details."
            )

    def delete_preset_dialog(self) -> None:
        """
        Show dialog to delete a preset
        """
        # Get list of available presets
        presets = self.list_presets()
        
        if not presets:
            QMessageBox.information(
                self,
                "No Presets",
                "No presets are available."
            )
            return
        
        # Create list of preset names for selection
        preset_names = [p["name"] for p in presets]
        
        # Show selection dialog
        preset_name, ok = QInputDialog.getItem(
            self,
            "Delete Preset",
            "Select a preset to delete:",
            preset_names,
            0,
            False
        )
        
        if not ok:
            return
        
        # Find the preset filename
        selected_preset = next((p for p in presets if p["name"] == preset_name), None)
        if not selected_preset:
            QMessageBox.warning(
                self,
                "Delete Failed",
                f"Could not find preset '{preset_name}'."
            )
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete preset '{preset_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete preset
        success = self.delete_preset(selected_preset["filename"])
        
        if success:
            QMessageBox.information(
                self,
                "Preset Deleted",
                f"Preset '{preset_name}' has been deleted successfully."
            )
        else:
            QMessageBox.warning(
                self,
                "Delete Failed",
                f"Failed to delete preset '{preset_name}'.\n\nPlease check the logs for details."
            )


class SettingsRestorer:
    """
    Helper class for restoring settings from configuration to MainScreen widgets
    
    This class provides methods to restore various settings groups from QSettings
    to the MainScreen UI widgets.
    """
    
    def __init__(self, main_screen, settings_instance):
        """
        Initialize the settings restorer
        
        Args:
            main_screen: MainScreen instance to restore settings to
            settings_instance: Settings instance for color conversion methods
        """
        self.main_screen = main_screen
        self.settings = settings_instance
    
    def restore_all(self, settings: QSettings) -> None:
        """Restore all settings from configuration"""
        self.restore_general(settings)
        self.restore_led(settings)
        self.restore_clock(settings)
        self.restore_formatting(settings)
        self.restore_weather(settings)
        self.restore_timer(settings)
        self.restore_font(settings)
    
    def restore_general(self, settings: QSettings) -> None:
        """
        Restore general settings (station name, slogan, colors)
        
        Args:
            settings: QSettings object to read from
        """
        with settings_group(settings, "General"):
            self.main_screen.labelStation.setText(settings.value('stationname', DEFAULT_STATION_NAME))
            self.main_screen.labelSlogan.setText(settings.value('slogan', DEFAULT_SLOGAN))
            self.main_screen.set_station_color(self.settings.getColorFromName(settings.value('stationcolor', DEFAULT_STATION_COLOR)))
            self.main_screen.set_slogan_color(self.settings.getColorFromName(settings.value('slogancolor', DEFAULT_SLOGAN_COLOR)))
    
    def restore_led(self, settings: QSettings) -> None:
        """
        Restore LED settings (text, visibility)
        
        Args:
            settings: QSettings object to read from
        """
        for led_num in range(1, 5):
            with settings_group(settings, f"LED{led_num}"):
                default_text = DEFAULT_LED_TEXTS.get(led_num, f'LED{led_num}')
                getattr(self.main_screen, f'set_led{led_num}_text')(settings.value('text', default_text))
                getattr(self.main_screen, f'buttonLED{led_num}').setVisible(settings.value('used', True, type=bool))
    
    def restore_clock(self, settings: QSettings) -> None:
        """
        Restore clock widget settings
        
        Args:
            settings: QSettings object to read from
        """
        with settings_group(settings, "Clock"):
            self.main_screen.clockWidget.set_clock_mode(settings.value('digital', True, type=bool))
            self.main_screen.clockWidget.set_digi_hour_color(
                self.settings.getColorFromName(settings.value('digitalhourcolor', DEFAULT_CLOCK_DIGITAL_HOUR_COLOR)))
            self.main_screen.clockWidget.set_digi_second_color(
                self.settings.getColorFromName(settings.value('digitalsecondcolor', DEFAULT_CLOCK_DIGITAL_SECOND_COLOR)))
            self.main_screen.clockWidget.set_digi_digit_color(
                self.settings.getColorFromName(settings.value('digitaldigitcolor', DEFAULT_CLOCK_DIGITAL_DIGIT_COLOR)))
            self.main_screen.clockWidget.set_logo(
                settings.value('logopath', DEFAULT_CLOCK_LOGO_PATH))
            self.main_screen.clockWidget.set_show_seconds(settings.value('showSeconds', False, type=bool))
            self.main_screen.clockWidget.set_one_line_time(settings.value('showSecondsInOneLine', False, type=bool) &
                                                           settings.value('showSeconds', False, type=bool))
            self.main_screen.clockWidget.set_static_colon(settings.value('staticColon', False, type=bool))
            self.main_screen.clockWidget.set_logo_upper(settings.value('logoUpper', False, type=bool))
            self.main_screen.labelTextRight.setVisible(settings.value('useTextClock', True, type=bool))
    
    def restore_formatting(self, settings: QSettings) -> None:
        """
        Restore formatting settings (AM/PM, text clock language)
        
        Args:
            settings: QSettings object to read from
        """
        with settings_group(settings, "Formatting"):
            self.main_screen.clockWidget.set_am_pm(settings.value('isAmPm', False, type=bool))
            self.main_screen.textLocale = settings.value('textClockLanguage', DEFAULT_TEXT_CLOCK_LANGUAGE)
    
    def restore_weather(self, settings: QSettings) -> None:
        """
        Restore weather widget settings
        
        Args:
            settings: QSettings object to read from
        """
        with settings_group(settings, "WeatherWidget"):
            if settings.value('owmWidgetEnabled', False, type=bool):
                self.main_screen.weatherWidget.show()
            else:
                self.main_screen.weatherWidget.hide()
    
    def restore_timer(self, settings: QSettings) -> None:
        """
        Restore timer/AIR settings
        
        Args:
            settings: QSettings object to read from
        """
        with settings_group(settings, "Timers"):
            # Configuration for each AIR timer
            air_timer_configs = [
                (1, 'TimerAIR1Enabled', 'TimerAIR1Text', 'air1iconpath'),
                (2, 'TimerAIR2Enabled', 'TimerAIR2Text', 'air2iconpath'),
                (3, 'TimerAIR3Enabled', 'TimerAIR3Text', 'air3iconpath'),
                (4, 'TimerAIR4Enabled', 'TimerAIR4Text', 'air4iconpath')
            ]
            
            for air_num, enabled_key, text_key, icon_key in air_timer_configs:
                text_default = DEFAULT_TIMER_AIR_TEXTS.get(air_num, f'AIR{air_num}')
                icon_default = DEFAULT_TIMER_AIR_ICON_PATHS.get(air_num, '')
                if not settings.value(enabled_key, True, type=bool):
                    led_widget = getattr(self.main_screen, f'AirLED_{air_num}')
                    led_widget.hide()
                else:
                    label_text = settings.value(text_key, text_default)
                    label_widget = getattr(self.main_screen, f'AirLabel_{air_num}')
                    icon_widget = getattr(self.main_screen, f'AirIcon_{air_num}')
                    led_widget = getattr(self.main_screen, f'AirLED_{air_num}')
                    
                    label_widget.setText(f"{label_text}\n0:00")
                    inactive_text_color = settings.value('inactivetextcolor', DEFAULT_TIMER_AIR_INACTIVE_TEXT_COLOR)
                    inactive_bg_color = settings.value('inactivebgcolor', DEFAULT_TIMER_AIR_INACTIVE_BG_COLOR)
                    
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
            min_width = settings.value('TimerAIRMinWidth', DEFAULT_TIMER_AIR_MIN_WIDTH, type=int)
            for air_num in range(1, 5):
                led_widget = getattr(self.main_screen, f'AirLED_{air_num}')
                led_widget.setMinimumWidth(min_width)
    
    def restore_font(self, settings: QSettings) -> None:
        """
        Restore font settings for all widgets
        
        Args:
            settings: QSettings object to read from
        """
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
                widget = getattr(self.main_screen, widget_name)
                font_name = settings.value(f'{font_prefix}FontName', DEFAULT_FONT_NAME)
                font_size = settings.value(f'{font_prefix}FontSize', 24, type=int)
                font_weight = settings.value(f'{font_prefix}FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)
                widget.setFont(QFont(font_name, font_size, font_weight))

