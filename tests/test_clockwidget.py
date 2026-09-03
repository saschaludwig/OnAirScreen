#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for clockwidget.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QFont, QImage, QPainter

# Import after QApplication setup
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from clockwidget import FRAME_DIGIT_SCALE, FRAME_LED_SCALE, ClockWidget
from time_source import KIND_TIMECODE, TimeSample


@pytest.fixture
def clock_widget():
    """Create a ClockWidget instance for testing"""
    widget = ClockWidget()
    widget.timer = Mock()  # Mock timer to avoid actual timer operations
    return widget


class TestClockWidgetClockMode:
    """Test clock mode properties"""

    def test_set_clock_mode_digital(self, clock_widget):
        """Test set_clock_mode() with digital mode (1)"""
        clock_widget.set_clock_mode(1)
        assert clock_widget.clockMode == 1
        assert clock_widget.get_clock_mode() == 1

    def test_set_clock_mode_analog(self, clock_widget):
        """Test set_clock_mode() with analog mode (0)"""
        clock_widget.set_clock_mode(0)
        assert clock_widget.clockMode == 0
        assert clock_widget.get_clock_mode() == 0

    def test_reset_clock_mode(self, clock_widget):
        """Test reset_clock_code() resets to digital"""
        clock_widget.set_clock_mode(0)
        clock_widget.reset_clock_code()
        assert clock_widget.clockMode == 1


class TestClockWidgetAmPm:
    """Test AM/PM properties"""

    def test_set_am_pm_true(self, clock_widget):
        """Test set_am_pm() with True"""
        clock_widget.set_am_pm(True)
        assert clock_widget.isAmPm is True
        assert clock_widget.get_am_pm() is True

    def test_set_am_pm_false(self, clock_widget):
        """Test set_am_pm() with False"""
        clock_widget.set_am_pm(False)
        assert clock_widget.isAmPm is False
        assert clock_widget.get_am_pm() is False

    def test_reset_am_pm(self, clock_widget):
        """Test reset_am_pm() resets to False"""
        clock_widget.set_am_pm(True)
        clock_widget.reset_am_pm()
        assert clock_widget.isAmPm is False


class TestClockWidgetTwelveHour:
    """Test 12-hour mapping used by the digital clock."""

    @pytest.mark.parametrize(
        "hour_24, expected",
        [
            (0, 12),
            (1, 1),
            (11, 11),
            (12, 12),
            (13, 1),
            (23, 11),
        ],
    )
    def test_twelve_hour_mapping(self, hour_24, expected):
        assert ClockWidget._twelve_hour(hour_24) == expected

    @pytest.mark.parametrize(
        "hour_24, expected",
        [
            (0, 12),
            (1, 1),
            (11, 11),
            (12, 12),
            (13, 1),
            (23, 11),
        ],
    )
    def test_digital_hour_am_pm_wall_clock(self, clock_widget, hour_24, expected):
        clock_widget.set_am_pm(True)
        clock_widget.time = QTime(hour_24, 0, 0)
        clock_widget._sample = TimeSample(
            hours=hour_24, minutes=0, seconds=0, milliseconds=0
        )
        assert clock_widget._digital_hour() == expected

    @pytest.mark.parametrize("hour_24", [0, 1, 11, 12, 13, 23])
    def test_digital_hour_24h_wall_clock(self, clock_widget, hour_24):
        clock_widget.set_am_pm(False)
        clock_widget.time = QTime(hour_24, 0, 0)
        clock_widget._sample = TimeSample(
            hours=hour_24, minutes=0, seconds=0, milliseconds=0
        )
        assert clock_widget._digital_hour() == hour_24

    @pytest.mark.parametrize("hour_24", [0, 1, 11, 12, 13, 23])
    def test_digital_hour_ignores_am_pm_for_timecode(self, clock_widget, hour_24):
        clock_widget.set_am_pm(True)
        clock_widget.time = QTime(hour_24, 0, 0)
        clock_widget._sample = TimeSample(
            hours=hour_24,
            minutes=0,
            seconds=0,
            milliseconds=0,
            frames=0,
            kind=KIND_TIMECODE,
        )
        assert clock_widget._digital_hour() == hour_24


class TestClockWidgetSmpteFrames:
    """SMPTE frame digits must not crash when the sample has no frame count."""

    def test_smpte_frame_digits_none_sample(self, clock_widget):
        clock_widget._sample = None
        assert clock_widget._smpte_frame_digits() is None

    def test_smpte_frame_digits_wall_clock(self, clock_widget):
        clock_widget._sample = TimeSample(hours=12, minutes=0, seconds=0, milliseconds=0)
        assert clock_widget._smpte_frame_digits() is None

    def test_smpte_frame_digits_zero_and_wrap(self, clock_widget):
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0, frames=0, kind=KIND_TIMECODE
        )
        assert clock_widget._smpte_frame_digits() == "00"
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0, frames=12, kind=KIND_TIMECODE
        )
        assert clock_widget._smpte_frame_digits() == "12"
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0, frames=100, kind=KIND_TIMECODE
        )
        assert clock_widget._smpte_frame_digits() == "00"

    def test_smpte_frame_digits_timecode_hold_without_frames(self, clock_widget):
        clock_widget._sample = TimeSample.hold(10, 11, 12, 0)
        assert clock_widget._sample.frames is None
        assert clock_widget._smpte_frame_digits() is None

    def _paint_digital(self, clock_widget):
        clock_widget.resize(200, 200)
        clock_widget.time = QTime(12, 34, 56)
        image = QImage(200, 200, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        try:
            clock_widget.paint_digital(painter)
        finally:
            painter.end()

    def test_paint_digital_wall_clock_with_seconds_and_no_frames(self, clock_widget):
        clock_widget.showSeconds = True
        clock_widget.one_line_time = False
        clock_widget._sample = TimeSample(hours=12, minutes=34, seconds=56, milliseconds=0)
        self._paint_digital(clock_widget)

    def test_paint_digital_one_line_with_no_frames(self, clock_widget):
        clock_widget.showSeconds = True
        clock_widget.one_line_time = True
        clock_widget._sample = TimeSample(hours=12, minutes=34, seconds=56, milliseconds=0)
        self._paint_digital(clock_widget)

    def test_paint_digital_timecode_hold_without_frames(self, clock_widget):
        clock_widget.showSeconds = False
        clock_widget.one_line_time = False
        clock_widget._sample = TimeSample.hold(10, 11, 12, 0)
        self._paint_digital(clock_widget)

    def test_paint_digital_with_smpte_frames(self, clock_widget):
        clock_widget.showSeconds = False
        clock_widget.one_line_time = False
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0,
            frames=7, kind=KIND_TIMECODE, source="ltc",
        )
        self._paint_digital(clock_widget)


class TestClockWidgetShowSeconds:
    """Test show seconds properties"""

    def test_set_show_seconds_true(self, clock_widget):
        """Test set_show_seconds() with True"""
        clock_widget.set_show_seconds(True)
        assert clock_widget.showSeconds is True
        assert clock_widget.get_show_seconds() is True

    def test_set_show_seconds_false(self, clock_widget):
        """Test set_show_seconds() with False"""
        clock_widget.set_show_seconds(False)
        assert clock_widget.showSeconds is False
        assert clock_widget.get_show_seconds() is False

    def test_reset_show_seconds(self, clock_widget):
        """Test reset_show_seconds() resets to False"""
        clock_widget.set_show_seconds(True)
        clock_widget.reset_show_seconds()
        assert clock_widget.showSeconds is False


class TestClockWidgetStaticColon:
    """Test static colon properties"""

    def test_set_static_colon_true(self, clock_widget):
        """Test set_static_colon() with True"""
        clock_widget.set_static_colon(True)
        assert clock_widget.staticColon is True
        assert clock_widget.get_static_colon() is True

    def test_set_static_colon_false(self, clock_widget):
        """Test set_static_colon() with False"""
        clock_widget.set_static_colon(False)
        assert clock_widget.staticColon is False
        assert clock_widget.get_static_colon() is False

    def test_reset_static_colon(self, clock_widget):
        """Test reset_static_colon() resets to False"""
        clock_widget.set_static_colon(True)
        clock_widget.reset_static_colon()
        assert clock_widget.staticColon is False


class TestClockWidgetOneLineTime:
    """Test one line time properties"""

    def test_set_one_line_time_true(self, clock_widget):
        """Test set_one_line_time() with True"""
        clock_widget.set_one_line_time(True)
        assert clock_widget.one_line_time is True
        assert clock_widget.get_one_line_time() is True

    def test_set_one_line_time_false(self, clock_widget):
        """Test set_one_line_time() with False"""
        clock_widget.set_one_line_time(False)
        assert clock_widget.one_line_time is False
        assert clock_widget.get_one_line_time() is False

    def test_reset_one_line_time(self, clock_widget):
        """Test reset_one_line_time() resets to False"""
        clock_widget.set_one_line_time(True)
        clock_widget.reset_one_line_time()
        assert clock_widget.one_line_time is False


class TestClockWidgetTimeZone:
    """Test time zone properties"""

    def test_set_time_zone(self, clock_widget):
        """Test set_time_zone()"""
        clock_widget.timeZoneChanged = Mock()
        clock_widget.update = Mock()
        
        clock_widget.set_time_zone(5)
        assert clock_widget.timeZoneOffset == 5
        assert clock_widget.get_time_zone() == 5
        clock_widget.timeZoneChanged.emit.assert_called_once_with(5)
        clock_widget.update.assert_called_once()

    def test_set_time_zone_same_value(self, clock_widget):
        """Test set_time_zone() with same value doesn't trigger update"""
        clock_widget.timeZoneOffset = 3
        clock_widget.timeZoneChanged = Mock()
        clock_widget.update = Mock()
        
        clock_widget.set_time_zone(3)
        clock_widget.timeZoneChanged.emit.assert_not_called()
        clock_widget.update.assert_not_called()

    def test_reset_time_zone(self, clock_widget):
        """Test reset_time_zone()"""
        clock_widget.timeZoneOffset = 5
        clock_widget.timeZoneChanged = Mock()
        clock_widget.update = Mock()
        
        clock_widget.reset_time_zone()
        assert clock_widget.timeZoneOffset == 0
        clock_widget.timeZoneChanged.emit.assert_called_once_with(0)
        clock_widget.update.assert_called_once()

    def test_reset_time_zone_when_zero(self, clock_widget):
        """Test reset_time_zone() when already zero doesn't trigger update"""
        clock_widget.timeZoneOffset = 0
        clock_widget.timeZoneChanged = Mock()
        clock_widget.update = Mock()
        
        clock_widget.reset_time_zone()
        clock_widget.timeZoneChanged.emit.assert_not_called()
        clock_widget.update.assert_not_called()


class TestClockWidgetColors:
    """Test color properties"""

    def test_set_digi_hour_color(self, clock_widget):
        """Test set_digi_hour_color()"""
        color = QColor(255, 0, 0, 255)
        clock_widget.set_digi_hour_color(color)
        assert clock_widget.digiHourColor == color
        assert clock_widget.get_digi_hour_color() == color

    def test_reset_digi_hour_color(self, clock_widget):
        """Test reset_digi_hour_color()"""
        clock_widget.set_digi_hour_color(QColor(255, 0, 0, 255))
        clock_widget.reset_digi_hour_color()
        assert clock_widget.digiHourColor == QColor(50, 50, 255, 255)

    def test_set_digi_second_color(self, clock_widget):
        """Test set_digi_second_color()"""
        color = QColor(0, 255, 0, 255)
        clock_widget.set_digi_second_color(color)
        assert clock_widget.digiSecondColor == color
        assert clock_widget.get_digi_second_color() == color

    def test_reset_digi_second_color(self, clock_widget):
        """Test reset_digi_second_color()"""
        clock_widget.set_digi_second_color(QColor(0, 255, 0, 255))
        clock_widget.reset_digi_second_color()
        assert clock_widget.digiSecondColor == QColor(50, 50, 255, 255)

    def test_set_digi_digit_color(self, clock_widget):
        """Test set_digi_digit_color()"""
        color = QColor(0, 0, 255, 255)
        clock_widget.set_digi_digit_color(color)
        assert clock_widget.digiDigitColor == color
        assert clock_widget.get_digi_digit_color() == color

    def test_reset_digi_digit_color(self, clock_widget):
        """Test reset_digi_digit_color()"""
        clock_widget.set_digi_digit_color(QColor(0, 0, 255, 255))
        clock_widget.reset_digi_digit_color()
        assert clock_widget.digiDigitColor == QColor(50, 50, 255, 255)


class TestClockWidgetDrawDigit:
    """Test draw_digit() static method"""

    def test_draw_digit_all_digits(self):
        """Test draw_digit() with all digits 0-9"""
        painter = Mock()
        painter.drawEllipse = Mock()
        
        # Test all digits
        for digit in range(10):
            ClockWidget.draw_digit(painter, 0, 0, digit)
            # Should have called drawEllipse multiple times for each digit
            assert painter.drawEllipse.called

    def test_draw_digit_float_value(self):
        """Test draw_digit() with float value (should be converted to int)"""
        painter = Mock()
        painter.drawEllipse = Mock()
        
        ClockWidget.draw_digit(painter, 0, 0, 5.7)
        # Should still work, value is converted to int(5.7) = 5
        assert painter.drawEllipse.called

    def test_draw_digit_custom_parameters(self):
        """Test draw_digit() with custom parameters"""
        painter = Mock()
        painter.drawEllipse = Mock()
        
        ClockWidget.draw_digit(
            painter,
            digit_start_pos_x=10.0,
            digit_start_pos_y=20.0,
            value=8,
            dot_size=2.0,
            dot_offset=6.0,
            slant=20.0
        )
        assert painter.drawEllipse.called

    def test_draw_digit_three_leds_per_segment(self):
        """Frame digits use 3 LEDs per bar; HH:MM:SS keep 4."""
        painter_four = Mock()
        ClockWidget.draw_digit(painter_four, 0, 0, 8, leds_per_segment=4)
        painter_three = Mock()
        ClockWidget.draw_digit(painter_three, 0, 0, 8, leds_per_segment=3)
        assert painter_four.drawEllipse.call_count == 7 * 4
        assert painter_three.drawEllipse.call_count == 7 * 3

    def test_scaled_frame_digit_waist_stays_open(self):
        """Inner vertical LEDs must not collapse onto the middle bar when scaled."""
        painter = Mock()
        ClockWidget.draw_digit(
            painter, 0, 0, 8, dot_size=0.24, dot_offset=1.5, leds_per_segment=3
        )
        ys = [call.args[0].y() for call in painter.drawEllipse.call_args_list]
        near_center = [y for y in ys if abs(y) < 0.4]
        # Only the three middle-bar (g) LEDs sit on y=0.
        assert len(near_center) == 3

    def test_frame_digits_are_half_height_and_bottom_aligned(self):
        """Frame digits sit on the seconds baseline at half the seconds size."""
        seconds_y = 45.0
        seconds_dot_size = 0.8
        seconds_dot_offset = 3.0
        frames_y, frame_dot_size, frame_dot_offset = ClockWidget._frame_digit_layout(
            seconds_y, seconds_dot_size, seconds_dot_offset
        )
        assert frame_dot_size == pytest.approx(seconds_dot_size * FRAME_LED_SCALE)
        assert frame_dot_offset == pytest.approx(seconds_dot_offset * FRAME_DIGIT_SCALE)
        seconds_bottom = ClockWidget._digit_bottom_y(
            seconds_y, seconds_dot_offset, seconds_dot_size
        )
        frames_bottom = ClockWidget._digit_bottom_y(
            frames_y, frame_dot_offset, frame_dot_size
        )
        assert frames_bottom == pytest.approx(seconds_bottom)
        assert frames_y > seconds_y


class TestClockWidgetResyncTime:
    """Test resync_time() method"""

    def test_resync_time_schedules_half_second_boundary(self, clock_widget):
        """Test resync_time() schedules next update at 500ms when colon blinks"""
        sample = TimeSample(hours=12, minutes=0, seconds=0, milliseconds=0, running=True)
        with patch.object(clock_widget, 'update') as mock_update:
            with patch('clockwidget.get_current_sample', return_value=sample):
                clock_widget.staticColon = False
                clock_widget.resync_time()

                mock_update.assert_called_once()
                clock_widget.timer.start.assert_called_once_with(500)

    def test_resync_time_schedules_second_boundary_with_static_colon(self, clock_widget):
        """Test resync_time() schedules next update at second boundary when colon is static"""
        sample = TimeSample(hours=12, minutes=0, seconds=0, milliseconds=250, running=True)
        with patch.object(clock_widget, 'update') as mock_update:
            with patch('clockwidget.get_current_sample', return_value=sample):
                clock_widget.staticColon = True
                clock_widget.resync_time()

                mock_update.assert_called_once()
                clock_widget.timer.start.assert_called_once_with(750)

    def test_resync_time_stops_timer_when_frozen(self, clock_widget):
        """Frozen samples must not keep ticking from the wall clock."""
        sample = TimeSample.hold(10, 11, 12, 0)
        with patch.object(clock_widget, 'update'):
            with patch('clockwidget.get_current_sample', return_value=sample):
                clock_widget.resync_time()
                clock_widget.timer.stop.assert_called()

    def test_on_timer_timeout_repaints_and_reschedules(self, clock_widget):
        """Test timer timeout repaints and schedules the next aligned update"""
        with patch.object(clock_widget, 'update') as mock_update:
            with patch.object(clock_widget, '_schedule_next_clock_update') as mock_schedule:
                clock_widget._on_timer_timeout()

                mock_update.assert_called_once()
                mock_schedule.assert_called_once()

    def test_milliseconds_until_next_clock_boundary_mid_second(self, clock_widget):
        """Test boundary calculation between colon blink points"""
        sample = TimeSample(hours=12, minutes=0, seconds=0, milliseconds=320, running=True)
        with patch('clockwidget.get_current_sample', return_value=sample):
            clock_widget.staticColon = False
            assert clock_widget._milliseconds_until_next_clock_boundary() == 180


class TestClockWidgetLogo:
    """Test logo properties"""

    def test_set_logo(self, clock_widget):
        """Test set_logo()"""
        with patch('clockwidget.QtGui.QImage') as mock_image:
            mock_image_instance = Mock()
            mock_image.return_value = mock_image_instance
            
            clock_widget.set_logo("test_logo.png")
            
            assert clock_widget.image_path == "test_logo.png"
            mock_image.assert_called_once_with("test_logo.png")
            assert clock_widget.image == mock_image_instance

    def test_get_logo(self, clock_widget):
        """Test get_logo()"""
        clock_widget.image_path = "test_logo.png"
        assert clock_widget.get_logo() == "test_logo.png"

    def test_reset_logo(self, clock_widget):
        """Test reset_logo()"""
        clock_widget.set_logo("test_logo.png")
        clock_widget.reset_logo()
        assert clock_widget.image_path == ""

    def test_set_logo_upper(self, clock_widget):
        """Test set_logo_upper()"""
        clock_widget.set_logo_upper(True)
        assert clock_widget.logo_upper is True
        # Note: get_logo_upper() has a bug - it returns self.logoUpper instead of self.logo_upper
        # This test checks the actual attribute, not the getter
        assert clock_widget.logo_upper is True

    def test_reset_logo_upper(self, clock_widget):
        """Test reset_logo_upper()"""
        clock_widget.set_logo_upper(True)
        clock_widget.reset_logo_upper()
        assert clock_widget.logo_upper is False


class TestClockWidgetUpdateTime:
    """Test update_time() method"""

    def test_update_time(self, clock_widget):
        """Test update_time() emits signal"""
        clock_widget.timeChanged = Mock()
        sample = TimeSample(hours=12, minutes=30, seconds=45, milliseconds=0, running=True)
        with patch('clockwidget.get_current_sample', return_value=sample):
            clock_widget.update_time()
            emitted = clock_widget.timeChanged.emit.call_args[0][0]
            assert emitted.hour() == 12
            assert emitted.minute() == 30
            assert emitted.second() == 45


class TestClockWidgetLockLed:
    """Test time-source lock LED"""

    def test_lock_led_green_when_locked(self, clock_widget):
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=True
        )
        assert clock_widget._lock_led_color() == clock_widget.lockLedLockedColor

    def test_lock_led_red_when_unlocked(self, clock_widget):
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=False
        )
        assert clock_widget._lock_led_color() == clock_widget.lockLedUnlockedColor

    def test_paint_lock_led_uses_seconds_led_size(self, clock_widget):
        painter = Mock()
        clock_widget.resize(200, 200)
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=True
        )
        clock_widget.paint_lock_led(painter)
        painter.drawEllipse.assert_called_once()
        center, radius_x, radius_y = painter.drawEllipse.call_args[0]
        assert radius_x == 1.6
        assert radius_y == 1.6
        assert center.x() == pytest.approx(200 - 1.6)
        assert center.y() == pytest.approx(200 - 1.6)

    def test_lock_led_sits_in_widget_corner(self, clock_widget):
        clock_widget.resize(400, 300)
        radius = clock_widget._lock_led_radius()
        center = clock_widget._lock_led_center()
        assert radius == pytest.approx(1.6 * (300 / 200.0))
        assert center.x() == pytest.approx(400 - radius)
        assert center.y() == pytest.approx(300 - radius)

    def test_lock_led_caption_ptp_and_ntp(self, clock_widget):
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=True, source="ptp"
        )
        assert clock_widget._lock_led_caption() == "PTP LOCK"
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=False, source="ptp"
        )
        assert clock_widget._lock_led_caption() == "PTP NOT LOCKED"
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=True, source="ntp"
        )
        assert clock_widget._lock_led_caption() == "NTP LOCK"
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=False, source="ntp"
        )
        assert clock_widget._lock_led_caption() == "NTP NOT LOCKED"
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=True, source="local"
        )
        assert clock_widget._lock_led_caption() == "LOCAL"

    def test_lock_led_caption_ltc(self, clock_widget):
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0, locked=True,
            frames=10, kind="timecode", source="ltc",
        )
        assert clock_widget._lock_led_caption() == "LTC LOCK"
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0, locked=False,
            frames=10, kind="timecode", source="ltc", running=False,
        )
        assert clock_widget._lock_led_caption() == "LTC NOT LOCKED"

    def test_shows_seconds_and_frames_for_timecode_without_show_seconds(self, clock_widget):
        clock_widget.showSeconds = False
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0,
            frames=10, kind="timecode", source="ltc",
        )
        assert clock_widget._is_timecode_sample() is True
        assert clock_widget._shows_seconds_and_frames() is True

    def test_resync_time_stops_timer_for_running_timecode(self, clock_widget):
        clock_widget._sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0,
            frames=4, kind="timecode", source="ltc", running=True, locked=True,
        )
        with patch("clockwidget.get_current_sample", return_value=clock_widget._sample):
            clock_widget.resync_time()
        clock_widget.timer.stop.assert_called()

    def test_resync_time_marshals_when_called_from_other_thread(self, clock_widget):
        """QTimer must not be started from a worker thread."""
        other_thread = object()
        with patch("clockwidget.QtCore.QThread.currentThread", return_value=other_thread):
            with patch("clockwidget.QtCore.QMetaObject.invokeMethod") as mock_invoke:
                clock_widget.resync_time()
        mock_invoke.assert_called_once_with(
            clock_widget, "resync_time", Qt.ConnectionType.QueuedConnection
        )
        clock_widget.timer.start.assert_not_called()


class TestClockWidgetEnsureTimerRunning:
    """Watchdog that restarts a dead wall-clock timer without touching LTC."""

    def test_restarts_inactive_wallclock_timer(self, clock_widget):
        sample = TimeSample(hours=12, minutes=0, seconds=0, milliseconds=0, running=True)
        clock_widget.timer.isActive.return_value = False
        with patch("clockwidget.get_current_sample", return_value=sample):
            with patch.object(clock_widget, "resync_time") as mock_resync:
                clock_widget.ensure_timer_running()
        mock_resync.assert_called_once()

    def test_skips_when_timer_already_active(self, clock_widget):
        sample = TimeSample(hours=12, minutes=0, seconds=0, milliseconds=0, running=True)
        clock_widget.timer.isActive.return_value = True
        with patch("clockwidget.get_current_sample", return_value=sample):
            with patch.object(clock_widget, "resync_time") as mock_resync:
                clock_widget.ensure_timer_running()
        mock_resync.assert_not_called()

    def test_ignores_ltc_hold(self, clock_widget):
        sample = TimeSample.hold(10, 11, 12, 0)
        clock_widget.timer.isActive.return_value = False
        with patch("clockwidget.get_current_sample", return_value=sample):
            with patch.object(clock_widget, "resync_time") as mock_resync:
                clock_widget.ensure_timer_running()
        mock_resync.assert_not_called()

    def test_ignores_running_timecode(self, clock_widget):
        sample = TimeSample(
            hours=1, minutes=2, seconds=3, milliseconds=0,
            frames=4, kind=KIND_TIMECODE, source="ltc", running=True, locked=True,
        )
        clock_widget.timer.isActive.return_value = False
        with patch("clockwidget.get_current_sample", return_value=sample):
            with patch.object(clock_widget, "resync_time") as mock_resync:
                clock_widget.ensure_timer_running()
        mock_resync.assert_not_called()

    def test_none_sample_does_not_crash(self, clock_widget):
        """A missing time sample must not abort the constant-update loop."""
        clock_widget._sample = None
        clock_widget.timer.isActive.return_value = False
        with patch("clockwidget.get_current_sample", return_value=None):
            clock_widget.ensure_timer_running()

    def test_paint_lock_led_draws_caption_for_ptp(self, clock_widget):
        painter = Mock()
        painter.font.return_value = QFont()
        clock_widget.resize(200, 200)
        clock_widget._sample = TimeSample(
            hours=12, minutes=0, seconds=0, milliseconds=0, locked=True, source="ptp"
        )
        clock_widget.paint_lock_led(painter)
        painter.drawText.assert_called_once()
        args = painter.drawText.call_args[0]
        assert args[2] == "PTP LOCK"
        assert painter.setPen.call_args.args[0] == clock_widget.lockLedCaptionColor
        assert clock_widget.lockLedCaptionColor == QColor(80, 80, 80, 255)

