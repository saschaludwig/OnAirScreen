#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# time_formatter.py
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
Time Formatter for OnAirScreen

This module provides text-based time formatting for different languages.
"""

from datetime import datetime


class TimeFormatter:
    """
    Formats time as text in different languages
    
    Supports English, German, Dutch, and French text clock formats.
    """
    
    @staticmethod
    def format_time(hour: int, minute: int, language: str = "English", is_am_pm: bool = False) -> str:
        """
        Format time as text based on language
        
        Args:
            hour: Current hour (0-23)
            minute: Current minute (0-59)
            language: Language name ("English", "German", "Dutch", "French")
            is_am_pm: Whether to use AM/PM format (for English and Dutch)
            
        Returns:
            Formatted time string
        """
        remain_min = 60 - minute
        
        # Dispatch to language-specific formatters
        language_formatters = {
            "German": TimeFormatter._format_time_german,
            "Dutch": TimeFormatter._format_time_dutch,
            "French": TimeFormatter._format_time_french,
        }
        
        formatter = language_formatters.get(language, TimeFormatter._format_time_english)
        return formatter(hour, minute, remain_min, is_am_pm)
    
    @staticmethod
    def _format_time_german(hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in German text clock style"""
        if hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"{hour} Uhr"
        elif minute == 30:
            return f"halb {1 if hour == 12 else hour + 1}"
        elif 0 < minute < 25:
            return f"{minute} Minute{'n' if minute > 1 else ''} nach {hour}"
        elif 25 <= minute < 30:
            return f"{remain_min - 30} Minute{'n' if remain_min - 30 > 1 else ''} vor halb {1 if hour == 12 else hour + 1}"
        elif 31 <= minute <= 39:
            return f"{30 - remain_min} Minute{'n' if 30 - remain_min > 1 else ''} nach halb {1 if hour == 12 else hour + 1}"
        elif 40 <= minute <= 59:
            return f"{remain_min} Minute{'n' if remain_min > 1 else ''} vor {1 if hour == 12 else hour + 1}"
        else:
            return f"{hour} Uhr"
    
    @staticmethod
    def _format_time_dutch(hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in Dutch text clock style"""
        if is_am_pm and hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"Het is {hour} uur"
        elif minute == 15:
            return f"Het is kwart over {hour}"
        elif minute == 30:
            return f"Het is half {1 if hour == 12 else hour + 1}"
        elif minute == 45:
            return f"Het is kwart voor {1 if hour == 12 else hour + 1}"
        elif (1 <= minute <= 14) or (16 <= minute <= 29):
            return f"Het is {minute} minu{'ten' if minute > 1 else 'ut'} over {hour}"
        elif (31 <= minute <= 44) or (46 <= minute <= 59):
            return f"Het is {remain_min} minu{'ten' if minute > 1 else 'ut'} voor {1 if hour == 12 else hour + 1}"
        else:
            return f"Het is {hour} uur"
    
    @staticmethod
    def _format_time_french(hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in French text clock style"""
        if hour > 12:
            hour -= 12
        
        if hour == 0:
            if minute == 0:
                return "minuit"
            elif minute == 15:
                return "minuit et quart"
            elif minute == 30:
                return "minuit et demie"
            elif 0 < minute < 59:
                return f"minuit {minute}"
        
        if minute == 0:
            return f"{hour} {'heures' if hour > 1 else 'heure'}"
        elif minute == 15:
            return f"{hour} {'heures' if hour > 1 else 'heure'} et quart"
        elif minute == 30:
            return f"{hour} {'heures' if hour > 1 else 'heure'} et demie"
        elif 0 < minute < 60:
            return f"{hour} {'heures' if hour > 1 else 'heure'} {minute}"
        else:
            return f"{hour} {'heures' if hour > 1 else 'heure'}"
    
    @staticmethod
    def _format_time_english(hour: int, minute: int, remain_min: int, is_am_pm: bool) -> str:
        """Format time in English text clock style"""
        if is_am_pm and hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"it's {hour} o'clock"
        elif minute == 15:
            return f"it's a quarter past {hour}"
        elif minute == 30:
            return f"it's half past {hour}"
        elif minute == 45:
            return f"it's a quarter to {hour + 1}"
        elif (0 < minute < 15) or (16 <= minute <= 29):
            return f"it's {minute} minute{'s' if minute > 1 else ''} past {hour}"
        elif (31 <= minute <= 44) or (46 <= minute <= 59):
            return f"it's {remain_min} minute{'s' if remain_min > 1 else ''} to {1 if hour == 12 else hour + 1}"
        else:
            return f"it's {hour} o'clock"

