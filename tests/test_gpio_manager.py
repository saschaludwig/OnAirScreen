#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for gpio_manager.py."""

import sys
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

if not QApplication.instance():
    QApplication(sys.argv)

from defaults import DEFAULT_GPIO_DEBOUNCE_MS, gpio_setting_key
from gpio_manager import (
    FakeGpioBackend,
    GpioManager,
    command_for_event,
    gpio_status_message,
    is_raspberry_pi,
    logical_active,
    read_gpio_config,
)


@pytest.fixture
def ini_settings(tmp_path):
    settings = QSettings(str(tmp_path / "gpio.ini"), QSettings.Format.IniFormat)
    yield settings
    settings.sync()


def _write_enabled_gpi1(settings: QSettings, **overrides) -> None:
    from utils import settings_group

    values = {
        "enabled": True,
        "debounce_ms": 50,
        gpio_setting_key(1, "enabled"): True,
        gpio_setting_key(1, "pin"): 17,
        gpio_setting_key(1, "invert"): True,
        gpio_setting_key(1, "mode"): "level",
        gpio_setting_key(1, "action"): "LED1",
        gpio_setting_key(1, "command"): "",
    }
    values.update(overrides)
    with settings_group(settings, "GPIO"):
        for key, value in values.items():
            settings.setValue(key, value)
    settings.sync()


class TestHelpers:
    def test_logical_active_invert(self):
        assert logical_active(raw_high=False, invert=True) is True
        assert logical_active(raw_high=True, invert=True) is False
        assert logical_active(raw_high=True, invert=False) is True
        assert logical_active(raw_high=False, invert=False) is False

    def test_level_led_commands(self):
        assert command_for_event("LED1", "level", True) == "LED1:ON"
        assert command_for_event("LED1", "level", False) == "LED1:OFF"

    def test_level_air_and_reset(self):
        assert command_for_event("AIR3", "level", True) == "AIR3:ON"
        assert command_for_event("AIR3", "level", False) == "AIR3:OFF"
        assert command_for_event("AIR3_RESET", "level", True) == "AIR3:RESET"
        assert command_for_event("AIR3_RESET", "level", False) is None

    def test_edge_modes(self):
        assert command_for_event("LED1", "rising", True) == "LED1:TOGGLE"
        assert command_for_event("LED1", "rising", False) is None
        assert command_for_event("AIR3", "falling", False) == "AIR3:TOGGLE"
        assert command_for_event("AIR3", "falling", True) is None
        assert command_for_event("LED2", "both", True) == "LED2:TOGGLE"
        assert command_for_event("LED2", "both", False) == "LED2:TOGGLE"

    def test_custom_command(self):
        assert command_for_event("CUSTOM", "level", True, "WARN:GPI") == "WARN:GPI"
        assert command_for_event("CUSTOM", "level", False, "WARN:GPI") is None
        assert command_for_event("CUSTOM", "rising", True, "") is None

    def test_status_not_pi(self):
        assert "not available" in gpio_status_message(platform_available=False).lower()

    def test_status_missing_library(self):
        text = gpio_status_message(platform_available=True, library_available=False)
        assert "gpiozero" in text.lower()

    def test_is_raspberry_pi_false_here(self):
        assert is_raspberry_pi() is False


class TestGpioManager:
    def test_noop_without_pi(self, ini_settings):
        _write_enabled_gpi1(ini_settings)
        backend = FakeGpioBackend()
        screen = Mock()
        manager = GpioManager(
            screen, backend=None, platform_available=False, library_available=True
        )
        manager.start(ini_settings)
        assert backend.lines == {}
        screen.parse_cmd.assert_not_called()
        assert "not available" in manager.status.lower()

    def test_level_dispatch_with_invert(self, ini_settings):
        _write_enabled_gpi1(ini_settings, debounce_ms=0)
        backend = FakeGpioBackend()
        screen = Mock()
        manager = GpioManager(
            screen, backend=backend, platform_available=True, library_available=True
        )
        manager.start(ini_settings)
        line = backend.lines[17]
        line.set_raw_high(False)
        screen._parse_cmd_with_source.assert_called_with(b"LED1:ON", "gpio")
        line.set_raw_high(True)
        screen._parse_cmd_with_source.assert_called_with(b"LED1:OFF", "gpio")

    def test_rising_edge_toggle(self, ini_settings):
        _write_enabled_gpi1(
            ini_settings, debounce_ms=0, **{gpio_setting_key(1, "mode"): "rising"}
        )
        backend = FakeGpioBackend()
        screen = Mock()
        manager = GpioManager(
            screen, backend=backend, platform_available=True, library_available=True
        )
        manager.start(ini_settings)
        line = backend.lines[17]
        line.set_raw_high(False)
        screen._parse_cmd_with_source.assert_called_once_with(b"LED1:TOGGLE", "gpio")
        line.set_raw_high(True)
        screen._parse_cmd_with_source.assert_called_once()

    def test_debounce_drops_bounce(self, ini_settings, monkeypatch):
        _write_enabled_gpi1(ini_settings, debounce_ms=50)
        backend = FakeGpioBackend()
        screen = Mock()
        manager = GpioManager(
            screen, backend=backend, platform_available=True, library_available=True
        )
        times = iter([1.0, 1.01, 1.10])
        monkeypatch.setattr("gpio_manager.time.monotonic", lambda: next(times))
        manager.start(ini_settings)
        line = backend.lines[17]
        line.set_raw_high(False)
        line.set_raw_high(True)
        assert screen._parse_cmd_with_source.call_count == 1
        screen._parse_cmd_with_source.assert_called_with(b"LED1:ON", "gpio")
        line.set_raw_high(True)
        screen._parse_cmd_with_source.assert_called_with(b"LED1:OFF", "gpio")
        assert screen._parse_cmd_with_source.call_count == 2

    def test_read_gpio_config_defaults(self, ini_settings):
        config = read_gpio_config(ini_settings)
        assert config.enabled is False
        assert config.debounce_ms == DEFAULT_GPIO_DEBOUNCE_MS
        assert config.channels[0].pin == 17
        assert config.channels[0].action == "LED1"
        assert config.channels[1].pin == 27
        assert config.channels[1].action == "AIR3"
        assert config.channels[0].enabled is True
        assert config.channels[7].enabled is False
