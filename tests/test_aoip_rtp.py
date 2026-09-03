#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for aoip_rtp.py (L16/L24 decode and channel downmix, no network).
"""

import struct

import numpy as np
import pytest

from aoip_rtp import decode_l16, decode_l24, decode_pcm, parse_rtp_payload
from livewire_capture import LivewireReceiver


def _pack_l24_sample(value: int) -> bytes:
    value &= 0xFFFFFF
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])


def _pack_l16_sample(value: int) -> bytes:
    return struct.pack(">h", int(value))


def _make_rtp_packet(payload: bytes, seq: int = 1) -> bytes:
    header = struct.pack("!BBHII", 0x80, 96, seq & 0xFFFF, 0, 0x12345678)
    return header + payload


class TestDecodeL16:
    def test_silence(self):
        frames = decode_l16(_pack_l16_sample(0) + _pack_l16_sample(0))
        assert frames.shape == (1, 2)
        assert frames[0, 0] == pytest.approx(0.0)
        assert frames[0, 1] == pytest.approx(0.0)

    def test_known_fraction(self):
        payload = _pack_l16_sample(16384) + _pack_l16_sample(-8192)
        frames = decode_l16(payload)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-4)
        assert frames[0, 1] == pytest.approx(-0.25, abs=1e-4)

    def test_full_scale_negative(self):
        payload = _pack_l16_sample(-32768) + _pack_l16_sample(-32768)
        frames = decode_l16(payload)
        assert frames[0, 0] == pytest.approx(-1.0)
        assert frames[0, 1] == pytest.approx(-1.0)

    def test_mono_duplicated_to_stereo(self):
        frames = decode_l16(_pack_l16_sample(16384), channels=1)
        assert frames.shape == (1, 2)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-4)
        assert frames[0, 1] == pytest.approx(0.5, abs=1e-4)

    def test_empty_payload(self):
        frames = decode_l16(b"")
        assert frames.shape == (0, 2)
        assert frames.dtype == np.float32


class TestDecodeL24Downmix:
    def test_eight_channel_uses_first_two(self):
        samples = [
            0x400000,  # ch0 = 0.5
            -0x200000,  # ch1 = -0.25
            0x7FFFFF,
            0x7FFFFF,
            0x7FFFFF,
            0x7FFFFF,
            0x7FFFFF,
            0x7FFFFF,
        ]
        payload = b"".join(_pack_l24_sample(value) for value in samples)
        frames = decode_l24(payload, channels=8)
        assert frames.shape == (1, 2)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-6)
        assert frames[0, 1] == pytest.approx(-0.25, abs=1e-6)

    def test_mono_duplicated_to_stereo(self):
        frames = decode_l24(_pack_l24_sample(0x400000), channels=1)
        assert frames.shape == (1, 2)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-6)
        assert frames[0, 1] == pytest.approx(0.5, abs=1e-6)


class TestDecodePcm:
    def test_l16_via_decode_pcm(self):
        payload = _pack_l16_sample(16384) + _pack_l16_sample(0)
        frames = decode_pcm(payload, codec="L16", channels=2)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-4)

    def test_l24_via_decode_pcm(self):
        payload = _pack_l24_sample(0x400000) + _pack_l24_sample(0)
        frames = decode_pcm(payload, codec="L24", channels=2)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-6)


class TestParseRtpPayload:
    def test_basic_packet(self):
        audio = _pack_l16_sample(0) + _pack_l16_sample(0)
        seq, payload = parse_rtp_payload(_make_rtp_packet(audio, seq=7))
        assert seq == 7
        assert payload == audio


class TestLivewireReceiverWrapper:
    def test_maps_channel_to_multicast(self):
        receiver = LivewireReceiver(channel=1, on_frames=lambda _frames: None)
        assert receiver.channel == 1
        assert receiver.multicast == "239.192.0.1"
        assert receiver.port == 5004
        assert receiver.codec == "L24"
        assert receiver.channels == 2
        assert receiver.sample_rate == 48000
