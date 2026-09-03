#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for livewire_adv.py (parse / discovery, no network).
"""

import time

from livewire_address import channel_to_multicast
from livewire_adv import (
    ADVT_FULL,
    ADVT_SUMMARY,
    LivewireDiscovery,
    build_adv_packet,
    format_livewire_source_label,
    is_standard_livewire_source,
    livewire_source_list_signature,
    parse_advertisement,
)


def _fsid(channel: int) -> str:
    return channel_to_multicast(channel)


class TestFormatLabel:
    def test_named_source(self):
        assert format_livewire_source_label("PGM1", 6031) == "PGM1 — ch 6031"

    def test_unnamed_is_channel_n(self):
        assert format_livewire_source_label("", 27) == "Channel 27"

    def test_duplicate_includes_node(self):
        label = format_livewire_source_label("PGM1", 6031, "StA-Node1", include_node=True)
        assert label == "PGM1 (StA-Node1) — ch 6031"


class TestStandardSource:
    def test_accepts_standard_fsid(self):
        ok, multicast = is_standard_livewire_source(27, "239.192.0.27")
        assert ok is True
        assert multicast == "239.192.0.27"

    def test_derives_multicast_without_fsid(self):
        ok, multicast = is_standard_livewire_source(1212, "")
        assert ok is True
        assert multicast == "239.192.4.188"

    def test_rejects_backfeed(self):
        ok, multicast = is_standard_livewire_source(27, "239.193.0.27")
        assert ok is False
        assert multicast == ""

    def test_rejects_mismatched_fsid(self):
        ok, _ = is_standard_livewire_source(27, "239.192.0.99")
        assert ok is False


class TestParseAdvertisement:
    def test_type1_extracts_channel_name_and_node(self):
        packet = build_adv_packet(
            ADVT_FULL,
            node_ip="10.1.245.60",
            node_name="StA-Node1",
            sources=[(6031, "PGM1", _fsid(6031))],
        )
        parsed = parse_advertisement(packet)
        assert parsed is not None
        assert parsed.advt == ADVT_FULL
        assert parsed.node_ip == "10.1.245.60"
        assert parsed.node_name == "StA-Node1"
        assert len(parsed.sources) == 1
        source = parsed.sources[0]
        assert source.channel == 6031
        assert source.name == "PGM1"
        assert source.multicast == "239.192.23.143"

    def test_type1_skips_backfeed_fsid(self):
        packet = build_adv_packet(
            ADVT_FULL,
            node_ip="10.1.245.60",
            sources=[(27, "Mic", "239.193.0.27"), (28, "PGM", _fsid(28))],
        )
        parsed = parse_advertisement(packet)
        assert parsed is not None
        channels = [source.channel for source in parsed.sources]
        assert channels == [28]

    def test_type2_has_no_sources(self):
        packet = build_adv_packet(
            ADVT_SUMMARY,
            node_ip="10.1.245.60",
            node_name="StA-Node1",
            sequence=34,
        )
        parsed = parse_advertisement(packet)
        assert parsed is not None
        assert parsed.advt == ADVT_SUMMARY
        assert parsed.sequence == 34
        assert parsed.sources == []

    def test_rejects_bad_magic(self):
        packet = build_adv_packet(ADVT_FULL, "10.0.0.1", sources=[(1, "A", "")])
        assert parse_advertisement(b"\x00" + packet[1:]) is None

    def test_rejects_truncated(self):
        assert parse_advertisement(b"\x03\x00\x02\x07") is None


class TestLivewireDiscovery:
    def test_type1_adds_source(self):
        discovery = LivewireDiscovery(timeout_s=60)
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                "Node",
                sources=[(27, "Mic 1", _fsid(27))],
            )
        )
        streams = discovery.streams()
        assert len(streams) == 1
        assert streams[0].channel == 27
        assert streams[0].name == "Mic 1"

    def test_type1_replaces_node_sources(self):
        discovery = LivewireDiscovery(timeout_s=60)
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                sources=[(27, "Old", _fsid(27)), (28, "Keep", _fsid(28))],
            )
        )
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                sources=[(28, "Keep", _fsid(28))],
            )
        )
        channels = [source.channel for source in discovery.streams()]
        assert channels == [28]

    def test_type2_keepalive_prevents_expiry(self):
        discovery = LivewireDiscovery(timeout_s=0.05)
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                sources=[(27, "Mic", _fsid(27))],
            )
        )
        time.sleep(0.03)
        discovery._handle_packet(build_adv_packet(ADVT_SUMMARY, "10.1.245.60"))
        time.sleep(0.03)
        assert [source.channel for source in discovery.streams()] == [27]

    def test_expiry_drops_silent_node(self):
        discovery = LivewireDiscovery(timeout_s=0.02)
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                sources=[(27, "Mic", _fsid(27))],
            )
        )
        time.sleep(0.04)
        assert discovery.streams() == []

    def test_on_change_fires_for_new_source(self):
        discovery = LivewireDiscovery(timeout_s=60)
        events = []
        discovery.set_on_change(lambda: events.append(len(discovery.streams())))
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                sources=[(27, "Mic", _fsid(27))],
            )
        )
        discovery._handle_packet(
            build_adv_packet(
                ADVT_FULL,
                "10.1.245.60",
                sources=[(27, "Mic", _fsid(27))],
            )
        )
        assert events == [1]


class TestSignature:
    def test_same_items_same_signature(self):
        items = [(27, "Mic — ch 27")]
        assert livewire_source_list_signature(items) == livewire_source_list_signature(list(items))

    def test_new_channel_changes_signature(self):
        first = [(27, "Mic — ch 27")]
        second = first + [(28, "PGM — ch 28")]
        assert livewire_source_list_signature(first) != livewire_source_list_signature(second)
