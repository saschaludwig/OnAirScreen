#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for meter_engine.py
"""

import numpy as np
import pytest

from meter_engine import (
    LUFS_SILENCE,
    MeterEngine,
    MeterUnit,
    bbc_ppm_to_db,
    db_to_bbc_ppm,
    linear_to_db,
    migrate_audio_layout_and_unit,
    normalize_meter_value,
    normalize_lr_unit,
)


class TestScaleHelpers:
    def test_linear_to_db_full_scale(self):
        assert linear_to_db(1.0) == pytest.approx(0.0, abs=1e-6)

    def test_linear_to_db_minus_20(self):
        assert linear_to_db(0.1) == pytest.approx(-20.0, abs=1e-6)

    def test_linear_to_db_silence(self):
        assert linear_to_db(0.0) == -120.0

    def test_bbc_ppm_alignment(self):
        assert db_to_bbc_ppm(-18.0) == pytest.approx(4.0)
        assert bbc_ppm_to_db(4.0) == pytest.approx(-18.0)
        assert db_to_bbc_ppm(-14.0) == pytest.approx(5.0)
        assert db_to_bbc_ppm(-6.0) == pytest.approx(7.0)

    def test_normalize_dbfs(self):
        assert normalize_meter_value(0.0, MeterUnit.DBFS) == pytest.approx(1.0)
        assert normalize_meter_value(-60.0, MeterUnit.DBFS) == pytest.approx(0.0)
        assert normalize_meter_value(-30.0, MeterUnit.DBFS) == pytest.approx(0.5)

    def test_normalize_bbc_ppm(self):
        assert normalize_meter_value(1.0, MeterUnit.BBC_PPM) == pytest.approx(0.0)
        assert normalize_meter_value(7.0, MeterUnit.BBC_PPM) == pytest.approx(1.0)
        assert normalize_meter_value(4.0, MeterUnit.BBC_PPM) == pytest.approx(0.5)

    def test_legacy_lufs_unit_maps_to_dbtp(self):
        assert normalize_lr_unit("lufs") == MeterUnit.DBTP
        assert normalize_lr_unit(MeterUnit.LUFS) == MeterUnit.DBTP

    def test_migrate_unit_lufs_without_layout(self):
        layout, unit = migrate_audio_layout_and_unit("lufs", None)
        assert layout == "lufs"
        assert unit == "dbtp"

    def test_migrate_keeps_layout_when_present(self):
        layout, unit = migrate_audio_layout_and_unit("lufs", "both")
        assert layout == "both"
        assert unit == "dbtp"


class TestMeterEngineDbfs:
    def test_sine_peak_dbfs(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        engine.set_unit(MeterUnit.DBFS)
        t = np.arange(sr) / sr
        # Peak amplitude 0.5 -> -6 dBFS
        left = 0.5 * np.sin(2 * np.pi * 1000 * t)
        right = 0.25 * np.sin(2 * np.pi * 1000 * t)
        frames = np.column_stack([left, right]).astype(np.float32)
        reading = engine.process(frames)
        assert reading.left == pytest.approx(-6.0, abs=0.2)
        assert reading.right == pytest.approx(-12.0, abs=0.2)
        assert reading.max_sample_peak_dbfs == pytest.approx(-6.0, abs=0.2)

    def test_rms_below_peak(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        engine.set_unit(MeterUnit.DBFS)
        t = np.arange(sr) / sr
        tone = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        reading = engine.process(frames)
        assert reading.rms_left < reading.left
        assert reading.rms_left == pytest.approx(-9.0, abs=0.5)


class TestMeterEngineDbtp:
    def test_true_peak_at_least_sample_peak(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        engine.set_unit(MeterUnit.DBTP)
        # Alternating samples that can create inter-sample peaks when upsampled
        mono = np.array([0.0, 0.9, 0.0, -0.9] * 2000, dtype=np.float64)
        frames = np.column_stack([mono, mono])
        reading = engine.process(frames)
        assert reading.max_true_peak_dbtp >= reading.max_sample_peak_dbfs - 0.01
        assert reading.left >= reading.max_sample_peak_dbfs - 1.0


class TestMeterEngineBbcPpm:
    def test_steady_tone_near_mark_4(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        engine.set_unit(MeterUnit.BBC_PPM)
        t = np.arange(int(0.5 * sr)) / sr
        # -18 dBFS sine -> ~ PPM 4 after attack settles
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        reading = None
        for i in range(0, len(tone), 1024):
            reading = engine.process(frames[i:i + 1024])
        assert reading.left == pytest.approx(4.0, abs=0.2)
        assert reading.right == pytest.approx(4.0, abs=0.2)

    def test_10ms_burst_underreads_by_about_2db(self):
        """IEC 60268-10 Type IIa: 10 ms / 5 kHz burst ~2 dB below continuous."""
        sr = 48000
        amp = 10 ** (-18.0 / 20.0)
        freq = 5000.0

        def ppm_after(signal: np.ndarray) -> float:
            engine = MeterEngine(sample_rate=sr, channels=1)
            engine.set_unit(MeterUnit.BBC_PPM)
            value = 0.0
            frames = signal.reshape(-1, 1)
            for i in range(0, len(signal), 256):
                value = engine.process(frames[i:i + 256]).left
            return value

        # Continuous reference
        t_cont = np.arange(int(0.3 * sr)) / sr
        continuous = amp * np.sin(2 * np.pi * freq * t_cont)
        ppm_cont = ppm_after(continuous)

        # 10 ms burst from silence
        n_burst = int(0.010 * sr)
        t_burst = np.arange(n_burst) / sr
        burst = amp * np.sin(2 * np.pi * freq * t_burst)
        ppm_burst = ppm_after(burst)

        underread_db = (ppm_cont - ppm_burst) * 4.0  # 4 dB per PPM mark
        assert underread_db == pytest.approx(2.0, abs=0.5)

    def test_release_falls_24db_in_2_8s(self):
        """IEC 60268-10 Type IIa return time: 24 dB in 2.8 s."""
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=1)
        engine.set_unit(MeterUnit.BBC_PPM)
        amp = 10 ** (-6.0 / 20.0)  # high enough to observe a full 24 dB fall
        t = np.arange(int(0.4 * sr)) / sr
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        for i in range(0, len(tone), 1024):
            engine.process(tone[i:i + 1024].reshape(-1, 1))
        env_start = engine._states[0].ppm_linear
        assert env_start > 0.0

        silence = np.zeros(int(2.8 * sr), dtype=np.float64)
        for i in range(0, len(silence), 1024):
            engine.process(silence[i:i + 1024].reshape(-1, 1))
        env_end = engine._states[0].ppm_linear
        fall_db = 20.0 * np.log10(env_start / max(env_end, 1e-12))
        assert fall_db == pytest.approx(24.0, abs=1.0)


class TestMeterEngineLufs:
    def test_programme_m_near_ebu_for_1khz(self):
        """Stereo 1 kHz at -18 dBFS peak is near -18 LUFS programme M (G_i=1)."""
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(sr) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        reading = None
        for i in range(0, len(tone), 2048):
            reading = engine.process(frames[i:i + 2048])
        # Two correlated channels sum in power: ~3 LU louder than per-channel
        assert reading.lufs_m == pytest.approx(-18.0, abs=2.5)

    def test_programme_m_louder_than_one_channel(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(sr) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        stereo = np.column_stack([tone, tone])
        mono_right_silent = np.column_stack([tone, np.zeros_like(tone)])
        stereo_m = LUFS_SILENCE
        mono_m = LUFS_SILENCE
        for i in range(0, len(tone), 2048):
            stereo_m = engine.process(stereo[i:i + 2048]).lufs_m
        engine.reset()
        for i in range(0, len(tone), 2048):
            mono_m = engine.process(mono_right_silent[i:i + 2048]).lufs_m
        assert stereo_m > mono_m + 2.0

    def test_short_term_tracks_steady_tone(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(int(3.2 * sr)) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        reading = None
        for i in range(0, len(tone), 2048):
            reading = engine.process(frames[i:i + 2048])
        assert reading.lufs_s == pytest.approx(reading.lufs_m, abs=1.5)

    def test_integrated_default_inactive(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(sr) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        reading = engine.process(frames[:4096])
        assert reading.integrated_running is False
        assert reading.lufs_i == LUFS_SILENCE
        assert reading.lra_low == LUFS_SILENCE

    def test_start_resets_and_measures(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(int(1.2 * sr)) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        engine.start_integrated()
        reading = None
        for i in range(0, len(tone), 2048):
            reading = engine.process(frames[i:i + 2048])
        assert reading.integrated_running is True
        assert reading.lufs_i > LUFS_SILENCE + 10

        frozen = reading.lufs_i
        engine.stop_integrated()
        silence = np.zeros((sr, 2), dtype=np.float64)
        for i in range(0, len(silence), 2048):
            reading = engine.process(silence[i:i + 2048])
        assert reading.integrated_running is False
        assert reading.lufs_i == pytest.approx(frozen, abs=0.01)

        engine.start_integrated()
        reading = engine.process(frames[:2048])
        assert reading.integrated_running is True
        assert reading.lufs_i == LUFS_SILENCE

    def test_reset_while_running_restarts_session(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(int(1.2 * sr)) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        engine.start_integrated()
        reading = None
        for i in range(0, len(tone), 2048):
            reading = engine.process(frames[i:i + 2048])
        assert reading.lufs_i > LUFS_SILENCE + 10

        engine.reset_integrated()
        reading = engine.process(frames[:2048])
        assert reading.integrated_running is True
        assert reading.lufs_i == LUFS_SILENCE

    def test_reset_while_stopped_clears_frozen_values(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(int(1.2 * sr)) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        engine.start_integrated()
        reading = None
        for i in range(0, len(tone), 2048):
            reading = engine.process(frames[i:i + 2048])
        engine.stop_integrated()
        assert reading.lufs_i > LUFS_SILENCE + 10

        engine.reset_integrated()
        silence = np.zeros((2048, 2), dtype=np.float64)
        reading = engine.process(silence)
        assert reading.integrated_running is False
        assert reading.lufs_i == LUFS_SILENCE
        assert reading.lra_low == LUFS_SILENCE
        assert reading.lra_high == LUFS_SILENCE

    def test_integrated_snapshot_clears_immediately_on_reset(self):
        """Snapshot reads the engine, so reset is visible before the next process()."""
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=2)
        t = np.arange(int(1.2 * sr)) / sr
        amp = 10 ** (-18.0 / 20.0)
        tone = (amp * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        frames = np.column_stack([tone, tone])
        engine.start_integrated()
        reading = None
        for i in range(0, len(tone), 2048):
            reading = engine.process(frames[i:i + 2048])
        assert reading.lufs_i > LUFS_SILENCE + 10
        running, lufs_i, _lra_low, _lra_high = engine.integrated_snapshot()
        assert running is True
        assert lufs_i == pytest.approx(reading.lufs_i, abs=0.01)

        engine.stop_integrated()
        engine.reset_integrated()
        running, lufs_i, lra_low, lra_high = engine.integrated_snapshot()
        assert running is False
        assert lufs_i == LUFS_SILENCE
        assert lra_low == LUFS_SILENCE
        assert lra_high == LUFS_SILENCE


class TestDigitalPeakBallistics:
    def test_peak_attacks_instantly(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=1)
        engine.set_unit(MeterUnit.DBFS)
        burst = np.full(256, 0.5, dtype=np.float64).reshape(-1, 1)
        reading = engine.process(burst)
        assert reading.left == pytest.approx(-6.0, abs=0.2)
        assert reading.max_sample_peak_dbfs == pytest.approx(-6.0, abs=0.2)

    def test_peak_falls_20db_in_1_7s(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=1)
        engine.set_unit(MeterUnit.DBFS)
        burst = np.full(1024, 0.5, dtype=np.float64).reshape(-1, 1)
        start = engine.process(burst).left
        silence = np.zeros(int(1.7 * sr), dtype=np.float64)
        reading = None
        for i in range(0, len(silence), 1024):
            reading = engine.process(silence[i:i + 1024].reshape(-1, 1))
        assert reading.left == pytest.approx(start - 20.0, abs=0.6)
        assert reading.max_sample_peak_dbfs == pytest.approx(-120.0, abs=0.01)

    def test_rms_window_holds_after_short_silence(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=1)
        engine.set_unit(MeterUnit.DBFS)
        t = np.arange(int(0.3 * sr)) / sr
        tone = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float64)
        engine.process(tone.reshape(-1, 1))
        short_silence = np.zeros(int(0.05 * sr), dtype=np.float64)
        reading = engine.process(short_silence.reshape(-1, 1))
        assert reading.rms_left == pytest.approx(-9.0, abs=2.0)
        assert reading.max_sample_peak_dbfs == pytest.approx(-120.0, abs=0.01)

    def test_snap_display_dumps_peak_immediately(self):
        sr = 48000
        engine = MeterEngine(sample_rate=sr, channels=1)
        engine.set_unit(MeterUnit.DBFS)
        engine.process(np.full((1024, 1), 0.5, dtype=np.float64))
        engine.snap_display_to_floor()
        reading = engine.process(np.zeros((256, 1), dtype=np.float64))
        assert reading.left == pytest.approx(-120.0)
        assert reading.rms_left == pytest.approx(-120.0)
