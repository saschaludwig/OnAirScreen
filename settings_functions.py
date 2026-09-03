#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# settings_functions.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

import json
import logging
import os
import textwrap
from collections import defaultdict
from pathlib import Path
from uuid import getnode

import PySide6.QtNetwork as QtNetwork
from PySide6.QtCore import (
    QSettings, QTimer, Qt, Signal, QUrl, QUrlQuery, QCoreApplication,
    QRectF, QPointF, QRegularExpression, QSize, QFile, QIODevice,
)
from PySide6.QtGui import (
    QPalette, QColor, QFont, QIcon, QPixmap, QPainter, QPen, QAction,
    QRegularExpressionValidator, QDesktopServices,
)
from PySide6.QtWidgets import (QWidget, QColorDialog, QFileDialog, QErrorMessage, QMessageBox,
                              QInputDialog, QLineEdit, QScrollArea, QFrame, QVBoxLayout,
                              QSizePolicy)

from settings import Ui_Settings
from crash_handler import get_log_directory, ensure_log_directory
from utils import TimerUpdateMessageBox, settings_group, INSTANCE_NAME_REGEX, normalize_instance_name
from version import versionString
from weatherwidget import WeatherWidget as ww, extract_owm_city_id, parse_owm_geocode_results
from defaults import *  # noqa: F403, F405
from exceptions import SettingsError, InvalidConfigValueError, log_exception
from font_loader import resolve_font_name
from meter_engine import migrate_audio_layout_and_unit, normalize_meter_layout

SETTINGS_WINDOW_INITIAL_WIDTH = 700
SETTINGS_WINDOW_INITIAL_HEIGHT = 800

LICENSE_RESOURCE_OASL = ":/licenses/LICENSE"
LICENSE_RESOURCE_THIRD_PARTY = ":/licenses/THIRD_PARTY_LICENSES.md"


def read_qt_resource_text(resource_path: str) -> str:
    """Read a UTF-8 text file from the Qt resource system."""
    resource_file = QFile(resource_path)
    if not resource_file.open(
        QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text
    ):
        logging.warning("Could not open license resource %s", resource_path)
        return ""
    try:
        return bytes(resource_file.readAll()).decode("utf-8")
    finally:
        resource_file.close()


def composed_license_dialog_text() -> str:
    """OASL plus third-party notices for the Settings License tab."""
    oasl = read_qt_resource_text(LICENSE_RESOURCE_OASL).rstrip()
    third_party = read_qt_resource_text(LICENSE_RESOURCE_THIRD_PARTY).rstrip()
    parts = [part for part in (oasl, third_party) if part]
    return "\n\n".join(parts) + "\n"


FONT_ROW_PREFIXES: tuple[str, ...] = (
    "AIR1", "AIR2", "AIR3", "AIR4",
    "LED1", "LED2", "LED3", "LED4",
    "StationName", "Slogan",
)
# Qt5 stored QFont.Bold as 75; older OnAirScreen defaults used 1.
QT5_BOLD_WEIGHT = 75


def default_font_size_for_prefix(prefix: str) -> int:
    """Return the default point size for a Fonts-tab row prefix."""
    if prefix.startswith("LED"):
        return DEFAULT_FONT_SIZE_LED
    if prefix.startswith("AIR"):
        return DEFAULT_FONT_SIZE_TIMER
    if prefix == "StationName":
        return DEFAULT_FONT_SIZE_STATION
    if prefix == "Slogan":
        return DEFAULT_FONT_SIZE_SLOGAN
    return DEFAULT_FONT_SIZE_LED


def is_bold_font_weight(weight) -> bool:
    """True if a stored QFont weight should be treated as bold."""
    if hasattr(weight, "value") and not isinstance(weight, (int, str)):
        weight = weight.value()
    try:
        weight_value = int(weight)
    except (TypeError, ValueError):
        return True
    if weight_value in (DEFAULT_FONT_WEIGHT_BOLD, QT5_BOLD_WEIGHT, int(QFont.Weight.Bold)):
        return True
    return weight_value >= int(QFont.Weight.Bold)


def font_weight_from_bold(bold: bool) -> int:
    """Settings weight value for a Bold checkbox."""
    return int(QFont.Weight.Bold if bold else QFont.Weight.Normal)


def qfont_weight_from_stored(weight) -> QFont.Weight:
    """Map a stored settings weight to QFont.Weight (PySide6 requires the enum)."""
    if isinstance(weight, QFont.Weight):
        return weight
    if is_bold_font_weight(weight):
        return QFont.Weight.Bold
    return QFont.Weight.Normal


try:
    from distribution import distributionString, update_url # type: ignore
except ModuleNotFoundError:
    distributionString = "OpenSource"
    update_url = "https://customer.astrastudio.de/updatemanager/c"

# Configure logging
logger = logging.getLogger(__name__)

AES67_NONE_LABEL = "None"
AES67_SAP_POLL_MS = 2000
AES67_SAP_FIRST_POLL_MS = 250
LIVEWIRE_ADV_POLL_MS = 2000
LIVEWIRE_ADV_FIRST_POLL_MS = 250


def _eye_icon(slashed: bool, color: QColor) -> QIcon:
    """Draw a simple open or slashed eye icon for secret-field toggles."""
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setWidthF(2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(4, 10, 24, 12))
    painter.setBrush(color)
    painter.drawEllipse(QRectF(13, 13, 6, 6))
    if slashed:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(7, 25), QPointF(25, 7))
    painter.end()
    return QIcon(pixmap)


def setup_secret_line_edit(line_edit: QLineEdit) -> QAction:
    """Mask a line edit and add a trailing slashed-eye toggle to reveal it."""
    color = line_edit.palette().color(QPalette.ColorRole.Text)
    icon_hidden = _eye_icon(slashed=True, color=color)
    icon_visible = _eye_icon(slashed=False, color=color)
    line_edit.setEchoMode(QLineEdit.EchoMode.Password)
    action = line_edit.addAction(icon_hidden, QLineEdit.ActionPosition.TrailingPosition)
    action.setCheckable(True)
    action.setToolTip("Show")

    def _toggle(visible: bool) -> None:
        if visible:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            action.setIcon(icon_visible)
            action.setToolTip("Hide")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            action.setIcon(icon_hidden)
            action.setToolTip("Show")

    action.toggled.connect(_toggle)
    return action


def aes67_sap_wanted(source, meters_enabled: bool, dialog_hidden: bool) -> bool:
    """SAP discovery runs while AES67 is selected, meters are on, and settings are shown."""
    return bool(meters_enabled) and source == "aes67" and not dialog_hidden


def livewire_adv_wanted(source, meters_enabled: bool, dialog_hidden: bool) -> bool:
    """Livewire ads run while Livewire is selected, meters are on, and settings are shown."""
    return bool(meters_enabled) and source == "livewire" and not dialog_hidden


def aes67_list_signature(items: list[tuple[str, str, dict]]) -> tuple:
    """Stable fingerprint of AES67 combo entries (skip rebuild when unchanged)."""
    return tuple(
        (
            stream_id,
            label,
            data.get("addr"),
            int(data.get("port") or 0),
            str(data.get("codec") or ""),
            int(data.get("rate") or 0),
            int(data.get("channels") or 0),
            bool(data.get("manual")),
        )
        for stream_id, label, data in items
    )


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
    test_color = QColor.fromString(color_str)
    if test_color.isValid():
        return True, color_str
    
    # Invalid color
    return False, ""


class _ShrinkableScrollArea(QScrollArea):
    """Scroll area that does not force the parent window to grow with its content."""

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(hint.width(), 0)


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

    def value(self, name: str, default=None):
        """Get a value from the current group"""
        try:
            return self.config[self.currentgroup][name]
        except KeyError:
            return default

    def fileName(self) -> str:
        """Return the settings file name (for compatibility)"""
        return "OAC Mode"


class Settings(QWidget, Ui_Settings):
    """
    Settings dialog for OnAirScreen
    
    Provides a comprehensive settings interface for configuring
    all aspects of the OnAirScreen application.
    """
    sigConfigChanged = Signal(int, str)
    sigExitOAS = Signal()
    sigRebootHost = Signal()
    sigShutdownHost = Signal()
    sigConfigFinished = Signal()
    sigConfigClosed = Signal()
    sigExitRemoteOAS = Signal(int)
    sigRebootRemoteHost = Signal(int)
    sigShutdownRemoteHost = Signal(int)
    sigCheckForUpdate = Signal()
    sigAes67StreamsChanged = Signal()
    sigLivewireStreamsChanged = Signal()

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
        self.plainTextEdit.setPlainText(composed_license_dialog_text())
        self._station_name_color = QColor(DEFAULT_STATION_COLOR)
        self._slogan_color = QColor(DEFAULT_SLOGAN_COLOR)
        self.resize(self._initial_settings_window_size())
        self._wrap_tabs_in_scroll_areas()
        self.InstanceName.setValidator(
            QRegularExpressionValidator(QRegularExpression(INSTANCE_NAME_REGEX), self)
        )
        setup_secret_line_edit(self.updateKey)
        setup_secret_line_edit(self.mqttpassword)
        setup_secret_line_edit(self.owmAPIKey)
        setup_secret_line_edit(self.websettingspin)
        self._web_pin_edited = False
        self.websettingspin.textEdited.connect(self._on_web_settings_pin_edited)
        self.owm_search_nam = QtNetwork.QNetworkAccessManager(self)
        self.owm_search_nam.finished.connect(self._handleOWMCitySearchResponse)
        self._sap_discovery = None
        self._aes67_saved = self._empty_aes67_snapshot()
        self._aes67_seen_sap_ids: set[str] = set()
        self._aes67_list_signature: tuple | None = None
        self._aes67_ui_active = False
        self._sap_poll_timer = QTimer(self)
        self._sap_poll_timer.setInterval(AES67_SAP_POLL_MS)
        self._sap_poll_timer.timeout.connect(self._on_sap_poll)
        self.sigAes67StreamsChanged.connect(
            self._on_sap_poll, Qt.ConnectionType.QueuedConnection
        )
        self._lw_discovery = None
        self._lw_list_signature: tuple | None = None
        self._lw_ui_active = False
        self._lw_poll_timer = QTimer(self)
        self._lw_poll_timer.setInterval(LIVEWIRE_ADV_POLL_MS)
        self._lw_poll_timer.timeout.connect(self._on_lw_poll)
        self.sigLivewireStreamsChanged.connect(
            self._on_lw_poll, Qt.ConnectionType.QueuedConnection
        )
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
        self.logfolderLabel.setText(f"Log Folder: {get_log_directory()}")
        # set update check mode
        self.manual_update_check = False
        self.sigCheckForUpdate.connect(self.check_for_updates)
        
        # Set tooltips for all settings widgets
        self._setup_tooltips()

    def show_settings(self):
        if self.isVisible():
            self._bring_to_front()
            return
        self.restoreSettingsFromConfig()
        self.sigConfigFinished.emit()
        self.show()
        self._bring_to_front()

    def _bring_to_front(self) -> None:
        """Raise the settings window above other windows and give it focus."""
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def _initial_settings_window_size(self) -> QSize:
        """Preferred 700×800, clamped to the available screen so small displays still fit."""
        width = SETTINGS_WINDOW_INITIAL_WIDTH
        height = SETTINGS_WINDOW_INITIAL_HEIGHT
        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            width = min(width, available.width())
            height = min(height, available.height())
        return QSize(width, height)

    def _wrap_tabs_in_scroll_areas(self) -> None:
        """Wrap each tab page so QTabWidget can shrink below the tallest page."""
        for index in range(self.tabWidget.count()):
            page = self.tabWidget.widget(index)
            if page is self.tab_general:
                continue
            old_layout = page.layout()
            if old_layout is None:
                continue
            container = QWidget()
            container.setLayout(old_layout)
            scroll = _ShrinkableScrollArea()
            scroll.setWidget(container)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            new_layout = QVBoxLayout(page)
            new_layout.setContentsMargins(0, 0, 0, 0)
            new_layout.setSpacing(0)
            new_layout.addWidget(scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_sap_discovery()
        self._sync_livewire_discovery()

    def hideEvent(self, event):
        self._stop_sap_discovery()
        self._stop_livewire_discovery()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._stop_sap_discovery()
        self._stop_livewire_discovery()
        app = QCoreApplication.instance()
        # QApplication.quit() closes this hidden top-level widget too.
        # Re-applying settings here would restart MQTT/AES67 during shutdown.
        if app is not None and app.closingDown():
            return
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

    def open_log_folder(self) -> None:
        """Open the application log folder in the system file manager."""
        try:
            log_dir = ensure_log_directory()
        except OSError as error:
            log_exception(logger, error, use_exc_info=False)
            QMessageBox.warning(
                self,
                "Log folder",
                f"Could not create or open the log folder:\n{error}",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

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
        self.openLogFolderButton.clicked.connect(self.open_log_folder)

        self.DigitalHourColorButton.clicked.connect(self.setDigitalHourColor)
        self.DigitalSecondColorButton.clicked.connect(self.setDigitalSecondColor)
        self.DigitalDigitColorButton.clicked.connect(self.setDigitalDigitColor)
        self.logoButton.clicked.connect(self.openLogoPathSelector)
        self.resetLogoButton.clicked.connect(self.resetLogo)

        self.StationNameColor.clicked.connect(self.setStationNameColor)
        self.SloganColor.clicked.connect(self.setSloganColor)

        self.owmTestAPI.clicked.connect(self.makeOWMTestCall)
        self.owmCityFind.clicked.connect(self.searchOWMCity)
        self.owmCitySearch.returnPressed.connect(self.searchOWMCity)
        self.owmCityResults.currentIndexChanged.connect(self._onOWMCityResultChanged)
        self.updateCheckNowButton.clicked.connect(self.trigger_manual_check_for_updates)

        # MQTT checkbox connection
        self.enablemqtt.toggled.connect(self._on_mqtt_enabled_changed)
        self.enableosc.toggled.connect(self._on_osc_enabled_changed)

        # Audio meters
        self.pushButton_AudioRefresh.clicked.connect(
            lambda: self.refresh_audio_input_devices(rescan=True)
        )
        self.pushButton_Aes67PasteSdp.clicked.connect(self._paste_aes67_sdp)
        self.comboBox_Aes67Stream.currentIndexChanged.connect(self._on_aes67_stream_changed)
        self.comboBox_LivewireStream.currentIndexChanged.connect(self._on_livewire_stream_changed)
        self.spinBox_LivewireChannel.valueChanged.connect(self._on_livewire_channel_changed)
        self.comboBox_LivewireIface.currentIndexChanged.connect(self._on_aoip_iface_changed)
        self.checkBox_TooLoud.toggled.connect(self._on_tooloud_enabled_changed)
        self.checkBox_Silence.toggled.connect(self._on_silence_enabled_changed)
        self.checkBox_SilenceWarn.toggled.connect(self._on_silence_warn_changed)
        self.checkBox_AudioMetersEnabled.toggled.connect(self._on_audio_meters_enabled_changed)
        self.comboBox_AudioSource.currentIndexChanged.connect(self._on_audio_source_changed)
        self.comboBox_TimeSource.currentIndexChanged.connect(self._on_time_source_changed)
        self.comboBox_LtcInput.currentIndexChanged.connect(self._on_time_source_changed)
        self.checkBox_NTPCheck.toggled.connect(self._on_time_source_changed)
        self.checkBox_PeakHold.toggled.connect(self._on_peak_hold_changed)
        self.comboBox_MeterLayout.currentIndexChanged.connect(self._on_meter_layout_changed)
        self.comboBox_LufsReferencePreset.currentIndexChanged.connect(self._on_lufs_reference_preset_changed)
        self.doubleSpinBox_LufsReference.valueChanged.connect(self._on_lufs_reference_value_changed)
        self.comboBox_TooLoudAction.currentIndexChanged.connect(self._on_tooloud_action_changed)

        self._connect_font_controls()

        self.AIR1IconSelectButton.clicked.connect(self.openAIR1IconPathSelector)
        self.AIR1IconResetButton.clicked.connect(self.resetAIR1Icon)
        self.AIR2IconSelectButton.clicked.connect(self.openAIR2IconPathSelector)
        self.AIR2IconResetButton.clicked.connect(self.resetAIR2Icon)
        self.AIR3IconSelectButton.clicked.connect(self.openAIR3IconPathSelector)
        self.AIR3IconResetButton.clicked.connect(self.resetAIR3Icon)
        self.AIR4IconSelectButton.clicked.connect(self.openAIR4IconPathSelector)
        self.AIR4IconResetButton.clicked.connect(self.resetAIR4Icon)

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

    def export_config_to_json(self, include_mqtt: bool = False) -> dict:
        """
        Export current QSettings configuration to a dictionary
        
        Args:
            include_mqtt: When True, include the MQTT group (web settings).
                Preset exports keep MQTT omitted on purpose.

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
            "General", "NTP", "TimeSource", "LEDS", "LED1", "LED2", "LED3", "LED4",
            "Clock", "Network", "OSC", "Formatting", "WeatherWidget", "Timers", "Fonts", "Audio"
        ]
        if include_mqtt:
            groups.append("MQTT")
        
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
                    # Unwrap Qt value objects if QSettings still returns them
                    if hasattr(value, "value") and not isinstance(value, (int, str, float, bool)):
                        try:
                            value = value.value()
                        except TypeError:
                            pass
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
            self.InstanceName.setText(
                normalize_instance_name(settings.value('instancename', DEFAULT_INSTANCE_NAME))
            )
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

        self._restore_time_source_settings(settings)

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
            stored_pin = settings.value('websettingspin', DEFAULT_WEB_SETTINGS_PIN, type=str) or ""
        self.websettingspin.blockSignals(True)
        self.websettingspin.clear()
        self.websettingspin.blockSignals(False)
        self._web_pin_edited = False
        if stored_pin:
            self.websettingspin.setPlaceholderText(
                "Leave empty to keep the current PIN. Enter - to remove it."
            )
        else:
            self.websettingspin.setPlaceholderText("Optional. Empty = no PIN.")

        with settings_group(settings, "MQTT"):
            self.enablemqtt.setChecked(settings.value('enablemqtt', False, type=bool))
            self.mqttserver.setText(settings.value('mqttserver', "localhost", type=str))
            self.mqttport.setText(str(settings.value('mqttport', 1883, type=int)))
            self.mqttuser.setText(settings.value('mqttuser', "", type=str))
            self.mqttpassword.setText(settings.value('mqttpassword', "", type=str))
            self.mqttdevicename.setText(settings.value('mqttdevicename', "OnAirScreen", type=str))
            # Enable/disable MQTT fields based on checkbox
            self.mqttserver.setEnabled(self.enablemqtt.isChecked())
            self.mqttport.setEnabled(self.enablemqtt.isChecked())
            self.mqttuser.setEnabled(self.enablemqtt.isChecked())
            self.mqttpassword.setEnabled(self.enablemqtt.isChecked())
            self.mqttdevicename.setEnabled(self.enablemqtt.isChecked())

        with settings_group(settings, "OSC"):
            self.enableosc.setChecked(settings.value('enableosc', DEFAULT_OSC_ENABLED, type=bool))
            self.oscport.setText(str(settings.value('oscport', str(DEFAULT_OSC_PORT))))
            self.oscsendhost.setText(settings.value('oscsendhost', DEFAULT_OSC_SEND_HOST, type=str) or "")
            self.oscsendport.setText(str(settings.value('oscsendport', str(DEFAULT_OSC_SEND_PORT))))
            osc_enabled = self.enableosc.isChecked()
            self.oscport.setEnabled(osc_enabled)
            self.oscsendhost.setEnabled(osc_enabled)
            self.oscsendport.setEnabled(osc_enabled)
            self.label_oscport.setEnabled(osc_enabled)
            self.label_oscsendhost.setEnabled(osc_enabled)
            self.label_oscsendport.setEnabled(osc_enabled)

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
            owm_enabled = settings.value('owmWidgetEnabled', DEFAULT_WEATHER_WIDGET_ENABLED, type=bool)
            self.owmAPIKey.setEnabled(owm_enabled)
            self.owmCityID.setEnabled(owm_enabled)
            self.owmCitySearch.setEnabled(owm_enabled)
            self.owmCityFind.setEnabled(owm_enabled)
            self.owmCityResults.setEnabled(owm_enabled)
            self.owmLanguage.setEnabled(owm_enabled)
            self.owmUnit.setEnabled(owm_enabled)
            self.owmTestAPI.setEnabled(owm_enabled)
            self.owmTestOutput.setEnabled(owm_enabled)

        with settings_group(settings, "Timers"):
            self.enableAIR1.setChecked(settings.value('TimerAIR1Enabled', True, type=bool))
            self.enableAIR2.setChecked(settings.value('TimerAIR2Enabled', True, type=bool))
            self.enableAIR3.setChecked(settings.value('TimerAIR3Enabled', True, type=bool))
            self.enableAIR4.setChecked(settings.value('TimerAIR4Enabled', True, type=bool))
            self.AIR1Text.setText(settings.value('TimerAIR1Text', DEFAULT_TIMER_AIR_TEXTS.get(1, 'Mic')))
            self.AIR2Text.setText(settings.value('TimerAIR2Text', DEFAULT_TIMER_AIR_TEXTS.get(2, 'Phone')))
            self.AIR3Text.setText(settings.value('TimerAIR3Text', DEFAULT_TIMER_AIR_TEXTS.get(3, 'Timer')))
            self.AIR4Text.setText(settings.value('TimerAIR4Text', DEFAULT_TIMER_AIR_TEXTS.get(4, 'Stream')))
            self.TOTHTimerText.setText(settings.value('TimerTOTHText', DEFAULT_TOTH_TIMER_TEXT))
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

        self._restore_audio_settings(settings)

        with settings_group(settings, "Fonts"):
            for prefix in FONT_ROW_PREFIXES:
                family = resolve_font_name(settings.value(f"{prefix}FontName", DEFAULT_FONT_NAME))
                size = settings.value(
                    f"{prefix}FontSize", default_font_size_for_prefix(prefix), type=int
                )
                weight = settings.value(
                    f"{prefix}FontWeight", DEFAULT_FONT_WEIGHT_BOLD, type=int
                )
                self._set_font_family_combo(prefix, family)
                getattr(self, f"FontSize_{prefix}").setValue(int(size))
                getattr(self, f"FontBold_{prefix}").setChecked(is_bold_font_weight(weight))
                self._apply_font_preview(prefix)

    def getSettingsFromDialog(self):
        if self.oacmode:
            settings = self.settings
        else:
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")

        with settings_group(settings, "General"):
            instance_name = normalize_instance_name(self.InstanceName.displayText())
            self.InstanceName.setText(instance_name)
            settings.setValue('instancename', instance_name)
            settings.setValue('stationname', self.StationName.displayText())
            settings.setValue('slogan', self.Slogan.displayText())
            settings.setValue('stationcolor', self.getStationNameColor().name())
            settings.setValue('slogancolor', self.getSloganColor().name())
            settings.setValue('updatecheck', self.checkBox_UpdateCheck.isChecked())
            settings.setValue('updatekey', self.updateKey.text())
            settings.setValue('updateincludebeta', self.checkBox_IncludeBetaVersions.isChecked())
            settings.setValue('replacenow', self.replaceNOW.isChecked())
            settings.setValue('replacenowtext', self.replaceNOWText.displayText())
            settings.setValue('loglevel', self.loglevelcombobox.currentText())

        with settings_group(settings, "NTP"):
            settings.setValue('ntpcheck', self.checkBox_NTPCheck.isChecked())
            settings.setValue('ntpcheckserver', self.NTPCheckServer.displayText())

        with settings_group(settings, "TimeSource"):
            source = self.comboBox_TimeSource.currentData()
            if source is None:
                source = DEFAULT_TIME_SOURCE
            settings.setValue('source', source)
            iface = self.comboBox_PtpIface.currentData()
            if iface is None:
                iface = ""
            settings.setValue('ptp_iface', iface)
            settings.setValue('ptp_domain', int(self.spinBox_PtpDomain.value()))
            port = self.comboBox_LtcPort.currentData()
            if port is None:
                port = ""
            settings.setValue('ltc_port', port)
            ltc_input = self.comboBox_LtcInput.currentData()
            if ltc_input is None:
                ltc_input = DEFAULT_LTC_INPUT
            settings.setValue('ltc_input', ltc_input)
            audio_device = self.comboBox_LtcAudioDevice.currentData()
            if audio_device is None:
                audio_device = ""
            settings.setValue('ltc_audio_device', audio_device)
            channel = self.comboBox_LtcChannel.currentData()
            if channel is None:
                channel = DEFAULT_LTC_AUDIO_CHANNEL
            settings.setValue('ltc_audio_channel', int(channel))
            settings.setValue('ltc_warn', self.checkBox_LtcWarn.isChecked())

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
            if getattr(self, "_web_pin_edited", False):
                from web_settings import PIN_CLEAR_TOKEN, hash_web_settings_pin

                pin_text = self.websettingspin.text()
                if pin_text in ("", PIN_CLEAR_TOKEN):
                    settings.setValue('websettingspin', "")
                else:
                    settings.setValue('websettingspin', hash_web_settings_pin(pin_text))

        with settings_group(settings, "MQTT"):
            settings.setValue('enablemqtt', self.enablemqtt.isChecked())
            settings.setValue('mqttserver', self.mqttserver.displayText())
            settings.setValue('mqttport', self.mqttport.displayText())
            settings.setValue('mqttuser', self.mqttuser.displayText())
            settings.setValue('mqttpassword', self.mqttpassword.text())
            settings.setValue('mqttdevicename', self.mqttdevicename.displayText())

        with settings_group(settings, "OSC"):
            settings.setValue('enableosc', self.enableosc.isChecked())
            settings.setValue('oscport', self.oscport.displayText())
            settings.setValue('oscsendhost', self.oscsendhost.displayText())
            settings.setValue('oscsendport', self.oscsendport.displayText())

        with settings_group(settings, "Formatting"):
            settings.setValue('dateFormat', self.dateFormat.displayText())
            settings.setValue('textClockLanguage', self.textClockLanguage.currentText())
            settings.setValue('isAmPm', self.time_am_pm.isChecked())

        with settings_group(settings, "WeatherWidget"):
            settings.setValue('owmWidgetEnabled', self.owmWidgetEnabled.isChecked())
            settings.setValue('owmAPIKey', self.owmAPIKey.text())
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
            settings.setValue('TimerTOTHText', self.TOTHTimerText.text())
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

        with settings_group(settings, "Audio"):
            settings.setValue('enabled', self.checkBox_AudioMetersEnabled.isChecked())
            source = self.comboBox_AudioSource.currentData()
            if source is None:
                source = DEFAULT_AUDIO_SOURCE
            settings.setValue('source', source)
            device_data = self.comboBox_AudioInput.currentData()
            if device_data is None:
                device_data = self.comboBox_AudioInput.currentText()
            settings.setValue('input_device', device_data if device_data is not None else "")
            settings.setValue('livewire_channel', int(self.spinBox_LivewireChannel.value()))
            iface = self.comboBox_LivewireIface.currentData()
            if iface is None:
                iface = ""
            settings.setValue('livewire_iface', iface)
            snapshot = self._current_aes67_snapshot()
            settings.setValue('aes67_id', snapshot.get("id") or "")
            settings.setValue('aes67_addr', snapshot.get("addr") or "")
            settings.setValue('aes67_port', int(snapshot.get("port") or DEFAULT_AUDIO_AES67_PORT))
            settings.setValue('aes67_name', snapshot.get("name") or "")
            settings.setValue('aes67_codec', snapshot.get("codec") or DEFAULT_AUDIO_AES67_CODEC)
            settings.setValue('aes67_rate', int(snapshot.get("rate") or DEFAULT_AUDIO_AES67_RATE))
            settings.setValue('aes67_channels', int(snapshot.get("channels") or DEFAULT_AUDIO_AES67_CHANNELS))
            settings.setValue('aes67_manual', bool(snapshot.get("manual")))
            unit_data = self.comboBox_AudioUnit.currentData()
            if unit_data is None:
                # Fallback from label
                label = self.comboBox_AudioUnit.currentText()
                unit_data = next((k for k, v in AUDIO_UNIT_LABELS.items() if v == label), DEFAULT_AUDIO_UNIT)
            settings.setValue('unit', unit_data)
            layout_data = self.comboBox_MeterLayout.currentData()
            if layout_data is None:
                layout_label = self.comboBox_MeterLayout.currentText()
                layout_data = next(
                    (k for k, v in AUDIO_LAYOUT_LABELS.items() if v == layout_label),
                    DEFAULT_AUDIO_LAYOUT,
                )
            settings.setValue('layout', layout_data)
            settings.setValue('tooloud', self.checkBox_TooLoud.isChecked())
            settings.setValue('tooloudtext', self.TooLoudText.displayText())
            settings.setValue('tooloud_threshold_dbtp', float(self.doubleSpinBox_TooLoudThreshold.value()))
            action = self.comboBox_TooLoudAction.currentData()
            if action is None:
                action = DEFAULT_AUDIO_TOOLOUD_ACTION
            settings.setValue('tooloud_action', action)
            led_data = self.comboBox_TooLoudLED.currentData()
            if led_data is None:
                led_data = self.comboBox_TooLoudLED.currentIndex() + 1
            settings.setValue('tooloud_led', int(led_data))
            settings.setValue('silence', self.checkBox_Silence.isChecked())
            settings.setValue('silence_warn', self.checkBox_SilenceWarn.isChecked())
            settings.setValue('silence_on_absent', self.checkBox_SilenceOnAbsent.isChecked())
            settings.setValue('silence_text', self.SilenceText.displayText())
            settings.setValue(
                'silence_threshold_dbfs', float(self.doubleSpinBox_SilenceThreshold.value())
            )
            settings.setValue(
                'silence_duration_s', float(self.doubleSpinBox_SilenceDuration.value())
            )
            settings.setValue(
                'silence_recovery_s', float(self.doubleSpinBox_SilenceRecovery.value())
            )
            settings.setValue('silence_http_url', self.SilenceHttpUrl.displayText().strip())
            preset = self.comboBox_LufsReferencePreset.currentData()
            if preset is None:
                preset = DEFAULT_AUDIO_LUFS_REFERENCE_PRESET
            settings.setValue('lufs_reference_preset', preset)
            settings.setValue('lufs_reference', float(self.doubleSpinBox_LufsReference.value()))
            settings.setValue('peak_hold', self.checkBox_PeakHold.isChecked())
            settings.setValue('peak_hold_seconds', float(self.doubleSpinBox_PeakHoldSeconds.value()))
            style = self.comboBox_DisplayStyle.currentData()
            if style is None:
                style = DEFAULT_AUDIO_DISPLAY_STYLE
            settings.setValue('display_style', style)
            settings.setValue('meter_width', int(self.spinBox_MeterWidth.value()))

        with settings_group(settings, "Fonts"):
            for prefix in FONT_ROW_PREFIXES:
                family = getattr(self, f"FontFamily_{prefix}").currentFont().family()
                size = getattr(self, f"FontSize_{prefix}").value()
                weight = font_weight_from_bold(getattr(self, f"FontBold_{prefix}").isChecked())
                settings.setValue(f"{prefix}FontName", family)
                settings.setValue(f"{prefix}FontSize", size)
                settings.setValue(f"{prefix}FontWeight", weight)

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
            update_key = self.updateKey.text()
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

    def searchOWMCity(self):
        """Search OpenWeatherMap geocoding for the typed city name."""
        query = self.owmCitySearch.displayText().strip()
        appid = self.owmAPIKey.text().strip()
        if not appid:
            self.owmTestOutput.setPlainText("Enter an OpenWeatherMap API key first.")
            return
        if not query:
            self.owmTestOutput.setPlainText("Enter a city name to search.")
            return

        url = QUrl("https://api.openweathermap.org/geo/1.0/direct")
        url_query = QUrlQuery()
        url_query.addQueryItem("q", query)
        url_query.addQueryItem("limit", "5")
        url_query.addQueryItem("appid", appid)
        url.setQuery(url_query)

        req = QtNetwork.QNetworkRequest(url)
        req.setAttribute(QtNetwork.QNetworkRequest.Attribute.User, {"kind": "geocode"})
        self.owm_search_nam.get(req)

    def _onOWMCityResultChanged(self, index: int) -> None:
        """Resolve the selected geocoding result to an OpenWeatherMap city ID."""
        data = self.owmCityResults.itemData(index)
        if not isinstance(data, dict):
            return
        city_id = data.get("id")
        if city_id:
            self.owmCityID.setText(str(city_id))
            return
        lat = data.get("lat")
        lon = data.get("lon")
        if lat is None or lon is None:
            return
        appid = self.owmAPIKey.text().strip()
        if not appid:
            self.owmTestOutput.setPlainText("Enter an OpenWeatherMap API key first.")
            return

        url = QUrl("https://api.openweathermap.org/data/2.5/weather")
        url_query = QUrlQuery()
        url_query.addQueryItem("lat", str(lat))
        url_query.addQueryItem("lon", str(lon))
        url_query.addQueryItem("appid", appid)
        url.setQuery(url_query)

        req = QtNetwork.QNetworkRequest(url)
        req.setAttribute(
            QtNetwork.QNetworkRequest.Attribute.User,
            {"kind": "cityid", "index": index},
        )
        self.owm_search_nam.get(req)

    def _handleOWMCitySearchResponse(self, reply) -> None:
        """Handle geocoding and city-ID lookup replies for the settings search."""
        meta = reply.request().attribute(QtNetwork.QNetworkRequest.Attribute.User)
        kind = meta.get("kind") if isinstance(meta, dict) else None
        if kind is None:
            path = reply.url().path()
            if "geo/1.0/direct" in path:
                kind = "geocode"
            elif "data/2.5/weather" in path:
                kind = "cityid"
        er = reply.error()
        if er != QtNetwork.QNetworkReply.NetworkError.NoError:
            error_string = f"Error occurred: {er}, {reply.errorString()}"
            logger.error(f"OWM city search network error: {error_string}")
            self.owmTestOutput.setPlainText(error_string)
            return

        bytes_string = reply.readAll()
        payload = str(bytes_string, "utf-8")
        if kind == "geocode":
            self._applyOWMGeocodeResults(payload)
        elif kind == "cityid":
            index = meta.get("index") if isinstance(meta, dict) else None
            self._applyOWMCityIdResult(payload, index)

    def _applyOWMGeocodeResults(self, payload: str) -> None:
        """Fill the city results combo from a geocoding JSON payload."""
        results = parse_owm_geocode_results(payload)
        self.owmCityResults.blockSignals(True)
        self.owmCityResults.clear()
        if not results:
            self.owmCityResults.addItem("No cities found", None)
            self.owmCityResults.blockSignals(False)
            self.owmTestOutput.setPlainText("No cities found.")
            return
        for label, coords in results:
            self.owmCityResults.addItem(label, coords)
        self.owmCityResults.setCurrentIndex(0)
        self.owmCityResults.blockSignals(False)
        self._onOWMCityResultChanged(0)

    def _applyOWMCityIdResult(self, payload: str, index) -> None:
        """Write the resolved city ID into the City ID field."""
        city_id = extract_owm_city_id(payload)
        if not city_id:
            self.owmTestOutput.setPlainText("Could not resolve city ID for the selected location.")
            return
        if isinstance(index, int) and 0 <= index < self.owmCityResults.count():
            data = self.owmCityResults.itemData(index)
            if isinstance(data, dict):
                data = dict(data)
                data["id"] = city_id
                self.owmCityResults.setItemData(index, data)
        self.owmCityID.setText(city_id)

    def makeOWMTestCall(self):
        appid = self.owmAPIKey.text()
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
        oldcolor = QColor(self._station_name_color)
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        self._station_name_color = QColor(newcolor)

    def setSloganColor(self, newcolor=False):
        oldcolor = QColor(self._slogan_color)
        if not newcolor:
            newcolor = self.openColorDialog(oldcolor)
        self._slogan_color = QColor(newcolor)

    def getStationNameColor(self):
        return QColor(self._station_name_color)

    def getSloganColor(self):
        return QColor(self._slogan_color)

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
        color = QColor.fromString(normalized_color)
        
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

    def _connect_font_controls(self) -> None:
        """Connect Fonts-tab combo, size, bold, and reset widgets."""
        for prefix in FONT_ROW_PREFIXES:
            getattr(self, f"FontFamily_{prefix}").currentFontChanged.connect(
                lambda _font, p=prefix: self._apply_font_preview(p)
            )
            getattr(self, f"FontSize_{prefix}").valueChanged.connect(
                lambda _value, p=prefix: self._apply_font_preview(p)
            )
            getattr(self, f"FontBold_{prefix}").toggled.connect(
                lambda _checked, p=prefix: self._apply_font_preview(p)
            )
            getattr(self, f"ResetFont_{prefix}").clicked.connect(
                lambda _checked=False, p=prefix: self._reset_font_row(p)
            )

    def _set_font_family_combo(self, prefix: str, family: str) -> None:
        """Select a family in the row combo, adding it if Qt does not list it yet."""
        combo = getattr(self, f"FontFamily_{prefix}")
        if combo.findText(family) < 0:
            combo.addItem(family)
        combo.setCurrentFont(QFont(family))

    def _apply_font_preview(self, prefix: str) -> None:
        """Apply the current family, size, and bold to the preview label."""
        family = getattr(self, f"FontFamily_{prefix}").currentFont().family()
        size = getattr(self, f"FontSize_{prefix}").value()
        bold = getattr(self, f"FontBold_{prefix}").isChecked()
        preview = getattr(self, f"ExampleFont_{prefix}")
        preview.setFont(QFont(family, size, qfont_weight_from_stored(font_weight_from_bold(bold))))

    def _reset_font_row(self, prefix: str) -> None:
        """Reset one Fonts-tab row to Roboto, default size, and bold."""
        self._set_font_family_combo(prefix, DEFAULT_FONT_NAME)
        getattr(self, f"FontSize_{prefix}").setValue(default_font_size_for_prefix(prefix))
        getattr(self, f"FontBold_{prefix}").setChecked(True)
        self._apply_font_preview(prefix)

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
        self.InstanceName.setToolTip(
            "Location of this OnAirScreen, e.g. Studio-1 or Studio-1-Outside. "
            "1-32 characters: letters, digits, and hyphens; must start and end with a letter or digit."
        )
        self.StationName.setToolTip("Enter the name of your radio station")
        self.Slogan.setToolTip("Enter your station's slogan or tagline")
        self.StationNameColor.setToolTip("Click to select the color for the station name")
        self.SloganColor.setToolTip("Click to select the color for the slogan")
        self.checkBox_UpdateCheck.setToolTip("Enable automatic update checking on startup")
        self.updateKey.setToolTip(
            "Enter your update key for automatic updates (if applicable). "
            "Masked; use the slashed-eye icon to show it."
        )
        self.checkBox_IncludeBetaVersions.setToolTip("Include beta versions when checking for updates")
        self.updateCheckNowButton.setToolTip("Manually check for updates now")
        self.replaceNOW.setToolTip("Replace the 'NOW' text with custom text after 10 seconds")
        self.replaceNOWText.setToolTip("Custom text to display after IP addresses are shown")
        
        # NTP / Time Source settings
        self.checkBox_NTPCheck.setToolTip(
            "Warn if the display clock diverges from the NTP server (also used when Local or PTP is selected)"
        )
        self.NTPCheckServer.setToolTip(
            "NTP server for the time source 'NTP Server' and for the NTP check. "
            "pool.ntp.org can be unreliable; a local studio NTP server is recommended."
        )
        self.comboBox_TimeSource.setToolTip(
            "Clock time source. Local uses the system clock. NTP and PTP steer an independent clock "
            "and do not change the operating-system time. LTC follows a serial LBE-1110 reader or "
            "SMPTE LTC decoded from a local audio input."
        )
        self.comboBox_PtpIface.setToolTip(
            "Network interface for PTPv2 multicast (independent of the AoIP interface)"
        )
        self.spinBox_PtpDomain.setToolTip("IEEE 1588 PTP domain number (0–255, default 0)")
        self.comboBox_LtcPort.setToolTip(
            "USB serial port of the LBE-1110 LTC reader. Auto picks a Leo Bodnar / CDC device."
        )
        self.comboBox_LtcInput.setToolTip(
            "LTC input: Leo Bodnar LBE-1110 USB serial, or SMPTE LTC decoded from a local audio device"
        )
        self.comboBox_LtcAudioDevice.setToolTip(
            "Local PortAudio capture device for LTC (independent of Audio Meters). "
            "Using the same device for both may fail on some hosts."
        )
        self.comboBox_LtcChannel.setToolTip("Audio channel that carries LTC (Left or Right)")
        self.checkBox_LtcWarn.setToolTip(
            "Show a WARN message when LTC drops (waiting for lock, not connected, or not synchronized). "
            "Off by default so scrubbing or editing does not flood WARN. "
            "The LTC NOT LOCKED LED always stays active."
        )
        
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
        self.websettingspin.setToolTip(
            "Optional PIN that protects the Web UI settings overlay. "
            "Leave empty to keep the current PIN. Enter a minus sign (-) to remove PIN protection. "
            "Remote Control stays unprotected."
        )
        
        # MQTT settings
        self.enablemqtt.setToolTip("Enable MQTT integration with Home Assistant Autodiscovery")
        self.mqttserver.setToolTip("MQTT broker hostname or IP address")
        self.mqttport.setToolTip("MQTT broker port (default: 1883)")
        self.mqttuser.setToolTip("MQTT username (optional)")
        self.mqttpassword.setToolTip(
            "MQTT password (optional). Masked; use the slashed-eye icon to show it."
        )
        self.mqttdevicename.setToolTip("MQTT device name (default: OnAirScreen)")

        # OSC settings
        self.enableosc.setToolTip(
            "Enable OSC remote control (listen port plus optional status push to Companion)"
        )
        self.oscport.setToolTip("UDP port for receiving OSC commands (default: 8000)")
        self.oscsendhost.setToolTip(
            "Destination host for OSC status push (Companion IP). Leave empty for receive/query only"
        )
        self.oscsendport.setToolTip(
            "Destination UDP port for OSC status push (Companion feedback port, default: 9000)"
        )
        
        # Formatting settings
        self.dateFormat.setToolTip("Date format string (e.g., 'dddd, dd. MMMM yyyy' for 'Monday, 01. January 2024')")
        self.textClockLanguage.setToolTip("Language for text-based clock display")
        self.time_am_pm.setToolTip("Use 12-hour format with AM/PM")
        self.time_24h.setToolTip("Use 24-hour format")
        
        # Weather Widget settings
        self.owmWidgetEnabled.setToolTip("Enable the weather widget display")
        self.owmAPIKey.setToolTip(
            "OpenWeatherMap API key (get one at openweathermap.org). "
            "Masked; use the slashed-eye icon to show it."
        )
        self.owmCityID.setToolTip("OpenWeatherMap City ID; use Find to look it up by city name")
        self.owmCitySearch.setToolTip("Type a city name and press Find or Return to search OpenWeatherMap")
        self.owmCityFind.setToolTip("Search OpenWeatherMap for matching cities")
        self.owmCityResults.setToolTip("Select a search result to fill the City ID")
        self.owmLanguage.setToolTip("Language for weather descriptions")
        self.owmUnit.setToolTip("Temperature unit (Celsius, Fahrenheit, or Kelvin)")
        self.owmTestAPI.setToolTip("Test the OpenWeatherMap API connection with current settings")

        # Audio meter settings
        self.checkBox_AudioMetersEnabled.setToolTip("Show stereo audio meters on the left side of the main screen")
        self.comboBox_AudioSource.setToolTip(
            "Meter audio source: local PortAudio input, Axia Livewire, or AES67 (SAP)"
        )
        self.comboBox_AudioInput.setToolTip("Select the live audio input device used for metering")
        self.pushButton_AudioRefresh.setToolTip(
            "Re-scan the system for audio input devices (newly plugged or unplugged hardware)"
        )
        self.spinBox_LivewireChannel.setToolTip(
            "Livewire channel number (1–32767). Multicast = 239.192.0.0 + channel"
        )
        self.comboBox_LivewireStream.setToolTip(
            "Announced Livewire sources (live while Settings are open). "
            "Pick a source or type a channel number below"
        )
        self.label_LivewireStream.setToolTip(
            "Announced Livewire sources on the selected AoIP interface"
        )
        self.comboBox_LivewireIface.setToolTip(
            "Network interface for Livewire/AES67 IGMP join (Default uses the system route)"
        )
        self.label_LivewireIface.setToolTip(
            "Network interface for Livewire/AES67 IGMP join (Default uses the system route)"
        )
        self.comboBox_Aes67Stream.setToolTip(
            "AES67 stream: None, live SAP on 239.255.255.255 and 224.2.127.254 (updates when streams change), or pasted SDP"
        )
        self.pushButton_Aes67PasteSdp.setToolTip(
            "Paste an SDP announcement if the device does not advertise via SAP"
        )
        self.comboBox_AudioUnit.setToolTip(
            "L/R display unit: dBFS, dBTP, or BBC PPM (PPM is only available in the L/R layout)"
        )
        self.comboBox_MeterLayout.setToolTip(
            "Show stereo L/R bars, a programme LUFS bar, or both"
        )
        self.comboBox_DisplayStyle.setToolTip("Meter fill style: solid continuous or bargraph (1px segments)")
        self.spinBox_MeterWidth.setToolTip("Overall meter width in pixels; wider values make both L/R bars thicker")
        self.label_MeterWidth.setToolTip("Overall meter width in pixels; wider values make both L/R bars thicker")
        self.checkBox_TooLoud.setToolTip("Show a warning when true peak exceeds the configured dBTP threshold")
        self.TooLoudText.setToolTip("Warning message shown when TooLoud is triggered")
        self.doubleSpinBox_TooLoudThreshold.setToolTip("True-peak threshold in dBTP (typical broadcast headroom: -1.0)")
        self.comboBox_LufsReferencePreset.setToolTip("Loudness target preset (EBU R128, ATSC A/85, AES, or Custom)")
        self.doubleSpinBox_LufsReference.setToolTip("LUFS/LKFS reference target shown as a peg on the meter")
        self.label_LufsReference.setToolTip("Loudness reference target for the LUFS meter scale")
        self.checkBox_PeakHold.setToolTip("Show a white peak marker that holds the highest meter reading")
        self.doubleSpinBox_PeakHoldSeconds.setToolTip("How long the peak marker holds before falling back to the current level")
        self.label_PeakHoldSeconds.setToolTip("Peak hold duration in seconds")
        self.comboBox_TooLoudAction.setToolTip("TooLoud action: show warning text or trigger an LED")
        self.comboBox_TooLoudLED.setToolTip("Which LED (1-4) to activate when TooLoud triggers in LED mode")

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
        self.TOTHTimerText.setToolTip(
            "Label shown on AIR3 while the top-of-hour countdown is active"
        )
        self.label_TOTHTimerText.setToolTip(
            "Label shown on AIR3 while the top-of-hour countdown is active"
        )

        # Font settings
        for prefix in FONT_ROW_PREFIXES:
            getattr(self, f"FontFamily_{prefix}").setToolTip(f"Font family for {prefix}")
            getattr(self, f"FontSize_{prefix}").setToolTip(f"Font size for {prefix} in points")
            getattr(self, f"FontBold_{prefix}").setToolTip(f"Use bold weight for {prefix}")
            getattr(self, f"ResetFont_{prefix}").setToolTip(
                f"Reset {prefix} to {DEFAULT_FONT_NAME}, default size, bold"
            )

        # Action buttons
        self.ApplyButton.setToolTip("Apply all settings and close the dialog")
        self.CloseButton.setToolTip("Close the settings dialog without applying changes")
        self.ExitButton.setToolTip("Exit OnAirScreen application")
        self.ResetSettingsButton.setToolTip("Reset all settings to default values (this cannot be undone)")
        self.openLogFolderButton.setToolTip(
            "Open the folder with onairscreen.log and crash reports"
        )
        self.logfolderLabel.setToolTip(
            "Application log and crash reports. Send this folder to support if asked."
        )

        # Preset management tooltips
        self.SaveSettingsButton.setToolTip("Save current configuration as a preset")
        self.LoadSettingsButton.setToolTip("Load a saved preset configuration")
        self.DeleteSettingsButton.setToolTip("Delete a saved preset")
        
    def _on_web_settings_pin_edited(self, _text: str) -> None:
        """Remember that the user changed the Web Settings PIN field."""
        self._web_pin_edited = True

    def _on_mqtt_enabled_changed(self, enabled: bool) -> None:
        """Handle MQTT enabled checkbox state change"""
        self.mqttserver.setEnabled(enabled)
        self.mqttport.setEnabled(enabled)
        self.mqttuser.setEnabled(enabled)
        self.mqttpassword.setEnabled(enabled)
        self.mqttdevicename.setEnabled(enabled)

    def _on_osc_enabled_changed(self, enabled: bool) -> None:
        """Handle OSC enabled checkbox state change"""
        self.oscport.setEnabled(enabled)
        self.oscsendhost.setEnabled(enabled)
        self.oscsendport.setEnabled(enabled)
        self.label_oscport.setEnabled(enabled)
        self.label_oscsendhost.setEnabled(enabled)
        self.label_oscsendport.setEnabled(enabled)

    def _on_audio_meters_enabled_changed(self, enabled: bool) -> None:
        """Enable/disable meter-related controls."""
        self.comboBox_AudioSource.setEnabled(enabled)
        self.label_AudioSource.setEnabled(enabled)
        self.comboBox_MeterLayout.setEnabled(enabled)
        self.label_MeterLayout.setEnabled(enabled)
        self.comboBox_DisplayStyle.setEnabled(enabled)
        self.label_DisplayStyle.setEnabled(enabled)
        self.spinBox_MeterWidth.setEnabled(enabled)
        self.label_MeterWidth.setEnabled(enabled)
        self._update_meter_layout_controls(enabled)
        self._update_audio_source_controls(enabled)

    def _on_meter_layout_changed(self, _index: int = 0) -> None:
        """Refresh unit / LUFS / peak-hold enablement when layout changes."""
        enabled = self.checkBox_AudioMetersEnabled.isChecked()
        self._update_meter_layout_controls(enabled)

    def _current_meter_layout(self) -> str:
        layout = self.comboBox_MeterLayout.currentData()
        if layout is None:
            return DEFAULT_AUDIO_LAYOUT
        return normalize_meter_layout(str(layout))

    def _update_meter_layout_controls(self, meters_enabled: bool) -> None:
        """Enable Display Unit, LUFS reference, and Peak Hold based on layout."""
        layout = self._current_meter_layout()
        show_lr = layout in ("lr", "both")
        show_lufs = layout in ("lufs", "both")
        self.comboBox_AudioUnit.setEnabled(meters_enabled and show_lr)
        self.label_AudioUnit.setEnabled(meters_enabled and show_lr)
        self.comboBox_LufsReferencePreset.setEnabled(meters_enabled and show_lufs)
        self.doubleSpinBox_LufsReference.setEnabled(meters_enabled and show_lufs)
        self.label_LufsReference.setEnabled(meters_enabled and show_lufs)
        self.checkBox_PeakHold.setEnabled(meters_enabled and show_lr)
        self._on_peak_hold_changed(self.checkBox_PeakHold.isChecked() and meters_enabled and show_lr)

        unit = self.comboBox_AudioUnit.currentData()
        if layout == "both" and unit == "bbc_ppm":
            index = self.comboBox_AudioUnit.findData(DEFAULT_AUDIO_UNIT)
            if index >= 0:
                self.comboBox_AudioUnit.setCurrentIndex(index)

        for i in range(self.comboBox_AudioUnit.count()):
            key = self.comboBox_AudioUnit.itemData(i)
            model = self.comboBox_AudioUnit.model()
            index = model.index(i, 0)
            if not index.isValid():
                continue
            enabled_flag = not (layout == "both" and key == "bbc_ppm")
            item = getattr(model, "item", lambda _i: None)(i)
            if item is not None:
                item.setEnabled(enabled_flag)

    def _on_audio_source_changed(self, _index: int = 0) -> None:
        """Show local / Livewire / AES67 controls based on selected source."""
        enabled = self.checkBox_AudioMetersEnabled.isChecked()
        self._update_audio_source_controls(enabled)

    def _update_audio_source_controls(self, meters_enabled: bool) -> None:
        """Enable local device, Livewire, or AES67 fields depending on source."""
        source = self.comboBox_AudioSource.currentData()
        if source is None:
            source = DEFAULT_AUDIO_SOURCE
        use_livewire = source == "livewire"
        use_aes67 = source == "aes67"
        use_aoip = use_livewire or use_aes67
        self.comboBox_AudioInput.setEnabled(meters_enabled and not use_aoip)
        self.pushButton_AudioRefresh.setEnabled(meters_enabled and not use_aoip)
        self.label_AudioInput.setEnabled(meters_enabled and not use_aoip)
        self.spinBox_LivewireChannel.setEnabled(meters_enabled and use_livewire)
        self.label_LivewireChannel.setEnabled(meters_enabled and use_livewire)
        self.comboBox_LivewireStream.setEnabled(meters_enabled and use_livewire)
        self.label_LivewireStream.setEnabled(meters_enabled and use_livewire)
        self.comboBox_LivewireIface.blockSignals(True)
        self.comboBox_LivewireIface.setEnabled(meters_enabled and use_aoip)
        self.comboBox_LivewireIface.blockSignals(False)
        self.label_LivewireIface.setEnabled(meters_enabled and use_aoip)
        self.comboBox_Aes67Stream.setEnabled(meters_enabled and use_aes67)
        self.label_Aes67Stream.setEnabled(meters_enabled and use_aes67)
        self.pushButton_Aes67PasteSdp.setEnabled(meters_enabled and use_aes67)
        self._sync_sap_discovery()
        self._sync_livewire_discovery()

    def _on_peak_hold_changed(self, _checked: bool = True) -> None:
        """Enable duration spin box only when peak hold and meters are on."""
        use_hold = self.checkBox_AudioMetersEnabled.isChecked() and self.checkBox_PeakHold.isChecked()
        self.doubleSpinBox_PeakHoldSeconds.setEnabled(use_hold)
        self.label_PeakHoldSeconds.setEnabled(use_hold)

    def _on_tooloud_enabled_changed(self, enabled: bool) -> None:
        """Enable/disable TooLoud-related controls."""
        self.TooLoudText.setEnabled(enabled)
        self.label_TooLoudText.setEnabled(enabled)
        self.doubleSpinBox_TooLoudThreshold.setEnabled(enabled)
        self.label_TooLoudThreshold.setEnabled(enabled)
        self.comboBox_TooLoudAction.setEnabled(enabled)
        self.label_TooLoudAction.setEnabled(enabled)
        self._on_tooloud_action_changed()

    def _populate_tooloud_action_controls(self) -> None:
        """Fill TooLoud action and LED combos."""
        self.comboBox_TooLoudAction.blockSignals(True)
        self.comboBox_TooLoudAction.clear()
        for key, label in AUDIO_TOOLOUD_ACTION_LABELS.items():
            self.comboBox_TooLoudAction.addItem(label, key)
        self.comboBox_TooLoudAction.blockSignals(False)

        self.comboBox_TooLoudLED.blockSignals(True)
        self.comboBox_TooLoudLED.clear()
        for led_num in range(1, 5):
            self.comboBox_TooLoudLED.addItem(f"LED {led_num}", led_num)
        self.comboBox_TooLoudLED.blockSignals(False)

    def _on_tooloud_action_changed(self, _index: int = 0) -> None:
        """Enable LED selector only when action is LED and TooLoud is enabled."""
        enabled = self.checkBox_TooLoud.isChecked()
        action = self.comboBox_TooLoudAction.currentData()
        use_led = enabled and action == "led"
        self.comboBox_TooLoudLED.setEnabled(use_led)
        self.label_TooLoudLED.setEnabled(use_led)
        # Message field only relevant for warning action
        show_message = enabled and action != "led"
        self.TooLoudText.setEnabled(show_message)
        self.label_TooLoudText.setEnabled(show_message)

    def _on_silence_enabled_changed(self, enabled: bool) -> None:
        """Enable/disable Silence Detection related controls."""
        self.checkBox_SilenceWarn.setEnabled(enabled)
        self.checkBox_SilenceOnAbsent.setEnabled(enabled)
        self.doubleSpinBox_SilenceThreshold.setEnabled(enabled)
        self.label_SilenceThreshold.setEnabled(enabled)
        self.doubleSpinBox_SilenceDuration.setEnabled(enabled)
        self.label_SilenceDuration.setEnabled(enabled)
        self.doubleSpinBox_SilenceRecovery.setEnabled(enabled)
        self.label_SilenceRecovery.setEnabled(enabled)
        self.SilenceHttpUrl.setEnabled(enabled)
        self.label_SilenceHttpUrl.setEnabled(enabled)
        self._on_silence_warn_changed()

    def _on_silence_warn_changed(self, _checked: bool = True) -> None:
        """Enable the WARN message field only when Silence Detection and WARN are on."""
        show_message = self.checkBox_Silence.isChecked() and self.checkBox_SilenceWarn.isChecked()
        self.SilenceText.setEnabled(show_message)
        self.label_SilenceText.setEnabled(show_message)

    def _populate_lufs_reference_presets(self) -> None:
        """Fill LUFS reference preset combo once."""
        self.comboBox_LufsReferencePreset.blockSignals(True)
        self.comboBox_LufsReferencePreset.clear()
        for key, meta in AUDIO_LUFS_REFERENCE_PRESETS.items():
            self.comboBox_LufsReferencePreset.addItem(meta["label"], key)
        self.comboBox_LufsReferencePreset.blockSignals(False)

    def _on_lufs_reference_preset_changed(self, _index: int = 0) -> None:
        """Apply preset value to the spin box; enable spin box only for Custom."""
        preset = self.comboBox_LufsReferencePreset.currentData()
        meta = AUDIO_LUFS_REFERENCE_PRESETS.get(preset or "", {})
        is_custom = preset == "custom" or meta.get("value") is None
        self.doubleSpinBox_LufsReference.setEnabled(is_custom)
        if not is_custom and meta.get("value") is not None:
            self.doubleSpinBox_LufsReference.blockSignals(True)
            self.doubleSpinBox_LufsReference.setValue(float(meta["value"]))
            self.doubleSpinBox_LufsReference.blockSignals(False)

    def _on_lufs_reference_value_changed(self, value: float) -> None:
        """Switch preset to Custom when the user edits the value freely."""
        preset = self.comboBox_LufsReferencePreset.currentData()
        meta = AUDIO_LUFS_REFERENCE_PRESETS.get(preset or "", {})
        expected = meta.get("value")
        if expected is not None and abs(float(value) - float(expected)) > 0.05:
            custom_index = self.comboBox_LufsReferencePreset.findData("custom")
            if custom_index >= 0:
                self.comboBox_LufsReferencePreset.blockSignals(True)
                self.comboBox_LufsReferencePreset.setCurrentIndex(custom_index)
                self.comboBox_LufsReferencePreset.blockSignals(False)
                self.doubleSpinBox_LufsReference.setEnabled(True)

    def refresh_audio_input_devices(
        self, selected_name: str | None = None, *, rescan: bool = False
    ) -> None:
        """Populate the audio input device combo box.

        Args:
            selected_name: Device name to keep selected. QPushButton.clicked
                may pass a bool; that is ignored so the current choice stays.
            rescan: If True, reinitialize PortAudio so hot-plugged or
                unplugged devices appear in (or leave) the list.
        """
        from audio_capture import list_input_devices

        if not isinstance(selected_name, str):
            selected_name = None
        if selected_name is None:
            selected_name = self.comboBox_AudioInput.currentData()
            if selected_name is None:
                selected_name = ""

        self.comboBox_AudioInput.blockSignals(True)
        self.comboBox_AudioInput.clear()
        self.comboBox_AudioInput.addItem("System Default", "")
        devices = list_input_devices(refresh=rescan)
        for device in devices:
            self.comboBox_AudioInput.addItem(str(device), device.name)

        index = self.comboBox_AudioInput.findData(selected_name or "")
        if index < 0 and selected_name:
            # Keep previously configured device even if currently missing
            self.comboBox_AudioInput.addItem(f"{selected_name} (unavailable)", selected_name)
            index = self.comboBox_AudioInput.findData(selected_name)
        self.comboBox_AudioInput.setCurrentIndex(max(0, index))
        self.comboBox_AudioInput.blockSignals(False)
        if rescan:
            self.refresh_ltc_audio_devices()

    def _on_time_source_changed(self, _value=None) -> None:
        """Enable PTP, LTC, and NTP fields based on the selected time source."""
        self._update_time_source_ui()

    def _update_time_source_ui(self) -> None:
        """Enable NTP server, PTP, and LTC controls depending on source and NTP-check."""
        source = self.comboBox_TimeSource.currentData()
        if source is None:
            source = DEFAULT_TIME_SOURCE
        ntp_check = self.checkBox_NTPCheck.isChecked()
        ntp_server_enabled = ntp_check or source == TIME_SOURCE_NTP
        self.NTPCheckServer.setEnabled(ntp_server_enabled)
        self.label_16.setEnabled(ntp_server_enabled)
        use_ptp = source == TIME_SOURCE_PTP
        self.comboBox_PtpIface.setEnabled(use_ptp)
        self.label_PtpIface.setEnabled(use_ptp)
        self.spinBox_PtpDomain.setEnabled(use_ptp)
        self.label_PtpDomain.setEnabled(use_ptp)
        use_ltc = source == TIME_SOURCE_LTC
        ltc_input = self.comboBox_LtcInput.currentData()
        if ltc_input is None:
            ltc_input = DEFAULT_LTC_INPUT
        use_serial = use_ltc and ltc_input == LTC_INPUT_SERIAL
        use_audio = use_ltc and ltc_input == LTC_INPUT_AUDIO
        self.comboBox_LtcInput.setEnabled(use_ltc)
        self.label_LtcInput.setEnabled(use_ltc)
        self.comboBox_LtcPort.setEnabled(use_serial)
        self.label_LtcPort.setEnabled(use_serial)
        self.comboBox_LtcAudioDevice.setEnabled(use_audio)
        self.label_LtcAudioDevice.setEnabled(use_audio)
        self.comboBox_LtcChannel.setEnabled(use_audio)
        self.label_LtcChannel.setEnabled(use_audio)
        self.checkBox_LtcWarn.setEnabled(use_ltc)

    def _restore_time_source_settings(self, settings: QSettings) -> None:
        """Restore TimeSource group widgets from configuration."""
        with settings_group(settings, "TimeSource"):
            source = settings.value('source', DEFAULT_TIME_SOURCE, type=str) or DEFAULT_TIME_SOURCE
            ptp_iface = settings.value('ptp_iface', DEFAULT_PTP_IFACE, type=str) or ""
            try:
                ptp_domain = int(settings.value('ptp_domain', DEFAULT_PTP_DOMAIN, type=int))
            except (TypeError, ValueError):
                ptp_domain = DEFAULT_PTP_DOMAIN
            ltc_port = settings.value('ltc_port', DEFAULT_LTC_PORT, type=str) or ""
            ltc_input = settings.value('ltc_input', DEFAULT_LTC_INPUT, type=str) or DEFAULT_LTC_INPUT
            if ltc_input not in LTC_INPUT_LABELS:
                ltc_input = DEFAULT_LTC_INPUT
            ltc_audio_device = (
                settings.value('ltc_audio_device', DEFAULT_LTC_AUDIO_DEVICE, type=str) or ""
            )
            try:
                ltc_audio_channel = int(
                    settings.value('ltc_audio_channel', DEFAULT_LTC_AUDIO_CHANNEL, type=int)
                )
            except (TypeError, ValueError):
                ltc_audio_channel = DEFAULT_LTC_AUDIO_CHANNEL
            ltc_audio_channel = 0 if ltc_audio_channel <= 0 else 1
            ltc_warn = settings.value('ltc_warn', DEFAULT_LTC_WARN, type=bool)

        self.comboBox_TimeSource.blockSignals(True)
        self.comboBox_TimeSource.clear()
        for key, label in TIME_SOURCE_LABELS.items():
            self.comboBox_TimeSource.addItem(label, key)
        source_index = self.comboBox_TimeSource.findData(source)
        if source_index < 0:
            source_index = self.comboBox_TimeSource.findData(DEFAULT_TIME_SOURCE)
        self.comboBox_TimeSource.setCurrentIndex(max(0, source_index))
        self.comboBox_TimeSource.blockSignals(False)

        self.refresh_ptp_interfaces(ptp_iface)
        self.spinBox_PtpDomain.blockSignals(True)
        self.spinBox_PtpDomain.setValue(max(0, min(255, ptp_domain)))
        self.spinBox_PtpDomain.blockSignals(False)
        self.refresh_ltc_ports(ltc_port)
        self.comboBox_LtcInput.blockSignals(True)
        self.comboBox_LtcInput.clear()
        for key, label in LTC_INPUT_LABELS.items():
            self.comboBox_LtcInput.addItem(label, key)
        input_index = self.comboBox_LtcInput.findData(ltc_input)
        if input_index < 0:
            input_index = self.comboBox_LtcInput.findData(DEFAULT_LTC_INPUT)
        self.comboBox_LtcInput.setCurrentIndex(max(0, input_index))
        self.comboBox_LtcInput.blockSignals(False)
        self.refresh_ltc_audio_devices(ltc_audio_device)
        self.comboBox_LtcChannel.blockSignals(True)
        self.comboBox_LtcChannel.clear()
        self.comboBox_LtcChannel.addItem("Left", 0)
        self.comboBox_LtcChannel.addItem("Right", 1)
        channel_index = self.comboBox_LtcChannel.findData(ltc_audio_channel)
        self.comboBox_LtcChannel.setCurrentIndex(max(0, channel_index))
        self.comboBox_LtcChannel.blockSignals(False)
        self.checkBox_LtcWarn.setChecked(bool(ltc_warn))
        self._update_time_source_ui()

    def refresh_ptp_interfaces(self, selected_iface: str | None = None) -> None:
        """Populate the PTP network interface combo box (independent of AoIP)."""
        from livewire_capture import list_ipv4_interfaces

        if selected_iface is None:
            selected_iface = self.comboBox_PtpIface.currentData()
            if selected_iface is None:
                selected_iface = ""

        self.comboBox_PtpIface.blockSignals(True)
        self.comboBox_PtpIface.clear()
        self.comboBox_PtpIface.addItem("Default", "")
        for label, ip_str in list_ipv4_interfaces():
            self.comboBox_PtpIface.addItem(label, ip_str)

        index = self.comboBox_PtpIface.findData(selected_iface or "")
        if index < 0 and selected_iface:
            self.comboBox_PtpIface.addItem(f"{selected_iface} (unavailable)", selected_iface)
            index = self.comboBox_PtpIface.findData(selected_iface)
        self.comboBox_PtpIface.setCurrentIndex(max(0, index))
        self.comboBox_PtpIface.blockSignals(False)

    def refresh_ltc_ports(self, selected_port: str | None = None) -> None:
        """Populate the LTC USB serial-port combo box."""
        from ltc_reader import list_serial_ports

        if selected_port is None:
            selected_port = self.comboBox_LtcPort.currentData()
            if selected_port is None:
                selected_port = ""

        self.comboBox_LtcPort.blockSignals(True)
        self.comboBox_LtcPort.clear()
        self.comboBox_LtcPort.addItem("Auto", "")
        for label, device in list_serial_ports():
            self.comboBox_LtcPort.addItem(label, device)

        index = self.comboBox_LtcPort.findData(selected_port or "")
        if index < 0 and selected_port:
            self.comboBox_LtcPort.addItem(f"{selected_port} (unavailable)", selected_port)
            index = self.comboBox_LtcPort.findData(selected_port)
        self.comboBox_LtcPort.setCurrentIndex(max(0, index))
        self.comboBox_LtcPort.blockSignals(False)

    def refresh_ltc_audio_devices(self, selected_name: str | None = None) -> None:
        """Populate the LTC audio input device combo box."""
        from audio_capture import list_input_devices

        if selected_name is None:
            selected_name = self.comboBox_LtcAudioDevice.currentData()
            if selected_name is None:
                selected_name = ""

        self.comboBox_LtcAudioDevice.blockSignals(True)
        self.comboBox_LtcAudioDevice.clear()
        self.comboBox_LtcAudioDevice.addItem("System Default", "")
        for device in list_input_devices():
            self.comboBox_LtcAudioDevice.addItem(str(device), device.name)

        index = self.comboBox_LtcAudioDevice.findData(selected_name or "")
        if index < 0 and selected_name:
            self.comboBox_LtcAudioDevice.addItem(f"{selected_name} (unavailable)", selected_name)
            index = self.comboBox_LtcAudioDevice.findData(selected_name)
        self.comboBox_LtcAudioDevice.setCurrentIndex(max(0, index))
        self.comboBox_LtcAudioDevice.blockSignals(False)

    def refresh_livewire_interfaces(self, selected_iface: str | None = None) -> None:
        """Populate the Livewire network interface combo box."""
        from livewire_capture import list_ipv4_interfaces

        if selected_iface is None:
            selected_iface = self.comboBox_LivewireIface.currentData()
            if selected_iface is None:
                selected_iface = ""

        self.comboBox_LivewireIface.blockSignals(True)
        self.comboBox_LivewireIface.clear()
        self.comboBox_LivewireIface.addItem("Default", "")
        for label, ip_str in list_ipv4_interfaces():
            self.comboBox_LivewireIface.addItem(label, ip_str)

        index = self.comboBox_LivewireIface.findData(selected_iface or "")
        if index < 0 and selected_iface:
            self.comboBox_LivewireIface.addItem(f"{selected_iface} (unavailable)", selected_iface)
            index = self.comboBox_LivewireIface.findData(selected_iface)
        self.comboBox_LivewireIface.setCurrentIndex(max(0, index))
        self.comboBox_LivewireIface.blockSignals(False)

    def _empty_aes67_snapshot(self) -> dict:
        """Empty AES67 selection (None in the combo)."""
        return {
            "id": DEFAULT_AUDIO_AES67_ID,
            "name": DEFAULT_AUDIO_AES67_NAME,
            "addr": DEFAULT_AUDIO_AES67_ADDR,
            "port": DEFAULT_AUDIO_AES67_PORT,
            "codec": DEFAULT_AUDIO_AES67_CODEC,
            "rate": DEFAULT_AUDIO_AES67_RATE,
            "channels": DEFAULT_AUDIO_AES67_CHANNELS,
            "dante": False,
            "manual": False,
        }

    def _current_aes67_snapshot(self) -> dict:
        """Return the combo selection; None clears the persisted stream."""
        data = self.comboBox_Aes67Stream.currentData()
        if isinstance(data, dict) and data.get("addr"):
            return dict(data)
        return self._empty_aes67_snapshot()

    def _sync_aes67_saved_from_combo(self) -> None:
        self._aes67_saved = self._current_aes67_snapshot()

    def _aes67_iface(self) -> str:
        iface = self.comboBox_LivewireIface.currentData()
        return iface if isinstance(iface, str) else ""

    def _on_aoip_iface_changed(self, _index: int = 0) -> None:
        """Restart SAP / Livewire ads on the newly selected AoIP interface."""
        if self.isHidden():
            return
        source = self.comboBox_AudioSource.currentData()
        meters_on = self.checkBox_AudioMetersEnabled.isChecked()
        if source == "aes67" and meters_on:
            self._stop_sap_discovery()
            self._sync_sap_discovery()
        elif source == "livewire" and meters_on:
            self._stop_livewire_discovery()
            self._sync_livewire_discovery()

    def _on_aes67_stream_changed(self, _index: int = 0) -> None:
        self._sync_aes67_saved_from_combo()

    def _on_sap_poll(self) -> None:
        """Rebuild the AES67 combo from SAP; used by the poll timer and live callbacks."""
        source = self.comboBox_AudioSource.currentData()
        if not aes67_sap_wanted(
            source, self.checkBox_AudioMetersEnabled.isChecked(), self.isHidden()
        ):
            return
        self.refresh_aes67_streams()
        if self._sap_poll_timer.isActive() and self._sap_poll_timer.interval() != AES67_SAP_POLL_MS:
            self._sap_poll_timer.setInterval(AES67_SAP_POLL_MS)

    def _sync_sap_discovery(self) -> None:
        """Listen for SAP only while the dialog is shown and AES67 is selected."""
        source = self.comboBox_AudioSource.currentData()
        want_sap = aes67_sap_wanted(
            source, self.checkBox_AudioMetersEnabled.isChecked(), self.isHidden()
        )
        if not want_sap:
            self._aes67_ui_active = False
            self._stop_sap_discovery()
            return

        from sap_sdp import SapDiscovery

        iface = self._aes67_iface()
        entering_aes67 = not self._aes67_ui_active
        already_running = (
            self._sap_discovery is not None
            and self._sap_discovery.is_running
            and self._sap_discovery.iface == iface
        )
        if self._sap_discovery is None:
            self._sap_discovery = SapDiscovery(iface=iface)
        self._sap_discovery.set_on_change(self.sigAes67StreamsChanged.emit)
        self._sap_discovery.start(iface=iface)
        if entering_aes67 or not already_running:
            self._aes67_seen_sap_ids = set()
            self._aes67_list_signature = None
        self._aes67_ui_active = True
        if not self._sap_poll_timer.isActive():
            self._sap_poll_timer.setInterval(AES67_SAP_FIRST_POLL_MS)
            self._sap_poll_timer.start()
        self.refresh_aes67_streams()
        QTimer.singleShot(AES67_SAP_FIRST_POLL_MS, self._on_sap_poll)

    def _stop_sap_discovery(self) -> None:
        self._aes67_ui_active = False
        self._sap_poll_timer.stop()
        if self._sap_discovery is not None:
            self._sap_discovery.set_on_change(None)
            self._sap_discovery.stop()

    def _on_livewire_stream_changed(self, _index: int = 0) -> None:
        """Copy the selected advertised channel into the spin box."""
        data = self.comboBox_LivewireStream.currentData()
        if data is None:
            return
        try:
            channel = int(data)
        except (TypeError, ValueError):
            return
        if self.spinBox_LivewireChannel.value() == channel:
            return
        self.spinBox_LivewireChannel.blockSignals(True)
        self.spinBox_LivewireChannel.setValue(channel)
        self.spinBox_LivewireChannel.blockSignals(False)

    def _on_livewire_channel_changed(self, _value: int = 0) -> None:
        """Keep the source combo in sync with a manually typed channel."""
        self.refresh_livewire_streams()

    def _on_lw_poll(self) -> None:
        """Rebuild the Livewire combo from advertisements."""
        source = self.comboBox_AudioSource.currentData()
        if not livewire_adv_wanted(
            source, self.checkBox_AudioMetersEnabled.isChecked(), self.isHidden()
        ):
            return
        self.refresh_livewire_streams()
        if self._lw_poll_timer.isActive() and self._lw_poll_timer.interval() != LIVEWIRE_ADV_POLL_MS:
            self._lw_poll_timer.setInterval(LIVEWIRE_ADV_POLL_MS)

    def _sync_livewire_discovery(self) -> None:
        """Listen for Livewire ads only while the dialog is shown and Livewire is selected."""
        source = self.comboBox_AudioSource.currentData()
        want = livewire_adv_wanted(
            source, self.checkBox_AudioMetersEnabled.isChecked(), self.isHidden()
        )
        if not want:
            self._lw_ui_active = False
            self._stop_livewire_discovery()
            return

        from livewire_adv import LivewireDiscovery

        iface = self._aes67_iface()
        entering = not self._lw_ui_active
        already_running = (
            self._lw_discovery is not None
            and self._lw_discovery.is_running
            and self._lw_discovery.iface == iface
        )
        if self._lw_discovery is None:
            self._lw_discovery = LivewireDiscovery(iface=iface)
        self._lw_discovery.set_on_change(self.sigLivewireStreamsChanged.emit)
        self._lw_discovery.start(iface=iface)
        if entering or not already_running:
            self._lw_list_signature = None
        self._lw_ui_active = True
        if not self._lw_poll_timer.isActive():
            self._lw_poll_timer.setInterval(LIVEWIRE_ADV_FIRST_POLL_MS)
            self._lw_poll_timer.start()
        self.refresh_livewire_streams()
        QTimer.singleShot(LIVEWIRE_ADV_FIRST_POLL_MS, self._on_lw_poll)

    def _stop_livewire_discovery(self) -> None:
        self._lw_ui_active = False
        self._lw_poll_timer.stop()
        if self._lw_discovery is not None:
            self._lw_discovery.set_on_change(None)
            self._lw_discovery.stop()

    def refresh_livewire_streams(self) -> None:
        """Update the Livewire source combo when advertised channels change."""
        from livewire_adv import format_livewire_source_label, livewire_source_list_signature

        channel = int(self.spinBox_LivewireChannel.value())
        discovered = []
        if self._lw_discovery is not None:
            discovered = list(self._lw_discovery.streams())

        name_counts: dict[str, int] = {}
        for source in discovered:
            key = (source.name or "").strip().lower()
            if key:
                name_counts[key] = name_counts.get(key, 0) + 1

        items: list[tuple[int, str]] = []
        seen: set[int] = set()
        for source in discovered:
            key = (source.name or "").strip().lower()
            include_node = bool(key) and name_counts.get(key, 0) > 1
            items.append((source.channel, source.label(include_node=include_node)))
            seen.add(source.channel)
        if channel not in seen:
            items.insert(0, (channel, format_livewire_source_label("", channel)))

        signature = livewire_source_list_signature(items)
        if signature == self._lw_list_signature and self.comboBox_LivewireStream.count() > 0:
            index = self.comboBox_LivewireStream.findData(channel)
            if index >= 0 and self.comboBox_LivewireStream.currentIndex() != index:
                self.comboBox_LivewireStream.blockSignals(True)
                self.comboBox_LivewireStream.setCurrentIndex(index)
                self.comboBox_LivewireStream.blockSignals(False)
            return

        self.comboBox_LivewireStream.blockSignals(True)
        self.comboBox_LivewireStream.clear()
        selected = 0
        for i, (stream_channel, label) in enumerate(items):
            self.comboBox_LivewireStream.addItem(label, stream_channel)
            if stream_channel == channel:
                selected = i
        if items:
            self.comboBox_LivewireStream.setCurrentIndex(selected)
        self.comboBox_LivewireStream.blockSignals(False)
        self._lw_list_signature = signature

    def refresh_aes67_streams(self, selected_id: str | None = None) -> None:
        """Update the AES67 combo only when discovered streams actually change."""
        from sap_sdp import snapshot_label

        if isinstance(selected_id, bool):
            selected_id = None

        current = self.comboBox_Aes67Stream.currentData()
        chose_none = current is None and self.comboBox_Aes67Stream.count() > 0
        if selected_id is None:
            if isinstance(current, dict):
                selected_id = current.get("id") or None
            if not selected_id and not chose_none:
                selected_id = self._aes67_saved.get("id") or None

        by_id: dict[str, tuple[str, dict]] = {}
        if self._sap_discovery is not None:
            for stream in self._sap_discovery.streams():
                data = stream.snapshot()
                by_id[data["id"]] = (stream.label(), data)
                self._aes67_seen_sap_ids.add(data["id"])

        saved = dict(self._aes67_saved)
        saved_id = saved.get("id") or ""
        if saved.get("addr") and saved_id and saved_id not in by_id:
            vanished = (not saved.get("manual")) and saved_id in self._aes67_seen_sap_ids
            if saved.get("manual") or (not chose_none and not vanished):
                by_id[saved_id] = (snapshot_label(saved), saved)

        items = [(stream_id, label, data) for stream_id, (label, data) in by_id.items()]
        signature = aes67_list_signature(items)
        if signature == self._aes67_list_signature and self.comboBox_Aes67Stream.count() > 0:
            return

        self.comboBox_Aes67Stream.blockSignals(True)
        self.comboBox_Aes67Stream.clear()
        self.comboBox_Aes67Stream.addItem(AES67_NONE_LABEL, None)
        index = 0
        for i, (stream_id, label, data) in enumerate(items, start=1):
            self.comboBox_Aes67Stream.addItem(label, data)
            if selected_id and stream_id == selected_id:
                index = i
        if chose_none:
            index = 0
        self.comboBox_Aes67Stream.setCurrentIndex(index)
        self.comboBox_Aes67Stream.blockSignals(False)
        self._aes67_list_signature = signature
        if index > 0:
            self._sync_aes67_saved_from_combo()
        elif chose_none or (selected_id and selected_id not in by_id):
            self._aes67_saved = self._empty_aes67_snapshot()

    def _paste_aes67_sdp(self) -> None:
        """Let the user paste an SDP announcement when SAP is unavailable."""
        from sap_sdp import SdpError, SapDiscovery

        text, ok = QInputDialog.getMultiLineText(
            self,
            "Paste SDP",
            "AES67 SDP announcement:",
        )
        if not ok or not (text or "").strip():
            return
        try:
            if self._sap_discovery is None:
                self._sap_discovery = SapDiscovery(iface=self._aes67_iface())
            stream = self._sap_discovery.add_manual_sdp(text)
        except SdpError as exc:
            QMessageBox.warning(self, "Invalid SDP", str(exc))
            return
        self._aes67_saved = stream.snapshot()
        self.refresh_aes67_streams(selected_id=stream.stream_id)

    def set_aes67_conf(self, key: str, value: str) -> None:
        """Update a persisted AES67 field from CONF:Audio:aes67_* commands."""
        snapshot = dict(self._aes67_saved)
        if key == "id":
            snapshot["id"] = str(value).strip()
        elif key == "addr":
            snapshot["addr"] = str(value).strip()
        elif key == "name":
            snapshot["name"] = str(value).strip()
        elif key == "codec":
            snapshot["codec"] = str(value).strip().upper() or DEFAULT_AUDIO_AES67_CODEC
        elif key == "manual":
            snapshot["manual"] = str(value).strip().lower() in ("1", "true", "yes")
        elif key == "port":
            try:
                port = int(value)
            except (TypeError, ValueError):
                port = DEFAULT_AUDIO_AES67_PORT
            snapshot["port"] = port if 1 <= port <= 65535 else DEFAULT_AUDIO_AES67_PORT
        elif key == "rate":
            try:
                snapshot["rate"] = int(value)
            except (TypeError, ValueError):
                snapshot["rate"] = DEFAULT_AUDIO_AES67_RATE
        elif key == "channels":
            try:
                snapshot["channels"] = int(value)
            except (TypeError, ValueError):
                snapshot["channels"] = DEFAULT_AUDIO_AES67_CHANNELS
        else:
            return
        if snapshot.get("addr") and not snapshot.get("id"):
            snapshot["id"] = f"{snapshot.get('addr')}:{snapshot.get('port')}"
        if snapshot.get("addr") and not snapshot.get("name"):
            snapshot["name"] = f"{snapshot.get('addr')}:{snapshot.get('port')}"
        snapshot.setdefault("manual", False)
        snapshot.setdefault("dante", False)
        self._aes67_saved = snapshot
        self.refresh_aes67_streams(selected_id=snapshot.get("id") or None)

    def set_audio_source(self, source: str) -> None:
        """Select audio source by key (device|livewire|aes67)."""
        index = self.comboBox_AudioSource.findData(source)
        if index < 0:
            index = self.comboBox_AudioSource.findData(DEFAULT_AUDIO_SOURCE)
        if index >= 0:
            self.comboBox_AudioSource.setCurrentIndex(index)

    def _restore_audio_settings(self, settings: QSettings) -> None:
        """Restore Audio group settings into the dialog widgets."""
        with settings_group(settings, "Audio"):
            enabled = settings.value('enabled', DEFAULT_AUDIO_METERS_ENABLED, type=bool)
            tooloud = settings.value('tooloud', DEFAULT_AUDIO_TOOLOUD, type=bool)
            unit = settings.value('unit', DEFAULT_AUDIO_UNIT, type=str) or DEFAULT_AUDIO_UNIT
            layout_raw = settings.value('layout', None)
            layout, unit = migrate_audio_layout_and_unit(unit, layout_raw)
            source = settings.value('source', DEFAULT_AUDIO_SOURCE, type=str) or DEFAULT_AUDIO_SOURCE
            device = settings.value('input_device', DEFAULT_AUDIO_INPUT_DEVICE, type=str) or ""
            livewire_channel = settings.value(
                'livewire_channel', DEFAULT_AUDIO_LIVEWIRE_CHANNEL, type=int
            )
            livewire_iface = settings.value(
                'livewire_iface', DEFAULT_AUDIO_LIVEWIRE_IFACE, type=str
            ) or ""
            aes67_id = settings.value('aes67_id', DEFAULT_AUDIO_AES67_ID, type=str) or ""
            aes67_addr = settings.value('aes67_addr', DEFAULT_AUDIO_AES67_ADDR, type=str) or ""
            aes67_port = settings.value('aes67_port', DEFAULT_AUDIO_AES67_PORT, type=int)
            aes67_name = settings.value('aes67_name', DEFAULT_AUDIO_AES67_NAME, type=str) or ""
            aes67_codec = settings.value(
                'aes67_codec', DEFAULT_AUDIO_AES67_CODEC, type=str
            ) or DEFAULT_AUDIO_AES67_CODEC
            aes67_rate = settings.value('aes67_rate', DEFAULT_AUDIO_AES67_RATE, type=int)
            aes67_channels = settings.value(
                'aes67_channels', DEFAULT_AUDIO_AES67_CHANNELS, type=int
            )
            aes67_manual = settings.value(
                'aes67_manual', DEFAULT_AUDIO_AES67_MANUAL, type=bool
            )
            text = settings.value('tooloudtext', DEFAULT_AUDIO_TOOLOUD_TEXT, type=str) or DEFAULT_AUDIO_TOOLOUD_TEXT
            threshold = settings.value(
                'tooloud_threshold_dbtp', DEFAULT_AUDIO_TOOLOUD_THRESHOLD_DBTP, type=float
            )
            tooloud_action = settings.value(
                'tooloud_action', DEFAULT_AUDIO_TOOLOUD_ACTION, type=str
            ) or DEFAULT_AUDIO_TOOLOUD_ACTION
            tooloud_led = settings.value('tooloud_led', DEFAULT_AUDIO_TOOLOUD_LED, type=int)
            silence = settings.value('silence', DEFAULT_AUDIO_SILENCE, type=bool)
            silence_warn = settings.value('silence_warn', DEFAULT_AUDIO_SILENCE_WARN, type=bool)
            silence_on_absent = settings.value(
                'silence_on_absent', DEFAULT_AUDIO_SILENCE_ON_ABSENT, type=bool
            )
            silence_text = settings.value(
                'silence_text', DEFAULT_AUDIO_SILENCE_TEXT, type=str
            ) or DEFAULT_AUDIO_SILENCE_TEXT
            silence_threshold = settings.value(
                'silence_threshold_dbfs', DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS, type=float
            )
            silence_duration = settings.value(
                'silence_duration_s', DEFAULT_AUDIO_SILENCE_DURATION_S, type=float
            )
            silence_recovery = settings.value(
                'silence_recovery_s', DEFAULT_AUDIO_SILENCE_RECOVERY_S, type=float
            )
            silence_http_url = settings.value(
                'silence_http_url', DEFAULT_AUDIO_SILENCE_HTTP_URL, type=str
            ) or ""
            lufs_preset = settings.value(
                'lufs_reference_preset', DEFAULT_AUDIO_LUFS_REFERENCE_PRESET, type=str
            ) or DEFAULT_AUDIO_LUFS_REFERENCE_PRESET
            lufs_reference = settings.value(
                'lufs_reference', DEFAULT_AUDIO_LUFS_REFERENCE, type=float
            )
            peak_hold = settings.value('peak_hold', DEFAULT_AUDIO_PEAK_HOLD, type=bool)
            peak_hold_seconds = settings.value(
                'peak_hold_seconds', DEFAULT_AUDIO_PEAK_HOLD_SECONDS, type=float
            )
            display_style = settings.value(
                'display_style', DEFAULT_AUDIO_DISPLAY_STYLE, type=str
            ) or DEFAULT_AUDIO_DISPLAY_STYLE
            meter_width = settings.value(
                'meter_width', DEFAULT_AUDIO_METER_WIDTH, type=int
            )

            self.checkBox_AudioMetersEnabled.setChecked(enabled)
            self.checkBox_TooLoud.setChecked(tooloud)
            self.TooLoudText.setText(text)
            self.doubleSpinBox_TooLoudThreshold.setValue(float(threshold))
            self.checkBox_PeakHold.blockSignals(True)
            self.checkBox_PeakHold.setChecked(bool(peak_hold))
            self.checkBox_PeakHold.blockSignals(False)
            self.doubleSpinBox_PeakHoldSeconds.setValue(float(peak_hold_seconds))

            self._populate_tooloud_action_controls()
            action_index = self.comboBox_TooLoudAction.findData(tooloud_action)
            if action_index < 0:
                action_index = self.comboBox_TooLoudAction.findData(DEFAULT_AUDIO_TOOLOUD_ACTION)
            self.comboBox_TooLoudAction.blockSignals(True)
            self.comboBox_TooLoudAction.setCurrentIndex(max(0, action_index))
            self.comboBox_TooLoudAction.blockSignals(False)
            led_index = self.comboBox_TooLoudLED.findData(int(tooloud_led))
            if led_index < 0:
                led_index = 0
            self.comboBox_TooLoudLED.setCurrentIndex(led_index)

            self.checkBox_Silence.setChecked(silence)
            self.checkBox_SilenceWarn.setChecked(silence_warn)
            self.checkBox_SilenceOnAbsent.setChecked(silence_on_absent)
            self.SilenceText.setText(silence_text)
            self.doubleSpinBox_SilenceThreshold.setValue(float(silence_threshold))
            self.doubleSpinBox_SilenceDuration.setValue(float(silence_duration))
            self.doubleSpinBox_SilenceRecovery.setValue(float(silence_recovery))
            self.SilenceHttpUrl.setText(silence_http_url)

            self._populate_lufs_reference_presets()
            preset_index = self.comboBox_LufsReferencePreset.findData(lufs_preset)
            if preset_index < 0:
                preset_index = self.comboBox_LufsReferencePreset.findData(DEFAULT_AUDIO_LUFS_REFERENCE_PRESET)
            self.comboBox_LufsReferencePreset.blockSignals(True)
            self.comboBox_LufsReferencePreset.setCurrentIndex(max(0, preset_index))
            self.comboBox_LufsReferencePreset.blockSignals(False)
            self.doubleSpinBox_LufsReference.blockSignals(True)
            self.doubleSpinBox_LufsReference.setValue(float(lufs_reference))
            self.doubleSpinBox_LufsReference.blockSignals(False)
            self._on_lufs_reference_preset_changed()

            self.comboBox_AudioSource.blockSignals(True)
            self.comboBox_AudioSource.clear()
            for key, label in AUDIO_SOURCE_LABELS.items():
                self.comboBox_AudioSource.addItem(label, key)
            source_index = self.comboBox_AudioSource.findData(source)
            if source_index < 0:
                source_index = self.comboBox_AudioSource.findData(DEFAULT_AUDIO_SOURCE)
            self.comboBox_AudioSource.setCurrentIndex(max(0, source_index))
            self.comboBox_AudioSource.blockSignals(False)

            try:
                channel_value = int(livewire_channel)
            except (TypeError, ValueError):
                channel_value = DEFAULT_AUDIO_LIVEWIRE_CHANNEL
            self.spinBox_LivewireChannel.blockSignals(True)
            self.spinBox_LivewireChannel.setValue(
                max(1, min(32767, channel_value))
            )
            self.spinBox_LivewireChannel.blockSignals(False)

            self.comboBox_MeterLayout.blockSignals(True)
            self.comboBox_MeterLayout.clear()
            for key, label in AUDIO_LAYOUT_LABELS.items():
                self.comboBox_MeterLayout.addItem(label, key)
            layout_index = self.comboBox_MeterLayout.findData(layout)
            if layout_index < 0:
                layout_index = self.comboBox_MeterLayout.findData(DEFAULT_AUDIO_LAYOUT)
            self.comboBox_MeterLayout.setCurrentIndex(max(0, layout_index))
            self.comboBox_MeterLayout.blockSignals(False)

            self.comboBox_AudioUnit.blockSignals(True)
            self.comboBox_AudioUnit.clear()
            for key, label in AUDIO_UNIT_LABELS.items():
                self.comboBox_AudioUnit.addItem(label, key)
            unit_index = self.comboBox_AudioUnit.findData(unit)
            if unit_index < 0:
                unit_index = self.comboBox_AudioUnit.findData(DEFAULT_AUDIO_UNIT)
            self.comboBox_AudioUnit.setCurrentIndex(max(0, unit_index))
            self.comboBox_AudioUnit.blockSignals(False)

            self.comboBox_DisplayStyle.blockSignals(True)
            self.comboBox_DisplayStyle.clear()
            for key, label in AUDIO_DISPLAY_STYLE_LABELS.items():
                self.comboBox_DisplayStyle.addItem(label, key)
            style_index = self.comboBox_DisplayStyle.findData(display_style)
            if style_index < 0:
                style_index = self.comboBox_DisplayStyle.findData(DEFAULT_AUDIO_DISPLAY_STYLE)
            self.comboBox_DisplayStyle.setCurrentIndex(max(0, style_index))
            self.comboBox_DisplayStyle.blockSignals(False)

            try:
                meter_width_value = int(meter_width)
            except (TypeError, ValueError):
                meter_width_value = DEFAULT_AUDIO_METER_WIDTH
            self.spinBox_MeterWidth.setMinimum(AUDIO_METER_WIDTH_MIN)
            self.spinBox_MeterWidth.setMaximum(AUDIO_METER_WIDTH_MAX)
            self.spinBox_MeterWidth.setValue(
                max(AUDIO_METER_WIDTH_MIN, min(AUDIO_METER_WIDTH_MAX, meter_width_value))
            )

            self.refresh_audio_input_devices(device)
            self.refresh_livewire_interfaces(livewire_iface)
            self._lw_list_signature = None
            self.refresh_livewire_streams()
            try:
                aes67_port_value = int(aes67_port)
            except (TypeError, ValueError):
                aes67_port_value = DEFAULT_AUDIO_AES67_PORT
            try:
                aes67_rate_value = int(aes67_rate)
            except (TypeError, ValueError):
                aes67_rate_value = DEFAULT_AUDIO_AES67_RATE
            try:
                aes67_channels_value = int(aes67_channels)
            except (TypeError, ValueError):
                aes67_channels_value = DEFAULT_AUDIO_AES67_CHANNELS
            self._aes67_saved = {
                "id": aes67_id or "",
                "name": aes67_name or "",
                "addr": aes67_addr or "",
                "port": aes67_port_value,
                "codec": aes67_codec or DEFAULT_AUDIO_AES67_CODEC,
                "rate": aes67_rate_value,
                "channels": aes67_channels_value,
                "dante": False,
                "manual": bool(aes67_manual),
            }
            self.refresh_aes67_streams(selected_id=aes67_id or None)
            self._on_audio_meters_enabled_changed(enabled)
            self._on_tooloud_enabled_changed(tooloud)
            self._on_silence_enabled_changed(silence)

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
        self.restore_audio(settings)
    
    def restore_general(self, settings: QSettings) -> None:
        """
        Restore general settings (instance name, station name, slogan, colors)
        
        Args:
            settings: QSettings object to read from
        """
        with settings_group(settings, "General"):
            instance_name = normalize_instance_name(
                settings.value('instancename', DEFAULT_INSTANCE_NAME)
            )
            self.main_screen.labelStation.setText(settings.value('stationname', DEFAULT_STATION_NAME))
            self.main_screen.labelSlogan.setText(settings.value('slogan', DEFAULT_SLOGAN))
            self.main_screen.set_station_color(self.settings.getColorFromName(settings.value('stationcolor', DEFAULT_STATION_COLOR)))
            self.main_screen.set_slogan_color(self.settings.getColorFromName(settings.value('slogancolor', DEFAULT_SLOGAN_COLOR)))
        if hasattr(self.main_screen, "setWindowTitle"):
            self.main_screen.setWindowTitle(f"OnAirScreen – {instance_name}")
    
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
                    configured_text = settings.value(text_key, text_default)
                    label_widget = getattr(self.main_screen, f'AirLabel_{air_num}')
                    icon_widget = getattr(self.main_screen, f'AirIcon_{air_num}')
                    led_widget = getattr(self.main_screen, f'AirLED_{air_num}')
                    status_attr = f'statusAIR{air_num}'
                    seconds_attr = f'Air{air_num}Seconds'
                    is_active = bool(getattr(self.main_screen, status_attr, False))
                    seconds = int(getattr(self.main_screen, seconds_attr, 0) or 0)
                    top_of_hour = (
                        air_num == 3 and bool(getattr(self.main_screen, "topOfHourActive", False))
                    )
                    toth_text = settings.value('TimerTOTHText', DEFAULT_TOTH_TIMER_TEXT)
                    label_text = air_timer_caption(
                        air_num, configured_text, top_of_hour, toth_text
                    )
                    try:
                        radio_mode = int(getattr(self.main_screen, "radioTimerMode", 0) or 0)
                    except (TypeError, ValueError):
                        radio_mode = 0
                    count_down = air_timer_count_down(air_num, radio_mode, top_of_hour)
                    label_widget.setText(format_air_timer_label(label_text, seconds))
                    if air_num == 3:
                        mark_widget = getattr(self.main_screen, "AirCountMark_3", None)
                        if mark_widget is not None:
                            mark_widget.setText(air_timer_count_mark(count_down))

                    if is_active:
                        text_color = settings.value(
                            f'AIR{air_num}activetextcolor', DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR
                        )
                        bg_color = settings.value(
                            f'AIR{air_num}activebgcolor', DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR
                        )
                    else:
                        text_color = settings.value(
                            'inactivetextcolor', DEFAULT_TIMER_AIR_INACTIVE_TEXT_COLOR
                        )
                        bg_color = settings.value(
                            'inactivebgcolor', DEFAULT_TIMER_AIR_INACTIVE_BG_COLOR
                        )

                    # Save icon before setStyleSheet to prevent flickering
                    with settings_group(settings, "AIR"):
                        icon_path = settings.value(icon_key, icon_default)
                        icon_pixmap = QPixmap(icon_path) if icon_path else None

                    label_widget.setStyleSheet(f"color:{text_color};background-color:{bg_color}")
                    icon_widget.setStyleSheet(f"color:{text_color};background-color:{bg_color}")
                    if air_num == 3:
                        chrome_style = f"color:{text_color};background-color:{bg_color}"
                        for chrome_name in ("AirCountMark_3", "AirIconColumn_3"):
                            chrome_widget = getattr(self.main_screen, chrome_name, None)
                            if chrome_widget is not None:
                                chrome_widget.setStyleSheet(chrome_style)

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
                font_name = resolve_font_name(settings.value(f'{font_prefix}FontName', DEFAULT_FONT_NAME))
                font_size = settings.value(
                    f'{font_prefix}FontSize', default_font_size_for_prefix(font_prefix), type=int
                )
                font_weight = settings.value(f'{font_prefix}FontWeight', DEFAULT_FONT_WEIGHT_BOLD, type=int)
                widget.setFont(QFont(font_name, font_size, qfont_weight_from_stored(font_weight)))
                if font_prefix == "AIR3":
                    mark_widget = getattr(self.main_screen, "AirCountMark_3", None)
                    if mark_widget is not None:
                        mark_widget.setFont(QFont(font_name, max(10, font_size - 8), qfont_weight_from_stored(font_weight)))


    def restore_audio(self, settings: QSettings) -> None:
        """
        Restore audio meter settings onto the main screen.

        Args:
            settings: QSettings object to read from
        """
        apply_fn = getattr(self.main_screen, "apply_audio_settings", None)
        if callable(apply_fn):
            apply_fn(settings)
