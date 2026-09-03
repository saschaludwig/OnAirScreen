#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# silence_detector.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Silence detector: duration / recovery state machine for sample-peak dBFS.
"""

from __future__ import annotations

from enum import Enum


# Same floor as meter_engine.linear_to_db(); used when no capture is running.
SILENCE_FLOOR_DBFS = -120.0


class SilenceState(str, Enum):
    """Internal detector states."""

    QUIET = "quiet"
    TIMING = "timing"
    ACTIVE = "active"
    RECOVERING = "recovering"


class SilenceDetector:
    """
    Track consecutive time below a dBFS threshold and raise/clear a silence alarm.

    States:
    - quiet: level is above threshold
    - timing: below threshold, waiting for duration
    - active: silence alarm is on
    - recovering: above threshold after an alarm, waiting for recovery time
    """

    def __init__(
        self,
        threshold_dbfs: float = -50.0,
        duration_s: float = 10.0,
        recovery_s: float = 2.0,
    ) -> None:
        self.threshold_dbfs = float(threshold_dbfs)
        self.duration_s = max(0.1, float(duration_s))
        self.recovery_s = max(0.0, float(recovery_s))
        self.state = SilenceState.QUIET
        self._below_since_s: float | None = None
        self._above_since_s: float | None = None

    @property
    def is_active(self) -> bool:
        """True while the silence alarm is latched (active or recovering)."""
        return self.state in (SilenceState.ACTIVE, SilenceState.RECOVERING)

    def configure(
        self,
        threshold_dbfs: float | None = None,
        duration_s: float | None = None,
        recovery_s: float | None = None,
    ) -> None:
        """Update thresholds without resetting the current state."""
        if threshold_dbfs is not None:
            self.threshold_dbfs = float(threshold_dbfs)
        if duration_s is not None:
            self.duration_s = max(0.1, float(duration_s))
        if recovery_s is not None:
            self.recovery_s = max(0.0, float(recovery_s))

    def reset(self) -> bool:
        """
        Clear timing and alarm state.

        Returns:
            True if the alarm was active and is now cleared.
        """
        was_active = self.is_active
        self.state = SilenceState.QUIET
        self._below_since_s = None
        self._above_since_s = None
        return was_active

    def process(self, level_dbfs: float, now_s: float) -> tuple[bool, bool]:
        """
        Feed a sample-peak dBFS reading.

        Args:
            level_dbfs: Current peak level in dBFS (use SILENCE_FLOOR_DBFS for absent capture).
            now_s: Monotonic timestamp in seconds.

        Returns:
            (changed, active) where changed is True if the alarm latched or cleared.
        """
        was_active = self.is_active
        below = float(level_dbfs) < self.threshold_dbfs

        if below:
            self._above_since_s = None
            if self.state == SilenceState.QUIET:
                self.state = SilenceState.TIMING
                self._below_since_s = now_s
            elif self.state == SilenceState.TIMING:
                if self._below_since_s is None:
                    self._below_since_s = now_s
                if (now_s - self._below_since_s) >= self.duration_s:
                    self.state = SilenceState.ACTIVE
            elif self.state == SilenceState.RECOVERING:
                self.state = SilenceState.ACTIVE
                self._below_since_s = now_s
            # ACTIVE: stay active
        else:
            self._below_since_s = None
            if self.state == SilenceState.TIMING:
                self.state = SilenceState.QUIET
            elif self.state == SilenceState.ACTIVE:
                if self.recovery_s <= 0.0:
                    self.state = SilenceState.QUIET
                    self._above_since_s = None
                else:
                    self.state = SilenceState.RECOVERING
                    self._above_since_s = now_s
            elif self.state == SilenceState.RECOVERING:
                if self._above_since_s is None:
                    self._above_since_s = now_s
                if (now_s - self._above_since_s) >= self.recovery_s:
                    self.state = SilenceState.QUIET
                    self._above_since_s = None
            # QUIET: stay quiet

        active = self.is_active
        return was_active != active, active
