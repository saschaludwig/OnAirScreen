#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# status_exporter.py
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

"""
Status Exporter for OnAirScreen

This module handles exporting the current application status as JSON.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings

from exceptions import WidgetAccessError, log_exception
from settings_functions import versionString, distributionString
from utils import settings_group

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
            status_attr = f'statusLED{led_num}'
            with settings_group(settings, f"LED{led_num}"):
                led_text = settings.value('text', f'LED{led_num}')
            leds[led_num] = {
                'status': getattr(self.main_screen, status_attr, False),
                'text': led_text
            }
        
        # Get AIR timer status
        air = {}
        for air_num in range(1, 5):
            status_attr = f'statusAIR{air_num}'
            seconds_attr = f'Air{air_num}Seconds'
            with settings_group(settings, "Timers"):
                air_text = settings.value(f'TimerAIR{air_num}Text', f'AIR{air_num}')
            air[air_num] = {
                'status': getattr(self.main_screen, status_attr, False),
                'seconds': getattr(self.main_screen, seconds_attr, 0),
                'text': air_text
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
        
        return {
            'leds': leds,
            'air': air,
            'texts': {
                'now': now_text,
                'next': next_text,
                'warn': warn_text  # Keep for backward compatibility
            },
            'warnings': warnings,  # New: all warnings with priorities
            'version': versionString,
            'distribution': distributionString
        }

