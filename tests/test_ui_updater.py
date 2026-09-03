#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ui_updater.py
"""

from datetime import datetime
from unittest.mock import Mock, patch

from ui_updater import UIUpdater


class _FakeSettings:
    """QSettings stand-in that honours beginGroup/endGroup like the real API."""

    def __init__(self, values):
        self._group = ""
        self._values = values

    def beginGroup(self, name):
        self._group = f"{self._group}/{name}" if self._group else name

    def endGroup(self):
        if "/" in self._group:
            self._group = self._group.rsplit("/", 1)[0]
        else:
            self._group = ""

    def value(self, key, default=None, type=None, **kwargs):
        full_key = f"{self._group}/{key}" if self._group else key
        value = self._values.get(full_key, default)
        if type is not None and value is not None:
            return type(value)
        return value


class TestUpdateDate:
    """Tests that the configured Formatting/dateFormat is applied to the date label."""

    def _update_date(self, values, when=None):
        settings = _FakeSettings(values)
        main_screen = Mock()
        updater = UIUpdater(main_screen)
        when = when or datetime(2026, 8, 28, 12, 0, 0)
        with patch("ui_updater.QSettings", return_value=settings):
            with patch("ui_updater.wall_datetime", return_value=when):
                updater.update_date()
        return main_screen.set_left_text

    def test_uses_date_format_from_formatting_group(self):
        """Custom dateFormat must be read from the Formatting group, not the root."""
        set_left_text = self._update_date({
            "Formatting/dateFormat": "yyyy-MM-dd",
            "Formatting/textClockLanguage": "English",
        })
        set_left_text.assert_called_once_with("2026-08-28")

    def test_numeric_european_date_format(self):
        set_left_text = self._update_date({
            "Formatting/dateFormat": "dd.MM.yyyy",
            "Formatting/textClockLanguage": "English",
        })
        set_left_text.assert_called_once_with("28.08.2026")

    def test_localizes_weekday_for_german(self):
        set_left_text = self._update_date({
            "Formatting/dateFormat": "dddd",
            "Formatting/textClockLanguage": "German",
        })
        set_left_text.assert_called_once_with("Freitag")

    def test_falls_back_to_default_format_when_unset(self):
        set_left_text = self._update_date({
            "Formatting/textClockLanguage": "English",
        })
        set_left_text.assert_called_once_with("Friday, 28. August 2026")


class TestConstantUpdate:
    def test_restarts_dead_clock_timer(self):
        main_screen = Mock()
        updater = UIUpdater(main_screen)
        with patch.object(updater, "update_date"), \
                patch.object(updater, "update_backtiming_text"), \
                patch.object(updater, "update_backtiming_seconds"):
            updater.constant_update()
        main_screen.clockWidget.ensure_timer_running.assert_called_once()
        main_screen.update_ntp_status.assert_called_once()
        main_screen.process_warnings.assert_called_once()
        main_screen.poll_silence_absent.assert_called_once()
