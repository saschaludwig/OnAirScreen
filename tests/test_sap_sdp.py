#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for sap_sdp.py (SAP/SDP parse, origin hash, discovery, no network).
"""

import time

import pytest

from sap_sdp import (
    SapDiscovery,
    SdpError,
    build_sap_packet,
    origin_hash,
    parse_sap_packet,
    parse_sdp,
)

SESSION_LEVEL_SDP = """\
v=0
o=- 111 1 IN IP4 192.168.1.10
s=Studio Mix
c=IN IP4 239.69.1.1/32
t=0 0
m=audio 5004 RTP/AVP 96
a=rtpmap:96 L24/48000/2
"""

MEDIA_LEVEL_SDP = """\
v=0
o=- 222 1 IN IP4 192.168.1.20
s=Mic 1
c=IN IP4 239.255.0.1/32
t=0 0
m=audio 5004 RTP/AVP 97
c=IN IP4 239.69.9.9/32
a=rtpmap:97 L16/44100/1
"""

DANTE_SDP = """\
v=0
o=- 333 1 IN IP4 192.168.1.30
s=Dante Out
c=IN IP4 239.69.2.2/32
t=0 0
m=audio 5004 RTP/AVP 96
a=rtpmap:96 L24/48000/8
a=keywords:Dante
"""


class TestOriginHash:
    def test_same_origin_same_id(self):
        assert origin_hash("- 111 1 IN IP4 192.168.1.10") == origin_hash(
            "- 111 1 IN IP4 192.168.1.10"
        )

    def test_different_origin_different_id_same_addr(self):
        first = parse_sdp(SESSION_LEVEL_SDP)
        other = SESSION_LEVEL_SDP.replace("o=- 111 1", "o=- 999 1")
        second = parse_sdp(other)
        assert first.multicast == second.multicast
        assert first.port == second.port
        assert first.stream_id != second.stream_id


class TestParseSdp:
    def test_session_level_connection_l24_stereo(self):
        stream = parse_sdp(SESSION_LEVEL_SDP)
        assert stream.name == "Studio Mix"
        assert stream.multicast == "239.69.1.1"
        assert stream.port == 5004
        assert stream.codec == "L24"
        assert stream.sample_rate == 48000
        assert stream.channels == 2
        assert stream.stream_id == origin_hash("- 111 1 IN IP4 192.168.1.10")
        assert stream.dante is False

    def test_media_level_connection_overrides_session(self):
        stream = parse_sdp(MEDIA_LEVEL_SDP)
        assert stream.multicast == "239.69.9.9"
        assert stream.codec == "L16"
        assert stream.sample_rate == 44100
        assert stream.channels == 1

    def test_dante_keyword_is_label_only(self):
        stream = parse_sdp(DANTE_SDP)
        assert stream.dante is True
        assert stream.channels == 8
        assert "Dante" in stream.label()

    def test_pasted_sdp_is_visible_in_label(self):
        stream = parse_sdp(SESSION_LEVEL_SDP, manual=True)
        assert stream.manual is True
        assert "pasted SDP" in stream.label()
        assert stream.snapshot()["manual"] is True

    def test_snapshot_keys(self):
        snap = parse_sdp(SESSION_LEVEL_SDP).snapshot()
        assert snap["addr"] == "239.69.1.1"
        assert snap["port"] == 5004
        assert snap["codec"] == "L24"
        assert snap["rate"] == 48000
        assert snap["channels"] == 2
        assert snap["manual"] is False

    def test_missing_origin(self):
        with pytest.raises(SdpError, match="origin"):
            parse_sdp("s=No Origin\nm=audio 5004 RTP/AVP 96\na=rtpmap:96 L24/48000/2\n")

    def test_unsupported_rtpmap(self):
        bad = SESSION_LEVEL_SDP.replace("L24/48000/2", "L24/48000/2\na=rtpmap:97 L16/48000/2")
        with pytest.raises(SdpError, match="rtpmap"):
            parse_sdp(bad)

    def test_unsupported_rate(self):
        with pytest.raises(SdpError, match="samplerate"):
            parse_sdp(SESSION_LEVEL_SDP.replace("L24/48000/2", "L24/32000/2"))


class TestParseSapPacket:
    def test_announcement_roundtrip(self):
        packet = build_sap_packet(SESSION_LEVEL_SDP, deleted=False)
        deleted, text = parse_sap_packet(packet)
        assert deleted is False
        assert text is not None
        stream = parse_sdp(text)
        assert stream.name == "Studio Mix"

    def test_deletion_bit(self):
        packet = build_sap_packet(SESSION_LEVEL_SDP, deleted=True)
        deleted, text = parse_sap_packet(packet)
        assert deleted is True
        assert text is not None
        assert packet[0] & 0x04

    def test_rejects_other_mime(self):
        packet = bytearray(build_sap_packet(SESSION_LEVEL_SDP))
        packet[8:24] = b"application/foo\x00"
        deleted, text = parse_sap_packet(bytes(packet))
        assert deleted is False
        assert text is None

    def test_rfc_packet_without_mime(self):
        packet = build_sap_packet(SESSION_LEVEL_SDP, with_mime=False)
        deleted, text = parse_sap_packet(packet)
        assert deleted is False
        assert text is not None
        stream = parse_sdp(text)
        assert stream.name == "Studio Mix"

    def test_rfc_deletion_without_mime(self):
        packet = build_sap_packet(SESSION_LEVEL_SDP, deleted=True, with_mime=False)
        deleted, text = parse_sap_packet(packet)
        assert deleted is True
        assert text is not None

    def test_too_short(self):
        deleted, text = parse_sap_packet(b"\x20" * 20)
        assert deleted is False
        assert text is None


class TestSapDiscovery:
    def test_announcement_and_deletion(self):
        discovery = SapDiscovery(timeout_s=300)
        discovery._handle_packet(build_sap_packet(SESSION_LEVEL_SDP))
        streams = discovery.streams()
        assert len(streams) == 1
        stream_id = streams[0].stream_id

        discovery._handle_packet(build_sap_packet(SESSION_LEVEL_SDP, deleted=True))
        assert discovery.streams() == []
        assert stream_id

    def test_rfc_packet_is_discovered(self):
        discovery = SapDiscovery(timeout_s=300)
        discovery._handle_packet(build_sap_packet(SESSION_LEVEL_SDP, with_mime=False))
        streams = discovery.streams()
        assert len(streams) == 1
        assert streams[0].name == "Studio Mix"

    def test_manual_not_overwritten_by_sap(self):
        discovery = SapDiscovery(timeout_s=300)
        manual = discovery.add_manual_sdp(SESSION_LEVEL_SDP)
        assert manual.manual is True

        updated = SESSION_LEVEL_SDP.replace("s=Studio Mix", "s=SAP Overwrite")
        discovery._handle_packet(build_sap_packet(updated))
        streams = discovery.streams()
        assert len(streams) == 1
        assert streams[0].name == "Studio Mix"
        assert streams[0].manual is True

    def test_expiry_drops_sap_keeps_manual(self):
        discovery = SapDiscovery(timeout_s=0.01)
        discovery.add_manual_sdp(SESSION_LEVEL_SDP)
        discovery._handle_packet(build_sap_packet(MEDIA_LEVEL_SDP))
        time.sleep(0.03)
        names = {stream.name for stream in discovery.streams()}
        assert "Studio Mix" in names
        assert "Mic 1" not in names

    def test_on_change_fires_for_new_and_deleted_streams(self):
        discovery = SapDiscovery(timeout_s=300)
        events = []
        discovery.set_on_change(lambda: events.append(len(discovery.streams())))

        discovery._handle_packet(build_sap_packet(SESSION_LEVEL_SDP))
        discovery._handle_packet(build_sap_packet(SESSION_LEVEL_SDP))
        discovery._handle_packet(build_sap_packet(SESSION_LEVEL_SDP, deleted=True))

        assert events == [1, 0]
