#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# status_exporter.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Status Exporter for OnAirScreen

This module handles exporting the current application status as JSON.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings

from exceptions import WidgetAccessError, log_exception
from settings_functions import versionString, distributionString
from utils import settings_group, normalize_instance_name
from defaults import DEFAULT_INSTANCE_NAME, DEFAULT_TOTH_TIMER_TEXT, air_timer_caption
from meter_engine import LUFS_SILENCE

# Same floor as the desktop meter ticks: values at silence are not displayable.
_LOUDNESS_DISPLAY_FLOOR = LUFS_SILENCE + 1.0


def json_loudness(value: float) -> float | None:
    """Round a LUFS reading to one decimal, or None when still at the silence floor."""
    if value <= _LOUDNESS_DISPLAY_FLOOR:
        return None
    return round(float(value), 1)


def json_lra(low: float, high: float) -> float | None:
    """EBU LRA in LU (P95−P10), or None when the span is not yet valid."""
    if high <= _LOUDNESS_DISPLAY_FLOOR or low <= _LOUDNESS_DISPLAY_FLOOR:
        return None
    return round(float(high) - float(low), 1)


def loudness_payload(value: float | None) -> str:
    """MQTT/OSC string for a JSON loudness field (`""` when unknown)."""
    if value is None:
        return ""
    return f"{float(value):.1f}"

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)


class StatusExporter:
    """
    Exports current application status as JSON-serializable dictionary
    
    This class collects status information from various components
    and formats it for API responses.
    """
    
    def __init__(self, main_screen: "MainScreen"):
        """
        Initialize status exporter
        
        Args:
            main_screen: Reference to MainScreen instance
        """
        self.main_screen = main_screen

    def _is_led_setting_checked(self, led_num: int, setting_suffix: str) -> bool:
        """Return True if LED{n}{suffix} checkbox (e.g. Autoflash/Timedflash) is checked."""
        try:
            settings = getattr(self.main_screen, 'settings', None)
            if not settings:
                return False
            widget_attr = f'LED{led_num}{setting_suffix}'
            if not hasattr(settings, widget_attr):
                return False
            return bool(getattr(settings, widget_attr).isChecked())
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not access {setting_suffix} status for LED{led_num}: {e}")
            return False
    
    def get_status_json(self) -> dict:
        """
        Get current status as JSON-serializable dictionary
        
        Returns:
            Dictionary containing current LED, AIR timer status, and text fields
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        
        # Get LED status
        leds = {}
        for led_num in range(1, 5):
            # IMPORTANT: Use LED{num}on for logical status, not statusLED{num}
            # statusLED{num} reflects the visual blinking state (changes between True/False)
            # LED{num}on reflects the logical state (True if LED is on, even if blinking)
            led_on_attr = f'LED{led_num}on'
            with settings_group(settings, f"LED{led_num}"):
                led_text = settings.value('text', f'LED{led_num}')
            
            # Get logical LED status (True if LED is on, regardless of blinking state)
            led_status = getattr(self.main_screen, led_on_attr, False)
            
            # Get flash settings (web UI blinks locally when either is enabled)
            autoflash_enabled = self._is_led_setting_checked(led_num, 'Autoflash')
            timedflash_enabled = self._is_led_setting_checked(led_num, 'Timedflash')
            
            leds[led_num] = {
                'status': led_status,  # Use logical status (LED{num}on), not visual status (statusLED{num})
                'text': led_text,
                'autoflash': autoflash_enabled,
                'timedflash': timedflash_enabled,
            }
        
        # Get AIR timer status
        air = {}
        for air_num in range(1, 5):
            status_attr = f'statusAIR{air_num}'
            seconds_attr = f'Air{air_num}Seconds'
            with settings_group(settings, "Timers"):
                air_text = settings.value(f'TimerAIR{air_num}Text', f'AIR{air_num}')
                toth_text = settings.value('TimerTOTHText', DEFAULT_TOTH_TIMER_TEXT)
            top_of_hour = False
            count_down = False
            if air_num == 3:
                try:
                    top_of_hour = bool(getattr(self.main_screen, 'topOfHourActive', False))
                except RuntimeError:
                    # Uninitialized Qt object (e.g. in unit tests)
                    top_of_hour = False
                try:
                    count_down = int(getattr(self.main_screen, 'radioTimerMode', 0) or 0) == 1
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    count_down = False
            elif air_num == 4:
                try:
                    count_down = int(getattr(self.main_screen, 'streamTimerMode', 0) or 0) == 1
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    count_down = False
            air[air_num] = {
                'status': getattr(self.main_screen, status_attr, False),
                'seconds': getattr(self.main_screen, seconds_attr, 0),
                'text': air_timer_caption(air_num, air_text, top_of_hour, toth_text),
                'topOfHour': top_of_hour,
                'countDown': count_down,
            }
        
        # Get text field values
        now_text = ""
        next_text = ""
        warn_text = ""
        
        if hasattr(self.main_screen, 'labelCurrentSong') and self.main_screen.labelCurrentSong:
            try:
                now_text = self.main_screen.labelCurrentSong.text() or ""
            except (AttributeError, RuntimeError) as e:
                error = WidgetAccessError(
                    f"Error accessing labelCurrentSong.text(): {e}",
                    widget_name="labelCurrentSong",
                    attribute="text"
                )
                log_exception(logger, error, use_exc_info=False)
                now_text = ""
        if hasattr(self.main_screen, 'labelNews') and self.main_screen.labelNews:
            try:
                next_text = self.main_screen.labelNews.text() or ""
            except (AttributeError, RuntimeError) as e:
                error = WidgetAccessError(
                    f"Error accessing labelNews.text(): {e}",
                    widget_name="labelNews",
                    attribute="text"
                )
                log_exception(logger, error, use_exc_info=False)
                next_text = ""
        if hasattr(self.main_screen, 'labelWarning') and self.main_screen.labelWarning:
            try:
                warn_text = self.main_screen.labelWarning.text() or ""
            except (AttributeError, RuntimeError) as e:
                error = WidgetAccessError(
                    f"Error accessing labelWarning.text(): {e}",
                    widget_name="labelWarning",
                    attribute="text"
                )
                log_exception(logger, error, use_exc_info=False)
                warn_text = ""
        
        # Get all warnings with priorities
        warnings = []
        try:
            if hasattr(self.main_screen, 'warning_manager') and self.main_screen.warning_manager:
                warnings = self.main_screen.warning_manager.get_warnings()
        except (AttributeError, RuntimeError) as e:
            # If warning_manager doesn't exist or can't be accessed, use empty list
            error = WidgetAccessError(
                f"Error accessing warning_manager: {e}",
                widget_name="MainScreen",
                attribute="warning_manager"
            )
            log_exception(logger, error, use_exc_info=False)
            pass

        silence_active = False
        try:
            silence_active = bool(getattr(self.main_screen, '_audio_silence_active', False))
        except (AttributeError, RuntimeError):
            silence_active = False

        lufs_integrated = False
        lufs_i = None
        lra = None
        try:
            capture = getattr(self.main_screen, 'audio_capture', None)
            snapshot = getattr(capture, 'integrated_snapshot', None) if capture is not None else None
            if callable(snapshot):
                running, i_value, lra_low, lra_high = snapshot()
                lufs_integrated = running is True
                lufs_i = json_loudness(i_value)
                lra = json_lra(lra_low, lra_high)
            else:
                running = getattr(capture, 'integrated_running', False) if capture is not None else False
                lufs_integrated = running is True
        except (AttributeError, RuntimeError, TypeError, ValueError):
            lufs_integrated = False
            lufs_i = None
            lra = None

        with settings_group(settings, "General"):
            instance_name = normalize_instance_name(
                settings.value('instancename', DEFAULT_INSTANCE_NAME)
            )

        return {
            'leds': leds,
            'air': air,
            'texts': {
                'now': now_text,
                'next': next_text,
                'warn': warn_text  # Keep for backward compatibility
            },
            'warnings': warnings,  # New: all warnings with priorities
            'silence': silence_active,
            'lufsIntegrated': lufs_integrated,
            'lufsI': lufs_i,
            'lra': lra,
            'version': versionString,
            'distribution': distributionString,
            'instance': instance_name,
        }

