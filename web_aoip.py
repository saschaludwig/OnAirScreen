#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# web_aoip.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""Web UI AoIP discovery: Livewire ads and AES67 SAP for the settings overlay."""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from defaults import (
    DEFAULT_AUDIO_AES67_ADDR,
    DEFAULT_AUDIO_AES67_CHANNELS,
    DEFAULT_AUDIO_AES67_CODEC,
    DEFAULT_AUDIO_AES67_ID,
    DEFAULT_AUDIO_AES67_MANUAL,
    DEFAULT_AUDIO_AES67_NAME,
    DEFAULT_AUDIO_AES67_PORT,
    DEFAULT_AUDIO_AES67_RATE,
    DEFAULT_AUDIO_LIVEWIRE_CHANNEL,
)

logger = logging.getLogger("OnAirScreen")

AES67_NONE_LABEL = "None"
AES67_NONE_VALUE = ""
IDLE_TIMEOUT_S = 8.0
LIVEWIRE_CHANNEL_MIN = 1
LIVEWIRE_CHANNEL_MAX = 32767

_session_lock = threading.Lock()
_session: Optional["WebAoipSession"] = None


def empty_aes67_snapshot() -> dict[str, Any]:
    """Empty AES67 selection (None in the combo)."""
    return {
        "id": DEFAULT_AUDIO_AES67_ID,
        "name": DEFAULT_AUDIO_AES67_NAME,
        "addr": DEFAULT_AUDIO_AES67_ADDR,
        "port": DEFAULT_AUDIO_AES67_PORT,
        "codec": DEFAULT_AUDIO_AES67_CODEC,
        "rate": DEFAULT_AUDIO_AES67_RATE,
        "channels": DEFAULT_AUDIO_AES67_CHANNELS,
        "dante": False,
        "manual": DEFAULT_AUDIO_AES67_MANUAL,
    }


def normalize_aes67_snapshot(raw: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Coerce a form/query snapshot into the persistable AES67 dict."""
    snapshot = empty_aes67_snapshot()
    if not isinstance(raw, dict):
        return snapshot
    snapshot["id"] = str(raw.get("id") or "").strip()
    snapshot["name"] = str(raw.get("name") or "").strip()
    snapshot["addr"] = str(raw.get("addr") or "").strip()
    try:
        port = int(raw.get("port") or DEFAULT_AUDIO_AES67_PORT)
    except (TypeError, ValueError):
        port = DEFAULT_AUDIO_AES67_PORT
    snapshot["port"] = port if 1 <= port <= 65535 else DEFAULT_AUDIO_AES67_PORT
    codec = str(raw.get("codec") or DEFAULT_AUDIO_AES67_CODEC).strip().upper()
    snapshot["codec"] = codec if codec in ("L16", "L24") else DEFAULT_AUDIO_AES67_CODEC
    try:
        rate = int(raw.get("rate") or DEFAULT_AUDIO_AES67_RATE)
    except (TypeError, ValueError):
        rate = DEFAULT_AUDIO_AES67_RATE
    snapshot["rate"] = rate if rate in (44100, 48000, 96000) else DEFAULT_AUDIO_AES67_RATE
    try:
        channels = int(raw.get("channels") or DEFAULT_AUDIO_AES67_CHANNELS)
    except (TypeError, ValueError):
        channels = DEFAULT_AUDIO_AES67_CHANNELS
    snapshot["channels"] = channels if 1 <= channels <= 64 else DEFAULT_AUDIO_AES67_CHANNELS
    snapshot["dante"] = _coerce_bool(raw.get("dante", False))
    snapshot["manual"] = _coerce_bool(raw.get("manual", False))
    return snapshot


def snapshot_from_audio_config(audio: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Build an AES67 snapshot from Audio group keys."""
    audio = audio or {}
    return normalize_aes67_snapshot({
        "id": audio.get("aes67_id") or audio.get("id"),
        "name": audio.get("aes67_name") or audio.get("name"),
        "addr": audio.get("aes67_addr") or audio.get("addr"),
        "port": audio.get("aes67_port") or audio.get("port"),
        "codec": audio.get("aes67_codec") or audio.get("codec"),
        "rate": audio.get("aes67_rate") or audio.get("rate"),
        "channels": audio.get("aes67_channels") or audio.get("channels"),
        "manual": audio.get("aes67_manual") if "aes67_manual" in audio else audio.get("manual"),
        "dante": audio.get("dante", False),
    })


def clamp_livewire_channel(value: Any) -> int:
    """Return a valid Livewire channel number."""
    try:
        channel = int(value)
    except (TypeError, ValueError):
        channel = DEFAULT_AUDIO_LIVEWIRE_CHANNEL
    return max(LIVEWIRE_CHANNEL_MIN, min(LIVEWIRE_CHANNEL_MAX, channel))


def livewire_stream_entries(discovered: list[Any], channel: int) -> list[dict[str, Any]]:
    """Combo entries: advertised sources plus the current channel if missing."""
    from livewire_adv import format_livewire_source_label

    name_counts: dict[str, int] = {}
    for source in discovered:
        key = (source.name or "").strip().lower()
        if key:
            name_counts[key] = name_counts.get(key, 0) + 1

    items: list[dict[str, Any]] = []
    seen: set[int] = set()
    for source in discovered:
        key = (source.name or "").strip().lower()
        include_node = bool(key) and name_counts.get(key, 0) > 1
        items.append({
            "value": int(source.channel),
            "label": source.label(include_node=include_node),
        })
        seen.add(int(source.channel))
    if channel not in seen:
        items.insert(0, {
            "value": channel,
            "label": format_livewire_source_label("", channel),
        })
    return items


def aes67_stream_entries(
    discovered: list[Any],
    saved: dict[str, Any],
    selected_id: Optional[str],
    seen_sap_ids: set[str],
) -> list[dict[str, Any]]:
    """Combo entries: None, SAP streams, and the saved stream when it should stay."""
    from sap_sdp import snapshot_label

    chose_none = selected_id is not None and selected_id == AES67_NONE_VALUE
    by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    for stream in discovered:
        data = stream.snapshot()
        stream_id = str(data.get("id") or "")
        if not stream_id:
            continue
        by_id[stream_id] = (stream.label(), data)
        seen_sap_ids.add(stream_id)

    saved = normalize_aes67_snapshot(saved)
    saved_id = saved.get("id") or ""
    if saved.get("addr") and saved_id and saved_id not in by_id:
        vanished = (not saved.get("manual")) and saved_id in seen_sap_ids
        if saved.get("manual") or (not chose_none and not vanished):
            by_id[saved_id] = (snapshot_label(saved), saved)

    entries = [{
        "value": AES67_NONE_VALUE,
        "label": AES67_NONE_LABEL,
        "snapshot": None,
    }]
    for stream_id, (label, data) in by_id.items():
        entries.append({
            "value": stream_id,
            "label": label,
            "snapshot": data,
        })
    return entries


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in ("1", "true", "yes", "on")


class WebAoipSession:
    """Web-owned SAP / Livewire listeners with an idle timeout."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sap = None
        self._lw = None
        self._seen_sap_ids: set[str] = set()
        self._idle_timer: Optional[threading.Timer] = None

    def list_streams(
        self,
        source: str,
        iface: str = "",
        channel: int = DEFAULT_AUDIO_LIVEWIRE_CHANNEL,
        selected_id: Optional[str] = None,
        saved: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Start the matching discovery listener and return combo entries."""
        source = (source or "").strip().lower()
        iface = (iface or "").strip()
        if source == "livewire":
            discovery = self._ensure_livewire(iface)
            discovered = list(discovery.streams()) if discovery is not None else []
            running = bool(discovery is not None and discovery.is_running)
            self._touch()
            return {
                "source": "livewire",
                "running": running,
                "streams": livewire_stream_entries(discovered, clamp_livewire_channel(channel)),
            }
        if source == "aes67":
            discovery = self._ensure_sap(iface)
            discovered = list(discovery.streams()) if discovery is not None else []
            running = bool(discovery is not None and discovery.is_running)
            with self._lock:
                seen = self._seen_sap_ids
            self._touch()
            return {
                "source": "aes67",
                "running": running,
                "streams": aes67_stream_entries(
                    discovered, saved or empty_aes67_snapshot(), selected_id, seen
                ),
            }
        from web_settings import SettingsApiError

        raise SettingsApiError("AoIP source must be livewire or aes67", 400)

    def paste_sdp(self, raw_sdp: str, iface: str = "") -> dict[str, Any]:
        """Parse pasted SDP, keep it in the web SAP session, and return the list."""
        from sap_sdp import SdpError
        from web_settings import SettingsApiError

        text = (raw_sdp or "").strip()
        if not text:
            raise SettingsApiError("SDP text is empty", 400)
        discovery = self._ensure_sap((iface or "").strip())
        if discovery is None:
            raise SettingsApiError("AES67 discovery is not available", 500)
        try:
            stream = discovery.add_manual_sdp(text)
        except SdpError as exc:
            raise SettingsApiError(str(exc), 400) from exc
        snapshot = stream.snapshot()
        listed = self.list_streams(
            source="aes67",
            iface=iface,
            selected_id=stream.stream_id,
            saved=snapshot,
        )
        listed["stream"] = snapshot
        return listed

    def stop(self) -> dict[str, Any]:
        """Leave multicast groups and cancel the idle timer."""
        self._cancel_idle_timer()
        self._stop_sap()
        self._stop_livewire()
        return {"status": "ok", "running": False}

    def _ensure_sap(self, iface: str):
        self._stop_livewire()
        from sap_sdp import SapDiscovery

        with self._lock:
            already = (
                self._sap is not None
                and self._sap.is_running
                and self._sap.iface == iface
            )
            if already:
                return self._sap
            if self._sap is None:
                self._sap = SapDiscovery(iface=iface)
            discovery = self._sap
            self._seen_sap_ids = set()
        discovery.start(iface=iface)
        return discovery

    def _ensure_livewire(self, iface: str):
        self._stop_sap()
        from livewire_adv import LivewireDiscovery

        with self._lock:
            already = (
                self._lw is not None
                and self._lw.is_running
                and self._lw.iface == iface
            )
            if already:
                return self._lw
            if self._lw is None:
                self._lw = LivewireDiscovery(iface=iface)
            discovery = self._lw
        discovery.start(iface=iface)
        return discovery

    def _stop_sap(self) -> None:
        with self._lock:
            discovery = self._sap
            self._sap = None
            self._seen_sap_ids = set()
        if discovery is not None:
            discovery.set_on_change(None)
            discovery.stop()

    def _stop_livewire(self) -> None:
        with self._lock:
            discovery = self._lw
            self._lw = None
        if discovery is not None:
            discovery.set_on_change(None)
            discovery.stop()

    def _touch(self) -> None:
        self._cancel_idle_timer()
        timer = threading.Timer(IDLE_TIMEOUT_S, self._idle_stop)
        timer.daemon = True
        timer.start()
        with self._lock:
            self._idle_timer = timer

    def _idle_stop(self) -> None:
        logger.debug("Stopping web AoIP discovery after idle timeout")
        self.stop()

    def _cancel_idle_timer(self) -> None:
        with self._lock:
            timer = self._idle_timer
            self._idle_timer = None
        if timer is not None:
            timer.cancel()


def get_web_aoip_session() -> WebAoipSession:
    """Return the process-wide web discovery session."""
    global _session
    with _session_lock:
        if _session is None:
            _session = WebAoipSession()
        return _session


def reset_web_aoip_session() -> None:
    """Stop listeners and drop the singleton (tests)."""
    global _session
    with _session_lock:
        session = _session
        _session = None
    if session is not None:
        session.stop()


def list_web_aoip_streams(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """API helper: list Livewire or AES67 streams for the overlay."""
    payload = payload or {}
    source = str(payload.get("source") or "")
    iface = str(payload.get("iface") or "")
    channel = clamp_livewire_channel(payload.get("channel", DEFAULT_AUDIO_LIVEWIRE_CHANNEL))
    selected = payload.get("selected")
    selected_id = None if selected is None else str(selected)
    saved = payload.get("saved")
    if not isinstance(saved, dict):
        saved = snapshot_from_audio_config(payload)
    return get_web_aoip_session().list_streams(
        source=source,
        iface=iface,
        channel=channel,
        selected_id=selected_id,
        saved=saved,
    )


def paste_web_aoip_sdp(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """API helper: add a pasted SDP announcement."""
    payload = payload or {}
    return get_web_aoip_session().paste_sdp(
        str(payload.get("sdp") or ""),
        iface=str(payload.get("iface") or ""),
    )


def stop_web_aoip_discovery() -> dict[str, Any]:
    """API helper: stop web-owned SAP/Livewire listeners."""
    return get_web_aoip_session().stop()
