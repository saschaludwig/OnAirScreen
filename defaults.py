#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# defaults.py
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
Default Values Configuration for OnAirScreen

This module contains all default values used throughout the application.
All default values should be defined here to avoid duplication and improve maintainability.
"""

from typing import Dict, Any

# General Settings
DEFAULT_STATION_NAME: str = "Radio Eriwan"
DEFAULT_SLOGAN: str = "Your question is our motivation"
DEFAULT_STATION_COLOR: str = "#FFAA00"
DEFAULT_SLOGAN_COLOR: str = "#FFAA00"
DEFAULT_REPLACE_NOW: bool = False
DEFAULT_REPLACE_NOW_TEXT: str = ""
DEFAULT_FULLSCREEN: bool = True

# LED Settings
DEFAULT_LED_TEXTS: Dict[int, str] = {
    1: "ON AIR",
    2: "PHONE",
    3: "DOORBELL",
    4: "EAS ACTIVE"
}
DEFAULT_LED_USED: bool = True
DEFAULT_LED_ACTIVE_TEXT_COLOR: str = "#FFFFFF"
DEFAULT_LED_ACTIVE_BG_COLOR: str = "#FF0000"
DEFAULT_LED_INACTIVE_TEXT_COLOR: str = "#555555"
DEFAULT_LED_INACTIVE_BG_COLOR: str = "#222222"
DEFAULT_LED_AUTOFLASH: bool = False
DEFAULT_LED_TIMEDFLASH: bool = False

# Clock Settings
DEFAULT_CLOCK_DIGITAL: bool = True
DEFAULT_CLOCK_SHOW_SECONDS: bool = False
DEFAULT_CLOCK_SECONDS_IN_ONE_LINE: bool = False
DEFAULT_CLOCK_STATIC_COLON: bool = False
DEFAULT_CLOCK_DIGITAL_HOUR_COLOR: str = "#3232FF"
DEFAULT_CLOCK_DIGITAL_SECOND_COLOR: str = "#FF9900"
DEFAULT_CLOCK_DIGITAL_DIGIT_COLOR: str = "#3232FF"
DEFAULT_CLOCK_LOGO_PATH: str = ":/astrastudio_logo/images/astrastudio_transparent.png"
DEFAULT_CLOCK_LOGO_UPPER: bool = False
DEFAULT_CLOCK_USE_TEXT_CLOCK: bool = True

# Timer/AIR Settings
DEFAULT_TIMER_AIR_ENABLED: bool = True
DEFAULT_TIMER_AIR_TEXTS: Dict[int, str] = {
    1: "Mic",
    2: "Phone",
    3: "Timer",
    4: "Stream"
}
DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR: str = "#FFFFFF"
DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR: str = "#FF0000"
DEFAULT_TIMER_AIR_INACTIVE_TEXT_COLOR: str = "#555555"
DEFAULT_TIMER_AIR_INACTIVE_BG_COLOR: str = "#222222"
DEFAULT_TIMER_AIR_MIN_WIDTH: int = 200
DEFAULT_TIMER_AIR_ICON_PATHS: Dict[int, str] = {
    1: ":/mic_icon/images/mic_icon.png",
    2: ":/phone_icon/images/phone_icon.png",
    3: ":/timer_icon/images/timer_icon.png",
    4: ":/stream_icon/images/antenna2.png"
}

# Network Settings
DEFAULT_UDP_PORT: int = 3310
DEFAULT_HTTP_PORT: int = 8010
DEFAULT_MULTICAST_ADDRESS: str = "239.194.0.1"

# Formatting Settings
DEFAULT_DATE_FORMAT: str = "dddd, dd. MMMM yyyy"
DEFAULT_TEXT_CLOCK_LANGUAGE: str = "English"
DEFAULT_IS_AM_PM: bool = False

# Font Settings
DEFAULT_FONT_NAME: str = "FreeSans"
DEFAULT_FONT_SIZE_LED: int = 24
DEFAULT_FONT_SIZE_STATION: int = 24
DEFAULT_FONT_SIZE_SLOGAN: int = 18
DEFAULT_FONT_SIZE_TIMER: int = 24
DEFAULT_FONT_WEIGHT_BOLD: int = 1  # QFont.Weight.Bold

# NTP Settings
DEFAULT_NTP_CHECK: bool = True
DEFAULT_NTP_CHECK_SERVER: str = "pool.ntp.org"

# Update Settings
DEFAULT_UPDATE_CHECK: bool = False
DEFAULT_UPDATE_KEY: str = ""
DEFAULT_UPDATE_INCLUDE_BETA: bool = False

# Weather Widget Settings
DEFAULT_WEATHER_WIDGET_ENABLED: bool = False
DEFAULT_WEATHER_API_KEY: str = ""
DEFAULT_WEATHER_CITY_ID: str = "2643743"  # Default: London, UK
DEFAULT_WEATHER_LANGUAGE: str = "English"  # Display name, not language code
DEFAULT_WEATHER_UNIT: str = "Celsius"  # Display name, not unit code

# Helper function to get default value by key path
def get_default(group: str, key: str, default: Any = None) -> Any:
    """
    Get default value by group and key
    
    Args:
        group: Settings group name (e.g., "General", "LED1", "Clock")
        key: Settings key name (e.g., "stationname", "text", "digital")
        default: Fallback default value if not found
        
    Returns:
        Default value for the given group and key, or provided default
    """
    # General group
    if group == "General":
        defaults = {
            "stationname": DEFAULT_STATION_NAME,
            "slogan": DEFAULT_SLOGAN,
            "stationcolor": DEFAULT_STATION_COLOR,
            "slogancolor": DEFAULT_SLOGAN_COLOR,
            "replacenow": DEFAULT_REPLACE_NOW,
            "replacenowtext": DEFAULT_REPLACE_NOW_TEXT,
            "fullscreen": DEFAULT_FULLSCREEN,
        }
        return defaults.get(key, default)
    
    # LED groups
    if group.startswith("LED") and group[3:].isdigit():
        led_num = int(group[3:])
        if key == "text":
            return DEFAULT_LED_TEXTS.get(led_num, default)
        elif key == "used":
            return DEFAULT_LED_USED
        elif key == "activebgcolor":
            return DEFAULT_LED_ACTIVE_BG_COLOR
        elif key == "activetextcolor":
            return DEFAULT_LED_ACTIVE_TEXT_COLOR
        elif key == "inactivebgcolor":
            return DEFAULT_LED_INACTIVE_BG_COLOR
        elif key == "inactivetextcolor":
            return DEFAULT_LED_INACTIVE_TEXT_COLOR
        elif key == "autoflash":
            return DEFAULT_LED_AUTOFLASH
        elif key == "timedflash":
            return DEFAULT_LED_TIMEDFLASH
    
    # Clock group
    if group == "Clock":
        defaults = {
            "digital": DEFAULT_CLOCK_DIGITAL,
            "showSeconds": DEFAULT_CLOCK_SHOW_SECONDS,
            "showSecondsInOneLine": DEFAULT_CLOCK_SECONDS_IN_ONE_LINE,
            "staticColon": DEFAULT_CLOCK_STATIC_COLON,
            "digitalhourcolor": DEFAULT_CLOCK_DIGITAL_HOUR_COLOR,
            "digitalsecondcolor": DEFAULT_CLOCK_DIGITAL_SECOND_COLOR,
            "digitaldigitcolor": DEFAULT_CLOCK_DIGITAL_DIGIT_COLOR,
            "logopath": DEFAULT_CLOCK_LOGO_PATH,
            "logoUpper": DEFAULT_CLOCK_LOGO_UPPER,
            "useTextClock": DEFAULT_CLOCK_USE_TEXT_CLOCK,
        }
        return defaults.get(key, default)
    
    # Timers group
    if group == "Timers":
        if key.startswith("TimerAIR") and key.endswith("Enabled"):
            return DEFAULT_TIMER_AIR_ENABLED
        elif key.startswith("TimerAIR") and key.endswith("Text"):
            # Extract AIR number from key like "TimerAIR1Text"
            try:
                air_num = int(key[8:-4])
                return DEFAULT_TIMER_AIR_TEXTS.get(air_num, default)
            except (ValueError, IndexError):
                return default
        elif key.startswith("AIR") and key.endswith("activebgcolor"):
            return DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR
        elif key.startswith("AIR") and key.endswith("activetextcolor"):
            return DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR
        elif key.startswith("AIR") and key.endswith("inactivebgcolor"):
            return DEFAULT_TIMER_AIR_INACTIVE_BG_COLOR
        elif key.startswith("AIR") and key.endswith("inactivetextcolor"):
            return DEFAULT_TIMER_AIR_INACTIVE_TEXT_COLOR
        elif key == "TimerAIRMinWidth":
            return DEFAULT_TIMER_AIR_MIN_WIDTH
        elif key.startswith("AIR") and key.endswith("iconpath"):
            try:
                air_num = int(key[3:-8])
                return DEFAULT_TIMER_AIR_ICON_PATHS.get(air_num, default)
            except (ValueError, IndexError):
                return default
    
    # Network group
    if group == "Network":
        defaults = {
            "udpport": str(DEFAULT_UDP_PORT),
            "httpport": str(DEFAULT_HTTP_PORT),
            "multicast_address": DEFAULT_MULTICAST_ADDRESS,
        }
        return defaults.get(key, default)
    
    # Formatting group
    if group == "Formatting":
        defaults = {
            "dateFormat": DEFAULT_DATE_FORMAT,
            "textClockLanguage": DEFAULT_TEXT_CLOCK_LANGUAGE,
            "isAmPm": DEFAULT_IS_AM_PM,
        }
        return defaults.get(key, default)
    
    # NTP group
    if group == "NTP":
        defaults = {
            "ntpcheck": DEFAULT_NTP_CHECK,
            "ntpcheckserver": DEFAULT_NTP_CHECK_SERVER,
        }
        return defaults.get(key, default)
    
    # WeatherWidget group
    if group == "WeatherWidget":
        defaults = {
            "owmWidgetEnabled": DEFAULT_WEATHER_WIDGET_ENABLED,
            "owmAPIKey": DEFAULT_WEATHER_API_KEY,
            "owmCityID": DEFAULT_WEATHER_CITY_ID,
            "owmLanguage": DEFAULT_WEATHER_LANGUAGE,
            "owmUnit": DEFAULT_WEATHER_UNIT,
        }
        return defaults.get(key, default)
    
    # Fonts group
    if group == "Fonts":
        if key.endswith("FontName"):
            font_prefix = key[:-8]  # Remove "FontName" suffix
            return DEFAULT_FONT_NAMES.get(font_prefix, default)
        elif key.endswith("FontSize"):
            font_prefix = key[:-8]  # Remove "FontSize" suffix
            return DEFAULT_FONT_SIZES.get(font_prefix, default)
        elif key.endswith("FontBold"):
            font_prefix = key[:-8]  # Remove "FontBold" suffix
            return DEFAULT_FONT_BOLD.get(font_prefix, default)
    
    return default

