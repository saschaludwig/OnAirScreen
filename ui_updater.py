#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# ui_updater.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
UI Updater for OnAirScreen

This module handles periodic UI updates like date, time, and NTP status.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, QLocale, QSettings

from defaults import DEFAULT_DATE_FORMAT, DEFAULT_TEXT_CLOCK_LANGUAGE
from time_formatter import TimeFormatter
from time_source import wall_datetime
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
        clock = getattr(self.main_screen, "clockWidget", None)
        ensure = getattr(clock, "ensure_timer_running", None) if clock is not None else None
        if callable(ensure):
            ensure()
        self.update_date()
        self.update_backtiming_text()
        self.update_backtiming_seconds()
        self.main_screen.update_ntp_status()
        self.main_screen.process_warnings()
        poll_silence = getattr(self.main_screen, "poll_silence_absent", None)
        if callable(poll_silence):
            poll_silence()
    
    def update_date(self) -> None:
        """
        Update the date display
        
        Updates the left text label with the current date formatted
        according to user settings.
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Formatting"):
            set_language = settings.value('textClockLanguage', DEFAULT_TEXT_CLOCK_LANGUAGE)
            date_format = settings.value('dateFormat', DEFAULT_DATE_FORMAT, type=str)
        lang = QLocale(self.languages[set_language] if set_language in self.languages else QLocale().name())
        now = wall_datetime()
        qdate = QDate(now.year, now.month, now.day)
        self.main_screen.set_left_text(lang.toString(qdate, date_format))
    
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

        now = wall_datetime()
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
        now = wall_datetime()
        second = now.second
        remain_seconds = 60 - second
        self.main_screen.set_backtiming_secs(remain_seconds)

