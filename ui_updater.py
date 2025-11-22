#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# ui_updater.py
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
UI Updater for OnAirScreen

This module handles periodic UI updates like date, time, and NTP status.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate, QLocale, QSettings

from defaults import DEFAULT_DATE_FORMAT, DEFAULT_TEXT_CLOCK_LANGUAGE
from time_formatter import TimeFormatter
from utils import settings_group

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)


class UIUpdater:
    """
    Handles periodic UI updates
    
    This class manages updates for date, time, and other periodic UI elements.
    """
    
    def __init__(self, main_screen: "MainScreen"):
        """
        Initialize UI updater
        
        Args:
            main_screen: Reference to MainScreen instance
        """
        self.main_screen = main_screen
        self.languages = {"English": 'en_US',
                         "German": 'de_DE',
                         "Dutch": 'nl_NL',
                         "French": 'fr_FR'}
    
    def constant_update(self) -> None:
        """
        Perform all constant UI updates
        
        Called periodically by the constant update timer to update
        date, time, and other UI elements.
        """
        self.update_date()
        self.update_backtiming_text()
        self.update_backtiming_seconds()
        self.main_screen.update_ntp_status()
        self.main_screen.process_warnings()
    
    def update_date(self) -> None:
        """
        Update the date display
        
        Updates the left text label with the current date formatted
        according to user settings.
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Formatting"):
            set_language = settings.value('textClockLanguage', DEFAULT_TEXT_CLOCK_LANGUAGE)
        lang = QLocale(self.languages[set_language] if set_language in self.languages else QLocale().name())
        self.main_screen.set_left_text(lang.toString(QDate.currentDate(), settings.value('dateFormat', DEFAULT_DATE_FORMAT)))
    
    def update_backtiming_text(self) -> None:
        """
        Update the text clock display based on current time and language
        
        Updates the right text label with formatted time according to
        user language and AM/PM settings.
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Formatting"):
            text_clock_language = settings.value('textClockLanguage', DEFAULT_TEXT_CLOCK_LANGUAGE)
            is_am_pm = settings.value('isAmPm', False, type=bool)

        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        string = TimeFormatter.format_time(hour, minute, text_clock_language, is_am_pm)
        
        self.main_screen.set_right_text(string)
    
    def update_backtiming_seconds(self) -> None:
        """
        Update backtiming seconds display
        
        Calculates remaining seconds until the next minute and updates
        the backtiming display.
        """
        now = datetime.now()
        second = now.second
        remain_seconds = 60 - second
        self.main_screen.set_backtiming_secs(remain_seconds)

