#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for silence_detector.py
"""

from silence_detector import SILENCE_FLOOR_DBFS, SilenceDetector, SilenceState


class TestSilenceDetectorDuration:
    def test_stays_quiet_below_duration(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=10.0, recovery_s=2.0)
        changed, active = detector.process(-60.0, 0.0)
        assert changed is False
        assert active is False
        changed, active = detector.process(-60.0, 9.9)
        assert changed is False
        assert active is False
        assert detector.state == SilenceState.TIMING

    def test_triggers_after_duration(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=10.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        changed, active = detector.process(-60.0, 10.0)
        assert changed is True
        assert active is True
        assert detector.state == SilenceState.ACTIVE

    def test_equal_to_threshold_is_not_silence(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=1.0)
        changed, active = detector.process(-50.0, 0.0)
        assert changed is False
        assert active is False
        assert detector.state == SilenceState.QUIET

    def test_above_threshold_during_timing_resets(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=10.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        detector.process(-60.0, 5.0)
        changed, active = detector.process(-40.0, 5.1)
        assert changed is False
        assert active is False
        assert detector.state == SilenceState.QUIET
        detector.process(-60.0, 5.2)
        changed, active = detector.process(-60.0, 14.1)
        assert changed is False
        assert active is False


class TestSilenceDetectorRecovery:
    def test_recovery_holds_alarm_until_time_elapsed(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        detector.process(-60.0, 1.0)
        assert detector.is_active is True

        changed, active = detector.process(-20.0, 1.1)
        assert changed is False
        assert active is True
        assert detector.state == SilenceState.RECOVERING

        changed, active = detector.process(-20.0, 2.9)
        assert changed is False
        assert active is True

        changed, active = detector.process(-20.0, 3.1)
        assert changed is True
        assert active is False
        assert detector.state == SilenceState.QUIET

    def test_dip_during_recovery_returns_to_active(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        detector.process(-60.0, 1.0)
        detector.process(-20.0, 1.1)
        assert detector.state == SilenceState.RECOVERING

        changed, active = detector.process(-60.0, 1.5)
        assert changed is False
        assert active is True
        assert detector.state == SilenceState.ACTIVE

        # Must recover from the new above-threshold stretch, not the aborted one.
        detector.process(-20.0, 1.6)
        changed, active = detector.process(-20.0, 3.5)
        assert changed is False
        assert active is True
        changed, active = detector.process(-20.0, 3.6)
        assert changed is True
        assert active is False

    def test_zero_recovery_clears_immediately(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=0.0)
        detector.process(-60.0, 0.0)
        detector.process(-60.0, 1.0)
        changed, active = detector.process(-20.0, 1.1)
        assert changed is True
        assert active is False
        assert detector.state == SilenceState.QUIET


class TestSilenceDetectorReset:
    def test_reset_clears_active_alarm(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        detector.process(-60.0, 1.0)
        assert detector.is_active is True
        assert detector.reset() is True
        assert detector.is_active is False
        assert detector.state == SilenceState.QUIET

    def test_reset_when_quiet_returns_false(self):
        detector = SilenceDetector()
        assert detector.reset() is False

    def test_reset_during_timing(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=10.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        assert detector.reset() is False
        detector.process(-60.0, 20.0)
        changed, active = detector.process(-60.0, 29.9)
        assert changed is False
        assert active is False


class TestSilenceDetectorAbsent:
    """Absent capture is modelled as feeding SILENCE_FLOOR_DBFS (on) vs reset (off)."""

    def test_floor_level_triggers_after_duration(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=10.0, recovery_s=2.0)
        detector.process(SILENCE_FLOOR_DBFS, 0.0)
        changed, active = detector.process(SILENCE_FLOOR_DBFS, 10.0)
        assert changed is True
        assert active is True

    def test_reset_on_absent_off_clears_without_stuck_true(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=2.0)
        detector.process(SILENCE_FLOOR_DBFS, 0.0)
        detector.process(SILENCE_FLOOR_DBFS, 1.0)
        assert detector.is_active is True
        detector.reset()
        assert detector.is_active is False
        # Without further floor samples the alarm must stay clear.
        assert detector.state == SilenceState.QUIET


class TestSilenceDetectorConfigure:
    def test_configure_does_not_reset_active(self):
        detector = SilenceDetector(threshold_dbfs=-50.0, duration_s=1.0, recovery_s=2.0)
        detector.process(-60.0, 0.0)
        detector.process(-60.0, 1.0)
        detector.configure(threshold_dbfs=-40.0, duration_s=5.0, recovery_s=3.0)
        assert detector.is_active is True
        assert detector.threshold_dbfs == -40.0
        assert detector.duration_s == 5.0
        assert detector.recovery_s == 3.0
