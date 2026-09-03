#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# sap_sdp.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
AES67 SAP/SDP helpers (RFC 2974 + RFC 4566) for stream discovery.

Listens on AES67/Dante ``239.255.255.255`` and RFC 2974 ``224.2.127.254``
(UDP 9875). Payload is SDP, optionally preceded by ``application/sdp\\0``.
"""

from __future__ import annotations

import hashlib
import logging
import re
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from aoip_rtp import CODEC_L16, CODEC_L24, MAX_STREAM_CHANNELS, _membership_request

logger = logging.getLogger("OnAirScreen")

SAP_PORT = 9875
SAP_MULTICAST = "239.255.255.255"  # AES67 / Dante
SAP_MULTICAST_RFC = "224.2.127.254"  # RFC 2974 session directory
SAP_GROUPS = (SAP_MULTICAST, SAP_MULTICAST_RFC)
SAP_MIME = b"application/sdp"
SAP_HEADER_LEN = 8
SAP_BODY_OFFSET = 24  # IPv4 header + "application/sdp\0"
SAP_DELETION_BIT = 0x04  # T bit: deletion vs announcement
SAP_ADDRESS_IPV6 = 0x10  # A bit
SAP_ENCRYPTED = 0x02  # E bit
SAP_COMPRESSED = 0x01  # C bit
SDP_DELETE_TIMEOUT_S = 300.0
SUPPORTED_RATES = (44100, 48000, 96000)

_RTPMAP_RE = re.compile(
    r"^a=rtpmap:\d+\s+(L16|L24)/(\d+)/(\d+)\s*$",
    re.IGNORECASE,
)
_CONNECTION_RE = re.compile(
    r"^c=IN\s+IP4\s+([0-9.]+)(?:/\d+)?",
    re.IGNORECASE,
)
_MEDIA_RE = re.compile(
    r"^m=audio\s+(\d+)\s+RTP/AVP\s+",
    re.IGNORECASE,
)


class SdpError(ValueError):
    """SDP is missing required AES67 fields or uses an unsupported format."""


@dataclass
class Aes67Stream:
    """Discovered or manually added AES67 stream."""

    stream_id: str
    name: str
    multicast: str
    port: int
    codec: str
    sample_rate: int
    channels: int
    origin: str
    raw_sdp: str
    dante: bool = False
    manual: bool = False
    last_seen: float = 0.0

    def label(self) -> str:
        """Human-readable combo label."""
        return format_stream_label(
            name=self.name,
            codec=self.codec,
            sample_rate=self.sample_rate,
            channels=self.channels,
            multicast=self.multicast,
            port=self.port,
            dante=self.dante,
            manual=self.manual,
        )

    def snapshot(self) -> dict:
        """Persistable combo userData (id, name, addr, port, codec, rate, channels)."""
        return {
            "id": self.stream_id,
            "name": self.name,
            "addr": self.multicast,
            "port": self.port,
            "codec": self.codec,
            "rate": self.sample_rate,
            "channels": self.channels,
            "dante": self.dante,
            "manual": self.manual,
        }


def origin_hash(origin_line: str) -> str:
    """Stable stream id from the SDP origin line (Dante may reuse multicast)."""
    return hashlib.md5(origin_line.strip().encode("utf-8")).hexdigest()


def format_stream_label(
    name: str,
    codec: str,
    sample_rate: int,
    channels: int,
    multicast: str,
    port: int,
    dante: bool = False,
    manual: bool = False,
) -> str:
    """Combo label; pasted SDP and Dante are visible suffixes only."""
    extras: List[str] = []
    if dante:
        extras.append("Dante")
    if manual:
        extras.append("pasted SDP")
    extra = f" {', '.join(extras)}" if extras else ""
    display = name or f"{multicast}:{port}"
    return f"{display} ({codec}/{sample_rate}/{channels} {multicast}:{port}{extra})"


def snapshot_label(snapshot: dict) -> str:
    """Build a combo label from a persisted stream snapshot."""
    return format_stream_label(
        name=str(snapshot.get("name") or ""),
        codec=str(snapshot.get("codec") or CODEC_L24),
        sample_rate=int(snapshot.get("rate") or 48000),
        channels=int(snapshot.get("channels") or 2),
        multicast=str(snapshot.get("addr") or ""),
        port=int(snapshot.get("port") or 0),
        dante=bool(snapshot.get("dante")),
        manual=bool(snapshot.get("manual")),
    )


def parse_sdp(raw_sdp: str, manual: bool = False, last_seen: Optional[float] = None) -> Aes67Stream:
    """
    Parse an AES67-ish SDP body into an Aes67Stream.

    Requires one audio RTP/AVP media line with a single L16/L24 rtpmap.
    """
    text = (raw_sdp or "").replace("\r\n", "\n").strip()
    if not text:
        raise SdpError("Empty SDP")

    session_conn = ""
    media_conn = ""
    in_media = False
    origin = ""
    name = ""
    port: Optional[int] = None
    codec = ""
    rate = 0
    channels = 0
    rtpmap_count = 0
    dante = False
    media_audio = False

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("o="):
            origin = line[2:].strip()
        elif line.startswith("s="):
            name = line[2:].strip() or name
        elif line.lower().startswith("a=keywords:") and "dante" in line.lower():
            dante = True
        elif line.startswith("m="):
            in_media = True
            match = _MEDIA_RE.match(line)
            if match is None:
                raise SdpError("Unsupported media type")
            media_audio = True
            port = int(match.group(1))
        elif line.startswith("c="):
            match = _CONNECTION_RE.match(line)
            if match is None:
                continue
            if in_media:
                media_conn = match.group(1)
            else:
                session_conn = match.group(1)
        elif line.startswith("a=rtpmap:"):
            match = _RTPMAP_RE.match(line)
            if match is None:
                raise SdpError("Unsupported rtpmap")
            rtpmap_count += 1
            codec = match.group(1).upper()
            rate = int(match.group(2))
            channels = int(match.group(3))

    if not origin:
        raise SdpError("Missing SDP origin")
    if not media_audio or port is None:
        raise SdpError("Unsupported media type")
    if rtpmap_count != 1:
        raise SdpError("Unsupported rtpmap")
    if codec not in (CODEC_L16, CODEC_L24):
        raise SdpError("Unsupported codec")
    if rate not in SUPPORTED_RATES:
        raise SdpError("Unsupported samplerate")
    if channels < 1 or channels > MAX_STREAM_CHANNELS:
        raise SdpError("Unsupported channel number")

    multicast = media_conn or session_conn
    if not multicast:
        raise SdpError("Missing multicast address")
    if port < 1 or port > 65535:
        raise SdpError(f"Invalid RTP port: {port}")

    display = name if name and name != "-" else f"{multicast}:{port}"
    now = time.time() if last_seen is None else float(last_seen)
    return Aes67Stream(
        stream_id=origin_hash(origin),
        name=display,
        multicast=multicast,
        port=port,
        codec=codec,
        sample_rate=rate,
        channels=channels,
        origin=origin,
        raw_sdp=text,
        dante=dante,
        manual=manual,
        last_seen=now,
    )


def _sap_payload(packet: bytes) -> Optional[bytes]:
    """
    Return the SDP body of a SAP datagram, or None if it is not SDP.

    RFC 2974: IPv4/IPv6 origin, optional auth, optional MIME. AES67/Dante
    typically send ``application/sdp\\0``; RFC tools often omit the MIME
    and start the payload at ``v=``.
    """
    if len(packet) < SAP_HEADER_LEN:
        return None
    flags = packet[0]
    if ((flags >> 5) & 0x07) != 1:
        return None
    if flags & (SAP_ENCRYPTED | SAP_COMPRESSED):
        return None
    origin_len = 16 if (flags & SAP_ADDRESS_IPV6) else 4
    offset = 4 + origin_len + packet[1] * 4
    if offset >= len(packet):
        return None
    payload = packet[offset:]
    mime = SAP_MIME + b"\x00"
    if payload.startswith(mime):
        return payload[len(mime) :]
    if payload.startswith(b"v="):
        return payload
    return None


def parse_sap_packet(packet: bytes) -> Tuple[bool, Optional[str]]:
    """
    Extract (is_deletion, sdp_text) from a SAP UDP datagram.

    Returns (False, None) if the packet is not an SDP announcement.
    """
    body = _sap_payload(packet)
    if body is None:
        return False, None
    deleted = bool(packet[0] & SAP_DELETION_BIT)
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return False, None
    return deleted, text


def build_sap_packet(
    raw_sdp: str, deleted: bool = False, with_mime: bool = True
) -> bytes:
    """Build a minimal IPv4 SAP announcement (for tests and senders)."""
    header = bytearray(SAP_HEADER_LEN)
    header[0] = 0x20 | (SAP_DELETION_BIT if deleted else 0)
    payload = raw_sdp.encode("utf-8")
    if with_mime:
        return bytes(header) + SAP_MIME + b"\x00" + payload
    return bytes(header) + payload


class SapDiscovery:
    """
    Background SAP listener. Streams expire after ``timeout_s`` unless manual.
    """

    def __init__(self, iface: str = "", timeout_s: float = SDP_DELETE_TIMEOUT_S):
        self._iface = (iface or "").strip()
        self._timeout_s = float(timeout_s)
        self._sessions: Dict[str, Aes67Stream] = {}
        self._lock = threading.Lock()
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._on_change: Optional[Callable[[], None]] = None

    def set_on_change(self, callback: Optional[Callable[[], None]]) -> None:
        """Optional callback invoked on the listener thread when the session set changes."""
        self._on_change = callback

    def _notify_change(self) -> None:
        callback = self._on_change
        if callback is None:
            return
        try:
            callback()
        except Exception:
            logger.debug("SAP change callback failed", exc_info=True)

    @property
    def iface(self) -> str:
        return self._iface

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, iface: str = "") -> None:
        """Join SAP multicast on ``iface`` (empty = INADDR_ANY)."""
        iface = (iface or "").strip()
        if self.is_running and iface == self._iface:
            return
        self.stop()
        self._iface = iface
        self._stop.clear()
        try:
            sock = self._create_socket()
        except Exception as exc:
            logger.error("SAP socket setup failed: %s", exc)
            return
        self._sock = sock
        self._thread = threading.Thread(target=self._run, name="SapDiscovery", daemon=True)
        self._thread.start()
        logger.info(
            "SAP discovery started (iface=%s, groups=%s)",
            self._iface or "default",
            ",".join(SAP_GROUPS),
        )

    def stop(self) -> None:
        """Leave SAP multicast and stop the listener thread."""
        self._stop.set()
        sock = self._sock
        self._sock = None
        if sock is not None:
            for group in SAP_GROUPS:
                try:
                    mreq = _membership_request(group, self._iface)
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                except OSError:
                    pass
            try:
                sock.close()
            except OSError:
                pass
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def streams(self) -> List[Aes67Stream]:
        """Return current streams, dropping expired SAP entries."""
        now = time.time()
        with self._lock:
            expired = [
                key
                for key, stream in self._sessions.items()
                if not stream.manual and (now - stream.last_seen) > self._timeout_s
            ]
            for key in expired:
                del self._sessions[key]
            return sorted(self._sessions.values(), key=lambda item: item.name.lower())

    def add_manual_sdp(self, raw_sdp: str) -> Aes67Stream:
        """Parse and store a manually pasted SDP (not overwritten by SAP)."""
        stream = parse_sdp(raw_sdp, manual=True)
        with self._lock:
            self._sessions[stream.stream_id] = stream
        self._notify_change()
        return stream

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        sock.bind(("", SAP_PORT))
        sock.settimeout(0.25)
        joined = 0
        last_error: Optional[OSError] = None
        for group in SAP_GROUPS:
            try:
                mreq = _membership_request(group, self._iface)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                joined += 1
            except OSError as exc:
                last_error = exc
                logger.warning("SAP join %s failed: %s", group, exc)
        if joined == 0:
            sock.close()
            raise last_error or OSError("SAP multicast join failed")
        return sock

    def _run(self) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            while not self._stop.is_set():
                try:
                    data, _addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop.is_set():
                        break
                    raise
                self._handle_packet(data)
        except Exception as exc:
            if not self._stop.is_set():
                logger.error("SAP receive error: %s", exc)

    def _handle_packet(self, packet: bytes) -> None:
        deleted, text = parse_sap_packet(packet)
        if text is None:
            return
        try:
            stream = parse_sdp(text, manual=False)
        except SdpError as exc:
            logger.debug("Ignoring SAP SDP: %s", exc)
            return
        changed = False
        with self._lock:
            existing = self._sessions.get(stream.stream_id)
            if existing is not None and existing.manual:
                return
            if deleted:
                changed = self._sessions.pop(stream.stream_id, None) is not None
            else:
                changed = existing is None
                self._sessions[stream.stream_id] = stream
        if changed:
            self._notify_change()
