#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ptp_client.py (packet parsing, no live network).
"""

from ptp_client import (
    FLAG_PTP_TIMESCALE,
    FLAG_TWO_STEP,
    MSG_ANNOUNCE,
    MSG_FOLLOW_UP,
    MSG_SYNC,
    PTP_HEADER_SIZE,
    build_delay_req,
    clock_identity_from_mac,
    effective_utc_offset,
    parse_announce_utc_offset,
    parse_header,
    parse_timestamp,
    ptp_timestamp_to_unix,
)


def _header_bytes(
    message_type: int,
    domain: int = 0,
    flags: int = 0,
    sequence_id: int = 1,
    clock_id: bytes = b"\x01\x02\x03\x04\x05\x06\x07\x08",
) -> bytes:
    from ptp_client import _HEADER_STRUCT, PTP_VERSION

    return _HEADER_STRUCT.pack(
        message_type & 0x0F,
        PTP_VERSION,
        44,
        domain,
        0,
        flags,
        0,
        0,
        clock_id,
        1,
        sequence_id,
        0,
        0,
    )


def _timestamp_bytes(seconds: int, nanos: int) -> bytes:
    return seconds.to_bytes(6, "big") + nanos.to_bytes(4, "big")


class TestPtpParsing:
    def test_parse_sync_header(self):
        data = _header_bytes(MSG_SYNC, domain=0, flags=FLAG_TWO_STEP, sequence_id=42)
        header = parse_header(data)
        assert header is not None
        assert header.message_type == MSG_SYNC
        assert header.two_step is True
        assert header.sequence_id == 42
        assert header.domain == 0
        assert header.version == 2

    def test_parse_header_rejects_short_buffer(self):
        assert parse_header(b"\x00" * 10) is None

    def test_parse_header_rejects_wrong_version(self):
        data = bytearray(_header_bytes(MSG_SYNC))
        data[1] = 1  # version 1
        assert parse_header(bytes(data)) is None

    def test_parse_timestamp(self):
        data = _header_bytes(MSG_FOLLOW_UP) + _timestamp_bytes(1_700_000_000, 123456789)
        ts = parse_timestamp(data)
        assert ts == (1_700_000_000, 123456789)

    def test_ptp_timestamp_to_unix_applies_utc_offset(self):
        unix = ptp_timestamp_to_unix(1_700_000_037, 0, utc_offset=37)
        assert unix == 1_700_000_000.0

    def test_effective_utc_offset_ignored_on_arb_timescale(self):
        assert effective_utc_offset(False, 37) == 0

    def test_effective_utc_offset_applied_on_ptp_timescale(self):
        assert effective_utc_offset(True, 37) == 37

    def test_parse_header_ptp_timescale_flag(self):
        data = _header_bytes(MSG_ANNOUNCE, flags=FLAG_PTP_TIMESCALE)
        header = parse_header(data)
        assert header is not None
        assert header.ptp_timescale is True
        assert parse_header(_header_bytes(MSG_ANNOUNCE)).ptp_timescale is False

    def test_parse_announce_utc_offset(self):
        body = _timestamp_bytes(0, 0) + (37).to_bytes(2, "big") + b"\x00" * 18
        data = _header_bytes(MSG_ANNOUNCE) + body
        assert parse_announce_utc_offset(data) == 37

    def test_clock_identity_from_mac(self):
        mac = bytes.fromhex("aabbccddeeff")
        ident = clock_identity_from_mac(mac)
        assert ident == bytes.fromhex("aabbccfffeddeeff")

    def test_build_delay_req(self):
        ident = b"\x11" * 8
        pkt = build_delay_req(ident, sequence_id=9, domain=2)
        header = parse_header(pkt)
        assert header is not None
        assert header.message_type == 0x1
        assert header.domain == 2
        assert header.sequence_id == 9
        assert len(pkt) == PTP_HEADER_SIZE + 10
