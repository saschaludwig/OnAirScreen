#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# audio_capture.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Cross-platform live audio input capture for OnAirScreen meters.

Supports local PortAudio devices (sounddevice), Axia Livewire, and AES67
multicast RTP. Levels are delivered on the Qt main thread via QTimer.
"""

from __future__ import annotations

import logging
import threading
import time
import weakref
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from aoip_rtp import (
    CODEC_L24,
    MAX_STREAM_CHANNELS,
    MulticastRtpReceiver,
    normalize_codec,
)
from livewire_address import (
    LIVEWIRE_CHANNEL_MIN,
    LIVEWIRE_SAMPLE_RATE,
    validate_channel,
)
from livewire_capture import LivewireReceiver
from meter_engine import (
    MeterEngine,
    MeterReadings,
    MeterUnit,
    floor_readings,
    normalize_lr_unit,
    normalize_meter_layout,
)
from sap_sdp import SUPPORTED_RATES

logger = logging.getLogger("OnAirScreen")

DEFAULT_SAMPLE_RATE = 48000
DEFAULT_BLOCK_SIZE = 1024
UI_POLL_INTERVAL_MS = 33
# After this gap without real audio, inject silence so meters fall to the floor.
SIGNAL_LOSS_TIMEOUT_S = 0.25
SILENCE_CATCHUP_MAX_S = 0.4

AUDIO_SOURCE_DEVICE = "device"
AUDIO_SOURCE_LIVEWIRE = "livewire"
AUDIO_SOURCE_AES67 = "aes67"
AUDIO_SOURCES = (AUDIO_SOURCE_DEVICE, AUDIO_SOURCE_LIVEWIRE, AUDIO_SOURCE_AES67)

# PortAudio snapshots devices at Pa_Initialize(); owners pause around a rescan.
_portaudio_owners: weakref.WeakSet[object] = weakref.WeakSet()


@dataclass
class AudioInputDevice:
    """Describes an available audio input device."""

    index: int
    name: str
    channels: int
    default_samplerate: float
    is_default: bool = False

    def __str__(self) -> str:
        suffix = " (default)" if self.is_default else ""
        return f"{self.name}{suffix}"


def register_portaudio_owner(owner: object) -> None:
    """Track a local PortAudio stream so device rescans can pause it safely."""
    _portaudio_owners.add(owner)


def reinitialize_portaudio() -> None:
    """Force PortAudio to re-enumerate host devices after plug/unplug.

    PortAudio caches the device list at initialize time, so query_devices()
    stays stale until terminate + initialize. Open streams are paused first
    and restored afterwards so the C library is not torn down under them.
    """
    try:
        import sounddevice as sd
    except Exception as exc:  # pragma: no cover - depends on system libs
        logger.warning("sounddevice unavailable: %s", exc)
        return

    terminate = getattr(sd, "_terminate", None)
    initialize = getattr(sd, "_initialize", None)
    if not callable(terminate) or not callable(initialize):
        logger.warning("sounddevice cannot reinitialize PortAudio")
        return

    paused: list[object] = []
    for owner in list(_portaudio_owners):
        pause = getattr(owner, "pause_for_portaudio_rescan", None)
        if not callable(pause):
            continue
        try:
            if pause():
                paused.append(owner)
        except Exception as exc:
            logger.warning("Error pausing PortAudio stream for rescan: %s", exc)

    try:
        initialized = getattr(sd, "_initialized", 1)
        try:
            rounds = max(int(initialized), 0)
        except (TypeError, ValueError):
            rounds = 1
        for _ in range(rounds):
            try:
                terminate()
            except Exception as exc:
                logger.debug("PortAudio terminate during device rescan: %s", exc)
                break
        initialize()
        logger.debug("PortAudio reinitialized to refresh the audio device list")
    except Exception as exc:
        logger.error("Failed to reinitialize PortAudio: %s", exc)

    for owner in paused:
        restore = getattr(owner, "restore_after_portaudio_rescan", None)
        if not callable(restore):
            continue
        try:
            restore()
        except Exception as exc:
            logger.warning("Error restoring PortAudio stream after rescan: %s", exc)


def list_input_devices(*, refresh: bool = False) -> List[AudioInputDevice]:
    """Return available input devices, or an empty list if sounddevice is unavailable.

    Args:
        refresh: If True, reinitialize PortAudio so newly plugged or unplugged
            devices are included (or dropped) in the returned list.
    """
    if refresh:
        reinitialize_portaudio()

    try:
        import sounddevice as sd
    except Exception as exc:  # pragma: no cover - depends on system libs
        logger.warning("sounddevice unavailable: %s", exc)
        return []

    devices: List[AudioInputDevice] = []
    try:
        host_default = sd.default.device[0] if sd.default.device else None
        for index, info in enumerate(sd.query_devices()):
            max_in = int(info.get("max_input_channels", 0))
            if max_in <= 0:
                continue
            devices.append(
                AudioInputDevice(
                    index=index,
                    name=str(info.get("name", f"Device {index}")),
                    channels=max_in,
                    default_samplerate=float(info.get("default_samplerate", DEFAULT_SAMPLE_RATE)),
                    is_default=(index == host_default),
                )
            )
    except Exception as exc:
        logger.error("Failed to enumerate audio input devices: %s", exc)
    return devices


def find_device_index(device_name: str) -> Optional[int]:
    """Resolve a stored device name to a sounddevice device index."""
    if not device_name:
        return None
    for device in list_input_devices():
        if device.name == device_name or str(device) == device_name:
            return device.index
    return None


def normalize_audio_source(source: str) -> str:
    """Return a valid audio source key, defaulting to local device."""
    value = (source or AUDIO_SOURCE_DEVICE).strip().lower()
    if value in AUDIO_SOURCES:
        return value
    return AUDIO_SOURCE_DEVICE


class AudioCaptureController(QObject):
    """
    Captures live input (PortAudio, Livewire, or AES67) and emits meter levels
    on the UI thread.
    """

    levels = Signal(object)
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._source = AUDIO_SOURCE_DEVICE
        self._device_name = ""
        self._livewire_channel = LIVEWIRE_CHANNEL_MIN
        self._livewire_iface = ""
        self._aes67_id = ""
        self._aes67_addr = ""
        self._aes67_port = 5004
        self._aes67_name = ""
        self._aes67_codec = CODEC_L24
        self._aes67_rate = DEFAULT_SAMPLE_RATE
        self._aes67_channels = 2
        self._unit: MeterUnit = MeterUnit.DBFS
        self._layout = normalize_meter_layout(None)
        self._true_peak_needed = False
        self._stream = None
        self._rtp: Optional[MulticastRtpReceiver] = None
        self._engine = MeterEngine(sample_rate=DEFAULT_SAMPLE_RATE, channels=2)
        self._lock = threading.Lock()
        self._latest: MeterReadings = floor_readings()
        self._last_signal_monotonic = 0.0
        self._last_process_monotonic = 0.0
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(UI_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._emit_latest_levels)

    def configure(
        self,
        device_name: str = "",
        unit: str | MeterUnit = MeterUnit.DBFS,
        source: str = AUDIO_SOURCE_DEVICE,
        livewire_channel: int = LIVEWIRE_CHANNEL_MIN,
        livewire_iface: str = "",
        aes67_id: str = "",
        aes67_addr: str = "",
        aes67_port: int = 5004,
        aes67_name: str = "",
        aes67_codec: str = CODEC_L24,
        aes67_rate: int = DEFAULT_SAMPLE_RATE,
        aes67_channels: int = 2,
        layout: str | None = None,
        true_peak_needed: bool = False,
    ) -> None:
        """Update desired source/device/unit (does not start/stop the stream)."""
        self._source = normalize_audio_source(source)
        self._device_name = device_name or ""
        try:
            self._livewire_channel = validate_channel(livewire_channel)
        except ValueError:
            self._livewire_channel = LIVEWIRE_CHANNEL_MIN
        self._livewire_iface = (livewire_iface or "").strip()
        self._aes67_id = (aes67_id or "").strip()
        self._aes67_addr = (aes67_addr or "").strip()
        try:
            port = int(aes67_port)
        except (TypeError, ValueError):
            port = 5004
        self._aes67_port = port if 1 <= port <= 65535 else 5004
        self._aes67_name = (aes67_name or "").strip()
        self._aes67_codec = normalize_codec(aes67_codec)
        try:
            rate = int(aes67_rate)
        except (TypeError, ValueError):
            rate = DEFAULT_SAMPLE_RATE
        self._aes67_rate = rate if rate in SUPPORTED_RATES else DEFAULT_SAMPLE_RATE
        try:
            channels = int(aes67_channels)
        except (TypeError, ValueError):
            channels = 2
        self._aes67_channels = max(1, min(MAX_STREAM_CHANNELS, channels))
        self._unit = normalize_lr_unit(unit)
        self._layout = normalize_meter_layout(layout)
        self._true_peak_needed = bool(true_peak_needed)
        self._apply_engine_options()

    def _apply_engine_options(self) -> None:
        """Push unit/layout/true-peak flags onto the current engine."""
        with self._lock:
            self._engine.set_unit(self._unit)
            self._engine.set_layout(self._layout)
            self._engine.set_true_peak_needed(self._true_peak_needed)

    def set_unit(self, unit: str | MeterUnit) -> None:
        """Update meter unit without restarting the stream."""
        self._unit = normalize_lr_unit(unit)
        with self._lock:
            self._engine.set_unit(self._unit)

    def set_layout(self, layout: str) -> None:
        """Update meter layout without restarting the stream."""
        self._layout = normalize_meter_layout(layout)
        with self._lock:
            self._engine.set_layout(self._layout)

    def set_true_peak_needed(self, needed: bool) -> None:
        """Enable true-peak DSP when TooLoud needs it independently of unit."""
        self._true_peak_needed = bool(needed)
        with self._lock:
            self._engine.set_true_peak_needed(self._true_peak_needed)

    def start_integrated(self) -> None:
        """Reset and start the I/LRA session (thread-safe)."""
        with self._lock:
            self._engine.start_integrated()

    def stop_integrated(self) -> None:
        """Stop accumulating I/LRA; last values stay frozen."""
        with self._lock:
            self._engine.stop_integrated()

    def reset_integrated(self) -> None:
        """Clear I/LRA. A running session continues from scratch."""
        with self._lock:
            self._engine.reset_integrated()

    def toggle_integrated(self) -> bool:
        """Start or stop the I/LRA session. Returns the new running state."""
        with self._lock:
            return self._engine.toggle_integrated()

    @property
    def integrated_running(self) -> bool:
        with self._lock:
            return self._engine.integrated_running

    def integrated_snapshot(self) -> tuple[bool, float, float, float]:
        """Thread-safe I/LRA snapshot from the engine (not the last audio block)."""
        with self._lock:
            return self._engine.integrated_snapshot()

    def start(self) -> None:
        """Start (or restart) capture for the configured source."""
        self.stop()
        if self._source == AUDIO_SOURCE_LIVEWIRE:
            self._start_livewire()
        elif self._source == AUDIO_SOURCE_AES67:
            self._start_aes67()
        else:
            self._start_device()

    def _process_frames(self, data: np.ndarray, *, is_signal: bool = True) -> None:
        try:
            arr = np.asarray(data, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            now = time.monotonic()
            with self._lock:
                if not is_signal:
                    self._engine.snap_display_to_floor()
                self._latest = self._engine.process(arr)
                self._last_process_monotonic = now
                if is_signal:
                    self._last_signal_monotonic = now
        except Exception as exc:
            logger.error("Meter processing error: %s", exc)

    def _inject_silence_if_stale(self, now: Optional[float] = None) -> bool:
        """
        If no real audio arrived recently, feed silence so meters fall to -inf.

        Also applies after a source restart that never received RTP (never-signal).

        Returns True if silence was processed.
        """
        now = time.monotonic() if now is None else float(now)
        with self._lock:
            if (now - self._last_signal_monotonic) < SIGNAL_LOSS_TIMEOUT_S:
                return False
            sample_rate = self._engine.sample_rate
            elapsed = now - self._last_process_monotonic
        if elapsed <= 0.0:
            return False
        n_frames = max(1, int(min(elapsed, SILENCE_CATCHUP_MAX_S) * sample_rate))
        silence = np.zeros((n_frames, 2), dtype=np.float32)
        self._process_frames(silence, is_signal=False)
        return True

    def _start_device(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:
            self.error.emit(f"Audio input unavailable: {exc}")
            return

        device_index = find_device_index(self._device_name)
        channels = 2
        sample_rate = DEFAULT_SAMPLE_RATE
        if device_index is not None:
            try:
                info = sd.query_devices(device_index)
                channels = 2 if int(info.get("max_input_channels", 1)) >= 2 else 1
                sample_rate = int(info.get("default_samplerate", DEFAULT_SAMPLE_RATE))
            except Exception:
                pass

        self._engine = MeterEngine(sample_rate=sample_rate, channels=2)
        self._apply_engine_options()
        self._reset_level_state()

        def callback(indata, frames, time_info, status):  # noqa: ARG001
            if status:
                logger.debug("Audio capture status: %s", status)
            self._process_frames(indata)

        try:
            self._stream = sd.InputStream(
                device=device_index,
                channels=channels,
                samplerate=sample_rate,
                blocksize=DEFAULT_BLOCK_SIZE,
                dtype="float32",
                callback=callback,
            )
            self._stream.start()
            register_portaudio_owner(self)
            self._poll_timer.start()
            logger.info(
                "Audio capture started (device=%s, sr=%s, ch=%s)",
                device_index if device_index is not None else "default",
                sample_rate,
                channels,
            )
        except Exception as exc:
            self._stream = None
            logger.error("Failed to start audio capture: %s", exc)
            self.error.emit(str(exc))

    def _start_livewire(self) -> None:
        self._engine = MeterEngine(sample_rate=LIVEWIRE_SAMPLE_RATE, channels=2)
        self._apply_engine_options()
        self._reset_level_state()

        def on_error(message: str) -> None:
            self.error.emit(message)

        try:
            receiver = LivewireReceiver(
                channel=self._livewire_channel,
                on_frames=self._process_frames,
                iface=self._livewire_iface,
                block_frames=DEFAULT_BLOCK_SIZE,
                on_error=on_error,
            )
            receiver.start()
        except Exception as exc:
            logger.error("Failed to start Livewire capture: %s", exc)
            self.error.emit(str(exc))
            return

        if not receiver.is_running:
            return

        self._rtp = receiver
        self._poll_timer.start()

    def _start_aes67(self) -> None:
        if not self._aes67_addr:
            logger.info("AES67 capture not started: no stream selected")
            return

        self._engine = MeterEngine(sample_rate=self._aes67_rate, channels=2)
        self._apply_engine_options()
        self._reset_level_state()

        def on_error(message: str) -> None:
            self.error.emit(message)

        try:
            receiver = MulticastRtpReceiver(
                multicast=self._aes67_addr,
                port=self._aes67_port,
                on_frames=self._process_frames,
                iface=self._livewire_iface,
                codec=self._aes67_codec,
                channels=self._aes67_channels,
                sample_rate=self._aes67_rate,
                block_frames=DEFAULT_BLOCK_SIZE,
                on_error=on_error,
                log_name="AES67",
            )
            receiver.start()
        except Exception as exc:
            logger.error("Failed to start AES67 capture: %s", exc)
            self.error.emit(str(exc))
            return

        if not receiver.is_running:
            return

        self._rtp = receiver
        self._poll_timer.start()

    def ensure_running(self) -> None:
        """Start capture only if it is not already running."""
        if not self.is_running:
            self.start()

    def stop(self) -> None:
        """Stop capture and UI polling."""
        self._poll_timer.stop()

        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                logger.warning("Error while stopping audio capture: %s", exc)

        receiver = self._rtp
        self._rtp = None
        if receiver is not None:
            try:
                receiver.stop()
            except Exception as exc:
                logger.warning("Error while stopping AoIP capture: %s", exc)

        self._engine.reset()
        self._reset_level_state()

    def pause_for_portaudio_rescan(self) -> bool:
        """Close the local PortAudio stream so the host API can be reinitialized."""
        stream = self._stream
        self._stream = None
        if stream is None:
            return False
        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            logger.warning("Error while pausing audio capture for device rescan: %s", exc)
        return True

    def restore_after_portaudio_rescan(self) -> None:
        """Re-open the local device stream after a PortAudio rescan."""
        if self._source != AUDIO_SOURCE_DEVICE or self._stream is not None:
            return
        self._start_device()

    def _reset_level_state(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._latest = floor_readings()
            # Grace period so a restart without RTP is treated as loss after
            # SIGNAL_LOSS_TIMEOUT_S, without immediately injecting catch-up silence.
            self._last_signal_monotonic = now
            self._last_process_monotonic = now

    def _emit_latest_levels(self) -> None:
        self._inject_silence_if_stale()
        with self._lock:
            latest = self._latest
        self.levels.emit(latest)

    @property
    def is_running(self) -> bool:
        if self._stream is not None:
            return True
        if self._rtp is not None and self._rtp.is_running:
            return True
        return False

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def source(self) -> str:
        return self._source

    @property
    def livewire_channel(self) -> int:
        return self._livewire_channel

    @property
    def livewire_iface(self) -> str:
        return self._livewire_iface

    @property
    def aes67_id(self) -> str:
        return self._aes67_id

    @property
    def aes67_addr(self) -> str:
        return self._aes67_addr

    @property
    def aes67_port(self) -> int:
        return self._aes67_port

    @property
    def aes67_name(self) -> str:
        return self._aes67_name

    @property
    def aes67_codec(self) -> str:
        return self._aes67_codec

    @property
    def aes67_rate(self) -> int:
        return self._aes67_rate

    @property
    def aes67_channels(self) -> int:
        return self._aes67_channels
