#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# defaults.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Default Values Configuration for OnAirScreen

This module contains all default values used throughout the application.
All default values should be defined here to avoid duplication and improve maintainability.
"""

from typing import Dict, Any, Optional

# General Settings
DEFAULT_STATION_NAME: str = "Radio Eriwan"
DEFAULT_SLOGAN: str = "Your question is our motivation"
DEFAULT_STATION_COLOR: str = "#FFAA00"
DEFAULT_SLOGAN_COLOR: str = "#FFAA00"
DEFAULT_REPLACE_NOW: bool = False
DEFAULT_REPLACE_NOW_TEXT: str = ""
DEFAULT_FULLSCREEN: bool = True
DEFAULT_INSTANCE_NAME: str = "Studio-1"
MAX_INSTANCE_NAME_LENGTH: int = 32

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
DEFAULT_TOTH_TIMER_TEXT: str = "TOTH Timer"


def air_timer_caption(
    air_num: int,
    configured_text: str,
    top_of_hour_active: bool = False,
    toth_text: Optional[str] = None,
) -> str:
    """Return the AIR label caption, using TOTH text while top-of-hour is active."""
    if air_num == 3 and top_of_hour_active:
        return DEFAULT_TOTH_TIMER_TEXT if toth_text is None else toth_text
    return configured_text


def format_air_clock(seconds: int) -> str:
    """Format elapsed or remaining seconds as m:ss (e.g. 125 -> '2:05')."""
    total = max(0, int(seconds or 0))
    return f"{total // 60}:{total % 60:02d}"


# Filled triangles read heavier than ↑/↓ in the timer font.
AIR_TIMER_COUNT_UP_MARK = "▲"
AIR_TIMER_COUNT_DOWN_MARK = "▼"


def air_timer_count_down(
    air_num: int,
    radio_timer_mode: int = 0,
    top_of_hour_active: bool = False,
) -> Optional[bool]:
    """
    Count direction for the AIR3 studio label.

    Returns True for countdown, False for count-up, and None for AIR1/2/4
    (no direction marker on those tiles).
    """
    if air_num == 3:
        return bool(top_of_hour_active) or int(radio_timer_mode or 0) == 1
    return None


def air_timer_count_mark(count_down: Optional[bool]) -> str:
    """Return ▲/▼ for AIR3, or an empty string when no direction is shown."""
    if count_down is None:
        return ""
    return AIR_TIMER_COUNT_DOWN_MARK if count_down else AIR_TIMER_COUNT_UP_MARK


def format_air_timer_label(caption: str, seconds: int) -> str:
    """Caption plus m:ss on two lines (AIR3 count mark lives under the icon)."""
    return f"{caption}\n{format_air_clock(seconds)}"


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

# OSC Settings
DEFAULT_OSC_ENABLED: bool = False
DEFAULT_OSC_PORT: int = 8000
DEFAULT_OSC_SEND_HOST: str = ""
DEFAULT_OSC_SEND_PORT: int = 9000

# Formatting Settings
DEFAULT_DATE_FORMAT: str = "dddd, dd. MMMM yyyy"
DEFAULT_TEXT_CLOCK_LANGUAGE: str = "English"
DEFAULT_IS_AM_PM: bool = False

# Font Settings
DEFAULT_FONT_NAME: str = "Roboto"
DEFAULT_FONT_SIZE_LED: int = 32
DEFAULT_FONT_SIZE_STATION: int = 24
DEFAULT_FONT_SIZE_SLOGAN: int = 18
DEFAULT_FONT_SIZE_TIMER: int = 24
DEFAULT_FONT_WEIGHT_BOLD: int = 1  # QFont.Weight.Bold

# NTP Settings
DEFAULT_NTP_CHECK: bool = True
DEFAULT_NTP_CHECK_SERVER: str = "pool.ntp.org"

# Time Source Settings
TIME_SOURCE_LOCAL: str = "local"
TIME_SOURCE_NTP: str = "ntp"
TIME_SOURCE_PTP: str = "ptp"
TIME_SOURCE_LTC: str = "ltc"
DEFAULT_TIME_SOURCE: str = TIME_SOURCE_LOCAL
DEFAULT_PTP_IFACE: str = ""
DEFAULT_PTP_DOMAIN: int = 0
DEFAULT_LTC_PORT: str = ""
LTC_INPUT_SERIAL: str = "serial"
LTC_INPUT_AUDIO: str = "audio"
DEFAULT_LTC_INPUT: str = LTC_INPUT_SERIAL
DEFAULT_LTC_AUDIO_DEVICE: str = ""
DEFAULT_LTC_AUDIO_CHANNEL: int = 0
DEFAULT_LTC_WARN: bool = False
LTC_INPUT_LABELS: Dict[str, str] = {
    LTC_INPUT_SERIAL: "LBE-1110 Serial",
    LTC_INPUT_AUDIO: "Audio Input",
}
TIME_SOURCE_LABELS: Dict[str, str] = {
    TIME_SOURCE_LOCAL: "Local System Clock",
    TIME_SOURCE_NTP: "NTP Server",
    TIME_SOURCE_PTP: "PTPv2 IEEE 1588-2008",
    TIME_SOURCE_LTC: "LTC",
}

# Update Settings
DEFAULT_UPDATE_CHECK: bool = False
DEFAULT_UPDATE_KEY: str = ""
DEFAULT_UPDATE_INCLUDE_BETA: bool = False

# Logging Settings
DEFAULT_LOG_LEVEL: str = "INFO"

# Weather Widget Settings
DEFAULT_WEATHER_WIDGET_ENABLED: bool = False
DEFAULT_WEATHER_API_KEY: str = ""
DEFAULT_WEATHER_CITY_ID: str = "2643743"  # Default: London, UK
DEFAULT_WEATHER_LANGUAGE: str = "English"  # Display name, not language code
DEFAULT_WEATHER_UNIT: str = "Celsius"  # Display name, not unit code

# Audio Meter Settings
DEFAULT_AUDIO_METERS_ENABLED: bool = True
DEFAULT_AUDIO_SOURCE: str = "device"  # device (local) | livewire | aes67
DEFAULT_AUDIO_INPUT_DEVICE: str = ""
DEFAULT_AUDIO_LIVEWIRE_CHANNEL: int = 1
DEFAULT_AUDIO_LIVEWIRE_IFACE: str = ""
# AES67: SAP-discovered RTP stream (L16/L24). Interface is shared with Livewire.
DEFAULT_AUDIO_AES67_ID: str = ""
DEFAULT_AUDIO_AES67_ADDR: str = ""
DEFAULT_AUDIO_AES67_PORT: int = 5004
DEFAULT_AUDIO_AES67_NAME: str = ""
DEFAULT_AUDIO_AES67_CODEC: str = "L24"
DEFAULT_AUDIO_AES67_RATE: int = 48000
DEFAULT_AUDIO_AES67_CHANNELS: int = 2
DEFAULT_AUDIO_AES67_MANUAL: bool = False
DEFAULT_AUDIO_UNIT: str = "dbtp"  # dbfs | dbtp | bbc_ppm
DEFAULT_AUDIO_LAYOUT: str = "both"  # lr | lufs | both
DEFAULT_AUDIO_TOOLOUD: bool = True
DEFAULT_AUDIO_TOOLOUD_TEXT: str = "TOO LOUD"
DEFAULT_AUDIO_TOOLOUD_THRESHOLD_DBTP: float = -1.0
DEFAULT_AUDIO_TOOLOUD_ACTION: str = "warning"  # warning | led
DEFAULT_AUDIO_TOOLOUD_LED: int = 1
DEFAULT_AUDIO_SILENCE: bool = False
DEFAULT_AUDIO_SILENCE_WARN: bool = True
DEFAULT_AUDIO_SILENCE_ON_ABSENT: bool = True
DEFAULT_AUDIO_SILENCE_TEXT: str = "SILENCE"
DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS: float = -50.0
DEFAULT_AUDIO_SILENCE_DURATION_S: float = 10.0
DEFAULT_AUDIO_SILENCE_RECOVERY_S: float = 2.0
DEFAULT_AUDIO_SILENCE_HTTP_URL: str = ""
DEFAULT_AUDIO_LUFS_REFERENCE_PRESET: str = "ebu_r128"
DEFAULT_AUDIO_LUFS_REFERENCE: float = -23.0
DEFAULT_AUDIO_PEAK_HOLD: bool = True
DEFAULT_AUDIO_PEAK_HOLD_SECONDS: float = 1.5
DEFAULT_AUDIO_DISPLAY_STYLE: str = "bargraph"  # solid | bargraph
DEFAULT_AUDIO_METER_WIDTH: int = 115  # px; L/R bars share extra width
AUDIO_METER_WIDTH_MIN: int = 53
AUDIO_METER_WIDTH_MAX: int = 150

AUDIO_SOURCE_LABELS: Dict[str, str] = {
    "device": "Local Input",
    "livewire": "Livewire",
    "aes67": "AES67",
}

AUDIO_UNIT_LABELS: Dict[str, str] = {
    "dbfs": "dBFS",
    "dbtp": "dBTP",
    "bbc_ppm": "BBC PPM",
}

AUDIO_LAYOUT_LABELS: Dict[str, str] = {
    "lr": "L/R",
    "lufs": "LUFS",
    "both": "L/R + LUFS",
}

AUDIO_DISPLAY_STYLE_LABELS: Dict[str, str] = {
    "solid": "Solid",
    "bargraph": "Bargraph",
}

AUDIO_TOOLOUD_ACTION_LABELS: Dict[str, str] = {
    "warning": "Warning message",
    "led": "Trigger LED",
}

# LUFS target presets (value None means custom / free entry)
AUDIO_LUFS_REFERENCE_PRESETS: Dict[str, Dict[str, Any]] = {
    "ebu_r128": {"label": "EBU R128 (−23 LUFS)", "value": -23.0},
    "atsc_a85": {"label": "ATSC A/85 (−24 LKFS)", "value": -24.0},
    "aes_16": {"label": "AES Streaming (−16 LUFS)", "value": -16.0},
    "aes_18": {"label": "AES / Podcast (−18 LUFS)", "value": -18.0},
    "custom": {"label": "Custom", "value": None},
}

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
            "loglevel": DEFAULT_LOG_LEVEL,
            "instancename": DEFAULT_INSTANCE_NAME,
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
        elif key == "TimerTOTHText":
            return DEFAULT_TOTH_TIMER_TEXT
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

    # OSC group
    if group == "OSC":
        defaults = {
            "enableosc": DEFAULT_OSC_ENABLED,
            "oscport": str(DEFAULT_OSC_PORT),
            "oscsendhost": DEFAULT_OSC_SEND_HOST,
            "oscsendport": str(DEFAULT_OSC_SEND_PORT),
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

    # TimeSource group
    if group == "TimeSource":
        defaults = {
            "source": DEFAULT_TIME_SOURCE,
            "ptp_iface": DEFAULT_PTP_IFACE,
            "ptp_domain": DEFAULT_PTP_DOMAIN,
            "ltc_port": DEFAULT_LTC_PORT,
            "ltc_input": DEFAULT_LTC_INPUT,
            "ltc_audio_device": DEFAULT_LTC_AUDIO_DEVICE,
            "ltc_audio_channel": DEFAULT_LTC_AUDIO_CHANNEL,
            "ltc_warn": DEFAULT_LTC_WARN,
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

    # Audio group
    if group == "Audio":
        defaults = {
            "enabled": DEFAULT_AUDIO_METERS_ENABLED,
            "source": DEFAULT_AUDIO_SOURCE,
            "input_device": DEFAULT_AUDIO_INPUT_DEVICE,
            "livewire_channel": DEFAULT_AUDIO_LIVEWIRE_CHANNEL,
            "livewire_iface": DEFAULT_AUDIO_LIVEWIRE_IFACE,
            "aes67_id": DEFAULT_AUDIO_AES67_ID,
            "aes67_addr": DEFAULT_AUDIO_AES67_ADDR,
            "aes67_port": DEFAULT_AUDIO_AES67_PORT,
            "aes67_name": DEFAULT_AUDIO_AES67_NAME,
            "aes67_codec": DEFAULT_AUDIO_AES67_CODEC,
            "aes67_rate": DEFAULT_AUDIO_AES67_RATE,
            "aes67_channels": DEFAULT_AUDIO_AES67_CHANNELS,
            "aes67_manual": DEFAULT_AUDIO_AES67_MANUAL,
            "unit": DEFAULT_AUDIO_UNIT,
            "layout": DEFAULT_AUDIO_LAYOUT,
            "tooloud": DEFAULT_AUDIO_TOOLOUD,
            "tooloudtext": DEFAULT_AUDIO_TOOLOUD_TEXT,
            "tooloud_threshold_dbtp": DEFAULT_AUDIO_TOOLOUD_THRESHOLD_DBTP,
            "tooloud_action": DEFAULT_AUDIO_TOOLOUD_ACTION,
            "tooloud_led": DEFAULT_AUDIO_TOOLOUD_LED,
            "silence": DEFAULT_AUDIO_SILENCE,
            "silence_warn": DEFAULT_AUDIO_SILENCE_WARN,
            "silence_on_absent": DEFAULT_AUDIO_SILENCE_ON_ABSENT,
            "silence_text": DEFAULT_AUDIO_SILENCE_TEXT,
            "silence_threshold_dbfs": DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS,
            "silence_duration_s": DEFAULT_AUDIO_SILENCE_DURATION_S,
            "silence_recovery_s": DEFAULT_AUDIO_SILENCE_RECOVERY_S,
            "silence_http_url": DEFAULT_AUDIO_SILENCE_HTTP_URL,
            "lufs_reference_preset": DEFAULT_AUDIO_LUFS_REFERENCE_PRESET,
            "lufs_reference": DEFAULT_AUDIO_LUFS_REFERENCE,
            "peak_hold": DEFAULT_AUDIO_PEAK_HOLD,
            "peak_hold_seconds": DEFAULT_AUDIO_PEAK_HOLD_SECONDS,
            "display_style": DEFAULT_AUDIO_DISPLAY_STYLE,
            "meter_width": DEFAULT_AUDIO_METER_WIDTH,
        }
        return defaults.get(key, default)
    
    # Fonts group
    if group == "Fonts":
        if key.endswith("FontName"):
            return DEFAULT_FONT_NAME
        elif key.endswith("FontSize"):
            font_prefix = key[:-8]  # Remove "FontSize" suffix
            # Map font prefixes to their default sizes
            size_map = {
                "LED1": DEFAULT_FONT_SIZE_LED,
                "LED2": DEFAULT_FONT_SIZE_LED,
                "LED3": DEFAULT_FONT_SIZE_LED,
                "LED4": DEFAULT_FONT_SIZE_LED,
                "AIR1": DEFAULT_FONT_SIZE_TIMER,
                "AIR2": DEFAULT_FONT_SIZE_TIMER,
                "AIR3": DEFAULT_FONT_SIZE_TIMER,
                "AIR4": DEFAULT_FONT_SIZE_TIMER,
                "StationName": DEFAULT_FONT_SIZE_STATION,
                "Slogan": DEFAULT_FONT_SIZE_SLOGAN,
            }
            return size_map.get(font_prefix, DEFAULT_FONT_SIZE_LED)
        elif key.endswith("FontWeight") or key.endswith("FontBold"):
            return DEFAULT_FONT_WEIGHT_BOLD
    
    return default

