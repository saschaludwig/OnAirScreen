#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for audio_capture.py (signal-loss fallback, no network).
"""

import sys
import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from audio_capture import (
    SIGNAL_LOSS_TIMEOUT_S,
    AudioCaptureController,
)
from meter_engine import MeterUnit

if not QApplication.instance():
    QApplication(sys.argv)


@pytest.fixture
def capture() -> AudioCaptureController:
    controller = AudioCaptureController()
    controller.configure(unit=MeterUnit.DBFS, source="device")
    return controller


def _loud_block(frames: int = 1024, amplitude: float = 0.5) -> np.ndarray:
    return np.full((frames, 2), amplitude, dtype=np.float32)


class TestSignalLossFallsToFloor:
    def test_levels_fall_to_minus_inf_after_timeout(self, capture: AudioCaptureController):
        capture._process_frames(_loud_block())
        assert capture._latest.left > -20.0
        assert capture._latest.right > -20.0
        assert capture._latest.max_sample_peak_dbfs > -20.0

        past = time.monotonic() - SIGNAL_LOSS_TIMEOUT_S - 0.2
        capture._last_signal_monotonic = past
        capture._last_process_monotonic = past

        injected = capture._inject_silence_if_stale()
        assert injected is True
        assert capture._latest.left == pytest.approx(-120.0)
        assert capture._latest.right == pytest.approx(-120.0)
        assert capture._latest.max_sample_peak_dbfs == pytest.approx(-120.0)
        assert capture._latest.max_true_peak_dbtp == pytest.approx(-120.0)

    def test_recent_signal_is_not_replaced_with_silence(self, capture: AudioCaptureController):
        capture._process_frames(_loud_block())
        before = capture._latest
        injected = capture._inject_silence_if_stale()
        assert injected is False
        assert capture._latest == before

    def test_poll_emits_floor_after_stream_loss(self, capture: AudioCaptureController):
        received = []
        capture.levels.connect(lambda *values: received.append(values))
        capture._process_frames(_loud_block())

        past = time.monotonic() - SIGNAL_LOSS_TIMEOUT_S - 0.2
        capture._last_signal_monotonic = past
        capture._last_process_monotonic = past
        capture._emit_latest_levels()

        assert received
        assert received[-1][0].left == pytest.approx(-120.0)
        assert received[-1][0].right == pytest.approx(-120.0)


class TestNeverSignalAfterRestart:
    def test_poll_emits_floor_before_any_frames(self, capture: AudioCaptureController):
        received = []
        capture.levels.connect(lambda readings: received.append(readings))
        capture._reset_level_state()
        capture._emit_latest_levels()

        assert received
        assert received[-1].left == pytest.approx(-120.0)
        assert received[-1].right == pytest.approx(-120.0)

    def test_injects_silence_after_timeout_without_ever_receiving_signal(
        self, capture: AudioCaptureController
    ):
        capture._reset_level_state()
        past = time.monotonic() - SIGNAL_LOSS_TIMEOUT_S - 0.2
        capture._last_signal_monotonic = past
        capture._last_process_monotonic = past

        injected = capture._inject_silence_if_stale()
        assert injected is True
        assert capture._latest.left == pytest.approx(-120.0)
        assert capture._latest.right == pytest.approx(-120.0)
        assert capture._latest.max_sample_peak_dbfs == pytest.approx(-120.0)


class TestAes67NoStream:
    def test_start_without_address_does_not_emit_error(self, capture: AudioCaptureController):
        errors = []
        capture.error.connect(errors.append)
        capture.configure(source="aes67", aes67_addr="", unit=MeterUnit.DBFS)
        capture.start()
        assert capture.is_running is False
        assert errors == []


class TestIntegratedSession:
    def test_start_and_stop_are_thread_safe_on_engine(self, capture: AudioCaptureController):
        assert capture.integrated_running is False
        capture.start_integrated()
        assert capture.integrated_running is True
        capture.stop_integrated()
        assert capture.integrated_running is False

    def test_reset_clears_without_starting(self, capture: AudioCaptureController):
        capture.start_integrated()
        capture.stop_integrated()
        capture.reset_integrated()
        assert capture.integrated_running is False
        running, lufs_i, lra_low, lra_high = capture.integrated_snapshot()
        assert running is False
        assert lufs_i == -120.0
        assert lra_low == -120.0
        assert lra_high == -120.0

    def test_toggle_starts_then_stops(self, capture: AudioCaptureController):
        assert capture.toggle_integrated() is True
        assert capture.integrated_running is True
        assert capture.toggle_integrated() is False
        assert capture.integrated_running is False

    def test_levels_include_programme_lufs(self, capture: AudioCaptureController):
        received = []
        capture.levels.connect(lambda readings: received.append(readings))
        capture._process_frames(_loud_block())
        capture._emit_latest_levels()
        assert received
        assert received[-1].lufs_m > -120.0
        assert received[-1].integrated_running is False


def _fake_sounddevice(monkeypatch, devices):
    """Install a fake sounddevice module for device-list tests."""
    import sys
    from unittest.mock import Mock

    fake = Mock()
    fake._initialized = 1
    fake.default.device = [0, 1]
    fake.query_devices.return_value = devices

    def terminate():
        fake._initialized -= 1

    def initialize():
        fake._initialized += 1

    fake._terminate.side_effect = terminate
    fake._initialize.side_effect = initialize
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    return fake


class TestListInputDevicesRefresh:
    @pytest.fixture(autouse=True)
    def _clear_portaudio_owners(self):
        from audio_capture import _portaudio_owners

        _portaudio_owners.clear()
        yield
        _portaudio_owners.clear()

    def test_without_refresh_does_not_reinitialize(self, monkeypatch):
        from audio_capture import list_input_devices

        fake = _fake_sounddevice(
            monkeypatch,
            [
                {"max_input_channels": 2, "name": "Mic", "default_samplerate": 48000},
                {"max_input_channels": 0, "name": "Out", "default_samplerate": 48000},
            ],
        )
        devices = list_input_devices()
        assert [device.name for device in devices] == ["Mic"]
        fake._terminate.assert_not_called()
        fake._initialize.assert_not_called()

    def test_refresh_reinitializes_portaudio(self, monkeypatch):
        from audio_capture import list_input_devices

        fake = _fake_sounddevice(
            monkeypatch,
            [{"max_input_channels": 1, "name": "USB", "default_samplerate": 44100}],
        )
        devices = list_input_devices(refresh=True)
        assert [device.name for device in devices] == ["USB"]
        fake._terminate.assert_called()
        fake._initialize.assert_called()
        assert fake._initialized == 1

    def test_refresh_pauses_and_restores_stream_owners(self, monkeypatch):
        from unittest.mock import Mock

        from audio_capture import list_input_devices, register_portaudio_owner

        _fake_sounddevice(monkeypatch, [])
        owner = Mock()
        order = []
        owner.pause_for_portaudio_rescan.side_effect = lambda: (order.append("pause") or True)
        owner.restore_after_portaudio_rescan.side_effect = lambda: order.append("restore")
        register_portaudio_owner(owner)
        list_input_devices(refresh=True)
        assert order == ["pause", "restore"]

    def test_pause_closes_local_stream_without_touching_aoip(self):
        capture = AudioCaptureController()
        stream = type("Stream", (), {})()
        stream.stop = lambda: None
        stream.close = lambda: None
        capture._stream = stream
        capture._rtp = object()
        assert capture.pause_for_portaudio_rescan() is True
        assert capture._stream is None
        assert capture._rtp is not None

    def test_pause_without_stream_returns_false(self):
        capture = AudioCaptureController()
        assert capture.pause_for_portaudio_rescan() is False
