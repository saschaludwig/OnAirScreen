#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# time_source.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Time source abstraction for OnAirScreen.

Display time is a TimeSample. Local uses the system clock. NTP and PTP steer
an independent clock from reference samples plus time.monotonic(), so system
clock jumps do not move the display. The LTC provider (LBE-1110 serial or
local audio decode) may freeze, jump, or carry SMPTE frames without changing
ClockWidget.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtCore import QObject, QSettings, Qt

from defaults import (
    DEFAULT_LTC_AUDIO_CHANNEL,
    DEFAULT_LTC_AUDIO_DEVICE,
    DEFAULT_LTC_INPUT,
    DEFAULT_LTC_PORT,
    DEFAULT_LTC_WARN,
    DEFAULT_NTP_CHECK_SERVER,
    DEFAULT_PTP_DOMAIN,
    DEFAULT_PTP_IFACE,
    DEFAULT_TIME_SOURCE,
    LTC_INPUT_AUDIO,
    LTC_INPUT_SERIAL,
    TIME_SOURCE_LOCAL,
    TIME_SOURCE_LTC,
    TIME_SOURCE_NTP,
    TIME_SOURCE_PTP,
)
from utils import settings_group

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)

KIND_WALLCLOCK = "wallclock"
KIND_TIMECODE = "timecode"

_manager: Optional["TimeSourceManager"] = None


@dataclass(frozen=True)
class TimeSample:
    """One instant of display time (wall clock or timecode)."""

    hours: int
    minutes: int
    seconds: int
    milliseconds: int
    frames: Optional[int] = None
    frame_rate: Optional[float] = None
    running: bool = True
    locked: bool = True
    kind: str = KIND_WALLCLOCK
    wall_datetime: Optional[datetime] = None
    source: str = ""

    @classmethod
    def from_datetime(
        cls,
        dt: datetime,
        *,
        running: bool = True,
        locked: bool = True,
        kind: str = KIND_WALLCLOCK,
        frames: Optional[int] = None,
        frame_rate: Optional[float] = None,
        source: str = "",
    ) -> "TimeSample":
        """Build a sample from a naive local datetime."""
        return cls(
            hours=dt.hour,
            minutes=dt.minute,
            seconds=dt.second,
            milliseconds=dt.microsecond // 1000,
            frames=frames,
            frame_rate=frame_rate,
            running=running,
            locked=locked,
            kind=kind,
            wall_datetime=dt if kind == KIND_WALLCLOCK else None,
            source=source,
        )

    @classmethod
    def from_system(cls, *, locked: bool = True, source: str = "") -> "TimeSample":
        """Sample from the operating-system clock."""
        return cls.from_datetime(datetime.now(), locked=locked, source=source)

    @classmethod
    def hold(
        cls,
        hours: int,
        minutes: int,
        seconds: int,
        milliseconds: int = 0,
        *,
        frames: Optional[int] = None,
        frame_rate: Optional[float] = None,
        kind: str = KIND_TIMECODE,
        source: str = "",
    ) -> "TimeSample":
        """Frozen sample (pause / lost LTC)."""
        return cls(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
            frames=frames,
            frame_rate=frame_rate,
            running=False,
            locked=False,
            kind=kind,
            wall_datetime=None,
            source=source,
        )


class SteeredClock:
    """
    Free-running clock steered by reference samples and a monotonic clock.

    ``t = ref_datetime + (monotonic_now - ref_monotonic) * rate``

    Independent of datetime.now() / the OS wall clock after the first lock.
    """

    def __init__(self) -> None:
        self._ref_datetime: Optional[datetime] = None
        self._ref_monotonic: Optional[float] = None
        self._rate: float = 1.0
        self._locked: bool = False
        self._ever_locked: bool = False
        self._hold_sample: Optional[TimeSample] = None
        self._monotonic: Callable[[], float] = time.monotonic

    @property
    def locked(self) -> bool:
        return self._locked

    @property
    def ever_locked(self) -> bool:
        return self._ever_locked

    def reset(self) -> None:
        """Drop lock and hold; next now() falls back to the system clock."""
        self._ref_datetime = None
        self._ref_monotonic = None
        self._rate = 1.0
        self._locked = False
        self._ever_locked = False
        self._hold_sample = None

    def set_reference(self, ref_datetime: datetime, monotonic_at: float) -> None:
        """Apply a new absolute reference sample (NTP or PTP)."""
        if (
            self._ref_datetime is not None
            and self._ref_monotonic is not None
            and monotonic_at > self._ref_monotonic + 0.5
        ):
            elapsed_mono = monotonic_at - self._ref_monotonic
            elapsed_ref = (ref_datetime - self._ref_datetime).total_seconds()
            if elapsed_ref > 0:
                new_rate = elapsed_ref / elapsed_mono
                if 0.9 < new_rate < 1.1:
                    self._rate = 0.8 * self._rate + 0.2 * new_rate
        self._ref_datetime = ref_datetime
        self._ref_monotonic = monotonic_at
        self._locked = True
        self._ever_locked = True
        self._hold_sample = None

    def set_unlocked(self) -> None:
        """Lost lock: keep freewheeling from the last reference."""
        self._locked = False

    def set_hold(self, sample: TimeSample) -> None:
        """Freeze the display at an arbitrary sample (LTC hold)."""
        self._hold_sample = sample
        self._locked = sample.locked

    def clear_hold(self) -> None:
        self._hold_sample = None

    def now(self, monotonic_now: Optional[float] = None) -> Optional[datetime]:
        """Steered local datetime, or None before the first lock / while held."""
        if self._hold_sample is not None:
            return None
        if self._ref_datetime is None or self._ref_monotonic is None:
            return None
        if monotonic_now is None:
            monotonic_now = self._monotonic()
        elapsed = (monotonic_now - self._ref_monotonic) * self._rate
        return self._ref_datetime + timedelta(seconds=elapsed)

    def sample(self, *, kind: str = KIND_WALLCLOCK, source: str = "") -> TimeSample:
        """Current TimeSample; system clock only before the first lock."""
        if self._hold_sample is not None:
            return self._hold_sample
        dt = self.now()
        if dt is None:
            return TimeSample.from_system(locked=False, source=source)
        return TimeSample.from_datetime(
            dt, running=True, locked=self._locked, kind=kind, source=source
        )


def set_manager(manager: Optional["TimeSourceManager"]) -> None:
    """Register the process-wide time source (used by ClockWidget)."""
    global _manager
    _manager = manager


def get_manager() -> Optional["TimeSourceManager"]:
    return _manager


def get_current_sample() -> TimeSample:
    """Display sample; system clock if no manager is registered."""
    if _manager is not None:
        sample = _manager.current_sample()
        if sample is not None:
            return sample
        logger.warning("Time source returned no sample; falling back to system clock")
    return TimeSample.from_system()


def wall_datetime() -> datetime:
    """
    Wall time for date, text clock, and top-of-hour.

    Uses the steered NTP/PTP clock when that is the source. Falls back to the
    system clock for local source and for timecode sources (LTC has no date).
    """
    sample = get_current_sample()
    if sample.kind == KIND_WALLCLOCK and sample.wall_datetime is not None:
        return sample.wall_datetime
    return datetime.now()


_VALID_SOURCES = (
    TIME_SOURCE_LOCAL,
    TIME_SOURCE_NTP,
    TIME_SOURCE_PTP,
    TIME_SOURCE_LTC,
)


def _normalize_ltc_channel(value) -> int:
    """Map a settings value to channel 0 (left) or 1 (right)."""
    try:
        channel = int(value)
    except (TypeError, ValueError):
        channel = DEFAULT_LTC_AUDIO_CHANNEL
    return 0 if channel <= 0 else 1


def _empty_ltc_sample() -> TimeSample:
    """Unlocked, frozen 00:00:00:00 before the first LTC lock."""
    return TimeSample.hold(0, 0, 0, 0, frames=0, frame_rate=25.0, source=TIME_SOURCE_LTC)


class TimeSourceManager(QObject):
    """Selects local / NTP / PTP / LTC and feeds ClockWidget via get_current_sample()."""

    def __init__(self, main_screen: "MainScreen") -> None:
        super().__init__(main_screen)
        self.main_screen = main_screen
        self._source = TIME_SOURCE_LOCAL
        self._steered = SteeredClock()
        self._ptp_slave = None
        self._ptp_iface = DEFAULT_PTP_IFACE
        self._ptp_domain = DEFAULT_PTP_DOMAIN
        self._ntp_server = ""
        self._ltc_reader = None
        self._ltc_port = DEFAULT_LTC_PORT
        self._ltc_input = DEFAULT_LTC_INPUT
        self._ltc_audio_device = DEFAULT_LTC_AUDIO_DEVICE
        self._ltc_audio_channel = DEFAULT_LTC_AUDIO_CHANNEL
        self._ltc_warn = DEFAULT_LTC_WARN
        self._ltc_sample: Optional[TimeSample] = None
        self._ltc_ever_locked = False
        self._ltc_connected = True
        self._ntp_signals_bound = None
        set_manager(self)
        self._bind_ntp_signals()
        self.apply_settings()

    @property
    def source(self) -> str:
        return self._source

    @property
    def steered(self) -> SteeredClock:
        return self._steered

    def current_sample(self) -> TimeSample:
        """TimeSample for the active source."""
        if self._source == TIME_SOURCE_LOCAL:
            return TimeSample.from_system(locked=True, source=TIME_SOURCE_LOCAL)
        if self._source == TIME_SOURCE_LTC:
            if self._ltc_sample is not None:
                return self._ltc_sample
            return _empty_ltc_sample()
        return self._steered.sample(kind=KIND_WALLCLOCK, source=self._source)

    def apply_settings(self) -> None:
        """Start/stop NTP poll, PTP slave, and LTC reader from QSettings."""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "TimeSource"):
            source = settings.value("source", DEFAULT_TIME_SOURCE, type=str) or DEFAULT_TIME_SOURCE
            ptp_iface = settings.value("ptp_iface", DEFAULT_PTP_IFACE, type=str) or ""
            try:
                ptp_domain = int(settings.value("ptp_domain", DEFAULT_PTP_DOMAIN, type=int))
            except (TypeError, ValueError):
                ptp_domain = DEFAULT_PTP_DOMAIN
            ltc_port = settings.value("ltc_port", DEFAULT_LTC_PORT, type=str) or ""
            ltc_input = settings.value("ltc_input", DEFAULT_LTC_INPUT, type=str) or DEFAULT_LTC_INPUT
            ltc_audio_device = (
                settings.value("ltc_audio_device", DEFAULT_LTC_AUDIO_DEVICE, type=str) or ""
            )
            ltc_audio_channel = _normalize_ltc_channel(
                settings.value("ltc_audio_channel", DEFAULT_LTC_AUDIO_CHANNEL)
            )
            ltc_warn = settings.value("ltc_warn", DEFAULT_LTC_WARN, type=bool)
        with settings_group(settings, "NTP"):
            ntp_server = str(settings.value("ntpcheckserver", DEFAULT_NTP_CHECK_SERVER) or DEFAULT_NTP_CHECK_SERVER)
        ptp_domain = max(0, min(255, ptp_domain))
        if source not in _VALID_SOURCES:
            source = DEFAULT_TIME_SOURCE
        if ltc_input not in (LTC_INPUT_SERIAL, LTC_INPUT_AUDIO):
            ltc_input = DEFAULT_LTC_INPUT

        previous = self._source
        previous_ntp_server = self._ntp_server
        previous_ltc_port = self._ltc_port
        previous_ltc_input = self._ltc_input
        previous_ltc_audio_device = self._ltc_audio_device
        previous_ltc_audio_channel = self._ltc_audio_channel
        self._source = source
        self._ptp_iface = ptp_iface
        self._ptp_domain = ptp_domain
        self._ntp_server = ntp_server
        self._ltc_port = ltc_port
        self._ltc_input = ltc_input
        self._ltc_audio_device = ltc_audio_device
        self._ltc_audio_channel = ltc_audio_channel
        self._ltc_warn = bool(ltc_warn)

        if source != TIME_SOURCE_PTP:
            self._stop_ptp()
        if source != TIME_SOURCE_LTC:
            self._stop_ltc()
        if source != previous:
            self._steered.reset()
            self._ltc_sample = None
            self._ltc_ever_locked = False
            self._ltc_connected = True
        elif source == TIME_SOURCE_NTP and ntp_server != previous_ntp_server:
            # Server changed: drop lock until the new server replies
            self._steered.set_unlocked()

        if source == TIME_SOURCE_PTP:
            self._start_ptp(ptp_iface, ptp_domain)
        if source == TIME_SOURCE_LTC:
            ltc_changed = (
                previous != TIME_SOURCE_LTC
                or ltc_input != previous_ltc_input
                or (ltc_input == LTC_INPUT_SERIAL and ltc_port != previous_ltc_port)
                or (
                    ltc_input == LTC_INPUT_AUDIO
                    and (
                        ltc_audio_device != previous_ltc_audio_device
                        or ltc_audio_channel != previous_ltc_audio_channel
                    )
                )
            )
            if ltc_changed:
                self._ltc_sample = _empty_ltc_sample()
                self._ltc_ever_locked = False
                self._ltc_connected = True
            self._start_ltc()

        ntp_manager = getattr(self.main_screen, "ntp_manager", None)
        if ntp_manager is not None:
            self._bind_ntp_signals()
            ntp_manager.apply_settings(force_poll=(source == TIME_SOURCE_NTP))

        self._resync_clock()
        logger.info("Time source set to %s", source)

    def _bind_ntp_signals(self) -> None:
        """Connect NTP poll results once, queued onto this object's thread."""
        ntp_manager = getattr(self.main_screen, "ntp_manager", None)
        if ntp_manager is None or not hasattr(ntp_manager, "sample_ready"):
            return
        if self._ntp_signals_bound is ntp_manager:
            return
        ntp_manager.sample_ready.connect(
            self._on_ntp_sample, Qt.ConnectionType.QueuedConnection
        )
        ntp_manager.poll_failed.connect(
            self._on_ntp_failure, Qt.ConnectionType.QueuedConnection
        )
        self._ntp_signals_bound = ntp_manager

    def _on_ntp_sample(self, ntp_unix: float, monotonic_at: float) -> None:
        """NTP query result: steer the clock when NTP is the selected source."""
        if self._source != TIME_SOURCE_NTP:
            return
        try:
            ref = datetime.fromtimestamp(ntp_unix)
        except (OSError, OverflowError, ValueError) as exc:
            logger.warning("Invalid NTP timestamp %s: %s", ntp_unix, exc)
            return
        self._steered.set_reference(ref, monotonic_at)
        logger.debug("NTP steered clock updated: %s", ref)

    def _on_ntp_failure(self) -> None:
        """NTP poll timed out or failed: drop lock, keep freewheeling."""
        if self._source != TIME_SOURCE_NTP:
            return
        self._steered.set_unlocked()
        self._resync_clock()

    def _on_ptp_sample(self, ref_datetime: datetime, monotonic_at: float) -> None:
        if self._source != TIME_SOURCE_PTP:
            return
        self._steered.set_reference(ref_datetime, monotonic_at)

    def _on_ptp_lock(self, locked: bool, message: str) -> None:
        if self._source != TIME_SOURCE_PTP:
            return
        if locked:
            logger.info("PTP locked")
        else:
            self._steered.set_unlocked()
            logger.warning("PTP unlocked: %s", message)

    def _start_ptp(self, iface: str, domain: int) -> None:
        from ptp_client import PtpV2Slave

        if (
            self._ptp_slave is not None
            and self._ptp_slave.iface == iface
            and self._ptp_slave.domain == domain
            and self._ptp_slave.is_running
        ):
            return
        self._stop_ptp()
        slave = PtpV2Slave(iface=iface, domain=domain)
        slave.sample_ready.connect(self._on_ptp_sample, Qt.ConnectionType.QueuedConnection)
        slave.lock_changed.connect(self._on_ptp_lock, Qt.ConnectionType.QueuedConnection)
        self._ptp_slave = slave
        slave.start()

    def _stop_ptp(self) -> None:
        slave = self._ptp_slave
        self._ptp_slave = None
        if slave is not None:
            slave.stop()

    def _on_ltc_frame(
        self,
        hours: int,
        minutes: int,
        seconds: int,
        frames: int,
        frame_rate: float,
        _monotonic_at: float,
    ) -> None:
        """LTC packet: store a timecode sample and push a clock repaint."""
        if self._source != TIME_SOURCE_LTC:
            return
        from ltc_reader import ltc_milliseconds

        self._ltc_connected = True
        self._ltc_ever_locked = True
        self._ltc_sample = TimeSample(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=ltc_milliseconds(frames, frame_rate),
            frames=frames,
            frame_rate=frame_rate,
            running=True,
            locked=True,
            kind=KIND_TIMECODE,
            wall_datetime=None,
            source=TIME_SOURCE_LTC,
        )
        self._resync_clock()

    def _on_ltc_lock(self, locked: bool, message: str) -> None:
        if self._source != TIME_SOURCE_LTC:
            return
        if locked:
            self._ltc_connected = True
            logger.info("LTC locked")
            return
        if message == "not connected":
            self._ltc_connected = False
            logger.warning("LTC reader not connected")
        else:
            logger.warning("LTC unlocked: %s", message)
        self._hold_ltc_sample()
        self._resync_clock()

    def _hold_ltc_sample(self) -> None:
        """Freeze the last LTC sample (or 00:00:00:00 before the first lock)."""
        last = self._ltc_sample
        if last is None:
            self._ltc_sample = _empty_ltc_sample()
            return
        self._ltc_sample = TimeSample.hold(
            last.hours,
            last.minutes,
            last.seconds,
            last.milliseconds,
            frames=last.frames,
            frame_rate=last.frame_rate,
            source=TIME_SOURCE_LTC,
        )

    def _start_ltc(self) -> None:
        if self._ltc_input == LTC_INPUT_AUDIO:
            from ltc_audio import LtcAudioReader

            reader = self._ltc_reader
            if (
                reader is not None
                and getattr(reader, "input_kind", None) == "audio"
                and reader.device_name == self._ltc_audio_device
                and reader.channel == self._ltc_audio_channel
                and reader.is_running
            ):
                return
            self._stop_ltc()
            audio_reader = LtcAudioReader(
                device_name=self._ltc_audio_device,
                channel=self._ltc_audio_channel,
            )
            audio_reader.frame_ready.connect(self._on_ltc_frame, Qt.ConnectionType.QueuedConnection)
            audio_reader.lock_changed.connect(self._on_ltc_lock, Qt.ConnectionType.QueuedConnection)
            self._ltc_reader = audio_reader
            audio_reader.start()
            return

        from ltc_reader import LtcReader

        reader = self._ltc_reader
        if (
            reader is not None
            and getattr(reader, "input_kind", None) == "serial"
            and reader.port == self._ltc_port
            and reader.is_running
        ):
            return
        self._stop_ltc()
        serial_reader = LtcReader(port=self._ltc_port)
        serial_reader.frame_ready.connect(self._on_ltc_frame, Qt.ConnectionType.QueuedConnection)
        serial_reader.lock_changed.connect(self._on_ltc_lock, Qt.ConnectionType.QueuedConnection)
        self._ltc_reader = serial_reader
        serial_reader.start()

    def _stop_ltc(self) -> None:
        reader = self._ltc_reader
        self._ltc_reader = None
        if reader is not None:
            reader.stop()

    def _resync_clock(self) -> None:
        clock = getattr(self.main_screen, "clockWidget", None)
        if clock is not None and hasattr(clock, "resync_time"):
            clock.resync_time()

    def update_status(self) -> None:
        """Set or clear the time-source warning (priority -1)."""
        message = self._warning_message()
        if message:
            self.main_screen.add_warning(message, -1)
        else:
            self.main_screen.remove_warning(-1)

    def _warning_message(self) -> str:
        ntp_manager = getattr(self.main_screen, "ntp_manager", None)
        ntp_msg = ""
        if ntp_manager is not None and ntp_manager.ntp_had_warning and ntp_manager.ntp_warn_message:
            ntp_msg = ntp_manager.ntp_warn_message

        if self._source == TIME_SOURCE_PTP:
            if not self._steered.ever_locked:
                return "waiting for PTP lock"
            if not self._steered.locked:
                return "Clock not PTP synchronized"
        elif self._source == TIME_SOURCE_NTP:
            if not self._steered.ever_locked:
                return ntp_msg or "waiting for NTP status check"
            if not self._steered.locked:
                return ntp_msg or "Clock not NTP synchronized"
        elif self._source == TIME_SOURCE_LTC:
            if self._ltc_warn:
                if not self._ltc_connected:
                    return "LTC reader not connected"
                if not self._ltc_ever_locked:
                    return "waiting for LTC lock"
                sample = self._ltc_sample
                if sample is None or not sample.locked:
                    return "Clock not LTC synchronized"

        if ntp_msg:
            if self._source == TIME_SOURCE_NTP and self._steered.locked:
                # Display is NTP-steered; only keep unreachable / error text
                if "offset too big" in ntp_msg:
                    return ""
                return ntp_msg
            return ntp_msg
        return ""

    def stop(self) -> None:
        """Shut down PTP/LTC and unregister the process-wide manager."""
        self._stop_ptp()
        self._stop_ltc()
        if get_manager() is self:
            set_manager(None)
