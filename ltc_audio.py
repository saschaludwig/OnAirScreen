#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# ltc_audio.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
SMPTE LTC (biphase-mark) decoder from a local audio input.

Decodes 80-bit Linear Timecode frames from a PortAudio capture stream.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PySide6.QtCore import QObject, Signal

from ltc_reader import (
    MAX_FRAMES,
    MAX_HOURS,
    MAX_MINUTES,
    MAX_SECONDS,
    LtcFrame,
    infer_frame_rate,
)

logger = logging.getLogger(__name__)

# SMPTE 12M sync word (bits 64–79): 0011 1111 1111 1101
SYNC_WORD = (0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1)
FRAME_BITS = 80
SYNC_LEN = 16
DATA_BITS = FRAME_BITS - SYNC_LEN
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_BLOCK_SIZE = 1024
BIT_BUFFER_MAX = 160
HYSTERESIS_MIN = 0.008
# Analog zero-crossings sit in the deadband for a sample or two; 3 ms is several
# LTC bit periods and means the carrier is gone (mute / generator pause).
SILENCE_RESET_S = 0.003
# Audio LTC is analog and can miss a few frames while jumping; serial uses 150 ms.
AUDIO_UNLOCK_TIMEOUT_S = 0.35
# After unlock, wait this long before flipping phase / re-bootstrapping.
HUNT_TIMEOUT_S = 0.12
DC_BLOCK_R = 0.995
PEAK_DECAY = 0.9995


@dataclass
class LtcDecodeState:
    """Incremental biphase-mark decoder state."""

    prev_sign: int = 0
    interval: int = 0
    half_bit: float = 0.0
    pending_half: bool = False
    bits: List[int] = field(default_factory=list)
    highest_frame: int = 0
    quiet: int = 0
    peak: float = 0.0
    dc_x: float = 0.0
    dc_y: float = 0.0


def _reset_pll(state: LtcDecodeState) -> None:
    """Forget bit period and partial frame after a timing glitch."""
    state.half_bit = 0.0
    state.pending_half = False
    state.bits.clear()


def _hunt_phase(state: LtcDecodeState) -> None:
    """Keep the bit period, flip Manchester phase, drop the bit buffer."""
    state.pending_half = not state.pending_half
    state.bits.clear()


def _reset_carrier(state: LtcDecodeState) -> None:
    """Treat the input as no-signal so the next edge bootstraps cleanly."""
    _reset_pll(state)
    state.prev_sign = 0
    state.interval = 0
    state.quiet = 0
    state.peak = 0.0
    state.dc_x = 0.0
    state.dc_y = 0.0


def _set_nibble(bits: List[int], start: int, value: int, width: int = 4) -> None:
    for index in range(width):
        bits[start + index] = (int(value) >> index) & 1


def encode_ltc_bits(
    hours: int,
    minutes: int,
    seconds: int,
    frames: int,
    *,
    drop_frame: bool = False,
) -> Tuple[int, ...]:
    """Build one 80-bit SMPTE LTC frame (LSB-first nibbles, trailing sync)."""
    bits = [0] * FRAME_BITS
    _set_nibble(bits, 0, frames % 10)
    tens_f = frames // 10
    bits[8] = tens_f & 1
    bits[9] = (tens_f >> 1) & 1
    bits[10] = 1 if drop_frame else 0
    _set_nibble(bits, 16, seconds % 10)
    tens_s = seconds // 10
    bits[24] = tens_s & 1
    bits[25] = (tens_s >> 1) & 1
    bits[26] = (tens_s >> 2) & 1
    _set_nibble(bits, 32, minutes % 10)
    tens_m = minutes // 10
    bits[40] = tens_m & 1
    bits[41] = (tens_m >> 1) & 1
    bits[42] = (tens_m >> 2) & 1
    _set_nibble(bits, 48, hours % 10)
    tens_h = hours // 10
    bits[56] = tens_h & 1
    bits[57] = (tens_h >> 1) & 1
    for offset, bit in enumerate(SYNC_WORD):
        bits[64 + offset] = bit
    return tuple(bits)


def _biphase_samples(bits: Sequence[int], half_len: int, amplitude: float) -> np.ndarray:
    """Square-wave biphase-mark samples for one bit list."""
    level = float(amplitude)
    chunks: List[np.ndarray] = []
    half = np.empty(half_len, dtype=np.float32)
    for bit in bits:
        level = -level
        half.fill(level)
        chunks.append(half.copy())
        if bit:
            level = -level
        half.fill(level)
        chunks.append(half.copy())
    return np.concatenate(chunks)


def synthesize_ltc_audio(
    hours: int,
    minutes: int,
    seconds: int,
    frames: int,
    fps: float,
    sample_rate: float,
    frame_count: int = 4,
    amplitude: float = 0.8,
) -> np.ndarray:
    """Generate a float32 biphase LTC waveform covering ``frame_count`` frames."""
    fps_int = max(1, int(round(fps)))
    samples_per_bit = float(sample_rate) / (float(fps_int) * FRAME_BITS)
    half_len = max(2, int(round(samples_per_bit / 2.0)))
    chunks: List[np.ndarray] = []
    hour, minute, second, frame = hours, minutes, seconds, frames
    for _ in range(max(1, int(frame_count))):
        bits = encode_ltc_bits(hour, minute, second, frame)
        chunks.append(_biphase_samples(bits, half_len, amplitude))
        frame += 1
        if frame >= fps_int:
            frame = 0
            second += 1
            if second >= 60:
                second = 0
                minute += 1
                if minute >= 60:
                    minute = 0
                    hour = (hour + 1) % 24
    return np.concatenate(chunks).astype(np.float32, copy=False)


def _nibble(bits: Sequence[int], start: int, width: int = 4) -> int:
    value = 0
    for index in range(width):
        value |= (int(bits[start + index]) & 1) << index
    return value


def parse_ltc_frame_bits(bits: Sequence[int]) -> Optional[LtcFrame]:
    """Parse 80 LTC bits ending with the sync word. Returns None if invalid."""
    if len(bits) < FRAME_BITS:
        return None
    payload = bits[-FRAME_BITS:]
    if tuple(payload[-SYNC_LEN:]) != SYNC_WORD:
        return None
    frames_n = _nibble(payload, 0) + 10 * _nibble(payload, 8, 2)
    seconds = _nibble(payload, 16) + 10 * _nibble(payload, 24, 3)
    minutes = _nibble(payload, 32) + 10 * _nibble(payload, 40, 3)
    hours = _nibble(payload, 48) + 10 * _nibble(payload, 56, 2)
    if hours > MAX_HOURS or minutes > MAX_MINUTES or seconds > MAX_SECONDS or frames_n > MAX_FRAMES:
        return None
    return LtcFrame(hours=hours, minutes=minutes, seconds=seconds, frames=frames_n)


def _append_decoded_bit(
    bits: List[int],
    bit: int,
    found: List[LtcFrame],
    state: LtcDecodeState,
) -> None:
    bits.append(int(bit) & 1)
    if len(bits) > BIT_BUFFER_MAX:
        del bits[:-BIT_BUFFER_MAX]
    if len(bits) < FRAME_BITS:
        return
    if tuple(bits[-SYNC_LEN:]) != SYNC_WORD:
        return
    frame = parse_ltc_frame_bits(tuple(bits)[-FRAME_BITS:])
    if frame is None:
        return
    if frame.frames > state.highest_frame:
        state.highest_frame = frame.frames
    found.append(frame)


def _handle_interval(state: LtcDecodeState, interval: int, found: List[LtcFrame]) -> None:
    if interval <= 0:
        return
    if state.half_bit <= 0.0:
        # First crossing: short ≈ half-bit, long ≈ full bit (zero).
        if interval >= 16:
            state.half_bit = interval / 2.0
            state.pending_half = False
            _append_decoded_bit(state.bits, 0, found, state)
        else:
            state.half_bit = float(interval)
            state.pending_half = True
        return

    ratio = interval / state.half_bit
    if 0.5 <= ratio < 1.5:
        if state.pending_half:
            _append_decoded_bit(state.bits, 1, found, state)
            state.pending_half = False
        else:
            state.pending_half = True
        state.half_bit = (0.92 * state.half_bit) + (0.08 * float(interval))
    elif 1.5 <= ratio < 2.8:
        if state.pending_half:
            state.pending_half = False
        _append_decoded_bit(state.bits, 0, found, state)
        state.half_bit = (0.92 * state.half_bit) + (0.08 * (interval / 2.0))
    elif ratio < 0.4 or ratio >= 4.0:
        # Stale/inflated period (everything looks too short) or a dropout edge.
        _reset_pll(state)
        return
    else:
        # ~1.5-bit gap (frame concat / missed edge): drop the interval, keep phase.
        pass


def parse_ltc_samples(
    samples: np.ndarray,
    sample_rate: float,
    state: Optional[LtcDecodeState] = None,
) -> Tuple[LtcDecodeState, List[LtcFrame]]:
    """
    Decode biphase-mark LTC from a 1-D float audio block.

    Bit timing is estimated from zero-crossing intervals. A muted generator
    (silence or a stuck DC level) resets the PLL so the next carrier bootstraps.
    """
    if state is None:
        state = LtcDecodeState()
    rate = float(sample_rate) if sample_rate and sample_rate > 0 else float(DEFAULT_SAMPLE_RATE)
    silence_samples = max(32, int(SILENCE_RESET_S * rate))
    mono = np.asarray(samples, dtype=np.float32).reshape(-1)
    found: List[LtcFrame] = []
    prev_sign = state.prev_sign
    interval = state.interval
    quiet = state.quiet
    peak = state.peak
    dc_x = state.dc_x
    dc_y = state.dc_y
    for raw in mono:
        hp = raw - dc_x + DC_BLOCK_R * dc_y
        dc_x = float(raw)
        dc_y = float(hp)
        mag = abs(hp)
        if mag > peak:
            peak = mag
        else:
            peak *= PEAK_DECAY
        thresh = max(HYSTERESIS_MIN, 0.25 * peak)
        if hp > thresh:
            sign = 1
            quiet = 0
        elif hp < -thresh:
            sign = -1
            quiet = 0
        else:
            quiet += 1
            if quiet >= silence_samples:
                _reset_carrier(state)
                prev_sign = 0
                interval = 0
                quiet = 0
                peak = 0.0
                continue
            sign = prev_sign
        if sign == 0:
            interval += 1
            continue
        if prev_sign == 0:
            prev_sign = sign
            interval = 1
            continue
        max_gap = int(8 * state.half_bit) if state.half_bit >= 2.0 else silence_samples
        if interval >= max_gap:
            _reset_carrier(state)
            prev_sign = sign
            interval = 1
            quiet = 0
            continue
        if sign != prev_sign:
            _handle_interval(state, interval, found)
            interval = 0
        interval += 1
        prev_sign = sign
    state.prev_sign = prev_sign
    state.interval = interval
    state.quiet = quiet
    state.peak = peak
    state.dc_x = dc_x
    state.dc_y = dc_y
    return state, found


class LtcAudioReader(QObject):
    """
    Background LTC audio decoder. Emits the same signals as LtcReader.
    """

    frame_ready = Signal(int, int, int, int, float, float)
    lock_changed = Signal(bool, str)

    def __init__(self, device_name: str = "", channel: int = 0) -> None:
        super().__init__()
        self._device_name = (device_name or "").strip()
        self._channel = 0 if int(channel) <= 0 else 1
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._stream = None
        self._lock = threading.Lock()
        self._state = LtcDecodeState()
        self._highest_frame = 0
        self._last_frame_mono = 0.0
        self._locked = False
        self._hunt_count = 0
        self._sample_rate = DEFAULT_SAMPLE_RATE

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def channel(self) -> int:
        return self._channel

    @property
    def input_kind(self) -> str:
        return "audio"

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._state = LtcDecodeState()
        self._highest_frame = 0
        self._last_frame_mono = time.monotonic()
        self._locked = False
        self._hunt_count = 0
        self._thread = threading.Thread(
            target=self._run,
            name=f"LtcAudioReader-{self._device_name or 'default'}-{self._channel}",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "LTC audio reader started (device=%s, channel=%s)",
            self._device_name or "default",
            self._channel,
        )

    def stop(self) -> None:
        self._stop.set()
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _reacquire(self) -> None:
        """Try the other Manchester phase, then a full PLL reset, in a cycle."""
        self._hunt_count += 1
        if self._hunt_count % 3 == 0:
            highest = self._state.highest_frame
            _reset_carrier(self._state)
            self._state.highest_frame = highest
            logger.debug("LTC audio: re-bootstrap decoder")
        else:
            _hunt_phase(self._state)
            logger.debug("LTC audio: flip biphase phase")

    def _on_audio_block(self, indata, channel: int, sample_rate: int) -> None:
        block = np.asarray(indata, dtype=np.float32)
        if block.ndim == 1:
            mono = block
        else:
            index = min(channel, block.shape[1] - 1)
            mono = block[:, index]
        now_mono = time.monotonic()
        with self._lock:
            self._state, frames = parse_ltc_samples(mono, sample_rate, self._state)
            gap = now_mono - self._last_frame_mono if self._last_frame_mono else 0.0
            lost_lock = False
            if not frames:
                if self._locked and gap > AUDIO_UNLOCK_TIMEOUT_S:
                    # Unlock first; keep decoder state so a brief dropout can recover.
                    lost_lock = True
                    self._last_frame_mono = now_mono
                elif not self._locked and gap > HUNT_TIMEOUT_S:
                    self._reacquire()
                    self._last_frame_mono = now_mono
        for frame in frames:
            if frame.frames > self._highest_frame:
                self._highest_frame = frame.frames
            frame_rate = infer_frame_rate(self._highest_frame)
            self._last_frame_mono = now_mono
            self._hunt_count = 0
            self.frame_ready.emit(
                frame.hours,
                frame.minutes,
                frame.seconds,
                frame.frames,
                frame_rate,
                now_mono,
            )
            if not self._locked:
                self._locked = True
                self.lock_changed.emit(True, "")
        if lost_lock:
            self._locked = False
            self.lock_changed.emit(False, "sync timeout")

    def _run(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:
            logger.error("LTC audio: sounddevice unavailable: %s", exc)
            self.lock_changed.emit(False, "not connected")
            return

        from audio_capture import find_device_index

        device_index = find_device_index(self._device_name)
        channels = 2 if self._channel > 0 else 1
        sample_rate = DEFAULT_SAMPLE_RATE
        if device_index is not None:
            try:
                info = sd.query_devices(device_index)
                max_in = int(info.get("max_input_channels", 1))
                channels = 2 if max_in >= 2 else 1
                sample_rate = int(info.get("default_samplerate", DEFAULT_SAMPLE_RATE) or DEFAULT_SAMPLE_RATE)
            except Exception:
                pass
        if self._channel >= channels:
            logger.warning("LTC audio channel %s not available, using 0", self._channel)
            channel = 0
        else:
            channel = self._channel
        self._sample_rate = sample_rate

        def callback(indata, _frames, _time_info, status):  # noqa: ARG001
            if self._stop.is_set():
                raise sd.CallbackStop()
            if status:
                logger.debug("LTC audio status: %s", status)
            try:
                self._on_audio_block(indata, channel, sample_rate)
            except sd.CallbackStop:
                raise
            except Exception:
                logger.exception("LTC audio callback failed")

        try:
            stream = sd.InputStream(
                device=device_index,
                channels=channels,
                samplerate=sample_rate,
                blocksize=DEFAULT_BLOCK_SIZE,
                dtype="float32",
                callback=callback,
            )
            self._stream = stream
            stream.start()
            logger.info(
                "LTC audio capture started (device=%s, sr=%s, ch=%s)",
                device_index if device_index is not None else "default",
                sample_rate,
                channel,
            )
        except Exception as exc:
            logger.error("LTC audio open failed: %s", exc)
            self.lock_changed.emit(False, "not connected")
            return

        while not self._stop.wait(0.05):
            if self._stream is None:
                break
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
        self._stream = None
