#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for livewire_capture.py (decode / RTP parse, no network).
"""

import struct

import numpy as np
import pytest

from livewire_capture import decode_l24_stereo, parse_rtp_payload


def _pack_l24_sample(value: int) -> bytes:
    """Pack a signed 24-bit integer as big-endian bytes."""
    value &= 0xFFFFFF
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])


def _make_rtp_packet(payload: bytes, seq: int = 1, padding: bool = False, pad_len: int = 0) -> bytes:
    """Build a minimal RTP v2 header + payload (no CSRC, no extension)."""
    first = 0x80  # V=2, P=0, X=0, CC=0
    if padding:
        first |= 0x20
    header = struct.pack("!BBHII", first, 96, seq & 0xFFFF, 0, 0x12345678)
    body = payload
    if padding and pad_len > 0:
        body = payload + (b"\x00" * (pad_len - 1)) + bytes([pad_len])
    return header + body


class TestDecodeL24Stereo:
    def test_silence(self):
        payload = _pack_l24_sample(0) + _pack_l24_sample(0)
        frames = decode_l24_stereo(payload)
        assert frames.shape == (1, 2)
        assert frames[0, 0] == pytest.approx(0.0)
        assert frames[0, 1] == pytest.approx(0.0)

    def test_full_scale_positive(self):
        # 0x7FFFFF ~= +1.0 (minus 1 LSB)
        left = _pack_l24_sample(0x7FFFFF)
        right = _pack_l24_sample(0)
        frames = decode_l24_stereo(left + right)
        assert frames.shape == (1, 2)
        assert frames[0, 0] == pytest.approx(1.0 - (1.0 / (1 << 23)), abs=1e-7)
        assert frames[0, 1] == pytest.approx(0.0)

    def test_full_scale_negative(self):
        # 0x800000 = -1.0 in signed 24-bit
        left = _pack_l24_sample(0x800000)
        right = _pack_l24_sample(0x800000)
        frames = decode_l24_stereo(left + right)
        assert frames[0, 0] == pytest.approx(-1.0)
        assert frames[0, 1] == pytest.approx(-1.0)

    def test_known_fraction(self):
        # 0x400000 = 0.5
        payload = _pack_l24_sample(0x400000) + _pack_l24_sample(-0x200000 & 0xFFFFFF)
        frames = decode_l24_stereo(payload)
        assert frames[0, 0] == pytest.approx(0.5, abs=1e-6)
        assert frames[0, 1] == pytest.approx(-0.25, abs=1e-6)

    def test_truncates_incomplete_frame(self):
        # One full stereo frame + 2 leftover bytes
        payload = _pack_l24_sample(0) + _pack_l24_sample(0) + b"\x01\x02"
        frames = decode_l24_stereo(payload)
        assert frames.shape == (1, 2)

    def test_empty_payload(self):
        frames = decode_l24_stereo(b"")
        assert frames.shape == (0, 2)
        assert frames.dtype == np.float32


class TestParseRtpPayload:
    def test_basic_packet(self):
        audio = _pack_l24_sample(0) + _pack_l24_sample(0)
        packet = _make_rtp_packet(audio, seq=42)
        seq, payload = parse_rtp_payload(packet)
        assert seq == 42
        assert payload == audio

    def test_too_short(self):
        seq, payload = parse_rtp_payload(b"\x80\x60")
        assert seq is None
        assert payload == b""

    def test_wrong_version(self):
        # V=1
        packet = b"\x40" + b"\x00" * 11 + b"\x00" * 6
        seq, payload = parse_rtp_payload(packet)
        assert seq is None

    def test_padding_stripped(self):
        audio = _pack_l24_sample(0x100000) + _pack_l24_sample(0)
        packet = _make_rtp_packet(audio, seq=7, padding=True, pad_len=4)
        seq, payload = parse_rtp_payload(packet)
        assert seq == 7
        assert payload == audio
