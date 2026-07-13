#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for time_formatter module"""

from time_formatter import TimeFormatter


class TestTimeFormatter24HourTextClock:
    """Text clock should always use 12-hour spoken form, even in 24h display mode."""

    def test_english_minutes_to_in_24h_mode(self):
        """15:48 should read '12 minutes to 4', not '12 minutes to 16'."""
        result = TimeFormatter.format_time(15, 48, "English", is_am_pm=False)
        assert result == "it's 12 minutes to 4"

    def test_english_minutes_past_in_24h_mode(self):
        result = TimeFormatter.format_time(16, 10, "English", is_am_pm=False)
        assert result == "it's 10 minutes past 4"

    def test_english_o_clock_in_24h_mode(self):
        result = TimeFormatter.format_time(14, 0, "English", is_am_pm=False)
        assert result == "it's 2 o'clock"

    def test_english_quarter_to_in_24h_mode(self):
        result = TimeFormatter.format_time(15, 45, "English", is_am_pm=False)
        assert result == "it's a quarter to 4"

    def test_english_still_works_in_am_pm_mode(self):
        result = TimeFormatter.format_time(15, 48, "English", is_am_pm=True)
        assert result == "it's 12 minutes to 4"

    def test_dutch_minutes_to_in_24h_mode(self):
        result = TimeFormatter.format_time(15, 48, "Dutch", is_am_pm=False)
        assert result == "Het is 12 minuten voor 4"

    def test_german_minutes_vor_in_24h_mode(self):
        result = TimeFormatter.format_time(15, 48, "German", is_am_pm=False)
        assert result == "12 Minuten vor 4"

    def test_french_afternoon_in_24h_mode(self):
        result = TimeFormatter.format_time(16, 30, "French", is_am_pm=False)
        assert result == "4 heures et demie"

    def test_french_midnight_still_uses_minuit(self):
        result = TimeFormatter.format_time(0, 0, "French", is_am_pm=False)
        assert result == "minuit"
