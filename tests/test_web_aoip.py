#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for web AoIP discovery lists (no multicast required)."""

from unittest.mock import Mock

import pytest

from livewire_adv import LivewireAdvertisedSource
from sap_sdp import SapDiscovery, parse_sdp
from web_aoip import (
    AES67_NONE_LABEL,
    WebAoipSession,
    aes67_stream_entries,
    livewire_stream_entries,
    reset_web_aoip_session,
)
from web_settings import SettingsApiError

SESSION_LEVEL_SDP = """\
v=0
o=- 111 1 IN IP4 192.168.1.10
s=Studio Mix
c=IN IP4 239.69.1.1/32
t=0 0
m=audio 5004 RTP/AVP 96
a=rtpmap:96 L24/48000/2
"""


@pytest.fixture(autouse=True)
def _reset_web_aoip():
    yield
    reset_web_aoip_session()


def test_livewire_entries_keep_current_channel():
    discovered = [
        LivewireAdvertisedSource(channel=6031, name="PGM1", multicast="239.192.23.143"),
    ]
    items = livewire_stream_entries(discovered, channel=12)
    values = [item["value"] for item in items]
    assert 12 in values
    assert 6031 in values
    assert items[0]["value"] == 12


def test_aes67_entries_start_with_none_and_keep_saved():
    stream = parse_sdp(SESSION_LEVEL_SDP)
    seen: set[str] = set()
    items = aes67_stream_entries([], stream.snapshot(), stream.stream_id, seen)
    assert items[0]["value"] == ""
    assert items[0]["label"] == AES67_NONE_LABEL
    values = [item["value"] for item in items]
    assert stream.stream_id in values


def test_aes67_vanished_sap_dropped_when_none_selected():
    stream = parse_sdp(SESSION_LEVEL_SDP)
    seen = {stream.stream_id}
    items = aes67_stream_entries([], stream.snapshot(), "", seen)
    values = [item["value"] for item in items]
    assert values == [""]


def test_aes67_pasted_sdp_stays_when_none_selected():
    stream = parse_sdp(SESSION_LEVEL_SDP, manual=True)
    seen = {stream.stream_id}
    items = aes67_stream_entries([], stream.snapshot(), "", seen)
    values = [item["value"] for item in items]
    assert stream.stream_id in values


def test_session_livewire_list_uses_discovery(monkeypatch):
    session = WebAoipSession()
    fake = Mock()
    fake.is_running = True
    fake.streams.return_value = [
        LivewireAdvertisedSource(channel=6031, name="PGM1", multicast="239.192.23.143"),
    ]
    monkeypatch.setattr(session, "_ensure_livewire", lambda iface: fake)
    monkeypatch.setattr(session, "_touch", lambda: None)
    result = session.list_streams("livewire", channel=1)
    assert result["source"] == "livewire"
    assert result["running"] is True
    values = [item["value"] for item in result["streams"]]
    assert 6031 in values
    assert 1 in values


def test_session_rejects_unknown_source(monkeypatch):
    session = WebAoipSession()
    monkeypatch.setattr(session, "_touch", lambda: None)
    with pytest.raises(SettingsApiError, match="livewire or aes67"):
        session.list_streams("device")


def test_session_paste_sdp_and_reject_invalid(monkeypatch):
    session = WebAoipSession()
    sap = SapDiscovery()
    monkeypatch.setattr(session, "_ensure_sap", lambda iface: sap)
    monkeypatch.setattr(session, "_touch", lambda: None)
    listed = session.paste_sdp(SESSION_LEVEL_SDP)
    assert listed["stream"]["name"] == "Studio Mix"
    assert listed["stream"]["manual"] is True
    values = [item["value"] for item in listed["streams"]]
    assert listed["stream"]["id"] in values
    with pytest.raises(SettingsApiError, match="empty"):
        session.paste_sdp("  ")
    with pytest.raises(SettingsApiError):
        session.paste_sdp("not an sdp")
