#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ltc_reader.py (parser and port selection; no hardware).
"""

from types import SimpleNamespace

from ltc_reader import (
    LEO_BODNAR_VID,
    auto_select_port,
    infer_frame_rate,
    ltc_milliseconds,
    pack_lbe1110_frame,
    parse_lbe1110_buffer,
)


def _port(device, vid=None, description="", manufacturer="", product=None):
    return SimpleNamespace(
        device=device,
        vid=vid,
        description=description,
        manufacturer=manufacturer,
        product=product,
        hwid="",
    )


class TestParseLbe1110Buffer:
    def test_one_complete_frame(self):
        data = pack_lbe1110_frame(12, 34, 56, 10)
        rest, frames = parse_lbe1110_buffer(data)
        assert rest == b""
        assert len(frames) == 1
        assert frames[0].hours == 12
        assert frames[0].minutes == 34
        assert frames[0].seconds == 56
        assert frames[0].frames == 10

    def test_two_frames(self):
        data = pack_lbe1110_frame(1, 2, 3, 4) + pack_lbe1110_frame(1, 2, 3, 5)
        rest, frames = parse_lbe1110_buffer(data)
        assert rest == b""
        assert [f.frames for f in frames] == [4, 5]

    def test_sync_in_the_middle_of_stream(self):
        prefix = b"\x00\x01\x02"
        data = prefix + pack_lbe1110_frame(9, 8, 7, 6)
        rest, frames = parse_lbe1110_buffer(data)
        assert rest == b""
        assert len(frames) == 1
        assert frames[0].hours == 9
        assert frames[0].frames == 6

    def test_remainder_kept_for_partial_packet(self):
        data = pack_lbe1110_frame(0, 0, 1, 0) + b"\x01\x02\x03"
        rest, frames = parse_lbe1110_buffer(data)
        assert len(frames) == 1
        assert rest == b"\x01\x02\x03"

    def test_incomplete_sync_is_remainder(self):
        rest, frames = parse_lbe1110_buffer(b"\x55")
        assert frames == []
        assert rest == b"\x55"

    def test_invalid_hours_are_skipped_but_consumed(self):
        data = pack_lbe1110_frame(99, 0, 0, 0) + pack_lbe1110_frame(1, 0, 0, 0)
        rest, frames = parse_lbe1110_buffer(data)
        assert rest == b""
        assert len(frames) == 1
        assert frames[0].hours == 1

    def test_invalid_minutes_skipped(self):
        rest, frames = parse_lbe1110_buffer(pack_lbe1110_frame(0, 60, 0, 0))
        assert rest == b""
        assert frames == []

    def test_invalid_seconds_skipped(self):
        rest, frames = parse_lbe1110_buffer(pack_lbe1110_frame(0, 0, 60, 0))
        assert rest == b""
        assert frames == []

    def test_frames_above_29_skipped(self):
        rest, frames = parse_lbe1110_buffer(pack_lbe1110_frame(0, 0, 0, 30))
        assert rest == b""
        assert frames == []

    def test_empty_buffer(self):
        rest, frames = parse_lbe1110_buffer(b"")
        assert rest == b""
        assert frames == []

    def test_sync_without_payload_is_skipped(self):
        data = b"\x55\xaa" + pack_lbe1110_frame(2, 3, 4, 5)
        rest, frames = parse_lbe1110_buffer(data)
        assert rest == b""
        assert len(frames) == 1
        assert frames[0].hours == 2


class TestInferFrameRate:
    def test_snaps_to_24_25_30(self):
        assert infer_frame_rate(0) == 24.0
        assert infer_frame_rate(23) == 24.0
        assert infer_frame_rate(24) == 25.0
        assert infer_frame_rate(29) == 30.0
        assert infer_frame_rate(40) == 30.0


class TestLtcMilliseconds:
    def test_25_fps(self):
        assert ltc_milliseconds(0, 25.0) == 0
        assert ltc_milliseconds(12, 25.0) == 480

    def test_zero_rate(self):
        assert ltc_milliseconds(10, 0.0) == 0


class TestAutoSelectPort:
    def test_prefers_leo_bodnar_vid(self):
        ports = [
            _port("/dev/tty.usbmodem1", description="Other"),
            _port("/dev/tty.usbmodem2", vid=LEO_BODNAR_VID, description="CDC"),
        ]
        assert auto_select_port(ports) == "/dev/tty.usbmodem2"

    def test_matches_lbe_1110_description(self):
        ports = [
            _port("COM3", description="USB Serial"),
            _port("COM4", description="LBE-1110 USB Serial Timecode Reader"),
        ]
        assert auto_select_port(ports) == "COM4"

    def test_falls_back_to_cdc_or_usbmodem(self):
        ports = [
            _port("/dev/tty.Bluetooth-Incoming-Port"),
            _port("/dev/tty.usbmodem1401"),
        ]
        assert auto_select_port(ports) == "/dev/tty.usbmodem1401"

    def test_empty_list(self):
        assert auto_select_port([]) == ""
