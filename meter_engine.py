#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# meter_engine.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Audio meter engine: dBFS, dBTP, programme LUFS (M/S, optional I/LRA), BBC PPM.

dBFS/dBTP bars use IEC 60268-18 display ballistics (instant attack, 20 dB in
1.7 s) and a 250 ms RMS fill. TooLoud/Silence keep using raw block peaks.

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, NamedTuple, Optional, Tuple

import numpy as np

from defaults import DEFAULT_AUDIO_LAYOUT


class MeterUnit(str, Enum):
    """Display unit for audio meters."""

    DBFS = "dbfs"
    DBTP = "dbtp"
    LUFS = "lufs"
    BBC_PPM = "bbc_ppm"


# L/R display layouts (LUFS is a layout, not an L/R unit)
METER_LAYOUT_LR = "lr"
METER_LAYOUT_LUFS = "lufs"
METER_LAYOUT_BOTH = "both"
METER_LAYOUTS = (METER_LAYOUT_LR, METER_LAYOUT_LUFS, METER_LAYOUT_BOTH)

# Display ranges for bar mapping (normalized 0..1)
UNIT_RANGES = {
    MeterUnit.DBFS: (-60.0, 0.0),
    MeterUnit.DBTP: (-60.0, 0.0),
    MeterUnit.LUFS: (-60.0, 0.0),
    MeterUnit.BBC_PPM: (1.0, 7.0),
}

LUFS_SILENCE = -120.0
MOMENTARY_SECONDS = 0.4
SHORT_TERM_SECONDS = 3.0
INTEGRATED_BLOCK_SECONDS = 0.4
INTEGRATED_HOP_SECONDS = 0.1
LRA_HOP_SECONDS = 1.0
GATE_ABS_LUFS = -70.0
GATE_REL_INTEGRATED_LU = 10.0
GATE_REL_LRA_LU = 20.0

# EBU digital alignment: PPM mark 4 == -18 dBFS
BBC_PPM_ALIGNMENT_DBFS = -18.0
BBC_PPM_DB_PER_MARK = 4.0

# BBC PPM Type IIa (IEC 60268-10):
# - Integration time 10 ms: 5 kHz burst reads 2 dB below steady-state
# - Return time: 24 dB fall in 2.8 s
BBC_PPM_INTEGRATION_S = 0.010
BBC_PPM_UNDERREAD_FACTOR = 10 ** (-2.0 / 20.0)  # 2 dB under-read at integration time
# Solve 1 - exp(-T/τ) = underread  →  τ = -T / ln(1 - underread)
BBC_PPM_ATTACK_TAU_S = -BBC_PPM_INTEGRATION_S / np.log(1.0 - BBC_PPM_UNDERREAD_FACTOR)
BBC_PPM_RELEASE_DB_PER_S = 24.0 / 2.8
# Fast peak rectifier hold: spans half-cycles of the 5 kHz IEC test tone
# without fighting the slower Type IIa attack/release stage.
BBC_PPM_PEAK_HOLD_TAU_S = 0.001

# IEC 60268-18 digital peak meter (dBFS / dBTP bars): instant attack,
# 20 dB fallback in 1.7 s. RMS fill uses a 250 ms power window.
DIGITAL_PEAK_FALL_DB = 20.0
DIGITAL_PEAK_FALL_S = 1.7
DIGITAL_RMS_SECONDS = 0.250

# L/R units shown on the stereo bars (LUFS is a separate programme meter)
LR_METER_UNITS = (MeterUnit.DBFS, MeterUnit.DBTP, MeterUnit.BBC_PPM)


class MeterReadings(NamedTuple):
    """One processed audio block: L/R display values plus programme loudness."""

    left: float
    right: float
    max_true_peak_dbtp: float
    max_sample_peak_dbfs: float
    lufs_m: float = LUFS_SILENCE
    lufs_s: float = LUFS_SILENCE
    lufs_i: float = LUFS_SILENCE
    lra_low: float = LUFS_SILENCE
    lra_high: float = LUFS_SILENCE
    rms_left: float = LUFS_SILENCE
    rms_right: float = LUFS_SILENCE
    integrated_running: bool = False
    clip_left: bool = False
    clip_right: bool = False


def floor_readings(*, integrated_running: bool = False) -> MeterReadings:
    """Silence-floor reading used when capture is idle."""
    return MeterReadings(
        left=LUFS_SILENCE,
        right=LUFS_SILENCE,
        max_true_peak_dbtp=LUFS_SILENCE,
        max_sample_peak_dbfs=LUFS_SILENCE,
        integrated_running=integrated_running,
    )


def normalize_meter_layout(layout: str | None) -> str:
    """Return a valid meter layout key, defaulting to DEFAULT_AUDIO_LAYOUT."""
    value = (layout or DEFAULT_AUDIO_LAYOUT).strip().lower()
    if value in METER_LAYOUTS:
        return value
    return DEFAULT_AUDIO_LAYOUT


def normalize_lr_unit(unit: MeterUnit | str) -> MeterUnit:
    """Map a stored unit onto an L/R display unit (legacy lufs -> dBTP)."""
    try:
        parsed = MeterUnit(unit)
    except ValueError:
        return MeterUnit.DBTP
    if parsed == MeterUnit.LUFS:
        return MeterUnit.DBTP
    return parsed


def migrate_audio_layout_and_unit(unit: str | None, layout: str | None) -> Tuple[str, str]:
    """
    Migrate legacy unit=lufs onto layout=lufs and an L/R unit.

    If layout is already set, a leftover unit=lufs still becomes dbtp.
    """
    raw_unit = (unit or MeterUnit.DBTP.value).strip().lower()
    has_layout = layout is not None and str(layout).strip() != ""
    if not has_layout and raw_unit == MeterUnit.LUFS.value:
        return METER_LAYOUT_LUFS, MeterUnit.DBTP.value
    resolved_layout = normalize_meter_layout(layout)
    resolved_unit = normalize_lr_unit(raw_unit).value
    return resolved_layout, resolved_unit


def linear_to_db(value: float, floor_db: float = -120.0) -> float:
    """Convert a linear amplitude to dB with a floor."""
    if value <= 0.0:
        return floor_db
    return max(20.0 * np.log10(value), floor_db)


def db_to_bbc_ppm(level_dbfs: float) -> float:
    """Map a dBFS level to BBC PPM marks (1..7, may exceed slightly)."""
    return 4.0 + (level_dbfs - BBC_PPM_ALIGNMENT_DBFS) / BBC_PPM_DB_PER_MARK


def bbc_ppm_to_db(ppm: float) -> float:
    """Map BBC PPM marks to dBFS."""
    return BBC_PPM_ALIGNMENT_DBFS + (ppm - 4.0) * BBC_PPM_DB_PER_MARK


def normalize_meter_value(value: float, unit: MeterUnit) -> float:
    """Normalize a meter reading to 0..1 for bar display."""
    low, high = UNIT_RANGES[unit]
    if high == low:
        return 0.0
    return float(np.clip((value - low) / (high - low), 0.0, 1.0))


def mean_square_to_lufs(mean_sq: float) -> float:
    """Convert a mean-square of K-weighted samples to LUFS."""
    if mean_sq <= 0.0:
        return LUFS_SILENCE
    return float(-0.691 + 10.0 * np.log10(mean_sq))


def _mean_square_to_lufs_array(mean_sq: np.ndarray) -> np.ndarray:
    out = np.full(mean_sq.shape, LUFS_SILENCE, dtype=np.float64)
    ok = mean_sq > 0.0
    out[ok] = -0.691 + 10.0 * np.log10(mean_sq[ok])
    return out


def _gated_integrated(block_ms: np.ndarray) -> float:
    """BS.1770-4 two-stage gated integrated loudness from 400 ms mean-squares."""
    if block_ms.size == 0:
        return LUFS_SILENCE
    block_lufs = _mean_square_to_lufs_array(block_ms)
    abs_pass = block_lufs > GATE_ABS_LUFS
    if not np.any(abs_pass):
        return LUFS_SILENCE
    gated = block_ms[abs_pass]
    ungated_i = mean_square_to_lufs(float(np.mean(gated)))
    rel_pass = block_lufs[abs_pass] > (ungated_i - GATE_REL_INTEGRATED_LU)
    if not np.any(rel_pass):
        return ungated_i
    return mean_square_to_lufs(float(np.mean(gated[rel_pass])))


def _loudness_range_span(short_term_ms: np.ndarray) -> Tuple[float, float, float]:
    """EBU Tech 3342: (10th-percentile LUFS, 95th-percentile LUFS, LRA)."""
    if short_term_ms.size == 0:
        return LUFS_SILENCE, LUFS_SILENCE, 0.0
    st_lufs = _mean_square_to_lufs_array(short_term_ms)
    abs_pass = st_lufs > GATE_ABS_LUFS
    if not np.any(abs_pass):
        return LUFS_SILENCE, LUFS_SILENCE, 0.0
    abs_vals = st_lufs[abs_pass]
    abs_loudness = mean_square_to_lufs(float(np.mean(short_term_ms[abs_pass])))
    remaining = abs_vals[abs_vals > (abs_loudness - GATE_REL_LRA_LU)]
    if remaining.size < 2:
        return LUFS_SILENCE, LUFS_SILENCE, 0.0
    low = float(np.percentile(remaining, 10))
    high = float(np.percentile(remaining, 95))
    return low, high, high - low


def _design_k_weighting(sample_rate: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Design ITU-R BS.1770 K-weighting biquad coefficients.

    Returns (b_pre, a_pre, b_rlb, a_rlb) for stage 1 (pre-filter) and stage 2 (RLB).
    """
    # Published coefficients for 48 kHz (BS.1770-4)
    if sample_rate == 48000:
        b_pre = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
        a_pre = np.array([1.0, -1.69065929318241, 0.73248077421585])
        b_rlb = np.array([1.0, -2.0, 1.0])
        a_rlb = np.array([1.0, -1.99004745429488, 0.99007225036621])
        return b_pre, a_pre, b_rlb, a_rlb

    # Continuous-time prototypes + bilinear transform for other sample rates
    f0_pre = 1681.974450955533
    f0_rlb = 38.13547087602444
    q_rlb = 0.5003270373238773
    shelf_db = 3.999843853973347

    k = np.tan(np.pi * f0_pre / sample_rate)
    v0 = 10 ** (shelf_db / 20.0)
    a0 = 1.0 + np.sqrt(2.0) * k + k * k
    b0 = (v0 + np.sqrt(2.0 * v0) * k + k * k) / a0
    b1 = 2.0 * (k * k - v0) / a0
    b2 = (v0 - np.sqrt(2.0 * v0) * k + k * k) / a0
    a1 = 2.0 * (k * k - 1.0) / a0
    a2 = (1.0 - np.sqrt(2.0) * k + k * k) / a0
    b_pre = np.array([b0, b1, b2])
    a_pre = np.array([1.0, a1, a2])

    k = np.tan(np.pi * f0_rlb / sample_rate)
    a0 = 1.0 + k / q_rlb + k * k
    b0 = 1.0 / a0
    b1 = -2.0 / a0
    b2 = 1.0 / a0
    a1 = 2.0 * (k * k - 1.0) / a0
    a2 = (1.0 - k / q_rlb + k * k) / a0
    b_rlb = np.array([b0, b1, b2])
    a_rlb = np.array([1.0, a1, a2])
    return b_pre, a_pre, b_rlb, a_rlb


def _biquad_filter(
    b: np.ndarray,
    a: np.ndarray,
    x: np.ndarray,
    zi: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Apply a direct-form II transposed biquad; return (y, zf)."""
    try:
        from scipy.signal import lfilter
        if zi is None:
            zi = np.zeros(max(len(a), len(b)) - 1, dtype=np.float64)
        y, zf = lfilter(b, a, x, zi=zi)
        return y.astype(np.float64, copy=False), np.asarray(zf, dtype=np.float64)
    except ImportError:
        pass

    if zi is None:
        zi = np.zeros(2, dtype=np.float64)
    y = np.empty_like(x, dtype=np.float64)
    z1, z2 = float(zi[0]), float(zi[1])
    b0, b1, b2 = float(b[0]), float(b[1]), float(b[2])
    a1, a2 = float(a[1]), float(a[2])
    for i, sample in enumerate(x):
        out = b0 * sample + z1
        z1 = b1 * sample - a1 * out + z2
        z2 = b2 * sample - a2 * out
        y[i] = out
    return y, np.array([z1, z2], dtype=np.float64)


def _true_peak_block(samples: np.ndarray, oversample: int = 4) -> float:
    """
    Estimate true-peak of a mono block via 4x upsampling.

    Uses zero-stuffing followed by a short low-pass FIR (windowed sinc).
    """
    if samples.size == 0:
        return 0.0
    sample_peak = float(np.max(np.abs(samples)))
    if sample_peak == 0.0:
        return 0.0

    taps = 32 * oversample + 1
    n = np.arange(taps) - (taps - 1) / 2.0
    h = np.sinc(n / oversample) / oversample
    h *= np.hanning(taps)
    h /= np.sum(h)

    up = np.zeros(samples.size * oversample, dtype=np.float64)
    up[::oversample] = samples.astype(np.float64)
    filtered = np.convolve(up, h, mode="same")
    return float(max(sample_peak, np.max(np.abs(filtered))))


@dataclass
class ChannelMeterState:
    """Per-channel running meter state."""

    sample_peak: float = 0.0
    true_peak: float = 0.0
    rms: float = 0.0
    peak_env: float = 0.0
    tp_env: float = 0.0
    rms_buffer: Optional[np.ndarray] = None
    rms_write: int = 0
    rms_filled: int = 0
    ppm_peak: float = 0.0
    ppm_linear: float = 0.0
    lufs_momentary: float = LUFS_SILENCE
    mean_sq: float = 0.0
    zi_pre: Optional[np.ndarray] = None
    zi_rlb: Optional[np.ndarray] = None
    ms_buffer: Optional[np.ndarray] = None
    ms_write: int = 0
    ms_filled: int = 0


class _IntegratedLoudness:
    """Running gated I and LRA from already K-weighted stereo power."""

    def __init__(self, sample_rate: int = 48000):
        self._sample_rate = 0
        self.reset(sample_rate)

    def reset(self, sample_rate: Optional[int] = None) -> None:
        sr = int(sample_rate) if sample_rate is not None else self._sample_rate
        sr = sr or 48000
        self._sample_rate = sr
        self._block_samples = max(1, int(round(INTEGRATED_BLOCK_SECONDS * sr)))
        self._hop_samples = max(1, int(round(INTEGRATED_HOP_SECONDS * sr)))
        self._st_samples = max(1, int(round(SHORT_TERM_SECONDS * sr)))
        self._st_hop_samples = max(1, int(round(LRA_HOP_SECONDS * sr)))
        self._ring = np.zeros(self._block_samples, dtype=np.float64)
        self._ring_write = 0
        self._ring_filled = 0
        self._hop_fill = 0
        self._blocks: List[float] = []
        self._st_ring = np.zeros(self._st_samples, dtype=np.float64)
        self._st_write = 0
        self._st_filled = 0
        self._st_hop_fill = 0
        self._st_blocks: List[float] = []
        self.integrated = LUFS_SILENCE
        self.lra_low = LUFS_SILENCE
        self.lra_high = LUFS_SILENCE

    def ingest_power(self, power: np.ndarray) -> None:
        """Accumulate stereo K-weighted power into I (400 ms) and LRA (3 s)."""
        power = np.asarray(power, dtype=np.float64)
        if power.size == 0:
            return
        offset = 0
        n = power.size
        while offset < n:
            take = min(
                n - offset,
                self._hop_samples - self._hop_fill,
                self._st_hop_samples - self._st_hop_fill,
            )
            chunk = power[offset:offset + take]
            self._write_ring(self._ring, "_ring_write", "_ring_filled", chunk)
            self._write_ring(self._st_ring, "_st_write", "_st_filled", chunk)
            self._hop_fill += take
            self._st_hop_fill += take
            offset += take
            if self._hop_fill >= self._hop_samples:
                self._hop_fill = 0
                if self._ring_filled >= self._block_samples:
                    self._blocks.append(float(np.mean(self._ring)))
                    self.integrated = _gated_integrated(
                        np.asarray(self._blocks, dtype=np.float64)
                    )
            if self._st_hop_fill >= self._st_hop_samples:
                self._st_hop_fill = 0
                if self._st_filled >= self._st_samples:
                    self._st_blocks.append(float(np.mean(self._st_ring)))
                    self._refresh_lra()

    def _refresh_lra(self) -> None:
        if len(self._st_blocks) < 2:
            self.lra_low = LUFS_SILENCE
            self.lra_high = LUFS_SILENCE
            return
        low, high, _lra = _loudness_range_span(
            np.asarray(self._st_blocks, dtype=np.float64)
        )
        self.lra_low = low
        self.lra_high = high

    def _write_ring(
        self,
        buf: np.ndarray,
        write_attr: str,
        filled_attr: str,
        chunk: np.ndarray,
    ) -> None:
        if chunk.size == 0:
            return
        n = chunk.size
        idx = getattr(self, write_attr)
        size = buf.size
        if n >= size:
            buf[:] = chunk[-size:]
            setattr(self, write_attr, 0)
            setattr(self, filled_attr, size)
            return
        first = min(n, size - idx)
        buf[idx:idx + first] = chunk[:first]
        rest = n - first
        if rest > 0:
            buf[0:rest] = chunk[first:]
        setattr(self, write_attr, (idx + n) % size)
        setattr(self, filled_attr, min(size, getattr(self, filled_attr) + n))


class MeterEngine:
    """
    Processes PCM float audio and produces meter readings.
    """

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        self.sample_rate = int(sample_rate)
        self.channels = max(1, int(channels))
        self.unit = MeterUnit.DBFS
        self._b_pre, self._a_pre, self._b_rlb, self._a_rlb = _design_k_weighting(self.sample_rate)
        self._momentary_samples = max(1, int(MOMENTARY_SECONDS * self.sample_rate))
        self._short_term_samples = max(1, int(SHORT_TERM_SECONDS * self.sample_rate))
        self._rms_samples = max(1, int(DIGITAL_RMS_SECONDS * self.sample_rate))
        self._states = [ChannelMeterState() for _ in range(self.channels)]
        self._peak_hold_l = LUFS_SILENCE
        self._peak_hold_r = LUFS_SILENCE
        self._peak_hold_frames = 0
        self._peak_hold_duration_frames = int(1.5 * self.sample_rate)
        self._st_buffer: Optional[np.ndarray] = None
        self._st_write = 0
        self._st_filled = 0
        self._lufs_short_term = LUFS_SILENCE
        self._integrated = _IntegratedLoudness(self.sample_rate)
        self._integrated_running = False

    def reset(self) -> None:
        """Reset all meter state, including a running I/LRA session."""
        self._states = [ChannelMeterState() for _ in range(self.channels)]
        self._peak_hold_l = LUFS_SILENCE
        self._peak_hold_r = LUFS_SILENCE
        self._peak_hold_frames = 0
        self._st_buffer = None
        self._st_write = 0
        self._st_filled = 0
        self._lufs_short_term = LUFS_SILENCE
        was_running = self._integrated_running
        self._integrated.reset(self.sample_rate)
        self._integrated_running = was_running

    def set_sample_rate(self, sample_rate: int) -> None:
        """Update sample rate and redesign filters."""
        if sample_rate == self.sample_rate:
            return
        self.sample_rate = int(sample_rate)
        self._b_pre, self._a_pre, self._b_rlb, self._a_rlb = _design_k_weighting(self.sample_rate)
        self._momentary_samples = max(1, int(MOMENTARY_SECONDS * self.sample_rate))
        self._short_term_samples = max(1, int(SHORT_TERM_SECONDS * self.sample_rate))
        self._rms_samples = max(1, int(DIGITAL_RMS_SECONDS * self.sample_rate))
        self._peak_hold_duration_frames = int(1.5 * self.sample_rate)
        self.reset()

    def set_unit(self, unit: MeterUnit | str) -> None:
        """Set L/R display unit (legacy lufs maps to dBTP)."""
        self.unit = normalize_lr_unit(unit)

    @property
    def integrated_running(self) -> bool:
        return self._integrated_running

    def integrated_snapshot(self) -> tuple[bool, float, float, float]:
        """Return (running, I LUFS, LRA low LUFS, LRA high LUFS) from the engine."""
        return (
            self._integrated_running,
            float(self._integrated.integrated),
            float(self._integrated.lra_low),
            float(self._integrated.lra_high),
        )

    def start_integrated(self) -> None:
        """Reset I/LRA and start a measurement session."""
        self._integrated.reset(self.sample_rate)
        self._integrated_running = True

    def stop_integrated(self) -> None:
        """Stop accumulating I/LRA; last values stay frozen."""
        self._integrated_running = False

    def reset_integrated(self) -> None:
        """Clear I/LRA. A running session continues from scratch."""
        self._integrated.reset(self.sample_rate)

    def toggle_integrated(self) -> bool:
        """Start or stop the I/LRA session. Returns the new running state."""
        if self._integrated_running:
            self.stop_integrated()
        else:
            self.start_integrated()
        return self._integrated_running

    def snap_display_to_floor(self) -> None:
        """Drop dBFS/dBTP/RMS display envelopes immediately (signal loss)."""
        for state in self._states:
            state.peak_env = 0.0
            state.tp_env = 0.0
            state.rms = 0.0
            state.rms_buffer = None
            state.rms_write = 0
            state.rms_filled = 0
            state.ppm_peak = 0.0
            state.ppm_linear = 0.0

    def process(self, frames: np.ndarray) -> MeterReadings:
        """
        Process an audio block.

        Args:
            frames: float array shaped (n_frames, channels) or (n_frames,) for mono

        Returns:
            MeterReadings with L/R in the current display unit plus programme LUFS.
        """
        if frames.ndim == 1:
            frames = frames.reshape(-1, 1)
        if frames.shape[1] < self.channels:
            if frames.shape[1] == 1 and self.channels >= 2:
                frames = np.repeat(frames, self.channels, axis=1)
            else:
                pad = np.zeros((frames.shape[0], self.channels - frames.shape[1]), dtype=frames.dtype)
                frames = np.concatenate([frames, pad], axis=1)

        n = frames.shape[0]
        true_peaks = []
        sample_peaks = []
        powers = []

        for ch in range(min(self.channels, 2)):
            mono = frames[:, ch].astype(np.float64, copy=False)
            state = self._states[ch]

            sample_peak = float(np.max(np.abs(mono))) if n else 0.0
            true_peak = _true_peak_block(mono) if n else 0.0
            state.sample_peak = sample_peak
            state.true_peak = true_peak
            sample_peaks.append(sample_peak)
            true_peaks.append(true_peak)

            self._update_rms_window(state, mono)
            self._update_digital_peak(state, sample_peak, true_peak, n)
            self._update_ppm(state, mono)
            powers.append(self._update_lufs(state, mono))

        while len(sample_peaks) < 2:
            sample_peaks.append(sample_peaks[0] if sample_peaks else 0.0)
            true_peaks.append(true_peaks[0] if true_peaks else 0.0)
            if len(self._states) < 2:
                self._states.append(ChannelMeterState())
            if len(powers) < 2:
                powers.append(powers[0] if powers else np.zeros(0, dtype=np.float64))

        left = self._display_value(self._states[0])
        right = self._display_value(self._states[1 if self.channels > 1 else 0])
        rms_left = linear_to_db(self._states[0].rms)
        rms_right = linear_to_db(self._states[1 if self.channels > 1 else 0].rms)

        left_power = powers[0] if powers else np.zeros(0, dtype=np.float64)
        right_power = powers[1] if len(powers) > 1 else left_power
        n_power = min(left_power.size, right_power.size)
        stereo_power = left_power[:n_power] + right_power[:n_power] if n_power else np.zeros(0)
        if n_power:
            self._push_short_term(stereo_power)
        lufs_m = mean_square_to_lufs(
            self._states[0].mean_sq + self._states[1 if self.channels > 1 else 0].mean_sq
        )
        if self._integrated_running and n_power:
            self._integrated.ingest_power(stereo_power)

        max_tp = linear_to_db(max(true_peaks) if true_peaks else 0.0)
        max_sp = linear_to_db(max(sample_peaks) if sample_peaks else 0.0)

        self._update_peak_hold(left, right, n)
        return MeterReadings(
            left=left,
            right=right,
            max_true_peak_dbtp=max_tp,
            max_sample_peak_dbfs=max_sp,
            lufs_m=lufs_m,
            lufs_s=self._lufs_short_term,
            lufs_i=self._integrated.integrated,
            lra_low=self._integrated.lra_low,
            lra_high=self._integrated.lra_high,
            rms_left=rms_left,
            rms_right=rms_right,
            integrated_running=self._integrated_running,
            clip_left=true_peaks[0] > 1.0 if true_peaks else False,
            clip_right=true_peaks[1] > 1.0 if len(true_peaks) > 1 else False,
        )

    def peak_hold(self) -> Tuple[float, float]:
        """Return current peak-hold values in display units."""
        return self._peak_hold_l, self._peak_hold_r

    def _display_value(self, state: ChannelMeterState) -> float:
        if self.unit == MeterUnit.DBFS:
            return linear_to_db(state.peak_env)
        if self.unit == MeterUnit.DBTP:
            return linear_to_db(state.tp_env)
        if self.unit == MeterUnit.BBC_PPM:
            return db_to_bbc_ppm(linear_to_db(state.ppm_linear))
        return linear_to_db(state.peak_env)

    def _update_digital_peak(
        self,
        state: ChannelMeterState,
        sample_peak: float,
        true_peak: float,
        n_frames: int,
    ) -> None:
        """IEC 60268-18: instant attack, 20 dB in 1.7 s fallback."""
        if n_frames <= 0:
            return
        fall_db = DIGITAL_PEAK_FALL_DB / DIGITAL_PEAK_FALL_S * (n_frames / self.sample_rate)
        coef = float(10 ** (-fall_db / 20.0))
        if sample_peak >= state.peak_env:
            state.peak_env = sample_peak
        else:
            state.peak_env *= coef
        if true_peak >= state.tp_env:
            state.tp_env = true_peak
        else:
            state.tp_env *= coef

    def _update_rms_window(self, state: ChannelMeterState, mono: np.ndarray) -> None:
        """Accumulate a 250 ms mean-square window for the L/R fill."""
        if mono.size == 0:
            return
        power = mono * mono
        window = self._rms_samples
        if state.rms_buffer is None or state.rms_buffer.size != window:
            state.rms_buffer = np.zeros(window, dtype=np.float64)
            state.rms_write = 0
            state.rms_filled = 0
        buf = state.rms_buffer
        n = power.size
        idx = state.rms_write
        if n >= window:
            buf[:] = power[-window:]
            state.rms_write = 0
            state.rms_filled = window
        else:
            first = min(n, window - idx)
            buf[idx:idx + first] = power[:first]
            rest = n - first
            if rest > 0:
                buf[0:rest] = power[first:]
            state.rms_write = (idx + n) % window
            state.rms_filled = min(window, state.rms_filled + n)
        mean_sq = float(np.mean(buf[:state.rms_filled])) if state.rms_filled else 0.0
        state.rms = float(np.sqrt(mean_sq)) if mean_sq > 0.0 else 0.0

    def _update_ppm(self, state: ChannelMeterState, mono: np.ndarray) -> None:
        """
        Update BBC PPM Type IIa quasi-peak envelope sample-by-sample.

        Stage 1: fast full-wave peak rectifier so audio-cycle valleys do not
        discharge the meter. Stage 2: first-order attack matched to IEC
        60268-10 integration (10 ms / 5 kHz burst under-reads continuous by
        2 dB) and release of 24 dB in 2.8 s.
        """
        if mono.size == 0:
            return
        peak_coef = float(np.exp(-1.0 / (BBC_PPM_PEAK_HOLD_TAU_S * self.sample_rate)))
        attack_coef = float(1.0 - np.exp(-1.0 / (BBC_PPM_ATTACK_TAU_S * self.sample_rate)))
        release_coef = float(10 ** (-(BBC_PPM_RELEASE_DB_PER_S / self.sample_rate) / 20.0))
        peak = float(state.ppm_peak)
        env = float(state.ppm_linear)
        for sample in mono:
            level = abs(float(sample))
            if level > peak:
                peak = level
            else:
                peak *= peak_coef
            if peak > env:
                env += attack_coef * (peak - env)
            else:
                env *= release_coef
        state.ppm_peak = peak
        state.ppm_linear = env

    def _update_lufs(self, state: ChannelMeterState, mono: np.ndarray) -> np.ndarray:
        """Update per-channel momentary LUFS; return K-weighted power."""
        if mono.size == 0:
            return np.zeros(0, dtype=np.float64)
        y, state.zi_pre = _biquad_filter(self._b_pre, self._a_pre, mono, state.zi_pre)
        y, state.zi_rlb = _biquad_filter(self._b_rlb, self._a_rlb, y, state.zi_rlb)
        power = y * y

        if state.ms_buffer is None or state.ms_buffer.size != self._momentary_samples:
            state.ms_buffer = np.zeros(self._momentary_samples, dtype=np.float64)
            state.ms_write = 0
            state.ms_filled = 0

        n = power.size
        buf = state.ms_buffer
        idx = state.ms_write
        if n >= self._momentary_samples:
            buf[:] = power[-self._momentary_samples:]
            state.ms_write = 0
            state.ms_filled = self._momentary_samples
        else:
            first = min(n, self._momentary_samples - idx)
            buf[idx:idx + first] = power[:first]
            rest = n - first
            if rest > 0:
                buf[0:rest] = power[first:]
            state.ms_write = (idx + n) % self._momentary_samples
            state.ms_filled = min(self._momentary_samples, state.ms_filled + n)

        mean_sq = float(np.mean(buf[:state.ms_filled])) if state.ms_filled else 0.0
        state.mean_sq = mean_sq
        state.lufs_momentary = mean_square_to_lufs(mean_sq)
        return power

    def _push_short_term(self, power: np.ndarray) -> None:
        """Accumulate stereo K-weighted power into the 3 s short-term window."""
        power = np.asarray(power, dtype=np.float64)
        if power.size == 0:
            return
        window = self._short_term_samples
        if self._st_buffer is None or self._st_buffer.size != window:
            self._st_buffer = np.zeros(window, dtype=np.float64)
            self._st_write = 0
            self._st_filled = 0
        buf = self._st_buffer
        n = power.size
        idx = self._st_write
        if n >= window:
            buf[:] = power[-window:]
            self._st_write = 0
            self._st_filled = window
        else:
            first = min(n, window - idx)
            buf[idx:idx + first] = power[:first]
            rest = n - first
            if rest > 0:
                buf[0:rest] = power[first:]
            self._st_write = (idx + n) % window
            self._st_filled = min(window, self._st_filled + n)
        mean_sq = float(np.mean(buf[:self._st_filled])) if self._st_filled else 0.0
        self._lufs_short_term = mean_square_to_lufs(mean_sq)

    def _update_peak_hold(self, left: float, right: float, n_frames: int) -> None:
        """Track short peak hold for UI."""
        if left > self._peak_hold_l or right > self._peak_hold_r:
            self._peak_hold_l = max(self._peak_hold_l, left)
            self._peak_hold_r = max(self._peak_hold_r, right)
            self._peak_hold_frames = 0
        else:
            self._peak_hold_frames += n_frames
            if self._peak_hold_frames >= self._peak_hold_duration_frames:
                self._peak_hold_l = left
                self._peak_hold_r = right
                self._peak_hold_frames = 0
