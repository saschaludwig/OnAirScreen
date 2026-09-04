#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# start.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

import sys

if sys.version_info < (3, 11):
    sys.stderr.write(
        f"OnAirScreen requires Python 3.11 or newer (found {sys.version.split()[0]})\n"
    )
    sys.exit(1)

import argparse
import logging
import math
import re
import time
from datetime import timedelta

from PySide6.QtCore import (
    Qt, QByteArray, QPoint, QSettings, QCoreApplication, QTimer,
    Signal, QObject, QElapsedTimer, QUrl,
)
from PySide6.QtGui import QCursor, QPalette, QIcon, QPixmap, QFont, QColor, QMouseEvent, QContextMenuEvent
from PySide6.QtNetwork import QNetworkInterface, QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import QApplication, QWidget, QDialog, QLineEdit, QVBoxLayout, QLabel, QMessageBox, QMenu

# Import resources FIRST to register them with Qt before UI files are loaded
import resources_rc  # noqa: F401
from mainscreen import Ui_MainScreen
from settings_functions import Settings, versionString, distributionString
from command_handler import CommandHandler
from network import UdpServer, HttpDaemon, WebSocketDaemon
from timer_manager import TimerManager
from event_logger import EventLogger
from warning_manager import WarningManager
from settings_functions import SettingsRestorer
from timer_input import TimerInputDialog
from ntp_manager import NTPManager
from time_source import TimeSourceManager, wall_datetime
from font_loader import available_font_families, load_fonts
from signal_handlers import setup_signal_handlers
from system_operations import SystemOperations
from status_exporter import StatusExporter
from ui_updater import UIUpdater
from hotkey_manager import HotkeyManager
from logging_config import (
    set_log_level, get_command_line_log_level, set_command_line_log_level,
    setup_file_logging,
)
from crash_handler import (
    install_crash_hooks, install_qt_message_handler, ensure_log_directory,
)
from crash_notice_dialog import maybe_show_crash_notice
from utils import settings_group, host_address_is_ipv4, host_address_is_ipv6
from defaults import *  # noqa: F403, F405
from exceptions import WidgetAccessError, log_exception
from audio_capture import AudioCaptureController
from meter_engine import MeterReadings, MeterUnit, migrate_audio_layout_and_unit
from silence_detector import SILENCE_FLOOR_DBFS, SilenceDetector

# Logging will be configured after QApplication initialization and settings loading
logger = logging.getLogger(__name__)

TOOLOUD_WARNING_PRIORITY = 1
TOOLOUD_CLEAR_HOLD_MS = 750
SILENCE_WARNING_PRIORITY = 2


class CommandSignal(QObject):
    """Signal object for thread-safe command execution"""
    command_received = Signal(bytes, str)


class MainScreen(QWidget, Ui_MainScreen):
    """
    Main application window for OnAirScreen
    
    This class handles the main UI, timer management, LED/AIR controls,
    network communication (UDP/HTTP/MQTT/OSC), and settings management.
    
    The class delegates specific responsibilities to specialized manager classes:
    - NTPManager: NTP time synchronization checking
    - UIUpdater: Periodic UI updates (date, time, backtiming)
    - SystemOperations: System operations (reboot, shutdown, exit)
    - StatusExporter: Status data export for API
    - HotkeyManager: Keyboard shortcut management
    - TimerManager: Timer object management
    - WarningManager: Warning system management
    """
    getTimeWindow: QDialog
    textLocale: str  # for text language
    languages = {"English": 'en_US',
                 "German": 'de_DE',
                 "Dutch": 'nl_NL',
                 "French": 'fr_FR'}
    # Receive left-clicks so LEDs and AIR timers can toggle; children stay
    # click-through so icon/label hits still reach these frames.
    CLICKABLE_CHILD_NAMES = frozenset({
        "buttonLED1", "buttonLED2", "buttonLED3", "buttonLED4",
        "AirLED_1", "AirLED_2", "AirLED_3", "AirLED_4",
    })

    def __init__(self) -> None:
        """Initialize the main screen and load settings"""
        QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)
        self._make_children_click_through()
        self._install_toggle_clicks()

        self.settings = Settings()
        self.restore_settings_from_config()
        self._is_quitting = False
        
        # Initialize event logger (needed for system operations)
        self.event_logger = EventLogger()
        
        # Initialize system operations (needed for signal connections)
        self.system_operations = SystemOperations(self)
        
        # quit app from settings window
        self.settings.sigExitOAS.connect(self.system_operations.exit_oas)
        self.settings.sigRebootHost.connect(self.system_operations.reboot_host)
        self.settings.sigShutdownHost.connect(self.system_operations.shutdown_host)
        self.settings.sigConfigFinished.connect(self.config_finished)
        self.settings.sigConfigClosed.connect(self.config_closed)

        # Initialize command handler
        self.command_handler = CommandHandler(self)
        
        # Initialize event logger
        self.event_logger = EventLogger()
        
        # Initialize status exporter
        self.status_exporter = StatusExporter(self)

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('fullscreen', True, type=bool):
                self.showFullScreen()
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
        logger.info(f"Loaded settings from: {settings.fileName()}")

        # Keep NOW/NEXT and Warning at a stable shared height to avoid layout jumps
        self._lock_bottom_stack_height()
        if hasattr(self, "bottomStack") and hasattr(self, "pageBottomNormal"):
            self.bottomStack.setCurrentWidget(self.pageBottomNormal)

        # Initialize warning manager
        self.warning_manager = WarningManager(
            self.labelWarning,
            self.labelCurrentSong,
            self.labelNews,
            self.event_logger,
            self._publish_mqtt_status,
            bottom_stack=getattr(self, "bottomStack", None),
            page_normal=getattr(self, "pageBottomNormal", None),
            page_warning=getattr(self, "pageBottomWarning", None),
        )
        # Keep warnings attribute for backward compatibility (used in get_status_json)
        self.warnings = self.warning_manager.warnings

        # Audio meters / TooLoud
        self._audio_meters_enabled = DEFAULT_AUDIO_METERS_ENABLED
        self._audio_tooloud_enabled = False
        self._audio_tooloud_text = DEFAULT_AUDIO_TOOLOUD_TEXT
        self._audio_tooloud_threshold = DEFAULT_AUDIO_TOOLOUD_THRESHOLD_DBTP
        self._audio_tooloud_action = DEFAULT_AUDIO_TOOLOUD_ACTION
        self._audio_tooloud_led = DEFAULT_AUDIO_TOOLOUD_LED
        self._audio_lufs_reference = DEFAULT_AUDIO_LUFS_REFERENCE
        self._audio_peak_hold = DEFAULT_AUDIO_PEAK_HOLD
        self._audio_peak_hold_seconds = DEFAULT_AUDIO_PEAK_HOLD_SECONDS
        self._audio_display_style = DEFAULT_AUDIO_DISPLAY_STYLE
        self._audio_meter_width = DEFAULT_AUDIO_METER_WIDTH
        self._audio_layout = DEFAULT_AUDIO_LAYOUT
        self._audio_tooloud_active = False
        self._audio_tooloud_led_lit = False
        self._audio_tooloud_clear_timer = QElapsedTimer()
        self._audio_silence_enabled = False
        self._audio_silence_warn = DEFAULT_AUDIO_SILENCE_WARN
        self._audio_silence_on_absent = DEFAULT_AUDIO_SILENCE_ON_ABSENT
        self._audio_silence_text = DEFAULT_AUDIO_SILENCE_TEXT
        self._audio_silence_http_url = DEFAULT_AUDIO_SILENCE_HTTP_URL
        self._audio_silence_active = False
        self._audio_silence_warn_shown = False
        self._silence_detector = SilenceDetector(
            threshold_dbfs=DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS,
            duration_s=DEFAULT_AUDIO_SILENCE_DURATION_S,
            recovery_s=DEFAULT_AUDIO_SILENCE_RECOVERY_S,
        )
        self._silence_nam: QNetworkAccessManager | None = None
        self.audio_capture = AudioCaptureController(self)
        self.audio_capture.levels.connect(self._on_audio_levels)
        self.audio_capture.error.connect(self._on_audio_capture_error)
        if hasattr(self, "audioMeterWidget"):
            self._set_audio_meter_visible(DEFAULT_AUDIO_METERS_ENABLED)
        self.apply_audio_settings(QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen"))

        # Initialize hotkey manager
        self.hotkey_manager = HotkeyManager(self)

        self.statusLED1 = False
        self.statusLED2 = False
        self.statusLED3 = False
        self.statusLED4 = False

        self.LED1on = False
        self.LED2on = False
        self.LED3on = False
        self.LED4on = False

        # Initialize UI updater
        self.ui_updater = UIUpdater(self)
        
        # Setup and start constant update timer
        self.ctimer = QTimer()
        self.ctimer.timeout.connect(self.ui_updater.constant_update)
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
        self.topOfHourActive = False
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

        # Initialize NTP and time-source managers
        self.ntp_manager = NTPManager(self)
        self.time_source_manager = TimeSourceManager(self)

        self.replacenowTimer = QTimer()
        self.replacenowTimer.timeout.connect(self.replace_now_next)

        # Setup command signal for thread-safe HTTP command execution
        self.command_signal = CommandSignal()
        self.command_signal.command_received.connect(self._parse_cmd_with_source)
        
        # Setup UDP Server with source tracking
        def udp_command_callback(data: bytes) -> None:
            self._parse_cmd_with_source(data, "udp")
        
        self.udp_server = UdpServer(udp_command_callback)

        # Setup HTTP Server with reference to MainScreen for status API and command signal
        from web_settings import SettingsApiBridge
        self.settings_api = SettingsApiBridge(self)
        self.httpd = HttpDaemon(self, self.command_signal, self.settings_api)
        self.httpd.start()
        
        # Setup WebSocket Server for real-time status updates
        self.wsd = WebSocketDaemon(self)
        self.wsd.start()
        
        # Setup MQTT Client
        try:
            from mqtt_client import MqttClient
            self.mqtt_client = MqttClient(self)
            self.mqtt_client.start()
        except Exception as e:
            logger.warning(f"Failed to initialize MQTT client: {e}")
            self.mqtt_client = None

        # Setup OSC Server
        try:
            from osc_server import OscDaemon
            self.osc_daemon = OscDaemon(self)
            self.osc_daemon.start()
        except Exception as e:
            logger.warning(f"Failed to initialize OSC server: {e}")
            self.osc_daemon = None

        # Setup GPIO inputs (Raspberry Pi)
        try:
            from gpio_manager import GpioManager
            self.gpio_manager = GpioManager(self)
            self.gpio_manager.start()
        except Exception as e:
            logger.warning(f"Failed to initialize GPIO manager: {e}")
            self.gpio_manager = None
        
        # Log application start
        self.event_logger.log_system_event("Application started")

        # display all host addresses
        self.display_all_hostaddresses()

        # NTP warning is already initialized in NTPManager

        # do initial update check
        self.settings.sigCheckForUpdate.emit()

        # Restore last windowed position/size after layout is ready
        if not self.isFullScreen():
            self._restore_window_geometry()

    def quit_oas(self) -> None:
        """
        Quit the application with cleanup

        Shows a WARN, then stops NTP, HTTP/WebSocket, MQTT, OSC, GPIO, audio capture,
        and quits the application. Cleanup is deferred so the WARN can paint.
        """
        if getattr(self, "_is_quitting", False):
            return
        logger.info("Quitting, cleaning up...")
        self.event_logger.log_system_event("Application quit")
        self._is_quitting = True
        self.add_warning("QUITTING ONAIRSCREEN", 2)
        self.process_warnings()
        self.repaint()
        # Return to the event loop so macOS can composite the WARN before we block.
        QTimer.singleShot(100, self._finish_quit)

    def _finish_quit(self) -> None:
        """Stop background services and quit after the quit WARN is on screen."""
        self._save_window_geometry()
        self._stop_background_services()
        QCoreApplication.instance().quit()

    def _stop_background_services(self) -> None:
        """Stop network, MQTT, OSC, GPIO, NTP, and audio services. Safe to call more than once."""
        try:
            if hasattr(self, 'time_source_manager') and self.time_source_manager:
                self.time_source_manager.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping time source: {e}")
                log_exception(logger, error)

        try:
            if hasattr(self, 'ntp_manager') and self.ntp_manager:
                self.ntp_manager.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping NTP check: {e}")
                log_exception(logger, error)

        try:
            if hasattr(self, 'httpd') and self.httpd:
                self.httpd.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping HTTP daemon: {e}")
                log_exception(logger, error)

        try:
            if hasattr(self, 'wsd') and self.wsd:
                self.wsd.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping WebSocket daemon: {e}")
                log_exception(logger, error)

        try:
            if hasattr(self, 'mqtt_client') and self.mqtt_client:
                self.mqtt_client.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping MQTT client: {e}")
                log_exception(logger, error)

        try:
            if hasattr(self, 'osc_daemon') and self.osc_daemon:
                self.osc_daemon.stop()
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Error stopping OSC server: {e}")
                log_exception(logger, error)

        try:
            if hasattr(self, 'gpio_manager') and self.gpio_manager:
                self.gpio_manager.stop()
        except Exception as e:
            logger.warning("Error stopping GPIO manager: %s", e)

        try:
            if hasattr(self, 'audio_capture') and self.audio_capture:
                self.audio_capture.stop()
        except Exception as e:
            logger.warning("Error stopping audio capture: %s", e)

    def radio_timer_start_stop(self) -> None:
        """
        Start or stop the radio timer (AIR3)
        
        Toggles the radio timer between running and stopped states.
        """
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
            self.topOfHourActive = False
            self.reset_air3()
            self.radioTimerMode = 0  # count up mode
        elif timer_type == 'stream':
            self.reset_air4()
            self.streamTimerMode = 0  # count up mode
        else:
            logger.warning(f"Invalid timer type: {timer_type}")

    def radio_timer_set(self, seconds: int) -> None:
        """
        Set radio timer duration in seconds
        
        Args:
            seconds: Timer duration in seconds (0 for count-up mode, >0 for count-down mode)
        """
        self.Air3Seconds = seconds
        if seconds > 0:
            self.radioTimerMode = 1  # count down mode
            mode = "count_down"
        else:
            self.radioTimerMode = 0  # count up mode
            mode = "count_up"
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Timers"):
            configured = settings.value("TimerAIR3Text", DEFAULT_TIMER_AIR_TEXTS.get(3, "Timer"))
            toth_text = settings.value("TimerTOTHText", DEFAULT_TOTH_TIMER_TEXT)
        caption = air_timer_caption(
            3, configured, getattr(self, "topOfHourActive", False), toth_text
        )
        self._apply_air_label_text(self.AirLabel_3, 3, caption, self.Air3Seconds)
        
        # Log timer set event
        self.event_logger.log_timer_set(3, seconds, mode)

    def _air_count_down(self, air_num: int):
        """Return True/False for AIR3 count direction, else None."""
        if air_num != 3:
            return None
        try:
            top_of_hour = bool(getattr(self, "topOfHourActive", False))
        except RuntimeError:
            top_of_hour = False
        try:
            radio_mode = int(getattr(self, "radioTimerMode", 0) or 0)
        except (TypeError, ValueError, RuntimeError):
            radio_mode = 0
        return air_timer_count_down(air_num, radio_mode, top_of_hour)

    def _format_air_label(self, air_num: int, caption: str, seconds: int) -> str:
        """AIR label text: caption and m:ss, centered as plain text."""
        return format_air_timer_label(caption, seconds)

    def _air3_widget(self, name: str):
        """Return an AIR3 extra widget, or None in tests without Qt init."""
        try:
            return getattr(self, name, None)
        except RuntimeError:
            return None

    def _apply_air_count_mark(self) -> None:
        """Show ▲/▼ under the AIR3 icon; no-op if the widget is missing (tests)."""
        mark_widget = self._air3_widget("AirCountMark_3")
        if mark_widget is None:
            return
        mark_widget.setText(air_timer_count_mark(self._air_count_down(3)))

    def _apply_air_icon_style(self, air_num: int, icon_widget, stylesheet: str) -> None:
        """Apply AIR icon colors; AIR3 also tints the count mark under the icon."""
        icon_widget.setStyleSheet(stylesheet)
        if air_num != 3:
            return
        for name in ("AirCountMark_3", "AirIconColumn_3"):
            widget = self._air3_widget(name)
            if widget is not None:
                widget.setStyleSheet(stylesheet)

    def _apply_air_label_text(self, label_widget, air_num: int, caption: str, seconds: int) -> None:
        """Set AIR label text and refresh the AIR3 count-direction mark."""
        label_widget.setText(self._format_air_label(air_num, caption, seconds))
        if air_num == 3:
            self._apply_air_count_mark()

    def _seconds_until_top_of_hour(self) -> int:
        """Return seconds until the next full hour (rounded up to whole seconds)."""
        now = wall_datetime()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return math.ceil((next_hour - now).total_seconds())

    def _milliseconds_until_next_wall_second(self) -> int:
        """Return milliseconds until the next wall-clock second boundary."""
        ms_into_second = wall_datetime().microsecond // 1000
        remaining_ms = 1000 - ms_into_second
        return remaining_ms if remaining_ms > 0 else 1000

    def _align_air3_timer_to_wall_clock(self) -> None:
        """Align AIR3 timer ticks to wall-clock second boundaries."""
        if self.statusAIR3 and self.topOfHourActive:
            self.timerAIR3.start(self._milliseconds_until_next_wall_second())

    def start_top_of_hour_countdown(self) -> None:
        """Start countdown to the next full hour in the AIR3 timer display."""
        self.topOfHourActive = True
        seconds = self._seconds_until_top_of_hour()
        self.radio_timer_set(seconds)
        if not self.statusAIR3:
            self.start_air3()
        else:
            self._align_air3_timer_to_wall_clock()
        self._publish_mqtt_status("air3toh")

    def stop_top_of_hour_countdown(self) -> None:
        """Stop top-of-hour countdown and reset AIR3 timer to 0:00."""
        self.topOfHourActive = False
        if self.statusAIR3:
            self.stop_air3()
        self.radio_timer_reset()
        self._publish_mqtt_status("air3toh")

    def toggle_top_of_hour_countdown(self) -> None:
        """Toggle top-of-hour countdown in the AIR3 timer display."""
        if self.topOfHourActive:
            self.stop_top_of_hour_countdown()
        else:
            self.start_top_of_hour_countdown()

    def get_timer_dialog(self) -> None:
        """
        Generate and display timer input dialog window
        
        Creates a dialog window for entering timer values in formats:
        - "2,10" or "2.10" for 2 minutes 10 seconds
        - "30" for 30 seconds only
        """
        if not hasattr(self, 'timer_input_dialog') or self.timer_input_dialog is None:
            self.timer_input_dialog = TimerInputDialog(self)
            self.timer_input_dialog.timer_set.connect(self.radio_timer_set)
        self.timer_input_dialog.show()

    def stream_timer_start_stop(self) -> None:
        """
        Start or stop the stream timer (AIR4)
        
        Toggles the stream timer between running and stopped states.
        """
        self.start_stop_air4()

    def stream_timer_reset(self) -> None:
        """
        Reset stream timer (AIR4)
        
        Resets the stream timer to 0 and sets it to count-up mode.
        """
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
        
        if air_num not in air_configs:
            logger.warning(f"Invalid AIR number: {air_num}, must be 1-4")
            return
        
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
                active_text_color = settings.value(config['active_text_color'], DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR)
                active_bg_color = settings.value(config['active_bg_color'], DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR)
                label_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
                
                # Set icon with active styles
                with settings_group(settings, "AIR"):
                    icon_path = settings.value(config['icon_key'], config['icon_default'])
                    if icon_path:
                        pixmap = QPixmap(icon_path)
                        self._apply_air_icon_style(
                            air_num,
                            icon_widget,
                            f"color:{active_text_color};background-color:{active_bg_color}",
                        )
                        icon_widget.setPixmap(pixmap)
                        icon_widget.update()
                
                # Set label text
                label_text = air_timer_caption(
                    air_num,
                    settings.value(config['label'], config['label_default']),
                    getattr(self, "topOfHourActive", False),
                    settings.value("TimerTOTHText", DEFAULT_TOTH_TIMER_TEXT),
                )
                seconds = getattr(self, seconds_attr)
                self._apply_air_label_text(label_widget, air_num, label_text, seconds)
                
                # Set status and start timer
                setattr(self, status_attr, True)
                timer = getattr(self, timer_attr)
                if air_num == 3 and getattr(self, 'topOfHourActive', False):
                    timer.start(self._milliseconds_until_next_wall_second())
                else:
                    timer.start(1000)
                
                # Log AIR started event
                self.event_logger.log_air_started(air_num, "manual")
                
                # Publish MQTT status immediately after AIR start
                self._publish_mqtt_status(f"air{air_num}")
                
                # Special handling for AIR3 and AIR4 countdown mode
                if 'special_mode' in config:
                    mode_attr = config['special_mode']
                    mode = getattr(self, mode_attr, 0)
                    if mode == 1 and seconds > 1:
                        if not (air_num == 3 and getattr(self, 'topOfHourActive', False)):
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
                self._apply_air_icon_style(
                    air_num,
                    icon_widget,
                    f"color:{inactive_text_color};background-color:{inactive_bg_color}",
                )
            
            # Restore icon immediately after styleSheet change to prevent flickering
            if icon_pixmap and not icon_pixmap.isNull():
                icon_widget.setPixmap(icon_pixmap)
                icon_widget.update()
            
            # Set status and stop timer
            setattr(self, status_attr, False)
            timer = getattr(self, timer_attr)
            timer.stop()
            
            # Log AIR stopped event
            self.event_logger.log_air_stopped(air_num, "manual")
        
        # Publish MQTT status immediately after AIR state change
        self._publish_mqtt_status(f"air{air_num}")

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
                if air_num == 3 and getattr(self, 'topOfHourActive', False):
                    current_seconds = getattr(self, seconds_attr)
                    remaining = self._seconds_until_top_of_hour()
                    # Detect hour boundary: remaining jumps up when the hour is reached
                    if current_seconds > 0 and remaining > current_seconds:
                        remaining = 0
                    setattr(self, seconds_attr, remaining)
                    if remaining < 1:
                        self.topOfHourActive = False
                        self._publish_mqtt_status("air3toh")
                        stop_method = getattr(self, f'stop_air{air_num}')
                        stop_method()
                        setattr(self, mode_attr, 0)
                else:
                    current_seconds = getattr(self, seconds_attr)
                    setattr(self, seconds_attr, current_seconds - 1)
                    if getattr(self, seconds_attr) < 1:
                        if air_num == 3:
                            self.topOfHourActive = False
                            self._publish_mqtt_status("air3toh")
                        stop_method = getattr(self, f'stop_air{air_num}')
                        stop_method()
                        # Reset the correct mode attribute
                        setattr(self, mode_attr, 0)
        else:
            # Simple count up for AIR1 and AIR2
            setattr(self, seconds_attr, getattr(self, seconds_attr) + 1)
        
        # Update label text
        with settings_group(settings, "Timers"):
            label_text = air_timer_caption(
                air_num,
                settings.value(config['label'], config['label_default']),
                getattr(self, "topOfHourActive", False),
                settings.value("TimerTOTHText", DEFAULT_TOTH_TIMER_TEXT),
            )
            seconds = getattr(self, seconds_attr)
            self._apply_air_label_text(label_widget, air_num, label_text, seconds)

        if air_num == 3 and getattr(self, 'topOfHourActive', False) and self.statusAIR3:
            self._align_air3_timer_to_wall_clock()

    def show_settings(self) -> None:
        """
        Show settings dialog window
        
        Restores mouse cursor, ensures AIR icons are set, and displays settings window.
        """
        global app
        # un-hide mouse cursor
        app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
        # Set icons BEFORE opening dialog to prevent flickering
        self._ensure_air_icons_are_set()
        self.settings.show_settings()

    def display_all_hostaddresses(self) -> None:
        """
        Display all local network IP addresses in NOW and NEXT text fields
        
        Retrieves all non-loopback IPv4 and IPv6 addresses from network interfaces
        and displays them in the UI. Starts a timer to replace with configured text
        after 10 seconds if replacenow setting is enabled.
        """
        v4addrs = list()
        v6addrs = list()
        
        # Get all network interfaces
        for interface in QNetworkInterface.allInterfaces():
            # Skip loopback interfaces
            if interface.flags() & QNetworkInterface.InterfaceFlag.IsLoopBack:
                continue
            
            # Get all address entries for this interface
            for entry in interface.addressEntries():
                address = entry.ip()
                addr_str = address.toString()
                
                if host_address_is_ipv4(address):
                    if not address.isLoopback():
                        v4addrs.append(addr_str)
                elif host_address_is_ipv6(address):
                    if not address.isLoopback() and not address.isLinkLocal():
                        v6addrs.append(addr_str)

        self.set_current_song_text(", ".join([str(addr) for addr in v4addrs]))
        self.set_news_text(", ".join([str(addr) for addr in v6addrs]))

        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('replacenow', True, type=bool):
                self.replacenowTimer.setSingleShot(True)
                self.replacenowTimer.start(10000)

    def _parse_cmd_with_source(self, data: bytes, source: str = "udp") -> None:
        """
        Parse and execute a command with source tracking
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            source: Source of command ('udp' or 'http')
        """
        try:
            command_str = data.decode('utf-8') if isinstance(data, bytes) else str(data)
            if ':' in command_str:
                command, value = command_str.split(':', 1)
                # Log command received event with source
                self.event_logger.log_command_received(command, value, source)
        except (UnicodeDecodeError, ValueError, AttributeError):
            pass
        
        # Forward to actual command handler
        self.command_handler.parse_cmd(data if isinstance(data, bytes) else data.encode())
    
    def parse_cmd(self, data: bytes) -> bool:
        """
        Parse and execute a command from UDP/HTTP input
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            
        Returns:
            True if command was parsed successfully, False otherwise
        """
        # Default to unknown source for backward compatibility
        self._parse_cmd_with_source(data, "unknown")
        return True


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
        """Toggle LED visual state only (used by autoflash/timedflash timers).

        Must not call led_logic: that would clear the logical LED{n}on state and
        stop the flash timer. Logical toggles belong in _manual_toggle_led.
        """
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
        
        # Determine source for logging
        source = "manual"
        if state:
            timer = getattr(self, timer_attr)
            autoflash = getattr(self.settings, autoflash_attr)
            timedflash = getattr(self.settings, timedflash_attr)
            
            if autoflash.isChecked() and timer.isActive():
                source = "autoflash"
            elif timedflash.isChecked():
                source = "timedflash"
        
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
        
        # Log LED change event
        self.event_logger.log_led_changed(led, state, source)
        
        # Publish MQTT status immediately after LED change
        self._publish_mqtt_status(f"led{led}")
        
        # Broadcast WebSocket status immediately after LED change
        self._broadcast_web_status()

    def set_station_color(self, newcolor: QColor) -> None:
        """
        Set the station label color
        
        Args:
            newcolor: QColor object for the station name label
        """
        self._set_label_color(self.labelStation, newcolor)

    def set_slogan_color(self, newcolor: QColor) -> None:
        """
        Set the slogan label color
        
        Args:
            newcolor: QColor object for the slogan label
        """
        self._set_label_color(self.labelSlogan, newcolor)

    def _set_label_color(self, widget: QLabel, color: QColor) -> None:
        """
        Generic method to set label color
        
        Args:
            widget: The label widget to set color for
            color: QColor object to set as text color
        """
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.WindowText, color)
        widget.setPalette(palette)

    def restore_settings_from_config(self) -> None:
        """Restore all settings from configuration"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings_restorer = SettingsRestorer(self, self.settings)
        settings_restorer.restore_all(settings)
        # Font/size changes can affect NOW/NEXT metrics — keep warning area height locked
        if hasattr(self, "_lock_bottom_stack_height"):
            self._lock_bottom_stack_height()

    def _lock_bottom_stack_height(self) -> None:
        """
        Fix the bottom NOW/NEXT/Warning area to a constant height.

        Uses the larger of the normal two-line block and a 45pt warning line,
        so switching to warnings does not shift the rest of the layout.
        """
        if not hasattr(self, "bottomStack"):
            return
        from PySide6.QtGui import QFontMetrics, QFont

        normal_height = (
            self.labelCurrentSong.sizeHint().height()
            + self.labelNews.sizeHint().height()
            + 2  # LayoutBottomNormal spacing
        )
        warning_font = QFont(self.labelWarning.font())
        warning_font.setPointSize(45)
        warning_height = QFontMetrics(warning_font).height() + 8
        locked = max(normal_height, warning_height)
        self.bottomStack.setMinimumHeight(locked)
        self.bottomStack.setMaximumHeight(locked)

    def apply_audio_settings(self, settings: QSettings) -> None:
        """Apply Audio group settings to meters, capture, and TooLoud logic."""
        if not hasattr(self, "audio_capture") or self.audio_capture is None:
            return

        with settings_group(settings, "Audio"):
            enabled = settings.value('enabled', DEFAULT_AUDIO_METERS_ENABLED, type=bool)
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
            unit = settings.value('unit', DEFAULT_AUDIO_UNIT, type=str) or DEFAULT_AUDIO_UNIT
            layout_raw = settings.value('layout', None)
            layout, unit = migrate_audio_layout_and_unit(unit, layout_raw)
            tooloud = settings.value('tooloud', DEFAULT_AUDIO_TOOLOUD, type=bool)
            tooloud_text = settings.value('tooloudtext', DEFAULT_AUDIO_TOOLOUD_TEXT, type=str) or DEFAULT_AUDIO_TOOLOUD_TEXT
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

        from audio_capture import normalize_audio_source

        source = normalize_audio_source(source)
        try:
            livewire_channel = int(livewire_channel)
        except (TypeError, ValueError):
            livewire_channel = DEFAULT_AUDIO_LIVEWIRE_CHANNEL
        livewire_iface = livewire_iface or ""
        aes67_id = aes67_id or ""
        aes67_addr = aes67_addr or ""
        aes67_name = aes67_name or ""
        aes67_codec = aes67_codec or DEFAULT_AUDIO_AES67_CODEC
        try:
            aes67_port = int(aes67_port)
        except (TypeError, ValueError):
            aes67_port = DEFAULT_AUDIO_AES67_PORT
        try:
            aes67_rate = int(aes67_rate)
        except (TypeError, ValueError):
            aes67_rate = DEFAULT_AUDIO_AES67_RATE
        try:
            aes67_channels = int(aes67_channels)
        except (TypeError, ValueError):
            aes67_channels = DEFAULT_AUDIO_AES67_CHANNELS

        self._audio_meters_enabled = bool(enabled)
        self._audio_tooloud_enabled = bool(tooloud)
        self._audio_tooloud_text = tooloud_text
        self._audio_tooloud_threshold = float(threshold)
        self._audio_tooloud_action = tooloud_action if tooloud_action in ("warning", "led") else DEFAULT_AUDIO_TOOLOUD_ACTION
        try:
            self._audio_tooloud_led = max(1, min(4, int(tooloud_led)))
        except (TypeError, ValueError):
            self._audio_tooloud_led = DEFAULT_AUDIO_TOOLOUD_LED
        self._audio_silence_enabled = bool(silence)
        self._audio_silence_warn = bool(silence_warn)
        self._audio_silence_on_absent = bool(silence_on_absent)
        self._audio_silence_text = silence_text
        try:
            silence_threshold_value = float(silence_threshold)
        except (TypeError, ValueError):
            silence_threshold_value = DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS
        try:
            silence_duration_value = float(silence_duration)
        except (TypeError, ValueError):
            silence_duration_value = DEFAULT_AUDIO_SILENCE_DURATION_S
        try:
            silence_recovery_value = float(silence_recovery)
        except (TypeError, ValueError):
            silence_recovery_value = DEFAULT_AUDIO_SILENCE_RECOVERY_S
        self._audio_silence_http_url = (silence_http_url or "").strip()
        self._silence_detector.configure(
            threshold_dbfs=silence_threshold_value,
            duration_s=silence_duration_value,
            recovery_s=silence_recovery_value,
        )
        self._audio_lufs_reference = float(lufs_reference)
        self._audio_peak_hold = bool(peak_hold)
        try:
            self._audio_peak_hold_seconds = max(0.1, float(peak_hold_seconds))
        except (TypeError, ValueError):
            self._audio_peak_hold_seconds = DEFAULT_AUDIO_PEAK_HOLD_SECONDS
        if display_style in AUDIO_DISPLAY_STYLE_LABELS:
            self._audio_display_style = display_style
        else:
            self._audio_display_style = DEFAULT_AUDIO_DISPLAY_STYLE
        try:
            self._audio_meter_width = int(meter_width)
        except (TypeError, ValueError):
            self._audio_meter_width = DEFAULT_AUDIO_METER_WIDTH

        self._audio_layout = layout
        try:
            meter_unit = MeterUnit(unit)
        except ValueError:
            meter_unit = MeterUnit.DBTP
        if layout == "both" and meter_unit == MeterUnit.BBC_PPM:
            meter_unit = MeterUnit.DBTP

        if hasattr(self, "audioMeterWidget"):
            self.audioMeterWidget.set_layout(layout)
            self.audioMeterWidget.set_unit(meter_unit)
            self.audioMeterWidget.set_lufs_reference(self._audio_lufs_reference)
            self.audioMeterWidget.set_dbtp_ceiling(
                self._audio_tooloud_threshold if self._audio_tooloud_enabled else None
            )
            self.audioMeterWidget.set_peak_hold(
                self._audio_peak_hold, self._audio_peak_hold_seconds
            )
            self.audioMeterWidget.set_display_style(self._audio_display_style)
            self._apply_audio_meter_width(self._audio_meter_width)
            if self._audio_meters_enabled:
                self._set_audio_meter_visible(True)
            else:
                self._set_audio_meter_visible(False)
                self.audioMeterWidget.clear_levels()

        should_capture = (
            self._audio_meters_enabled
            or self._audio_tooloud_enabled
            or self._audio_silence_enabled
        )
        aes67_without_stream = source == "aes67" and not (aes67_addr or "").strip()
        source_changed = (
            self.audio_capture.source != source
            or self.audio_capture.device_name != device
            or self.audio_capture.livewire_channel != livewire_channel
            or self.audio_capture.livewire_iface != livewire_iface
            or self.audio_capture.aes67_id != aes67_id
            or self.audio_capture.aes67_addr != aes67_addr
            or self.audio_capture.aes67_port != aes67_port
            or self.audio_capture.aes67_codec != aes67_codec
            or self.audio_capture.aes67_rate != aes67_rate
            or self.audio_capture.aes67_channels != aes67_channels
        )
        capture_kwargs = dict(
            device_name=device,
            unit=meter_unit,
            source=source,
            livewire_channel=livewire_channel,
            livewire_iface=livewire_iface,
            aes67_id=aes67_id,
            aes67_addr=aes67_addr,
            aes67_port=aes67_port,
            aes67_name=aes67_name,
            aes67_codec=aes67_codec,
            aes67_rate=aes67_rate,
            aes67_channels=aes67_channels,
            layout=layout,
            true_peak_needed=self._audio_tooloud_enabled,
        )
        if should_capture and not aes67_without_stream:
            self.audio_capture.configure(**capture_kwargs)
            if (not self.audio_capture.is_running) or source_changed:
                self.audio_capture.start()
            else:
                self.audio_capture.set_unit(meter_unit)
                self.audio_capture.set_layout(layout)
                self.audio_capture.set_true_peak_needed(self._audio_tooloud_enabled)
            if not self.audio_capture.is_running:
                self._reset_audio_meter_display()
        else:
            self.audio_capture.configure(**capture_kwargs)
            self.audio_capture.stop()
            self._reset_audio_meter_display()

        self._sync_silence_after_settings()
        self.poll_silence_absent()

    def _set_audio_meter_visible(self, visible: bool) -> None:
        """Show/hide the meter column (widget + gap before the left LEDs)."""
        column = getattr(self, "audioMeterColumn", None)
        if column is not None:
            column.setVisible(visible)
        elif hasattr(self, "audioMeterWidget"):
            self.audioMeterWidget.setVisible(visible)

    def _reset_audio_meter_display(self) -> None:
        """Drop frozen levels when capture is not running."""
        if hasattr(self, "audioMeterWidget"):
            self.audioMeterWidget.clear_levels()
        self._clear_tooloud_warning(force=True)
        capture_running = bool(getattr(self, "audio_capture", None) and self.audio_capture.is_running)
        if self._audio_silence_enabled and self._audio_silence_on_absent and not capture_running:
            return
        self._clear_silence_warning(force=True)

    def _apply_audio_meter_width(self, width: int) -> None:
        """Apply meter width so L/R bars grow and the column follows."""
        if not hasattr(self, "audioMeterWidget"):
            return
        from audiometer_widget import METER_LED_GAP_PX

        self.audioMeterWidget.set_meter_width(width)
        self._audio_meter_width = self.audioMeterWidget.meter_width
        column = getattr(self, "audioMeterColumn", None)
        if column is not None:
            column_width = self._audio_meter_width + METER_LED_GAP_PX
            column.setFixedWidth(column_width)
            column.setMinimumWidth(column_width)
            column.setMaximumWidth(column_width)

    def _on_audio_capture_error(self, message: str) -> None:
        logger.error("Audio capture error: %s", message)

    def _on_audio_levels(self, readings: MeterReadings) -> None:
        """Handle meter levels from the capture worker."""
        if self._audio_meters_enabled and hasattr(self, "audioMeterWidget"):
            self.audioMeterWidget.set_levels(readings)

        self._process_tooloud_level(readings.max_true_peak_dbtp)
        self._process_silence_level(readings.max_sample_peak_dbfs)

    def start_integrated_loudness(self) -> None:
        """Reset and start gated I + LRA measurement."""
        if getattr(self, "audio_capture", None) is not None:
            self.audio_capture.start_integrated()
        self._publish_mqtt_status("lufs")
        self._broadcast_web_status()

    def stop_integrated_loudness(self) -> None:
        """Stop gated I + LRA; freeze the last values on the meter."""
        if getattr(self, "audio_capture", None) is not None:
            self.audio_capture.stop_integrated()
        self._publish_mqtt_status("lufs")
        self._broadcast_web_status()

    def toggle_integrated_loudness(self) -> None:
        """Start or stop the I/LRA session."""
        if getattr(self, "audio_capture", None) is not None:
            self.audio_capture.toggle_integrated()
        self._publish_mqtt_status("lufs")
        self._broadcast_web_status()

    def reset_integrated_loudness(self) -> None:
        """Restart a running I+LRA session, or hide frozen I/LRA when stopped."""
        if getattr(self, "audio_capture", None) is not None:
            self.audio_capture.reset_integrated()
        if hasattr(self, "audioMeterWidget"):
            self.audioMeterWidget.clear_integrated_markers()
        self._publish_mqtt_status("lufs")
        self._broadcast_web_status()

    def _process_tooloud_level(self, true_peak_dbtp: float) -> None:
        """Update TooLoud warning/LED from a true-peak reading."""
        if not self._audio_tooloud_enabled:
            self._clear_tooloud_warning(force=True)
            return

        if true_peak_dbtp >= self._audio_tooloud_threshold:
            was_active = self._audio_tooloud_active
            self._audio_tooloud_active = True
            self._audio_tooloud_clear_timer.invalidate()
            if not was_active:
                self._apply_tooloud_active(True)
        else:
            if self._audio_tooloud_active:
                if not self._audio_tooloud_clear_timer.isValid():
                    self._audio_tooloud_clear_timer.start()
                elif self._audio_tooloud_clear_timer.elapsed() >= TOOLOUD_CLEAR_HOLD_MS:
                    self._clear_tooloud_warning(force=True)

    def poll_silence_absent(self) -> None:
        """Feed floor level when capture is absent, or clear if that option is off."""
        if not self._audio_silence_enabled:
            return
        capture = getattr(self, "audio_capture", None)
        if capture is not None and capture.is_running:
            return
        if self._audio_silence_on_absent:
            self._process_silence_level(SILENCE_FLOOR_DBFS)
        elif self._audio_silence_active:
            self._clear_silence_warning(force=True)

    def _process_silence_level(self, level_dbfs: float) -> None:
        """Update silence alarm from a sample-peak dBFS reading."""
        if not self._audio_silence_enabled:
            if self._audio_silence_active:
                self._clear_silence_warning(force=True)
            return
        changed, active = self._silence_detector.process(level_dbfs, time.monotonic())
        if changed:
            self._apply_silence_active(active)

    def _sync_silence_after_settings(self) -> None:
        """Apply enable/warn/absent changes without re-triggering HTTP GET."""
        if not self._audio_silence_enabled:
            self._clear_silence_warning(force=True)
            return
        capture_running = bool(getattr(self, "audio_capture", None) and self.audio_capture.is_running)
        if not capture_running and not self._audio_silence_on_absent:
            self._clear_silence_warning(force=True)
            return
        self._sync_silence_warning()

    def _sync_silence_warning(self) -> None:
        """Show or hide the OAS WARN text for the current silence alarm."""
        try:
            warning_manager = getattr(self, "warning_manager", None)
        except (AttributeError, RuntimeError):
            return
        if not warning_manager:
            return
        should_show = (
            self._audio_silence_enabled
            and self._audio_silence_warn
            and self._audio_silence_active
        )
        if should_show:
            warning_manager.add_warning(self._audio_silence_text, SILENCE_WARNING_PRIORITY)
            self._audio_silence_warn_shown = True
        elif getattr(self, "_audio_silence_warn_shown", False):
            warning_manager.remove_warning(SILENCE_WARNING_PRIORITY)
            self._audio_silence_warn_shown = False

    def _apply_silence_active(self, active: bool) -> None:
        """Latch silence alarm, optional WARN, MQTT/WS, and HTTP GET on rising edge."""
        rising = active and not self._audio_silence_active
        self._audio_silence_active = active
        self._sync_silence_warning()
        self._publish_mqtt_status("silence")
        self._broadcast_web_status()
        if rising:
            self._trigger_silence_http_get()

    def _clear_silence_warning(self, force: bool = False) -> None:
        """Clear the silence alarm if active."""
        if not self._audio_silence_active and not force:
            return
        was_active = self._audio_silence_active
        self._silence_detector.reset()
        if was_active:
            self._apply_silence_active(False)
        else:
            self._audio_silence_active = False
            self._sync_silence_warning()

    def _trigger_silence_http_get(self) -> None:
        """Fire-and-forget HTTP GET when silence becomes active."""
        url = (self._audio_silence_http_url or "").strip()
        if not url:
            return
        parsed = QUrl(url)
        if not parsed.isValid() or parsed.scheme() not in ("http", "https"):
            logger.warning("Invalid silence HTTP GET URL: %s", url)
            return
        if self._silence_nam is None:
            self._silence_nam = QNetworkAccessManager(self)
            self._silence_nam.finished.connect(self._on_silence_http_finished)
        request = QNetworkRequest(parsed)
        self._silence_nam.get(request)

    def _on_silence_http_finished(self, reply: QNetworkReply) -> None:
        """Log HTTP GET failures without blocking the UI."""
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                logger.warning("Silence HTTP GET failed: %s", reply.errorString())
        finally:
            reply.deleteLater()

    def _apply_tooloud_active(self, active: bool) -> None:
        """Apply TooLoud action (warning message or LED)."""
        if self._audio_tooloud_action == "led":
            # Clear any previous warning text when using LED mode
            if hasattr(self, "warning_manager") and self.warning_manager:
                self.warning_manager.remove_warning(TOOLOUD_WARNING_PRIORITY)
            led_num = self._audio_tooloud_led
            if active:
                getattr(self, f"set_led{led_num}")(True)
                self._audio_tooloud_led_lit = True
                self._publish_mqtt_status(f"led{led_num}")
            elif self._audio_tooloud_led_lit:
                getattr(self, f"set_led{led_num}")(False)
                self._audio_tooloud_led_lit = False
                self._publish_mqtt_status(f"led{led_num}")
            return

        # Warning mode
        if self._audio_tooloud_led_lit:
            getattr(self, f"set_led{self._audio_tooloud_led}")(False)
            self._audio_tooloud_led_lit = False
        if hasattr(self, "warning_manager") and self.warning_manager:
            if active:
                self.warning_manager.add_warning(self._audio_tooloud_text, TOOLOUD_WARNING_PRIORITY)
            else:
                self.warning_manager.remove_warning(TOOLOUD_WARNING_PRIORITY)

    def _clear_tooloud_warning(self, force: bool = False) -> None:
        """Clear the TooLoud warning/LED if active."""
        if not self._audio_tooloud_active and not force:
            return
        self._audio_tooloud_active = False
        self._audio_tooloud_clear_timer.invalidate()
        self._apply_tooloud_active(False)

    def constant_update(self):
        """Slot for constant timer timeout - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.constant_update()
        except (AttributeError, RuntimeError):
            # Fallback if ui_updater not yet initialized
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.constant_update()

    def update_date(self):
        """Update the date display - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.update_date()
        except (AttributeError, RuntimeError):
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.update_date()

    def update_backtiming_text(self) -> None:
        """Update the text clock display - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.update_backtiming_text()
        except (AttributeError, RuntimeError):
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.update_backtiming_text()

    def update_backtiming_seconds(self):
        """Update backtiming seconds - delegates to UI updater"""
        try:
            if self.ui_updater:
                self.ui_updater.update_backtiming_seconds()
        except (AttributeError, RuntimeError):
            from ui_updater import UIUpdater
            self.ui_updater = UIUpdater(self)
            self.ui_updater.update_backtiming_seconds()

    def update_ntp_status(self):
        """Update time-source / NTP warning (priority -1)."""
        time_source = self.__dict__.get("time_source_manager")
        if time_source is not None:
            time_source.update_status()
            return
        try:
            if self.ntp_manager:
                self.ntp_manager.update_ntp_status()
        except (AttributeError, RuntimeError):
            from ntp_manager import NTPManager
            self.ntp_manager = NTPManager(self)
            self.ntp_manager.update_ntp_status()

    def _save_window_geometry(self) -> None:
        """Persist windowed position and size. Skip while fullscreen."""
        if self.isFullScreen():
            return
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Window"):
            settings.setValue("geometry", self.saveGeometry())
        settings.sync()

    def _restore_window_geometry(self) -> None:
        """Restore last windowed position and size, if one was saved."""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Window"):
            geometry = settings.value("geometry", QByteArray())
        if isinstance(geometry, QByteArray):
            if geometry.isEmpty():
                return
        elif not geometry:
            return
        else:
            geometry = QByteArray(geometry)
        self.restoreGeometry(geometry)

    def toggle_full_screen(self):
        global app
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if not settings.value('fullscreen', True, type=bool):
                self._save_window_geometry()
                self.showFullScreen()
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
                settings.setValue('fullscreen', True)
            else:
                self.showNormal()
                self._restore_window_geometry()
                app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
                settings.setValue('fullscreen', False)

    def _make_children_click_through(self) -> None:
        """Let double-click and right-click reach MainScreen through child widgets."""
        # Do not use a Python eventFilter: ChildAdded and QApplication filters
        # segfault in Qt/PySide when wrapping half-built or internal objects.
        for child in self.findChildren(QWidget):
            if isinstance(child, QMenu):
                continue
            if child.windowFlags() & Qt.WindowType.Popup:
                continue
            if child.objectName() in MainScreen.CLICKABLE_CHILD_NAMES:
                continue
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def _install_toggle_clicks(self) -> None:
        """Bind left-click toggle on status LEDs and AIR timer frames."""
        bindings = (
            ("buttonLED1", self.manual_toggle_led1),
            ("buttonLED2", self.manual_toggle_led2),
            ("buttonLED3", self.manual_toggle_led3),
            ("buttonLED4", self.manual_toggle_led4),
            ("AirLED_1", self.toggle_air1),
            ("AirLED_2", self.toggle_air2),
            ("AirLED_3", self.radio_timer_start_stop),
            ("AirLED_4", self.toggle_air4),
        )
        for name, callback in bindings:
            widget = getattr(self, name, None)
            if widget is None:
                continue
            self._bind_left_click_toggle(widget, callback)

    def _bind_left_click_toggle(self, widget: QWidget, callback) -> None:
        """Toggle on left-click; keep right-click menu; do not toggle fullscreen."""
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        def mouse_press(event: QMouseEvent, cb=callback) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                cb()
                event.accept()
                return
            event.ignore()

        def mouse_double_click(event: QMouseEvent) -> None:
            # Consume so MainScreen does not toggle fullscreen.
            event.accept()

        def context_menu(event: QContextMenuEvent) -> None:
            self._show_main_context_menu(event.globalPos())
            event.accept()

        widget.mousePressEvent = mouse_press
        widget.mouseDoubleClickEvent = mouse_double_click
        widget.contextMenuEvent = context_menu

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Toggle windowed/fullscreen mode on left double-click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_full_screen()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show the main screen context menu on right-click."""
        self._show_main_context_menu(event.globalPos())
        event.accept()

    def _show_main_context_menu(self, global_pos: QPoint) -> None:
        """Show context menu with fullscreen toggle, settings, and quit."""
        global app
        menu = QMenu(self)
        toggle_action = menu.addAction("Toggle Fullscreen")
        settings_action = menu.addAction("Settings")
        start_lufs_action = None
        stop_lufs_action = None
        reset_lufs_action = None
        if getattr(self, "_audio_meters_enabled", False):
            menu.addSeparator()
            start_lufs_action = menu.addAction("Start I+LRA")
            stop_lufs_action = menu.addAction("Stop I+LRA")
            reset_lufs_action = menu.addAction("Reset I+LRA")
        menu.addSeparator()
        quit_action = menu.addAction("Quit OnAirScreen")

        # Make the cursor visible while the menu is open (hidden in fullscreen).
        app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
        try:
            chosen = menu.exec(global_pos)
        finally:
            app.restoreOverrideCursor()

        if chosen == toggle_action:
            self.toggle_full_screen()
        elif chosen == settings_action:
            self.show_settings()
        elif start_lufs_action is not None and chosen == start_lufs_action:
            self.start_integrated_loudness()
        elif stop_lufs_action is not None and chosen == stop_lufs_action:
            self.stop_integrated_loudness()
        elif reset_lufs_action is not None and chosen == reset_lufs_action:
            self.reset_integrated_loudness()
        elif chosen == quit_action:
            self.quit_oas()

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
            
            text_key = f'TimerAIR{air_num}Text'
            
            timer = getattr(self, timer_attr)
            timer.stop()
            setattr(self, seconds_attr, 0)
            if air_num == 3:
                self.radioTimerMode = 0
            elif air_num == 4:
                self.streamTimerMode = 0
            
            configured = settings.value(text_key, DEFAULT_TIMER_AIR_TEXTS.get(air_num, f'AIR{air_num}'))
            toth_text = settings.value("TimerTOTHText", DEFAULT_TOTH_TIMER_TEXT)
            label_text = air_timer_caption(
                air_num, configured, getattr(self, "topOfHourActive", False), toth_text
            )
            label_widget = getattr(self, label_attr)
            seconds = getattr(self, seconds_attr)
            self._apply_air_label_text(label_widget, air_num, label_text, seconds)
            
            # Log AIR reset event
            self.event_logger.log_air_reset(air_num, "manual")
            
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

    def replace_now_next(self) -> None:
        """
        Replace NOW and NEXT text fields with configured replacement text
        
        Called by timer after displaying IP addresses. Replaces NOW field with
        configured replacement text and clears NEXT field.
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            self.set_current_song_text(settings.value('replacenowtext', DEFAULT_REPLACE_NOW_TEXT))
            self.set_news_text("")

    def trigger_ntp_check(self) -> None:
        """
        Trigger NTP offset check
        
        Checks if NTP checking is enabled and triggers NTP offset check.
        """
        try:
            if self.ntp_manager:
                self.ntp_manager.trigger_ntp_check()
        except (AttributeError, RuntimeError):
            # Fallback if ntp_manager not yet initialized
            from ntp_manager import NTPManager
            self.ntp_manager = NTPManager(self)
            self.ntp_manager.trigger_ntp_check()

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
                active_text_color = settings.value('activetextcolor', DEFAULT_LED_ACTIVE_TEXT_COLOR)
                active_bg_color = settings.value('activebgcolor', default_active_colors[led_num])
                button_widget.setStyleSheet(f"color:{active_text_color};background-color:{active_bg_color}")
            setattr(self, status_attr, True)
        else:
            with settings_group(settings, "LEDS"):
                inactive_text_color = settings.value('inactivetextcolor', DEFAULT_LED_INACTIVE_TEXT_COLOR)
                inactive_bg_color = settings.value('inactivebgcolor', DEFAULT_LED_INACTIVE_BG_COLOR)
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
        # Publish MQTT status immediately after NOW text change
        self._publish_mqtt_status("now")

    def set_news_text(self, text: str) -> None:
        """Set news text"""
        self._set_text('labelNews', text)
        # Publish MQTT status immediately after NEXT text change
        self._publish_mqtt_status("next")

    def _publish_mqtt_status(self, specific_item: str | None = None) -> None:
        """
        Publish status immediately after a status change (MQTT and OSC).

        Args:
            specific_item: Optional specific item to publish (e.g., 'led1', 'air2', 'now', 'next', 'warn')
                          If None, publishes all status items
        """
        try:
            mqtt_client = getattr(self, 'mqtt_client', None)
            if mqtt_client:
                try:
                    mqtt_client.publish_status(specific_item)
                except Exception as e:
                    logger.warning(f"Failed to publish MQTT status: {e}")
        except (RuntimeError, AttributeError) as e:
            # Ignore errors when object is not fully initialized (e.g., in tests)
            # Log but don't raise - this is expected in test scenarios
            error = WidgetAccessError(
                f"Error accessing MQTT client (object may not be initialized): {e}",
                widget_name="mqtt_client",
                attribute="publish_status"
            )
            log_exception(logger, error, use_exc_info=False)
            pass

        try:
            osc_daemon = getattr(self, 'osc_daemon', None)
            if osc_daemon:
                try:
                    osc_daemon.publish_status(specific_item)
                except Exception as e:
                    logger.warning(f"Failed to publish OSC status: {e}")
        except (RuntimeError, AttributeError) as e:
            error = WidgetAccessError(
                f"Error accessing OSC daemon (object may not be initialized): {e}",
                widget_name="osc_daemon",
                attribute="publish_status"
            )
            log_exception(logger, error, use_exc_info=False)
    
    def _broadcast_web_status(self) -> None:
        """
        Broadcast WebSocket status immediately after status change
        
        Triggers immediate status update to all connected WebSocket clients
        instead of waiting for the periodic broadcast.
        """
        try:
            wsd = getattr(self, 'wsd', None)
            if wsd:
                try:
                    wsd.broadcast_status()
                except Exception as e:
                    logger.warning(f"Failed to broadcast WebSocket status: {e}")
        except (RuntimeError, AttributeError) as e:
            # Ignore errors when object is not fully initialized (e.g., in tests)
            # Log but don't raise - this is expected in test scenarios
            error = WidgetAccessError(
                f"Error accessing WebSocket daemon (object may not be initialized): {e}",
                widget_name="wsd",
                attribute="broadcast_status"
            )
            log_exception(logger, error, use_exc_info=False)
            pass

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

    def set_backtiming_secs(self, value: int) -> None:
        """
        Set backtiming seconds (currently not implemented)
        
        Args:
            value: Seconds value (not currently used)
        """
        pass
        # self.labelSeconds.setText( str(value) )

    def add_warning(self, text: str, priority: int = 0) -> None:
        """
        Add a warning message to the warning system
        
        Args:
            text: Warning message text
            priority: Warning priority level (-1=NTP, 0=normal/legacy, 1=medium, 2=high, default: 0)
        """
        self.warning_manager.add_warning(text, priority)

    def remove_warning(self, priority: int = 0) -> None:
        """
        Remove warning message from the warning system
        
        Args:
            priority: Warning priority level (-1=NTP, 0=normal/legacy, 1=medium, 2=high, default: 0)
        """
        self.warning_manager.remove_warning(priority)

    def process_warnings(self) -> None:
        """
        Process all warnings and display the highest priority warning
        
        Checks all warning priority levels and displays the highest priority
        warning found (excluding NTP warnings if other warnings exist),
        or hides the warning label if no warnings are present.
        
        Priority order: 2 (high) > 1 (medium) > 0 (normal) > -1 (NTP)
        NTP warnings are only shown if no other warnings exist.
        """
        self.warning_manager.process_warnings()

    def show_warning(self, text: str) -> None:
        """
        Show warning message in the UI
        
        Hides current song and news labels and displays warning text with large font.
        
        Args:
            text: Warning message text to display
        """
        self.warning_manager.show_warning(text)

    def hide_warning(self, priority: int = 0) -> None:
        """
        Hide warning message and restore normal UI
        
        Args:
            priority: Warning priority level (0-2, default: 0, currently unused)
        """
        self.warning_manager.hide_warning(priority)

    def config_closed(self) -> None:
        """
        Handle settings window closed event
        
        Restores mouse cursor state and ensures AIR icons are set correctly.
        """
        global app
        # hide mouse cursor if in fullscreen mode
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "General"):
            if settings.value('fullscreen', True, type=bool):
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
        # Ensure icons are still set after dialog is closed
        self._ensure_air_icons_are_set()

    def config_finished(self) -> None:
        """
        Handle settings applied event
        
        Restores settings from configuration, updates weather widget config,
        and triggers weather update.
        """
        if getattr(self, "_is_quitting", False):
            return
        # IMPORTANT: Check command-line log level FIRST, before restoring settings
        # Command-line log level ALWAYS overrides settings and must not be changed
        import sys as sys_module
        
        # If command-line log level is set, use it and ignore settings completely
        # This check MUST happen BEFORE restoring settings to prevent settings from overriding
        command_line_log_level = get_command_line_log_level()
        if command_line_log_level is not None:
            # Command-line log level always overrides settings - do not change it
            log_level = command_line_log_level
            set_log_level(log_level)
            # Always print log level change, regardless of current log level
            print(f"Log level (from command-line, ignoring settings): {log_level}", file=sys_module.stderr)
            # Restore other settings (but keep command-line log level - do NOT read log level from settings)
            self.restore_settings_from_config()
            self.weatherWidget.readConfig()
            self.weatherWidget.updateWeather()
            # Note: We do NOT read or apply log level from settings when command-line level is set
        else:
            # No command-line level set, restore all settings including log level
            self.restore_settings_from_config()
            self.weatherWidget.readConfig()
            self.weatherWidget.updateWeather()
            
            # Apply log level from settings
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "General"):
                log_level = settings.value('loglevel', DEFAULT_LOG_LEVEL, type=str)
            set_log_level(log_level)
            # Always print log level change, regardless of current log level
            print(f"Log level updated to: {log_level}", file=sys_module.stderr)
        
        if hasattr(self, 'time_source_manager') and self.time_source_manager:
            self.time_source_manager.apply_settings()
        
        # Restart MQTT only when MQTT-related settings changed (handled inside restart())
        if hasattr(self, 'mqtt_client') and self.mqtt_client:
            self.mqtt_client.restart()

        # Restart OSC only when OSC-related settings changed (handled inside restart())
        if hasattr(self, 'osc_daemon') and self.osc_daemon:
            self.osc_daemon.restart()

        if hasattr(self, 'gpio_manager') and self.gpio_manager:
            self.gpio_manager.restart()

        # Re-apply after Apply: settings may recreate main-screen children.
        self._make_children_click_through()
        self._install_toggle_clicks()

    def reboot_host(self):
        """Reboot the host system safely using subprocess"""
        self.system_operations.reboot_host()

    def shutdown_host(self):
        """Shutdown the host system safely using subprocess"""
        self.system_operations.shutdown_host()

    def get_status_json(self) -> dict:
        """
        Get current status as JSON-serializable dictionary
        
        Returns:
            Dictionary containing current LED, AIR timer status, and text fields
        """
        try:
            if self.status_exporter:
                return self.status_exporter.get_status_json()
        except (AttributeError, RuntimeError):
            # Fallback if status_exporter not yet initialized
            from status_exporter import StatusExporter
            self.status_exporter = StatusExporter(self)
            return self.status_exporter.get_status_json()
    
    
    def closeEvent(self, event):
        """Handle window close event"""
        self._save_window_geometry()
        if not getattr(self, "_is_quitting", False):
            logger.info("Quitting, cleaning up...")
            if hasattr(self, "event_logger") and self.event_logger:
                self.event_logger.log_system_event("Application quit")
            self._is_quitting = True
            self._stop_background_services()
        event.accept()


###################################
# App Init
###################################
if __name__ == "__main__":
    setup_signal_handlers()
    try:
        log_dir = ensure_log_directory()
    except OSError as error:
        print(f"Could not create log directory: {error}", file=sys.stderr)
        log_dir = None
    install_crash_hooks(log_dir)
    
    # Parse command-line arguments before QApplication initialization
    parser = argparse.ArgumentParser(description='OnAirScreen')
    parser.add_argument('-l', '--loglevel', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set log level (overrides settings, but does not save)')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    install_qt_message_handler()
    
    # Initialize logging: load from settings first, then override with command-line if provided
    settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
    with settings_group(settings, "General"):
        log_level = settings.value('loglevel', DEFAULT_LOG_LEVEL, type=str)
    
    # Command-line argument overrides settings (temporarily, not saved)
    if args.loglevel:
        # Set module-level variable to remember command-line log level (for settings dialog)
        set_command_line_log_level(args.loglevel)
        log_level = args.loglevel
    else:
        # Clear command-line log level
        set_command_line_log_level(None)
    
    # Configure logging with determined level
    set_log_level(log_level)
    if log_dir is not None:
        setup_file_logging(log_dir)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Always print log level change, regardless of current log level
    print(f"Log level set to: {log_level}", file=sys.stderr)
    if log_dir is not None:
        print(f"Log folder: {log_dir}", file=sys.stderr)
    
    # Load fonts from fonts/ directory before creating UI
    load_fonts()
    # Warm the font database so the first Fonts-tab open is not a full system scan
    available_font_families()
    app.setFont(QFont(DEFAULT_FONT_NAME))
    
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
        main_screen._set_air_state(i, False)

    main_screen.show()
    maybe_show_crash_notice(main_screen)

    sys.exit(app.exec())
