#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# livewire_adv.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Axia Livewire advertisement parser and passive discovery.

Listens on multicast ``239.192.255.3`` UDP **4001** (Advertisement and Source
Allocation Protocol). Packet layout is a 16-byte header followed by TLV
phrases: 4-byte ASCII opcode, 1-byte type, then a typed operand.
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from aoip_rtp import _membership_request
from livewire_address import (
    LivewireAddressError,
    channel_to_multicast,
    multicast_to_channel,
    validate_channel,
)

logger = logging.getLogger("OnAirScreen")

LWADV_MULTICAST = "239.192.255.3"
LWADV_PORT = 4001
LWADV_TIMEOUT_S = 60.0
LWADV_MAGIC = b"\x03\x00\x02\x07"
LWADV_HEADER_LEN = 16

ADVT_FULL = 1
ADVT_SUMMARY = 2


class AdvParseError(ValueError):
    """Livewire advertisement datagram is truncated or malformed."""


@dataclass
class LivewireAdvertisedSource:
    """Standard Livewire audio source from an advertisement."""

    channel: int
    name: str
    multicast: str
    node_ip: str = ""
    node_name: str = ""
    last_seen: float = 0.0

    def label(self, include_node: bool = False) -> str:
        """Human-readable combo label."""
        return format_livewire_source_label(
            self.name, self.channel, self.node_name, include_node=include_node
        )


@dataclass
class ParsedAdvertisement:
    """Decoded advertisement datagram (ADVT 1 = full list, 2 = summary)."""

    advt: int
    node_ip: str
    node_name: str
    sequence: int
    sources: List[LivewireAdvertisedSource] = field(default_factory=list)


def format_livewire_source_label(
    name: str,
    channel: int,
    node_name: str = "",
    include_node: bool = False,
) -> str:
    """Combo label; unnamed sources are ``Channel N``."""
    display = (name or "").strip()
    if not display:
        return f"Channel {channel}"
    if include_node and (node_name or "").strip():
        return f"{display} ({node_name.strip()}) — ch {channel}"
    return f"{display} — ch {channel}"


def livewire_source_list_signature(
    items: Sequence[Tuple[int, str]],
) -> tuple:
    """Stable fingerprint of Livewire combo entries (skip rebuild when unchanged)."""
    return tuple((int(channel), str(label)) for channel, label in items)


def is_standard_livewire_source(channel: int, fsid: str = "") -> Tuple[bool, str]:
    """
    Return (ok, multicast) for a standard stereo Livewire source.

    Backfeed (239.193…) and other non-standard groups are rejected.
    """
    try:
        channel = validate_channel(channel)
    except LivewireAddressError:
        return False, ""
    expected = channel_to_multicast(channel)
    if fsid:
        try:
            mapped = multicast_to_channel(fsid)
        except LivewireAddressError:
            return False, ""
        if mapped != channel:
            return False, ""
        return True, fsid
    return True, expected


def _read_phrase(data: bytes, pos: int) -> Tuple[str, Any, int]:
    """Read one TLV phrase; raise AdvParseError if truncated."""
    if pos + 5 > len(data):
        raise AdvParseError("truncated phrase header")
    opcode_raw = data[pos : pos + 4]
    typ = data[pos + 4]
    pos += 5
    try:
        opcode = opcode_raw.decode("ascii")
    except UnicodeDecodeError:
        opcode = opcode_raw.hex()

    remaining = len(data) - pos
    if typ in (0x00, 0x07):
        if remaining < 1:
            raise AdvParseError("truncated u8 operand")
        value: Any = data[pos]
        pos += 1
    elif typ == 0x01:
        if remaining < 4:
            raise AdvParseError("truncated u32/IPv4 operand")
        payload = data[pos : pos + 4]
        pos += 4
        if opcode in ("PSID", "ADVV", "LPID"):
            value = struct.unpack(">I", payload)[0]
        elif opcode == "TYPE":
            value = payload.decode("ascii", errors="replace")
        else:
            value = ".".join(str(byte) for byte in payload)
    elif typ == 0x03:
        if remaining < 2:
            raise AdvParseError("truncated text length")
        length = struct.unpack(">H", data[pos : pos + 2])[0]
        pos += 2
        if len(data) - pos < length:
            raise AdvParseError("truncated text operand")
        raw = data[pos : pos + length]
        pos += length
        value = raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    elif typ in (0x06, 0x08):
        if remaining < 2:
            raise AdvParseError("truncated u16 operand")
        value = struct.unpack(">H", data[pos : pos + 2])[0]
        pos += 2
    elif typ == 0x09:
        if remaining < 8:
            raise AdvParseError("truncated padding operand")
        value = data[pos : pos + 8]
        pos += 8
    else:
        raise AdvParseError(f"unknown operand type {typ:#x}")
    return opcode, value, pos


def parse_advertisement(packet: bytes) -> Optional[ParsedAdvertisement]:
    """
    Decode a Livewire advertisement datagram.

    Returns None if the header is not a Livewire advertisement.
    """
    if len(packet) < LWADV_HEADER_LEN:
        return None
    if packet[:4] != LWADV_MAGIC:
        return None

    advt = 0
    node_ip = ""
    node_name = ""
    sequence = 0
    current: Dict[str, Any] = {}
    raw_sources: List[Dict[str, Any]] = []

    def flush_source() -> None:
        if current.get("psid") is not None:
            raw_sources.append(dict(current))
        current.clear()

    pos = LWADV_HEADER_LEN
    try:
        while pos < len(packet):
            opcode, value, pos = _read_phrase(packet, pos)
            if len(opcode) == 4 and opcode[0] == "S" and opcode[1:].isdigit():
                flush_source()
                continue
            if opcode == "ADVT":
                advt = int(value)
            elif opcode == "INIP":
                node_ip = str(value)
            elif opcode == "ATRN":
                node_name = str(value)
            elif opcode == "ADVV":
                sequence = int(value)
            elif opcode == "PSID":
                current["psid"] = int(value)
            elif opcode == "PSNM":
                current["psnm"] = str(value)
            elif opcode == "FSID":
                current["fsid"] = str(value)
    except AdvParseError as exc:
        logger.debug("Ignoring Livewire advertisement: %s", exc)
        return None

    flush_source()
    if advt not in (ADVT_FULL, ADVT_SUMMARY):
        return None

    now = time.time()
    sources: List[LivewireAdvertisedSource] = []
    if advt == ADVT_FULL:
        for item in raw_sources:
            channel = int(item.get("psid") or 0)
            fsid = str(item.get("fsid") or "")
            ok, multicast = is_standard_livewire_source(channel, fsid)
            if not ok:
                continue
            sources.append(
                LivewireAdvertisedSource(
                    channel=channel,
                    name=str(item.get("psnm") or "").strip(),
                    multicast=multicast,
                    node_ip=node_ip,
                    node_name=node_name,
                    last_seen=now,
                )
            )

    return ParsedAdvertisement(
        advt=advt,
        node_ip=node_ip,
        node_name=node_name,
        sequence=sequence,
        sources=sources,
    )


def _u8_phrase(opcode: bytes, value: int, typ: int = 0x07) -> bytes:
    return opcode + bytes((typ, value & 0xFF))


def _u16_phrase(opcode: bytes, value: int, typ: int = 0x08) -> bytes:
    return opcode + bytes((typ,)) + struct.pack(">H", value & 0xFFFF)


def _u32_phrase(opcode: bytes, value: int) -> bytes:
    return opcode + b"\x01" + struct.pack(">I", value & 0xFFFFFFFF)


def _ip_phrase(opcode: bytes, ip_str: str) -> bytes:
    packed = socket.inet_aton(ip_str)
    return opcode + b"\x01" + packed


def _text_phrase(opcode: bytes, text: str, width: int) -> bytes:
    raw = text.encode("utf-8", errors="replace").split(b"\x00", 1)[0][: width - 1]
    padded = raw + b"\x00" * (width - len(raw))
    return opcode + b"\x03" + struct.pack(">H", width) + padded


def build_adv_packet(
    advt: int,
    node_ip: str,
    node_name: str = "",
    sources: Optional[Sequence[Tuple[int, str, str]]] = None,
    sequence: int = 1,
    msg_counter: int = 0,
) -> bytes:
    """
    Build a minimal advertisement datagram for tests.

    ``sources`` items are ``(channel, name, fsid)``. Empty ``fsid`` uses the
    standard multicast for the channel.
    """
    body = b""
    body += _u8_phrase(b"NEST", 4, typ=0x00)
    body += _u16_phrase(b"PVER", 2)
    body += _u8_phrase(b"ADVT", advt)
    body += _u16_phrase(b"TERM", 0, typ=0x06)
    body += _u8_phrase(b"INDI", 5, typ=0x00)
    body += _u32_phrase(b"ADVV", sequence)
    body += _ip_phrase(b"INIP", node_ip)
    body += _u16_phrase(b"HWID", 0)
    body += _u16_phrase(b"UDPC", 4000)
    body += _u16_phrase(b"NUMS", len(sources or ()))
    if node_name:
        body += _text_phrase(b"ATRN", node_name, 32)
    if advt == ADVT_FULL:
        for index, (channel, name, fsid) in enumerate(sources or (), start=1):
            multicast = fsid or channel_to_multicast(channel)
            section = b""
            section += _u8_phrase(b"INDI", 3, typ=0x00)
            section += _u32_phrase(b"PSID", channel)
            section += _ip_phrase(b"FSID", multicast)
            section += _text_phrase(b"PSNM", name, 16)
            tag = f"S{index:03d}".encode("ascii")
            body += _u16_phrase(tag, len(section), typ=0x06) + section
    header = LWADV_MAGIC + struct.pack(">I", msg_counter) + (b"\x00" * 8)
    return header + body


class LivewireDiscovery:
    """
    Background Livewire advertisement listener.

    Sources expire after ``timeout_s``. ADVT-1 replaces a node's source list;
    ADVT-2 refreshes ``last_seen`` for that node's known sources.
    """

    def __init__(self, iface: str = "", timeout_s: float = LWADV_TIMEOUT_S):
        self._iface = (iface or "").strip()
        self._timeout_s = float(timeout_s)
        self._sources: Dict[int, LivewireAdvertisedSource] = {}
        self._node_channels: Dict[str, set[int]] = {}
        self._lock = threading.Lock()
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._on_change: Optional[Callable[[], None]] = None

    def set_on_change(self, callback: Optional[Callable[[], None]]) -> None:
        """Optional callback invoked on the listener thread when the set changes."""
        self._on_change = callback

    def _notify_change(self) -> None:
        callback = self._on_change
        if callback is None:
            return
        try:
            callback()
        except Exception:
            logger.debug("Livewire advertisement change callback failed", exc_info=True)

    @property
    def iface(self) -> str:
        return self._iface

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, iface: str = "") -> None:
        """Join the advertisement multicast on ``iface`` (empty = INADDR_ANY)."""
        iface = (iface or "").strip()
        if self.is_running and iface == self._iface:
            return
        self.stop()
        self._iface = iface
        self._stop.clear()
        try:
            sock = self._create_socket()
        except Exception as exc:
            logger.error("Livewire advertisement socket setup failed: %s", exc)
            return
        self._sock = sock
        self._thread = threading.Thread(
            target=self._run, name="LivewireDiscovery", daemon=True
        )
        self._thread.start()
        logger.info(
            "Livewire advertisement discovery started (iface=%s)",
            self._iface or "default",
        )

    def stop(self) -> None:
        """Leave the advertisement multicast and stop the listener thread."""
        self._stop.set()
        sock = self._sock
        self._sock = None
        if sock is not None:
            try:
                mreq = _membership_request(LWADV_MULTICAST, self._iface)
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

    def streams(self) -> List[LivewireAdvertisedSource]:
        """Return current standard sources, dropping expired entries."""
        now = time.time()
        with self._lock:
            expired = [
                channel
                for channel, source in self._sources.items()
                if (now - source.last_seen) > self._timeout_s
            ]
            for channel in expired:
                source = self._sources.pop(channel)
                node_set = self._node_channels.get(source.node_ip)
                if node_set is not None:
                    node_set.discard(channel)
                    if not node_set:
                        self._node_channels.pop(source.node_ip, None)
            return sorted(self._sources.values(), key=lambda item: item.channel)

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        sock.bind(("", LWADV_PORT))
        sock.settimeout(0.25)
        mreq = _membership_request(LWADV_MULTICAST, self._iface)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock

    def _run(self) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            while not self._stop.is_set():
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop.is_set():
                        break
                    raise
                sender_ip = addr[0] if addr else ""
                self._handle_packet(data, sender_ip=sender_ip)
        except Exception as exc:
            if not self._stop.is_set():
                logger.error("Livewire advertisement receive error: %s", exc)

    def _handle_packet(self, packet: bytes, sender_ip: str = "") -> None:
        parsed = parse_advertisement(packet)
        if parsed is None:
            return
        node_ip = parsed.node_ip or sender_ip
        if not node_ip:
            return
        changed = False
        now = time.time()
        with self._lock:
            if parsed.advt == ADVT_FULL:
                previous = set(self._node_channels.get(node_ip, set()))
                incoming = {source.channel: source for source in parsed.sources}
                for channel in previous - set(incoming):
                    existing = self._sources.get(channel)
                    if existing is not None and existing.node_ip == node_ip:
                        del self._sources[channel]
                        changed = True
                for channel, source in incoming.items():
                    source.node_ip = node_ip
                    source.node_name = parsed.node_name or source.node_name
                    source.last_seen = now
                    old = self._sources.get(channel)
                    if (
                        old is None
                        or old.name != source.name
                        or old.node_ip != source.node_ip
                        or old.multicast != source.multicast
                    ):
                        changed = True
                    self._sources[channel] = source
                self._node_channels[node_ip] = set(incoming)
            elif parsed.advt == ADVT_SUMMARY:
                channels = self._node_channels.get(node_ip)
                if not channels:
                    return
                for channel in channels:
                    source = self._sources.get(channel)
                    if source is not None:
                        source.last_seen = now
        if changed:
            self._notify_change()
