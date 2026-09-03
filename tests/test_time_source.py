#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for time_source.py
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

if not QApplication.instance():
    QApplication(sys.argv)

from defaults import (
    LTC_INPUT_AUDIO,
    TIME_SOURCE_LOCAL,
    TIME_SOURCE_LTC,
    TIME_SOURCE_NTP,
)
from time_source import (
    KIND_TIMECODE,
    KIND_WALLCLOCK,
    SteeredClock,
    TimeSample,
    TimeSourceManager,
    _normalize_ltc_channel,
    get_current_sample,
    set_manager,
    wall_datetime,
)


class TestTimeSample:
    def test_from_datetime(self):
        dt = datetime(2026, 8, 27, 14, 30, 45, 250000)
        sample = TimeSample.from_datetime(dt)
        assert sample.hours == 14
        assert sample.minutes == 30
        assert sample.seconds == 45
        assert sample.milliseconds == 250
        assert sample.running is True
        assert sample.locked is True
        assert sample.kind == KIND_WALLCLOCK
        assert sample.wall_datetime == dt
        assert sample.frames is None
        assert sample.source == ""

    def test_hold_is_frozen_timecode(self):
        sample = TimeSample.hold(10, 11, 12, 0, frames=7, frame_rate=25.0)
        assert sample.running is False
        assert sample.locked is False
        assert sample.kind == KIND_TIMECODE
        assert sample.frames == 7
        assert sample.wall_datetime is None


class TestSteeredClock:
    def test_before_lock_falls_back_to_system(self):
        clock = SteeredClock()
        sample = clock.sample()
        assert sample.kind == KIND_WALLCLOCK
        assert sample.locked is False
        assert sample.running is True

    def test_steers_from_reference_not_system_clock(self):
        clock = SteeredClock()
        ref = datetime(2020, 1, 1, 12, 0, 0)
        clock.set_reference(ref, monotonic_at=100.0)
        dt = clock.now(monotonic_now=101.5)
        assert dt == ref + timedelta(seconds=1.5)

    def test_system_clock_jump_does_not_move_steered_time(self):
        clock = SteeredClock()
        ref = datetime(2020, 1, 1, 12, 0, 0)
        clock.set_reference(ref, monotonic_at=50.0)
        with patch("time_source.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(1999, 1, 1, 0, 0, 0)
            dt = clock.now(monotonic_now=50.0)
        assert dt == ref

    def test_unlock_keeps_freewheeling(self):
        clock = SteeredClock()
        ref = datetime(2020, 1, 1, 12, 0, 0)
        clock.set_reference(ref, monotonic_at=10.0)
        clock.set_unlocked()
        assert clock.locked is False
        assert clock.ever_locked is True
        dt = clock.now(monotonic_now=12.0)
        assert dt == ref + timedelta(seconds=2)

    def test_hold_sample_freezes(self):
        clock = SteeredClock()
        hold = TimeSample.hold(1, 2, 3, 0, frames=12)
        clock.set_hold(hold)
        sample = clock.sample()
        assert sample.running is False
        assert sample.hours == 1
        assert sample.frames == 12
        assert clock.now() is None

    def test_reset_clears_lock(self):
        clock = SteeredClock()
        clock.set_reference(datetime(2020, 1, 1, 12, 0, 0), 1.0)
        clock.reset()
        assert clock.ever_locked is False
        assert clock.now() is None


class TestModuleHelpers:
    def test_get_current_sample_without_manager(self):
        set_manager(None)
        sample = get_current_sample()
        assert sample.kind == KIND_WALLCLOCK
        assert sample.running is True

    def test_get_current_sample_when_manager_returns_none(self):
        manager = Mock()
        manager.current_sample.return_value = None
        set_manager(manager)
        try:
            sample = get_current_sample()
            assert sample.kind == KIND_WALLCLOCK
            assert sample.running is True
        finally:
            set_manager(None)

    def test_wall_datetime_uses_sample_when_wallclock(self):
        dt = datetime(2026, 3, 1, 8, 15, 0)
        manager = Mock()
        manager.current_sample.return_value = TimeSample.from_datetime(dt)
        set_manager(manager)
        try:
            assert wall_datetime() == dt
        finally:
            set_manager(None)

    def test_wall_datetime_falls_back_for_timecode(self):
        manager = Mock()
        manager.current_sample.return_value = TimeSample.hold(10, 0, 0)
        set_manager(manager)
        try:
            now = wall_datetime()
            assert isinstance(now, datetime)
            assert now.year >= 2020
        finally:
            set_manager(None)


def _make_time_source_manager():
    """TimeSourceManager with apply_settings skipped (no QSettings / PTP)."""
    main_screen = QObject()
    main_screen.ntp_manager = Mock()
    main_screen.ntp_manager.ntp_had_warning = True
    main_screen.ntp_manager.ntp_warn_message = "waiting for NTP status check"
    main_screen.clockWidget = Mock()
    main_screen.add_warning = Mock()
    main_screen.remove_warning = Mock()
    with patch.object(TimeSourceManager, "apply_settings"):
        manager = TimeSourceManager(main_screen)
    manager._source = TIME_SOURCE_NTP
    return manager, main_screen


class TestTimeSourceManagerNtpLock:
    def test_waiting_for_ntp_is_not_locked(self):
        manager, _main = _make_time_source_manager()
        try:
            sample = manager.current_sample()
            assert sample.source == TIME_SOURCE_NTP
            assert sample.locked is False
            assert manager._warning_message() == "waiting for NTP status check"
        finally:
            set_manager(None)

    def test_sample_locked_follows_steered_clock(self):
        manager, main_screen = _make_time_source_manager()
        try:
            manager._steered.set_reference(datetime(2026, 1, 1, 12, 0, 0), 1.0)
            main_screen.ntp_manager.ntp_had_warning = True
            main_screen.ntp_manager.ntp_warn_message = "Clock not NTP synchronized"
            assert manager.current_sample().locked is True
            manager._steered.set_unlocked()
            assert manager.current_sample().locked is False
        finally:
            set_manager(None)

    def test_successful_ntp_sample_is_locked(self):
        manager, main_screen = _make_time_source_manager()
        try:
            main_screen.ntp_manager.ntp_had_warning = False
            manager._on_ntp_sample(datetime(2026, 1, 1, 12, 0, 0).timestamp(), 10.0)
            sample = manager.current_sample()
            assert sample.locked is True
            assert manager._warning_message() == ""
        finally:
            set_manager(None)

    def test_ntp_failure_unlocks_and_keeps_warning(self):
        manager, main_screen = _make_time_source_manager()
        try:
            main_screen.ntp_manager.ntp_had_warning = False
            manager._on_ntp_sample(datetime(2026, 1, 1, 12, 0, 0).timestamp(), 10.0)
            main_screen.ntp_manager.ntp_had_warning = True
            main_screen.ntp_manager.ntp_warn_message = "Clock not NTP synchronized"
            manager._on_ntp_failure()
            assert manager._steered.locked is False
            assert manager._steered.ever_locked is True
            sample = manager.current_sample()
            assert sample.locked is False
            assert manager._warning_message() == "Clock not NTP synchronized"
            main_screen.clockWidget.resync_time.assert_called()
        finally:
            set_manager(None)

    def test_timeout_without_prior_lock_shows_ntp_error_not_waiting(self):
        manager, main_screen = _make_time_source_manager()
        try:
            main_screen.ntp_manager.ntp_had_warning = True
            main_screen.ntp_manager.ntp_warn_message = "Clock not NTP synchronized"
            assert manager._steered.ever_locked is False
            assert manager._warning_message() == "Clock not NTP synchronized"
            assert manager.current_sample().locked is False
        finally:
            set_manager(None)

    def test_ntp_failure_ignored_when_source_is_local(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LOCAL
            manager._steered.set_reference(datetime(2026, 1, 1, 12, 0, 0), 1.0)
            manager._on_ntp_failure()
            assert manager._steered.locked is True
        finally:
            set_manager(None)

    def test_ntp_poll_failed_signal_is_queued(self):
        """NTP failure from a signal must not run until the GUI event loop processes it."""

        class FakeNtpManager(QObject):
            sample_ready = Signal(float, float)
            poll_failed = Signal()

        main_screen = QObject()
        main_screen.ntp_manager = FakeNtpManager()
        main_screen.clockWidget = Mock()
        main_screen.add_warning = Mock()
        main_screen.remove_warning = Mock()
        with patch.object(TimeSourceManager, "apply_settings"):
            manager = TimeSourceManager(main_screen)
        try:
            manager._source = TIME_SOURCE_NTP
            manager._steered.set_reference(datetime(2026, 1, 1, 12, 0, 0), 1.0)
            assert manager._steered.locked is True
            main_screen.ntp_manager.poll_failed.emit()
            assert manager._steered.locked is True
            QApplication.processEvents()
            assert manager._steered.locked is False
            main_screen.clockWidget.resync_time.assert_called()
        finally:
            set_manager(None)


class TestTimeSourceManagerLtc:
    def test_empty_sample_before_lock(self):
        manager, main_screen = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            main_screen.ntp_manager.ntp_had_warning = False
            sample = manager.current_sample()
            assert sample.kind == KIND_TIMECODE
            assert sample.running is False
            assert sample.locked is False
            assert sample.hours == 0
            assert sample.frames == 0
            assert sample.source == TIME_SOURCE_LTC
            assert manager._warning_message() == ""
        finally:
            set_manager(None)

    def test_waiting_for_lock_warning_when_enabled(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            manager._ltc_warn = True
            assert manager._warning_message() == "waiting for LTC lock"
        finally:
            set_manager(None)

    def test_frame_updates_sample_and_resyncs_clock(self):
        manager, main_screen = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            main_screen.ntp_manager.ntp_had_warning = False
            manager._on_ltc_frame(1, 2, 3, 12, 25.0, 10.0)
            sample = manager.current_sample()
            assert sample.locked is True
            assert sample.running is True
            assert sample.kind == KIND_TIMECODE
            assert sample.hours == 1
            assert sample.minutes == 2
            assert sample.seconds == 3
            assert sample.frames == 12
            assert sample.milliseconds == 480
            assert sample.wall_datetime is None
            main_screen.clockWidget.resync_time.assert_called()
            assert manager._warning_message() == ""
        finally:
            set_manager(None)

    def test_unlock_holds_last_sample(self):
        manager, main_screen = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            main_screen.ntp_manager.ntp_had_warning = False
            manager._on_ltc_frame(10, 11, 12, 7, 25.0, 1.0)
            manager._on_ltc_lock(False, "sync timeout")
            sample = manager.current_sample()
            assert sample.running is False
            assert sample.locked is False
            assert sample.hours == 10
            assert sample.frames == 7
            assert manager._warning_message() == ""
        finally:
            set_manager(None)

    def test_unlock_warning_when_enabled(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            manager._ltc_warn = True
            manager._on_ltc_frame(10, 11, 12, 7, 25.0, 1.0)
            manager._on_ltc_lock(False, "sync timeout")
            assert manager._warning_message() == "Clock not LTC synchronized"
            assert manager.current_sample().locked is False
        finally:
            set_manager(None)

    def test_not_connected_warning(self):
        manager, main_screen = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            main_screen.ntp_manager.ntp_had_warning = False
            manager._on_ltc_lock(False, "not connected")
            assert manager._warning_message() == ""
            sample = manager.current_sample()
            assert sample.locked is False
            assert sample.running is False
        finally:
            set_manager(None)

    def test_not_connected_warning_when_enabled(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            manager._ltc_warn = True
            manager._on_ltc_lock(False, "not connected")
            assert manager._warning_message() == "LTC reader not connected"
        finally:
            set_manager(None)

    def test_wall_datetime_stays_system_for_ltc(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            manager._on_ltc_frame(1, 2, 3, 0, 25.0, 1.0)
            set_manager(manager)
            now = wall_datetime()
            assert isinstance(now, datetime)
            assert now.year >= 2020
            assert manager.current_sample().wall_datetime is None
        finally:
            set_manager(None)

    def test_ltc_frame_ignored_when_source_is_local(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LOCAL
            manager._on_ltc_frame(1, 2, 3, 0, 25.0, 1.0)
            sample = manager.current_sample()
            assert sample.kind == KIND_WALLCLOCK
            assert sample.source == TIME_SOURCE_LOCAL
        finally:
            set_manager(None)

    def test_start_ltc_defaults_to_serial_reader(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            fake = Mock()
            fake.port = ""
            fake.is_running = True
            fake.input_kind = "serial"
            fake.frame_ready = Mock()
            fake.lock_changed = Mock()
            with patch("ltc_reader.LtcReader", return_value=fake) as ctor:
                manager._start_ltc()
            ctor.assert_called_once_with(port="")
            fake.start.assert_called_once()
            fake.frame_ready.connect.assert_called()
            fake.lock_changed.connect.assert_called()
            assert manager._ltc_reader is fake
        finally:
            manager._ltc_reader = None
            set_manager(None)

    def test_start_ltc_audio_uses_audio_reader(self):
        manager, _main = _make_time_source_manager()
        try:
            manager._source = TIME_SOURCE_LTC
            manager._ltc_input = LTC_INPUT_AUDIO
            manager._ltc_audio_device = "Mic"
            manager._ltc_audio_channel = 1
            fake = Mock()
            fake.device_name = "Mic"
            fake.channel = 1
            fake.is_running = True
            fake.input_kind = "audio"
            fake.frame_ready = Mock()
            fake.lock_changed = Mock()
            with patch("ltc_audio.LtcAudioReader", return_value=fake) as ctor:
                manager._start_ltc()
            ctor.assert_called_once_with(device_name="Mic", channel=1)
            fake.start.assert_called_once()
            assert manager._ltc_reader is fake
        finally:
            manager._ltc_reader = None
            set_manager(None)

    def test_start_ltc_audio_replaces_serial_reader(self):
        manager, _main = _make_time_source_manager()
        try:
            serial_reader = Mock()
            serial_reader.port = ""
            serial_reader.is_running = True
            serial_reader.input_kind = "serial"
            manager._ltc_reader = serial_reader
            manager._source = TIME_SOURCE_LTC
            manager._ltc_input = LTC_INPUT_AUDIO
            audio_reader = Mock()
            audio_reader.device_name = ""
            audio_reader.channel = 0
            audio_reader.is_running = True
            audio_reader.input_kind = "audio"
            audio_reader.frame_ready = Mock()
            audio_reader.lock_changed = Mock()
            with patch("ltc_audio.LtcAudioReader", return_value=audio_reader):
                manager._start_ltc()
            serial_reader.stop.assert_called_once()
            audio_reader.start.assert_called_once()
            assert manager._ltc_reader is audio_reader
        finally:
            manager._ltc_reader = None
            set_manager(None)


class TestNormalizeLtcChannel:
    def test_left_right_and_invalid(self):
        assert _normalize_ltc_channel(0) == 0
        assert _normalize_ltc_channel(1) == 1
        assert _normalize_ltc_channel(9) == 1
        assert _normalize_ltc_channel("1") == 1
        assert _normalize_ltc_channel("nope") == 0
