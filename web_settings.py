#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# web_settings.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""Web settings API: schema, PIN hashing, config snapshot, apply, presets."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, QSettings, Qt, Signal

from defaults import (
    AUDIO_DISPLAY_STYLE_LABELS,
    AUDIO_LAYOUT_LABELS,
    AUDIO_LUFS_REFERENCE_PRESETS,
    AUDIO_METER_WIDTH_MAX,
    AUDIO_METER_WIDTH_MIN,
    AUDIO_SOURCE_LABELS,
    AUDIO_TOOLOUD_ACTION_LABELS,
    AUDIO_UNIT_LABELS,
    DEFAULT_AUDIO_AES67_CHANNELS,
    DEFAULT_AUDIO_AES67_CODEC,
    DEFAULT_AUDIO_AES67_MANUAL,
    DEFAULT_AUDIO_AES67_PORT,
    DEFAULT_AUDIO_AES67_RATE,
    DEFAULT_AUDIO_DISPLAY_STYLE,
    DEFAULT_AUDIO_INPUT_DEVICE,
    DEFAULT_AUDIO_LAYOUT,
    DEFAULT_AUDIO_LIVEWIRE_CHANNEL,
    DEFAULT_AUDIO_LIVEWIRE_IFACE,
    DEFAULT_AUDIO_LUFS_REFERENCE,
    DEFAULT_AUDIO_LUFS_REFERENCE_PRESET,
    DEFAULT_AUDIO_METER_WIDTH,
    DEFAULT_AUDIO_METERS_ENABLED,
    DEFAULT_AUDIO_PEAK_HOLD,
    DEFAULT_AUDIO_PEAK_HOLD_SECONDS,
    DEFAULT_AUDIO_SILENCE,
    DEFAULT_AUDIO_SILENCE_DURATION_S,
    DEFAULT_AUDIO_SILENCE_HTTP_URL,
    DEFAULT_AUDIO_SILENCE_ON_ABSENT,
    DEFAULT_AUDIO_SILENCE_RECOVERY_S,
    DEFAULT_AUDIO_SILENCE_TEXT,
    DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS,
    DEFAULT_AUDIO_SILENCE_WARN,
    DEFAULT_AUDIO_SOURCE,
    DEFAULT_AUDIO_TOOLOUD,
    DEFAULT_AUDIO_TOOLOUD_ACTION,
    DEFAULT_AUDIO_TOOLOUD_LED,
    DEFAULT_AUDIO_TOOLOUD_TEXT,
    DEFAULT_AUDIO_TOOLOUD_THRESHOLD_DBTP,
    DEFAULT_AUDIO_UNIT,
    DEFAULT_ALWAYS_START_FULLSCREEN,
    DEFAULT_CLOCK_DIGITAL,
    DEFAULT_CLOCK_DIGITAL_DIGIT_COLOR,
    DEFAULT_CLOCK_DIGITAL_HOUR_COLOR,
    DEFAULT_CLOCK_DIGITAL_SECOND_COLOR,
    DEFAULT_CLOCK_LOGO_PATH,
    DEFAULT_CLOCK_LOGO_UPPER,
    DEFAULT_CLOCK_SECONDS_IN_ONE_LINE,
    DEFAULT_CLOCK_SHOW_SECONDS,
    DEFAULT_CLOCK_STATIC_COLON,
    DEFAULT_CLOCK_USE_TEXT_CLOCK,
    DEFAULT_DATE_FORMAT,
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE_LED,
    DEFAULT_FONT_SIZE_SLOGAN,
    DEFAULT_FONT_SIZE_STATION,
    DEFAULT_FONT_SIZE_TIMER,
    DEFAULT_GPIO_DEBOUNCE_MS,
    DEFAULT_GPIO_ENABLED,
    DEFAULT_HTTP_PORT,
    DEFAULT_INSTANCE_NAME,
    DEFAULT_IS_AM_PM,
    DEFAULT_LED_ACTIVE_TEXT_COLOR,
    DEFAULT_LED_AUTOFLASH,
    DEFAULT_LED_INACTIVE_BG_COLOR,
    DEFAULT_LED_INACTIVE_TEXT_COLOR,
    DEFAULT_LED_TEXTS,
    DEFAULT_LED_TIMEDFLASH,
    DEFAULT_LED_USED,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LTC_AUDIO_CHANNEL,
    DEFAULT_LTC_AUDIO_DEVICE,
    DEFAULT_LTC_INPUT,
    DEFAULT_LTC_PORT,
    DEFAULT_LTC_WARN,
    DEFAULT_MQTT_DEVICE_NAME,
    DEFAULT_MQTT_ENABLED,
    DEFAULT_MQTT_PASSWORD,
    DEFAULT_MQTT_PORT,
    DEFAULT_MQTT_SERVER,
    DEFAULT_MQTT_USER,
    DEFAULT_MULTICAST_ADDRESS,
    DEFAULT_NTP_CHECK,
    DEFAULT_NTP_CHECK_SERVER,
    DEFAULT_OSC_ENABLED,
    DEFAULT_OSC_PORT,
    DEFAULT_OSC_SEND_HOST,
    DEFAULT_OSC_SEND_PORT,
    DEFAULT_PTP_DOMAIN,
    DEFAULT_PTP_IFACE,
    DEFAULT_REPLACE_NOW,
    DEFAULT_REPLACE_NOW_TEXT,
    DEFAULT_SLOGAN,
    DEFAULT_SLOGAN_COLOR,
    DEFAULT_STATION_COLOR,
    DEFAULT_STATION_NAME,
    DEFAULT_TEXT_CLOCK_LANGUAGE,
    DEFAULT_TIME_SOURCE,
    DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR,
    DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR,
    DEFAULT_TIMER_AIR_ENABLED,
    DEFAULT_TIMER_AIR_ICON_PATHS,
    DEFAULT_TIMER_AIR_MIN_WIDTH,
    DEFAULT_TIMER_AIR_TEXTS,
    DEFAULT_TOTH_TIMER_TEXT,
    DEFAULT_UDP_PORT,
    DEFAULT_UPDATE_CHECK,
    DEFAULT_UPDATE_INCLUDE_BETA,
    DEFAULT_UPDATE_KEY,
    DEFAULT_WEATHER_API_KEY,
    DEFAULT_WEATHER_CITY_ID,
    DEFAULT_WEATHER_LANGUAGE,
    DEFAULT_WEATHER_UNIT,
    DEFAULT_WEATHER_WIDGET_ENABLED,
    DEFAULT_WEB_SETTINGS_PIN,
    GPIO_ACTION_LABELS,
    GPIO_CHANNEL_COUNT,
    GPIO_MODE_LABELS,
    GPIO_SAFE_BCM_PINS,
    LTC_INPUT_LABELS,
    TIME_SOURCE_LABELS,
    default_gpio_channel,
)
from utils import INSTANCE_NAME_PATTERN, normalize_instance_name, settings_group

logger = logging.getLogger(__name__)

UNCHANGED_SENTINEL = "__unchanged__"
PIN_CLEAR_TOKEN = "-"
PIN_HASH_ITERATIONS = 200_000
SESSION_TTL_SECONDS = 30 * 60
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
PORT_MIN = 1
PORT_MAX = 65535

LED_DEFAULT_BG = {1: "#FF0000", 2: "#DCDC00", 3: "#00C8C8", 4: "#FF00FF"}
TEXT_CLOCK_LANGUAGES = ["English", "German", "Dutch", "French"]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]
FONT_ROW_PREFIXES = (
    "AIR1", "AIR2", "AIR3", "AIR4",
    "LED1", "LED2", "LED3", "LED4",
    "StationName", "Slogan",
)
CONFIG_GROUPS = [
    "General", "NTP", "TimeSource", "LEDS", "LED1", "LED2", "LED3", "LED4",
    "Clock", "Network", "OSC", "Formatting", "WeatherWidget", "Timers", "Fonts", "Audio", "GPIO",
]
MQTT_GROUP = "MQTT"

SECRET_KEYS = {
    ("General", "updatekey"),
    ("MQTT", "mqttpassword"),
    ("WeatherWidget", "owmAPIKey"),
    ("Network", "websettingspin"),
}


class SettingsApiError(Exception):
    """HTTP-facing error for the web settings API."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SettingsField:
    """One editable settings field exposed to the web UI."""

    group: str
    key: str
    label: str
    field_type: str
    default: Any = ""
    options: Optional[list[dict[str, Any]]] = None
    options_key: Optional[str] = None
    secret: bool = False
    restart_required: bool = False
    hint: str = ""
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    widget: Optional[str] = None
    hidden: bool = False
    virtual: bool = False
    enabled_when: Optional[list[dict[str, Any]]] = None
    enabled_when_any: Optional[list[dict[str, Any]]] = None


@dataclass
class SettingsTab:
    """A settings overlay tab matching the desktop dialog."""

    id: str
    label: str
    fields: list[SettingsField] = field(default_factory=list)


def _eq(group: str, key: str, value: Any) -> dict[str, Any]:
    """AND/OR enablement rule: field equals value."""
    return {"group": group, "key": key, "eq": value}


def _in_values(group: str, key: str, values: list[Any]) -> dict[str, Any]:
    """Enablement rule: field is one of the given values."""
    return {"group": group, "key": key, "in": values}


def _values_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        if isinstance(actual, str):
            return actual.strip().lower() in ("1", "true", "yes", "on") if expected else (
                actual.strip().lower() not in ("1", "true", "yes", "on")
            )
        return bool(actual) is expected
    return str(actual) == str(expected)


def _rule_matches(rule: dict[str, Any], config: dict[str, Any]) -> bool:
    actual = (config.get(rule["group"]) or {}).get(rule["key"])
    if "eq" in rule:
        return _values_equal(actual, rule["eq"])
    if "neq" in rule:
        return not _values_equal(actual, rule["neq"])
    if "in" in rule:
        return any(_values_equal(actual, item) for item in rule["in"])
    return True


def field_is_enabled(field_def: SettingsField, config: dict[str, Any]) -> bool:
    """True when a field should be interactive for the given config snapshot."""
    and_rules = field_def.enabled_when or []
    or_rules = field_def.enabled_when_any or []
    and_ok = all(_rule_matches(rule, config) for rule in and_rules)
    or_ok = (not or_rules) or any(_rule_matches(rule, config) for rule in or_rules)
    return and_ok and or_ok


def _enum_options(mapping: dict[str, str]) -> list[dict[str, Any]]:
    return [{"value": key, "label": label} for key, label in mapping.items()]


def _string_options(values: list[str]) -> list[dict[str, Any]]:
    return [{"value": value, "label": value} for value in values]


def _font_size_for_prefix(prefix: str) -> int:
    if prefix.startswith("LED"):
        return DEFAULT_FONT_SIZE_LED
    if prefix.startswith("AIR"):
        return DEFAULT_FONT_SIZE_TIMER
    if prefix == "StationName":
        return DEFAULT_FONT_SIZE_STATION
    if prefix == "Slogan":
        return DEFAULT_FONT_SIZE_SLOGAN
    return DEFAULT_FONT_SIZE_LED


def _is_bold_weight(value: Any) -> bool:
    if hasattr(value, "value") and not isinstance(value, (int, str, float, bool)):
        try:
            value = value.value()
        except TypeError:
            pass
    try:
        weight_value = int(value)
    except (TypeError, ValueError):
        return True
    return weight_value in (1, 75) or weight_value >= 70


def _weight_from_bold(bold: bool) -> int:
    return 700 if bold else 400


def _ows_settings() -> QSettings:
    return QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")


def hash_web_settings_pin(pin: str) -> str:
    """Return a salted PBKDF2 hash, or an empty string when no PIN is set."""
    if not pin:
        return ""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), salt, PIN_HASH_ITERATIONS
    )
    return f"pbkdf2_sha256${PIN_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_web_settings_pin(pin: str, stored: str) -> bool:
    """Return True if pin matches the stored hash."""
    if not stored:
        return not bool(pin)
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def stored_web_settings_pin(settings: Optional[QSettings] = None) -> str:
    """Return the stored PIN hash from QSettings."""
    settings = settings or _ows_settings()
    with settings_group(settings, "Network"):
        return str(settings.value("websettingspin", DEFAULT_WEB_SETTINGS_PIN, type=str) or "")


def web_settings_pin_required(settings: Optional[QSettings] = None) -> bool:
    """True when a web settings PIN is configured."""
    return bool(stored_web_settings_pin(settings))


class SettingsSessionStore:
    """In-memory tokens for unlocked web-settings sessions."""

    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._tokens: dict[str, float] = {}

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        expiry = time.monotonic() + self._ttl
        with self._lock:
            self._prune_unlocked()
            self._tokens[token] = expiry
        return token

    def valid(self, token: Optional[str]) -> bool:
        if not token:
            return False
        now = time.monotonic()
        with self._lock:
            expiry = self._tokens.get(token)
            if expiry is None:
                return False
            if expiry < now:
                self._tokens.pop(token, None)
                return False
            self._tokens[token] = now + self._ttl
            return True

    def _prune_unlocked(self) -> None:
        now = time.monotonic()
        expired = [key for key, expiry in self._tokens.items() if expiry < now]
        for key in expired:
            self._tokens.pop(key, None)


session_store = SettingsSessionStore()


def authenticate_web_settings_pin(pin: str, settings: Optional[QSettings] = None) -> str:
    """Validate the PIN and return a session token."""
    stored = stored_web_settings_pin(settings)
    if not stored:
        return session_store.create()
    if not verify_web_settings_pin(pin or "", stored):
        raise SettingsApiError("Invalid PIN", 401)
    return session_store.create()


def build_settings_schema() -> list[SettingsTab]:
    """Return the web settings form schema (tabs and fields)."""
    meters_on = [_eq("Audio", "enabled", True)]
    source_device = meters_on + [_eq("Audio", "source", "device")]
    source_livewire = meters_on + [_eq("Audio", "source", "livewire")]
    source_aes67 = meters_on + [_eq("Audio", "source", "aes67")]
    source_aoip = meters_on + [_in_values("Audio", "source", ["livewire", "aes67"])]
    layout_lr = meters_on + [_in_values("Audio", "layout", ["lr", "both"])]
    layout_lufs = meters_on + [_in_values("Audio", "layout", ["lufs", "both"])]
    weather_on = [_eq("WeatherWidget", "owmWidgetEnabled", True)]
    mqtt_on = [_eq("MQTT", "enablemqtt", True)]
    osc_on = [_eq("OSC", "enableosc", True)]
    ltc_on = [_eq("TimeSource", "source", "ltc")]
    general_fields: list[SettingsField] = [
        SettingsField("General", "instancename", "Instance Name", "string", DEFAULT_INSTANCE_NAME,
                      hint="DNS-safe label, up to 32 characters"),
        SettingsField("General", "stationname", "Station Name", "string", DEFAULT_STATION_NAME),
        SettingsField("General", "stationcolor", "Station Color", "color", DEFAULT_STATION_COLOR),
        SettingsField("General", "slogan", "Slogan", "string", DEFAULT_SLOGAN),
        SettingsField("General", "slogancolor", "Slogan Color", "color", DEFAULT_SLOGAN_COLOR),
        SettingsField("LEDS", "inactivebgcolor", "Inactive LED Background", "color", DEFAULT_LED_INACTIVE_BG_COLOR),
        SettingsField("LEDS", "inactivetextcolor", "Inactive LED Text", "color", DEFAULT_LED_INACTIVE_TEXT_COLOR),
    ]
    for led_num in range(1, 5):
        group = f"LED{led_num}"
        led_on = [_eq(group, "used", True)]
        general_fields.extend([
            SettingsField(group, "used", f"LED{led_num} Enabled", "bool", DEFAULT_LED_USED),
            SettingsField(group, "text", f"LED{led_num} Text", "string", DEFAULT_LED_TEXTS[led_num],
                          enabled_when=led_on),
            SettingsField(group, "activebgcolor", f"LED{led_num} Active Background", "color",
                          LED_DEFAULT_BG[led_num], enabled_when=led_on),
            SettingsField(group, "activetextcolor", f"LED{led_num} Active Text", "color",
                          DEFAULT_LED_ACTIVE_TEXT_COLOR, enabled_when=led_on),
            SettingsField(group, "autoflash", f"LED{led_num} Autoflash", "bool", DEFAULT_LED_AUTOFLASH,
                          enabled_when=led_on),
            SettingsField(group, "timedflash", f"LED{led_num} 20s Flash", "bool", DEFAULT_LED_TIMEDFLASH,
                          enabled_when=led_on),
        ])
    clock_digital = [_eq("Clock", "digital", True)]
    general_fields.extend([
        SettingsField("Clock", "digital", "Digital Clock", "bool", DEFAULT_CLOCK_DIGITAL,
                      hint="Off = analog clock"),
        SettingsField("Clock", "showSeconds", "Show Seconds", "bool", DEFAULT_CLOCK_SHOW_SECONDS),
        SettingsField("Clock", "showSecondsInOneLine", "Seconds In One Line", "bool",
                      DEFAULT_CLOCK_SECONDS_IN_ONE_LINE,
                      enabled_when=[_eq("Clock", "showSeconds", True)]),
        SettingsField("Clock", "staticColon", "Static Colon", "bool", DEFAULT_CLOCK_STATIC_COLON),
        SettingsField("Clock", "useTextClock", "Use Text Clock", "bool", DEFAULT_CLOCK_USE_TEXT_CLOCK),
        SettingsField("Clock", "digitalhourcolor", "Hour Digit Color", "color",
                      DEFAULT_CLOCK_DIGITAL_HOUR_COLOR, enabled_when=clock_digital),
        SettingsField("Clock", "digitalsecondcolor", "Seconds Color", "color",
                      DEFAULT_CLOCK_DIGITAL_SECOND_COLOR, enabled_when=clock_digital),
        SettingsField("Clock", "digitaldigitcolor", "Digit Color", "color",
                      DEFAULT_CLOCK_DIGITAL_DIGIT_COLOR, enabled_when=clock_digital),
        SettingsField("Clock", "logopath", "Logo Path", "path", DEFAULT_CLOCK_LOGO_PATH),
        SettingsField("Clock", "logoUpper", "Logo Upper Position", "bool", DEFAULT_CLOCK_LOGO_UPPER),
        SettingsField("General", "replacenow", "Replace IPs after 10s", "bool", DEFAULT_REPLACE_NOW),
        SettingsField("General", "replacenowtext", "Replace NOW Text", "string", DEFAULT_REPLACE_NOW_TEXT,
                      enabled_when=[_eq("General", "replacenow", True)]),
        SettingsField("General", "always_start_fullscreen", "Always start in fullscreen mode", "bool",
                      DEFAULT_ALWAYS_START_FULLSCREEN),
        SettingsField("General", "updatecheck", "Check for Updates", "bool", DEFAULT_UPDATE_CHECK),
        SettingsField("General", "updatekey", "Update Key", "secret", DEFAULT_UPDATE_KEY, secret=True,
                      enabled_when=[_eq("General", "updatecheck", True)]),
        SettingsField("General", "updateincludebeta", "Include Beta Versions", "bool",
                      DEFAULT_UPDATE_INCLUDE_BETA,
                      enabled_when=[_eq("General", "updatecheck", True)]),
        SettingsField("General", "loglevel", "Log Level", "enum", DEFAULT_LOG_LEVEL,
                      options=_string_options(LOG_LEVELS)),
    ])

    network_fields = [
        SettingsField("Network", "udpport", "UDP Port", "int", str(DEFAULT_UDP_PORT),
                      restart_required=True, minimum=PORT_MIN, maximum=PORT_MAX),
        SettingsField("Network", "httpport", "HTTP Port", "int", str(DEFAULT_HTTP_PORT),
                      restart_required=True, minimum=PORT_MIN, maximum=PORT_MAX,
                      hint="Requires an application restart"),
        SettingsField("Network", "multicast_address", "Multicast Address", "string",
                      DEFAULT_MULTICAST_ADDRESS),
        SettingsField("Network", "websettingspin", "Web Settings PIN", "secret",
                      DEFAULT_WEB_SETTINGS_PIN, secret=True,
                      hint="Leave unchanged to keep the current PIN. Enter - to remove PIN protection."),
        SettingsField("MQTT", "enablemqtt", "Enable MQTT", "bool", DEFAULT_MQTT_ENABLED),
        SettingsField("MQTT", "mqttserver", "MQTT Server", "string", DEFAULT_MQTT_SERVER,
                      enabled_when=mqtt_on),
        SettingsField("MQTT", "mqttport", "MQTT Port", "int", str(DEFAULT_MQTT_PORT),
                      minimum=PORT_MIN, maximum=PORT_MAX, enabled_when=mqtt_on),
        SettingsField("MQTT", "mqttuser", "MQTT User", "string", DEFAULT_MQTT_USER,
                      enabled_when=mqtt_on),
        SettingsField("MQTT", "mqttpassword", "MQTT Password", "secret", DEFAULT_MQTT_PASSWORD,
                      secret=True, enabled_when=mqtt_on),
        SettingsField("MQTT", "mqttdevicename", "MQTT Device Name", "string",
                      DEFAULT_MQTT_DEVICE_NAME, enabled_when=mqtt_on),
        SettingsField("OSC", "enableosc", "Enable OSC", "bool", DEFAULT_OSC_ENABLED),
        SettingsField("OSC", "oscport", "OSC Listen Port", "int", str(DEFAULT_OSC_PORT),
                      minimum=PORT_MIN, maximum=PORT_MAX, enabled_when=osc_on),
        SettingsField("OSC", "oscsendhost", "OSC Send Host", "string", DEFAULT_OSC_SEND_HOST,
                      enabled_when=osc_on),
        SettingsField("OSC", "oscsendport", "OSC Send Port", "int", str(DEFAULT_OSC_SEND_PORT),
                      minimum=PORT_MIN, maximum=PORT_MAX, enabled_when=osc_on),
    ]

    advanced_fields = [
        SettingsField("Formatting", "dateFormat", "Date Format", "string", DEFAULT_DATE_FORMAT),
        SettingsField("Formatting", "isAmPm", "12-hour Clock", "bool", DEFAULT_IS_AM_PM),
        SettingsField("Formatting", "textClockLanguage", "Text Clock Language", "enum",
                      DEFAULT_TEXT_CLOCK_LANGUAGE, options=_string_options(TEXT_CLOCK_LANGUAGES)),
        SettingsField("WeatherWidget", "owmWidgetEnabled", "Enable Weather Widget", "bool",
                      DEFAULT_WEATHER_WIDGET_ENABLED),
        SettingsField("WeatherWidget", "owmAPIKey", "OpenWeatherMap API Key", "secret",
                      DEFAULT_WEATHER_API_KEY, secret=True, enabled_when=weather_on),
        SettingsField("WeatherWidget", "owmCityID", "City ID", "string", DEFAULT_WEATHER_CITY_ID,
                      widget="weather_city", enabled_when=weather_on),
        SettingsField("WeatherWidget", "owmLanguage", "Weather Language", "enum",
                      DEFAULT_WEATHER_LANGUAGE, options_key="weather_languages",
                      enabled_when=weather_on),
        SettingsField("WeatherWidget", "owmUnit", "Weather Unit", "enum", DEFAULT_WEATHER_UNIT,
                      options_key="weather_units", enabled_when=weather_on),
    ]

    timer_fields: list[SettingsField] = []
    for air_num in range(1, 5):
        air_on = [_eq("Timers", f"TimerAIR{air_num}Enabled", True)]
        timer_fields.extend([
            SettingsField("Timers", f"TimerAIR{air_num}Enabled", f"AIR{air_num} Enabled", "bool",
                          DEFAULT_TIMER_AIR_ENABLED),
            SettingsField("Timers", f"TimerAIR{air_num}Text", f"AIR{air_num} Text", "string",
                          DEFAULT_TIMER_AIR_TEXTS[air_num], enabled_when=air_on),
            SettingsField("Timers", f"AIR{air_num}activebgcolor", f"AIR{air_num} Active Background",
                          "color", DEFAULT_TIMER_AIR_ACTIVE_BG_COLOR, enabled_when=air_on),
            SettingsField("Timers", f"AIR{air_num}activetextcolor", f"AIR{air_num} Active Text",
                          "color", DEFAULT_TIMER_AIR_ACTIVE_TEXT_COLOR, enabled_when=air_on),
            SettingsField("Timers", f"air{air_num}iconpath", f"AIR{air_num} Icon Path", "path",
                          DEFAULT_TIMER_AIR_ICON_PATHS[air_num], enabled_when=air_on),
        ])
    timer_fields.extend([
        SettingsField("Timers", "TimerTOTHText", "TOTH Text", "string", DEFAULT_TOTH_TIMER_TEXT),
        SettingsField("Timers", "TimerAIRMinWidth", "AIR Minimum Width", "int",
                      DEFAULT_TIMER_AIR_MIN_WIDTH, minimum=50, maximum=800),
    ])

    font_fields: list[SettingsField] = []
    for prefix in FONT_ROW_PREFIXES:
        font_fields.extend([
            SettingsField("Fonts", f"{prefix}FontName", f"{prefix} Font", "enum", DEFAULT_FONT_NAME,
                          options_key="fonts"),
            SettingsField("Fonts", f"{prefix}FontSize", f"{prefix} Size", "int",
                          _font_size_for_prefix(prefix), minimum=6, maximum=200),
            SettingsField("Fonts", f"{prefix}FontWeight", f"{prefix} Bold", "font_bold", True),
        ])

    time_source_fields = [
        SettingsField("TimeSource", "source", "Time Source", "enum", DEFAULT_TIME_SOURCE,
                      options=_enum_options(TIME_SOURCE_LABELS)),
        SettingsField("NTP", "ntpcheck", "Enable NTP Check", "bool", DEFAULT_NTP_CHECK),
        SettingsField("NTP", "ntpcheckserver", "NTP Server", "string", DEFAULT_NTP_CHECK_SERVER,
                      enabled_when_any=[
                          _eq("NTP", "ntpcheck", True),
                          _eq("TimeSource", "source", "ntp"),
                      ]),
        SettingsField("TimeSource", "ptp_iface", "PTP Interface", "enum", DEFAULT_PTP_IFACE,
                      options_key="ipv4_interfaces",
                      enabled_when=[_eq("TimeSource", "source", "ptp")]),
        SettingsField("TimeSource", "ptp_domain", "PTP Domain", "int", DEFAULT_PTP_DOMAIN,
                      minimum=0, maximum=255,
                      enabled_when=[_eq("TimeSource", "source", "ptp")]),
        SettingsField("TimeSource", "ltc_input", "LTC Input", "enum", DEFAULT_LTC_INPUT,
                      options=_enum_options(LTC_INPUT_LABELS), enabled_when=ltc_on),
        SettingsField("TimeSource", "ltc_port", "LTC Serial Port", "enum", DEFAULT_LTC_PORT,
                      options_key="ltc_ports",
                      enabled_when=ltc_on + [_eq("TimeSource", "ltc_input", "serial")]),
        SettingsField("TimeSource", "ltc_audio_device", "LTC Audio Device", "enum",
                      DEFAULT_LTC_AUDIO_DEVICE, options_key="audio_devices",
                      enabled_when=ltc_on + [_eq("TimeSource", "ltc_input", "audio")]),
        SettingsField("TimeSource", "ltc_audio_channel", "LTC Channel", "enum",
                      DEFAULT_LTC_AUDIO_CHANNEL,
                      options=[{"value": 0, "label": "Left"}, {"value": 1, "label": "Right"}],
                      enabled_when=ltc_on + [_eq("TimeSource", "ltc_input", "audio")]),
        SettingsField("TimeSource", "ltc_warn", "LTC Unlock Warning", "bool", DEFAULT_LTC_WARN,
                      enabled_when=ltc_on),
    ]

    tooloud_on = [_eq("Audio", "tooloud", True)]
    silence_on = [_eq("Audio", "silence", True)]
    audio_fields = [
        SettingsField("Audio", "enabled", "Enable Audio Meters", "bool", DEFAULT_AUDIO_METERS_ENABLED),
        SettingsField("Audio", "source", "Audio Source", "enum", DEFAULT_AUDIO_SOURCE,
                      options=_enum_options(AUDIO_SOURCE_LABELS), enabled_when=meters_on),
        SettingsField("Audio", "input_device", "Audio Input", "enum", DEFAULT_AUDIO_INPUT_DEVICE,
                      options_key="audio_devices", enabled_when=source_device),
        SettingsField("Audio", "livewire_iface", "AoIP Interface", "enum",
                      DEFAULT_AUDIO_LIVEWIRE_IFACE, options_key="ipv4_interfaces",
                      enabled_when=source_aoip),
        SettingsField("Audio", "livewire_source", "Livewire Source", "enum", "",
                      widget="livewire_source", virtual=True, enabled_when=source_livewire,
                      hint="Announced sources appear while this overlay is open. "
                           "Pick a source or type a channel number below."),
        SettingsField("Audio", "livewire_channel", "Livewire Channel", "int",
                      DEFAULT_AUDIO_LIVEWIRE_CHANNEL, minimum=1, maximum=32767,
                      enabled_when=source_livewire),
        SettingsField("Audio", "aes67_stream", "AES67 Stream", "enum", "",
                      widget="aes67_stream", virtual=True, enabled_when=source_aes67,
                      hint="None, live SAP, or pasted SDP while this overlay is open."),
        SettingsField("Audio", "aes67_id", "AES67 Stream ID", "string", "",
                      hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_addr", "AES67 Address", "string", "",
                      hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_port", "AES67 Port", "int", DEFAULT_AUDIO_AES67_PORT,
                      minimum=PORT_MIN, maximum=PORT_MAX, hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_name", "AES67 Name", "string", "",
                      hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_codec", "AES67 Codec", "enum", DEFAULT_AUDIO_AES67_CODEC,
                      options=_string_options(["L16", "L24"]), hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_rate", "AES67 Sample Rate", "enum", DEFAULT_AUDIO_AES67_RATE,
                      options=[{"value": 44100, "label": "44100"}, {"value": 48000, "label": "48000"},
                               {"value": 96000, "label": "96000"}],
                      hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_channels", "AES67 Channels", "int",
                      DEFAULT_AUDIO_AES67_CHANNELS, minimum=1, maximum=64,
                      hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "aes67_manual", "AES67 Pasted SDP", "bool", DEFAULT_AUDIO_AES67_MANUAL,
                      hidden=True, enabled_when=source_aes67),
        SettingsField("Audio", "layout", "Meter Layout", "enum", DEFAULT_AUDIO_LAYOUT,
                      options=_enum_options(AUDIO_LAYOUT_LABELS), enabled_when=meters_on),
        SettingsField("Audio", "unit", "Display Unit", "enum", DEFAULT_AUDIO_UNIT,
                      options=_enum_options(AUDIO_UNIT_LABELS), enabled_when=layout_lr),
        SettingsField("Audio", "display_style", "Display Style", "enum", DEFAULT_AUDIO_DISPLAY_STYLE,
                      options=_enum_options(AUDIO_DISPLAY_STYLE_LABELS), enabled_when=meters_on),
        SettingsField("Audio", "meter_width", "Meter Width", "int", DEFAULT_AUDIO_METER_WIDTH,
                      minimum=AUDIO_METER_WIDTH_MIN, maximum=AUDIO_METER_WIDTH_MAX,
                      enabled_when=meters_on),
        SettingsField("Audio", "lufs_reference_preset", "LUFS Reference Preset", "enum",
                      DEFAULT_AUDIO_LUFS_REFERENCE_PRESET,
                      options=[{"value": key, "label": data["label"]}
                               for key, data in AUDIO_LUFS_REFERENCE_PRESETS.items()],
                      enabled_when=layout_lufs),
        SettingsField("Audio", "lufs_reference", "LUFS Reference", "float",
                      DEFAULT_AUDIO_LUFS_REFERENCE, minimum=-70, maximum=0, step=0.1,
                      enabled_when=layout_lufs + [_eq("Audio", "lufs_reference_preset", "custom")]),
        SettingsField("Audio", "peak_hold", "Peak Hold", "bool", DEFAULT_AUDIO_PEAK_HOLD,
                      enabled_when=layout_lr),
        SettingsField("Audio", "peak_hold_seconds", "Peak Hold Seconds", "float",
                      DEFAULT_AUDIO_PEAK_HOLD_SECONDS, minimum=0.1, maximum=10, step=0.1,
                      enabled_when=layout_lr + [_eq("Audio", "peak_hold", True)]),
        SettingsField("Audio", "tooloud", "Too Loud", "bool", DEFAULT_AUDIO_TOOLOUD),
        SettingsField("Audio", "tooloudtext", "Too Loud Text", "string", DEFAULT_AUDIO_TOOLOUD_TEXT,
                      enabled_when=tooloud_on + [_eq("Audio", "tooloud_action", "warning")]),
        SettingsField("Audio", "tooloud_threshold_dbtp", "Too Loud Threshold", "float",
                      DEFAULT_AUDIO_TOOLOUD_THRESHOLD_DBTP, minimum=-20, maximum=0, step=0.1,
                      enabled_when=tooloud_on),
        SettingsField("Audio", "tooloud_action", "Too Loud Action", "enum",
                      DEFAULT_AUDIO_TOOLOUD_ACTION, options=_enum_options(AUDIO_TOOLOUD_ACTION_LABELS),
                      enabled_when=tooloud_on),
        SettingsField("Audio", "tooloud_led", "Too Loud LED", "enum", DEFAULT_AUDIO_TOOLOUD_LED,
                      options=[{"value": n, "label": f"LED {n}"} for n in range(1, 5)],
                      enabled_when=tooloud_on + [_eq("Audio", "tooloud_action", "led")]),
        SettingsField("Audio", "silence", "Enable Silence Detection", "bool", DEFAULT_AUDIO_SILENCE),
        SettingsField("Audio", "silence_warn", "Show Silence WARN", "bool", DEFAULT_AUDIO_SILENCE_WARN,
                      enabled_when=silence_on),
        SettingsField("Audio", "silence_on_absent", "Trigger When Device/Stream Absent", "bool",
                      DEFAULT_AUDIO_SILENCE_ON_ABSENT, enabled_when=silence_on),
        SettingsField("Audio", "silence_text", "Silence Message", "string", DEFAULT_AUDIO_SILENCE_TEXT,
                      enabled_when=silence_on + [_eq("Audio", "silence_warn", True)]),
        SettingsField("Audio", "silence_threshold_dbfs", "Silence Threshold", "float",
                      DEFAULT_AUDIO_SILENCE_THRESHOLD_DBFS, minimum=-90, maximum=0, step=0.1,
                      enabled_when=silence_on),
        SettingsField("Audio", "silence_duration_s", "Max. Silence Duration", "float",
                      DEFAULT_AUDIO_SILENCE_DURATION_S, minimum=0.1, maximum=120, step=0.1,
                      enabled_when=silence_on),
        SettingsField("Audio", "silence_recovery_s", "Recovery Time", "float",
                      DEFAULT_AUDIO_SILENCE_RECOVERY_S, minimum=0.1, maximum=60, step=0.1,
                      enabled_when=silence_on),
        SettingsField("Audio", "silence_http_url", "Silence HTTP GET URL", "string",
                      DEFAULT_AUDIO_SILENCE_HTTP_URL, enabled_when=silence_on),
    ]

    gpio_on = [_eq("GPIO", "enabled", True)]
    gpio_fields = [
        SettingsField(
            "GPIO", "enabled", "Enable GPIO Inputs", "bool", DEFAULT_GPIO_ENABLED,
            hint="Raspberry Pi GPIO inputs mapped to LED and AIR commands. Use an optocoupler for mixer GPI.",
        ),
        SettingsField(
            "GPIO", "debounce_ms", "Debounce", "int", str(DEFAULT_GPIO_DEBOUNCE_MS),
            minimum=0, maximum=1000, step=10, enabled_when=gpio_on,
            hint="Ignore contact bounce shorter than this interval (milliseconds)",
        ),
    ]
    pin_options = [{"value": str(pin), "label": str(pin)} for pin in GPIO_SAFE_BCM_PINS]
    for index in range(1, GPIO_CHANNEL_COUNT + 1):
        channel = default_gpio_channel(index)
        prefix = f"gpi{index}_"
        gpio_fields.extend([
            SettingsField(
                "GPIO", f"{prefix}enabled", f"GPI{index} Enable", "bool", channel["enabled"],
                enabled_when=gpio_on,
            ),
            SettingsField(
                "GPIO", f"{prefix}pin", f"GPI{index} BCM Pin", "enum", str(channel["pin"]),
                options=pin_options, enabled_when=gpio_on,
            ),
            SettingsField(
                "GPIO", f"{prefix}invert", f"GPI{index} Invert", "bool", channel["invert"],
                enabled_when=gpio_on,
                hint="On: contact to GND is active (internal pull-up)",
            ),
            SettingsField(
                "GPIO", f"{prefix}mode", f"GPI{index} Mode", "enum", channel["mode"],
                options=_enum_options(GPIO_MODE_LABELS), enabled_when=gpio_on,
            ),
            SettingsField(
                "GPIO", f"{prefix}action", f"GPI{index} Action", "enum", channel["action"],
                options=_enum_options(GPIO_ACTION_LABELS), enabled_when=gpio_on,
            ),
            SettingsField(
                "GPIO", f"{prefix}command", f"GPI{index} Custom Command", "string",
                channel["command"],
                enabled_when=[*gpio_on, _eq("GPIO", f"{prefix}action", "CUSTOM")],
                hint="API command sent for Custom action, e.g. LED1:ON",
            ),
        ])

    return [
        SettingsTab("general", "General", general_fields),
        SettingsTab("network", "Network", network_fields),
        SettingsTab("advanced", "Advanced", advanced_fields),
        SettingsTab("timers", "Timers", timer_fields),
        SettingsTab("fonts", "Fonts", font_fields),
        SettingsTab("timesource", "Time Source", time_source_fields),
        SettingsTab("audio", "Audio Meters", audio_fields),
        SettingsTab("gpio", "GPIO", gpio_fields),
    ]


def iter_schema_fields() -> list[SettingsField]:
    fields: list[SettingsField] = []
    for tab in build_settings_schema():
        fields.extend(tab.fields)
    return fields


def field_index() -> dict[tuple[str, str], SettingsField]:
    return {(item.group, item.key): item for item in iter_schema_fields()}


def _json_primitive(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "name") and callable(getattr(value, "name", None)):
        try:
            name = value.name()
            if isinstance(name, str) and name.startswith("#"):
                return name
        except TypeError:
            pass
    if hasattr(value, "value") and not isinstance(value, (int, str, float, bool)):
        try:
            value = value.value()
        except TypeError:
            pass
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        return value
    return str(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _coerce_for_field(field_def: SettingsField, value: Any) -> Any:
    if value is None:
        return field_def.default
    if field_def.field_type == "bool":
        return _coerce_bool(value)
    if field_def.field_type == "font_bold":
        return _is_bold_weight(value) if not isinstance(value, bool) else value
    if field_def.field_type == "int":
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return field_def.default
    if field_def.field_type == "float":
        try:
            return float(value)
        except (TypeError, ValueError):
            return field_def.default
    if field_def.field_type == "color":
        text = str(value)
        if COLOR_PATTERN.match(text):
            return text.upper()
        return str(field_def.default)
    primitive = _json_primitive(value)
    if primitive is None:
        return field_def.default
    return primitive


def export_config_dict(
    include_mqtt: bool = False,
    settings: Optional[QSettings] = None,
) -> dict[str, dict[str, Any]]:
    """Export QSettings groups as a JSON-serializable dict."""
    settings = settings or _ows_settings()
    groups = list(CONFIG_GROUPS)
    if include_mqtt:
        groups.append(MQTT_GROUP)
    config: dict[str, dict[str, Any]] = {}
    for group in groups:
        group_dict: dict[str, Any] = {}
        with settings_group(settings, group):
            for key in settings.allKeys():
                group_dict[key] = _json_primitive(settings.value(key))
        if group_dict:
            config[group] = group_dict
    return config


def get_web_config(settings: Optional[QSettings] = None) -> dict[str, dict[str, Any]]:
    """Full settings snapshot for the web UI.

    Plaintext secrets (MQTT password, API key, update key) are returned so the
    overlay can reveal them. The PIN stays masked because only its hash is stored.
    """
    settings = settings or _ows_settings()
    exported = export_config_dict(include_mqtt=True, settings=settings)
    result: dict[str, dict[str, Any]] = {}
    for field_def in iter_schema_fields():
        if field_def.virtual:
            continue
        raw = exported.get(field_def.group, {}).get(field_def.key, field_def.default)
        if field_def.secret:
            if field_def.group == "Network" and field_def.key == "websettingspin":
                value = UNCHANGED_SENTINEL if raw not in (None, "") else ""
            else:
                value = "" if raw in (None, "") else str(raw)
        else:
            value = _coerce_for_field(field_def, raw)
        result.setdefault(field_def.group, {})[field_def.key] = value
    return result


def collect_settings_options() -> dict[str, list[dict[str, Any]]]:
    """Collect machine-local dropdown options for the web form."""
    fonts: list[dict[str, Any]] = []
    try:
        from PySide6.QtGui import QFontDatabase, QGuiApplication

        if QGuiApplication.instance() is not None:
            fonts = _string_options(list(QFontDatabase.families()))
    except Exception as exc:
        logger.debug("Could not list fonts: %s", exc)
    if not fonts:
        fonts = _string_options([DEFAULT_FONT_NAME, "Noto Sans"])

    audio_devices = [{"value": "", "label": "System Default"}]
    try:
        from audio_capture import list_input_devices

        for device in list_input_devices():
            audio_devices.append({"value": device.name, "label": str(device)})
    except Exception as exc:
        logger.debug("Could not list audio devices: %s", exc)

    ipv4_interfaces = [{"value": "", "label": "Default"}]
    try:
        from livewire_capture import list_ipv4_interfaces

        for label, ip_str in list_ipv4_interfaces():
            ipv4_interfaces.append({"value": ip_str, "label": label})
    except Exception as exc:
        logger.debug("Could not list IPv4 interfaces: %s", exc)

    ltc_ports = [{"value": "", "label": "Auto"}]
    try:
        from ltc_reader import list_serial_ports

        for label, device in list_serial_ports():
            ltc_ports.append({"value": device, "label": label})
    except Exception as exc:
        logger.debug("Could not list LTC serial ports: %s", exc)

    weather_languages = _string_options(TEXT_CLOCK_LANGUAGES)
    weather_units = _string_options(["Celsius", "Fahrenheit", "Kelvin"])
    try:
        from weatherwidget import WeatherWidget

        weather_languages = _string_options(list(WeatherWidget.owm_languages.keys()))
        weather_units = _string_options(list(WeatherWidget.owm_units.keys()))
    except Exception as exc:
        logger.debug("Could not load weather labels: %s", exc)

    return {
        "fonts": fonts,
        "audio_devices": audio_devices,
        "ipv4_interfaces": ipv4_interfaces,
        "ltc_ports": ltc_ports,
        "weather_languages": weather_languages,
        "weather_units": weather_units,
    }


def schema_as_json() -> dict[str, Any]:
    """JSON-serializable schema plus live option lists."""
    tabs = []
    for tab in build_settings_schema():
        fields = []
        for item in tab.fields:
            payload = {
                "group": item.group,
                "key": item.key,
                "label": item.label,
                "type": item.field_type,
                "default": item.default,
                "options": item.options,
                "optionsKey": item.options_key,
                "secret": item.secret,
                "restartRequired": item.restart_required,
                "hint": item.hint,
                "minimum": item.minimum,
                "maximum": item.maximum,
                "step": item.step,
                "widget": item.widget,
                "hidden": item.hidden,
                "virtual": item.virtual,
            }
            if item.enabled_when:
                payload["enabledWhen"] = item.enabled_when
            if item.enabled_when_any:
                payload["enabledWhenAny"] = item.enabled_when_any
            fields.append(payload)
        tabs.append({"id": tab.id, "label": tab.label, "fields": fields})
    return {"tabs": tabs, "options": collect_settings_options(), "unchanged": UNCHANGED_SENTINEL}


def _validate_and_convert(field_def: SettingsField, value: Any) -> Any:
    if field_def.secret and value == UNCHANGED_SENTINEL:
        return UNCHANGED_SENTINEL
    if field_def.field_type == "bool":
        return _coerce_bool(value)
    if field_def.field_type == "font_bold":
        return _weight_from_bold(_coerce_bool(value))
    if field_def.field_type in ("int",):
        number = int(float(value))
        if field_def.minimum is not None and number < field_def.minimum:
            raise SettingsApiError(f"{field_def.label} is below the minimum {field_def.minimum}")
        if field_def.maximum is not None and number > field_def.maximum:
            raise SettingsApiError(f"{field_def.label} is above the maximum {field_def.maximum}")
        if field_def.key in ("udpport", "httpport", "mqttport", "oscport", "oscsendport", "aes67_port"):
            return str(number) if field_def.group in ("Network", "OSC") or field_def.key == "mqttport" else number
        return number
    if field_def.field_type == "float":
        number = float(value)
        if field_def.minimum is not None and number < field_def.minimum:
            raise SettingsApiError(f"{field_def.label} is below the minimum {field_def.minimum}")
        if field_def.maximum is not None and number > field_def.maximum:
            raise SettingsApiError(f"{field_def.label} is above the maximum {field_def.maximum}")
        return number
    if field_def.field_type == "color":
        text = str(value)
        if not COLOR_PATTERN.match(text):
            raise SettingsApiError(f"{field_def.label} must be a #RRGGBB color")
        return text.upper()
    if field_def.group == "General" and field_def.key == "instancename":
        text = str(value).strip()
        if not INSTANCE_NAME_PATTERN.fullmatch(text):
            raise SettingsApiError("Instance name must be a DNS label (A–Z, 0–9, hyphen, max 32)")
        return normalize_instance_name(text)
    if field_def.group == "Network" and field_def.key == "websettingspin":
        text = "" if value is None else str(value)
        if text == UNCHANGED_SENTINEL:
            return UNCHANGED_SENTINEL
        if text == PIN_CLEAR_TOKEN:
            return ""
        if text == "":
            return ""
        return hash_web_settings_pin(text)
    if field_def.secret:
        return "" if value is None else str(value)
    if value is None:
        return ""
    return value


def apply_web_config(
    config: dict[str, Any],
    main_screen: Optional[Any] = None,
    settings: Optional[QSettings] = None,
) -> dict[str, Any]:
    """Validate config, write QSettings, sync the dialog, and apply live."""
    if not isinstance(config, dict):
        raise SettingsApiError("Config must be an object")
    index = field_index()
    writes: list[tuple[str, str, Any]] = []
    for group, content in config.items():
        if not isinstance(content, dict):
            raise SettingsApiError(f"Group {group} must be an object")
        for key, value in content.items():
            field_def = index.get((group, key))
            if field_def is None:
                raise SettingsApiError(f"Unknown setting {group}/{key}")
            if field_def.virtual:
                continue
            converted = _validate_and_convert(field_def, value)
            if converted == UNCHANGED_SENTINEL:
                continue
            writes.append((group, key, converted))

    settings = settings or _ows_settings()
    for group, key, value in writes:
        with settings_group(settings, group):
            settings.setValue(key, value)
    settings.sync()

    if main_screen is not None:
        settings_dialog = getattr(main_screen, "settings", None)
        if settings_dialog is not None and hasattr(settings_dialog, "restoreSettingsFromConfig"):
            settings_dialog.restoreSettingsFromConfig()
            if hasattr(settings_dialog, "sigConfigFinished"):
                settings_dialog.sigConfigFinished.emit()
        elif hasattr(main_screen, "config_finished"):
            main_screen.config_finished()
    return {"status": "ok"}


def presets_directory(settings: Optional[QSettings] = None) -> Path:
    settings = settings or _ows_settings()
    return Path(settings.fileName()).parent / "presets"


def list_web_presets(settings: Optional[QSettings] = None) -> list[dict[str, str]]:
    presets_dir = presets_directory(settings)
    presets: list[dict[str, str]] = []
    if not presets_dir.exists():
        return presets
    for preset_file in presets_dir.glob("*.json"):
        name = preset_file.stem
        version = "unknown"
        try:
            with open(preset_file, encoding="utf-8") as handle:
                data = json.load(handle)
            name = data.get("name", name)
            version = data.get("version", version)
        except Exception as exc:
            logger.warning("Error reading preset %s: %s", preset_file, exc)
        presets.append({"filename": preset_file.stem, "name": str(name), "version": str(version)})
    presets.sort(key=lambda item: item["name"].lower())
    return presets


def save_web_preset(preset_name: str, settings: Optional[QSettings] = None) -> dict[str, Any]:
    if not preset_name or not str(preset_name).strip():
        raise SettingsApiError("Preset name cannot be empty")
    safe_name = "".join(
        char for char in preset_name.strip() if char.isalnum() or char in (" ", "-", "_")
    ).strip().replace(" ", "_")
    if not safe_name:
        raise SettingsApiError("Preset name contains no valid characters")
    from settings_functions import versionString

    settings = settings or _ows_settings()
    presets_dir = presets_directory(settings)
    presets_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": preset_name.strip(),
        "version": versionString,
        "config": export_config_dict(include_mqtt=False, settings=settings),
    }
    preset_file = presets_dir / f"{safe_name}.json"
    with open(preset_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return {"status": "ok", "filename": safe_name, "name": preset_name.strip()}


def load_web_preset(preset_name: str, settings: Optional[QSettings] = None) -> dict[str, dict[str, Any]]:
    if not preset_name:
        raise SettingsApiError("Preset name cannot be empty")
    preset_file = presets_directory(settings) / f"{preset_name}.json"
    if not preset_file.exists():
        raise SettingsApiError(f"Preset not found: {preset_name}", 404)
    with open(preset_file, encoding="utf-8") as handle:
        data = json.load(handle)
    config = data.get("config", data)
    if not isinstance(config, dict):
        raise SettingsApiError("Preset file is invalid")
    merged = get_web_config(settings)
    index = field_index()
    for group, content in config.items():
        if not isinstance(content, dict):
            continue
        for key, value in content.items():
            field_def = index.get((group, key))
            if field_def is None:
                continue
            if field_def.secret:
                continue
            merged.setdefault(group, {})[key] = _coerce_for_field(field_def, value)
    return merged


def search_weather_cities(query: str, api_key: str) -> list[dict[str, Any]]:
    """Search OpenWeatherMap geocoding and resolve city IDs."""
    query = (query or "").strip()
    api_key = (api_key or "").strip()
    if not api_key:
        raise SettingsApiError("Enter an OpenWeatherMap API key first")
    if not query:
        raise SettingsApiError("Enter a city name to search")
    geo_url = "https://api.openweathermap.org/geo/1.0/direct?" + urllib.parse.urlencode({
        "q": query,
        "limit": 5,
        "appid": api_key,
    })
    places = _http_json(geo_url)
    if not isinstance(places, list):
        raise SettingsApiError("Unexpected geocoding response")
    from weatherwidget import format_owm_city_label

    results = []
    for place in places:
        if not isinstance(place, dict):
            continue
        city_id = place.get("id")
        lat = place.get("lat")
        lon = place.get("lon")
        if not city_id and lat is not None and lon is not None:
            weather_url = "https://api.openweathermap.org/data/2.5/weather?" + urllib.parse.urlencode({
                "lat": lat,
                "lon": lon,
                "appid": api_key,
            })
            try:
                weather = _http_json(weather_url)
                if isinstance(weather, dict):
                    city_id = weather.get("id")
            except SettingsApiError:
                city_id = None
        if not city_id:
            continue
        results.append({
            "id": str(city_id),
            "label": format_owm_city_label(place),
        })
    return results


def _http_json(url: str, timeout: float = 8.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "OnAirScreen"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SettingsApiError(f"Weather search failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SettingsApiError(f"Weather search failed: {exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SettingsApiError("Weather search returned invalid JSON") from exc


def resolve_weather_api_key(payload_key: Optional[str], settings: Optional[QSettings] = None) -> str:
    if payload_key and payload_key != UNCHANGED_SENTINEL:
        return payload_key
    settings = settings or _ows_settings()
    with settings_group(settings, "WeatherWidget"):
        return str(settings.value("owmAPIKey", DEFAULT_WEATHER_API_KEY, type=str) or "")


def dispatch_settings_api(main_screen: Optional[Any], action: str, payload: Any = None) -> Any:
    """Run a settings API action on the GUI thread."""
    payload = payload or {}
    if action == "schema":
        return schema_as_json()
    if action == "get":
        return {"config": get_web_config()}
    if action == "put":
        config = payload.get("config", payload)
        return apply_web_config(config, main_screen=main_screen)
    if action == "presets_list":
        return {"presets": list_web_presets()}
    if action == "presets_save":
        return save_web_preset(str(payload.get("name", "")))
    if action == "presets_load":
        name = str(payload.get("name") or payload.get("filename") or "")
        return {"config": load_web_preset(name)}
    if action == "aoip_list":
        from web_aoip import list_web_aoip_streams

        return list_web_aoip_streams(payload)
    if action == "aoip_sdp":
        from web_aoip import paste_web_aoip_sdp

        return paste_web_aoip_sdp(payload)
    if action == "aoip_stop":
        from web_aoip import stop_web_aoip_discovery

        return stop_web_aoip_discovery()
    raise SettingsApiError(f"Unknown settings action: {action}", 404)


class SettingsApiBridge(QObject):
    """Marshal settings API calls from the HTTP thread onto the GUI thread."""

    _requested = Signal(str, object, object)

    def __init__(self, main_screen: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.main_screen = main_screen
        self._requested.connect(self._handle, Qt.ConnectionType.QueuedConnection)

    def call(self, action: str, payload: Any = None, timeout: float = 20.0) -> Any:
        box: dict[str, Any] = {"event": threading.Event(), "result": None, "error": None}
        self._requested.emit(action, payload, box)
        if not box["event"].wait(timeout):
            raise SettingsApiError("Timed out waiting for settings API", 504)
        error = box["error"]
        if error is not None:
            raise error
        return box["result"]

    def _handle(self, action: str, payload: Any, box: dict[str, Any]) -> None:
        try:
            box["result"] = dispatch_settings_api(self.main_screen, action, payload)
        except Exception as exc:
            box["error"] = exc
        finally:
            box["event"].set()
