#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# ptp_client.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Software PTPv2 (IEEE 1588-2008) ordinary-clock slave for OnAirScreen.

Listens on UDP 319/320 multicast 224.0.1.129. Uses software receive timestamps
and a monotonic clock; accuracy is typically milliseconds, not microseconds.
"""

from __future__ import annotations

import logging
import select
import socket
import struct
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

PTP_MULTICAST = "224.0.1.129"
PTP_EVENT_PORT = 319
PTP_GENERAL_PORT = 320
PTP_VERSION = 2
PTP_HEADER_SIZE = 34
PTP_TIMESTAMP_SIZE = 10

MSG_SYNC = 0x0
MSG_DELAY_REQ = 0x1
MSG_FOLLOW_UP = 0x8
MSG_DELAY_RESP = 0x9
MSG_ANNOUNCE = 0xB

# flagField as big-endian uint16 (octet 0 in the high byte).
FLAG_TWO_STEP = 0x0200
FLAG_CURRENT_UTC_OFFSET_VALID = 0x0004
FLAG_PTP_TIMESCALE = 0x0008
DEFAULT_UTC_OFFSET = 37
UNLOCK_TIMEOUT_S = 6.0
DELAY_REQ_INTERVAL_S = 1.0

_HEADER_STRUCT = struct.Struct("!BBHBBHQI8sHHBb")


@dataclass
class PtpHeader:
    """Parsed IEEE 1588-2008 header."""

    message_type: int
    version: int
    message_length: int
    domain: int
    flags: int
    correction_ns: float
    clock_identity: bytes
    port_number: int
    sequence_id: int
    log_message_interval: int

    @property
    def two_step(self) -> bool:
        return bool(self.flags & FLAG_TWO_STEP)

    @property
    def ptp_timescale(self) -> bool:
        """True when timestamps use the PTP epoch (TAI), not ARB/UTC."""
        return bool(self.flags & FLAG_PTP_TIMESCALE)

    @property
    def source_key(self) -> bytes:
        return self.clock_identity + struct.pack("!H", self.port_number)


def parse_header(data: bytes) -> Optional[PtpHeader]:
    """Parse a 34-byte PTPv2 header. Returns None if the buffer is too short."""
    if len(data) < PTP_HEADER_SIZE:
        return None
    (
        b0,
        b1,
        length,
        domain,
        _reserved1,
        flags,
        correction,
        _reserved2,
        clock_id,
        port,
        seq,
        _control,
        log_interval,
    ) = _HEADER_STRUCT.unpack(data[:PTP_HEADER_SIZE])
    version = b1 & 0x0F
    if version != PTP_VERSION:
        return None
    return PtpHeader(
        message_type=b0 & 0x0F,
        version=version,
        message_length=length,
        domain=domain,
        flags=flags,
        correction_ns=correction / 65536.0,
        clock_identity=clock_id,
        port_number=port,
        sequence_id=seq,
        log_message_interval=log_interval,
    )


def parse_timestamp(data: bytes, offset: int = PTP_HEADER_SIZE) -> Optional[Tuple[int, int]]:
    """Return (seconds, nanoseconds) from a PTP timestamp field."""
    if len(data) < offset + PTP_TIMESTAMP_SIZE:
        return None
    seconds = int.from_bytes(data[offset:offset + 6], "big")
    nanos = struct.unpack("!I", data[offset + 6:offset + 10])[0]
    return seconds, nanos


def effective_utc_offset(ptp_timescale: bool, utc_offset: int) -> int:
    """
    Seconds to subtract from a PTP timestamp to get POSIX UTC.

    IEEE 1588-2008: currentUtcOffset (TAI − UTC) is meaningful only when the
    PTP timescale flag is set. Software ptp4l grandmasters announce ARB
    timescale and put CLOCK_REALTIME (UTC) in the timestamps; subtracting 37
    there makes the clock run slow by the leap-second offset.
    """
    if not ptp_timescale:
        return 0
    return int(utc_offset)


def ptp_timestamp_to_unix(seconds: int, nanos: int, utc_offset: int) -> float:
    """Convert PTP seconds+ns to POSIX UTC seconds using TAI−UTC when needed."""
    return float(seconds) - float(utc_offset) + nanos / 1_000_000_000.0


def unix_to_local_datetime(unix: float) -> datetime:
    """POSIX timestamp to naive local datetime."""
    return datetime.fromtimestamp(unix)


def parse_announce_utc_offset(data: bytes) -> Optional[int]:
    """currentUtcOffset from an Announce message (int16 after originTimestamp)."""
    offset = PTP_HEADER_SIZE + PTP_TIMESTAMP_SIZE
    if len(data) < offset + 2:
        return None
    value = struct.unpack("!h", data[offset:offset + 2])[0]
    if value < 0 or value > 64:
        return None
    return value


def parse_announce_quality(data: bytes) -> Tuple[int, int, int, bytes]:
    """
    Return (priority1, clockClass, priority2, grandmasterIdentity) from Announce.

    Missing fields yield worst-case values so incomplete packets lose BMCA.
    """
    base = PTP_HEADER_SIZE + PTP_TIMESTAMP_SIZE
    if len(data) < base + 20:
        return 255, 255, 255, b"\xff" * 8
    priority1 = data[base + 3]
    clock_class = data[base + 4]
    priority2 = data[base + 8]
    gm_identity = data[base + 9:base + 17]
    return priority1, clock_class, priority2, gm_identity


def clock_identity_from_mac(mac: bytes) -> bytes:
    """Build an 8-byte clock identity from a 6-byte MAC (EUI-64)."""
    if len(mac) >= 8:
        return mac[:8]
    if len(mac) == 6:
        return mac[:3] + b"\xff\xfe" + mac[3:]
    return (mac + b"\x00" * 8)[:8]


def build_delay_req(
    clock_identity: bytes,
    sequence_id: int,
    domain: int,
) -> bytes:
    """Build a Delay_Req event message with a zero origin timestamp."""
    b0 = MSG_DELAY_REQ
    b1 = PTP_VERSION
    length = PTP_HEADER_SIZE + PTP_TIMESTAMP_SIZE
    flags = 0
    correction = 0
    reserved2 = 0
    port = 1
    control = 1  # Delay_Req
    log_interval = 0x7F
    header = _HEADER_STRUCT.pack(
        b0,
        b1,
        length,
        domain,
        0,
        flags,
        correction,
        reserved2,
        clock_identity[:8],
        port,
        sequence_id & 0xFFFF,
        control,
        log_interval,
    )
    timestamp = b"\x00" * PTP_TIMESTAMP_SIZE
    return header + timestamp


def _membership_request(group_ip: str, iface_ip: str) -> bytes:
    group = socket.inet_aton(group_ip)
    if iface_ip:
        return group + socket.inet_aton(iface_ip)
    return group + struct.pack("=I", socket.INADDR_ANY)


def _create_multicast_socket(port: int, iface_ip: str) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass
    sock.bind(("", port))
    sock.setblocking(False)
    if iface_ip:
        try:
            sock.setsockopt(
                socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface_ip)
            )
        except OSError as exc:
            logger.debug("IP_MULTICAST_IF failed: %s", exc)
    mreq = _membership_request(PTP_MULTICAST, iface_ip)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return sock


def _leave_group(sock: socket.socket, iface_ip: str) -> None:
    try:
        mreq = _membership_request(PTP_MULTICAST, iface_ip)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
    except OSError:
        pass


def _interface_mac(iface_ip: str) -> bytes:
    """Best-effort MAC for the interface that owns iface_ip."""
    try:
        from PySide6.QtNetwork import QAbstractSocket, QNetworkInterface

        for iface in QNetworkInterface.allInterfaces():
            for entry in iface.addressEntries():
                addr = entry.ip()
                if addr.protocol() != QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                    continue
                if addr.toString() != iface_ip:
                    continue
                hw = bytes(iface.hardwareAddress().replace(":", "").replace("-", "")[:12], "ascii")
                try:
                    return bytes.fromhex(hw.decode("ascii"))
                except ValueError:
                    break
    except Exception as exc:
        logger.debug("MAC lookup failed: %s", exc)
    return b"\x02\x00\x00\x00\x00\x01"


class PtpV2Slave(QObject):
    """
    Background PTPv2 slave. Emits local datetime samples independent of the OS clock.
    """

    sample_ready = Signal(object, float)
    lock_changed = Signal(bool, str)

    def __init__(self, iface: str = "", domain: int = 0) -> None:
        super().__init__()
        self._iface = (iface or "").strip()
        self._domain = int(domain) & 0xFF
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._clock_identity = clock_identity_from_mac(_interface_mac(self._iface))
        self._logged_first_sample = False

    @property
    def iface(self) -> str:
        return self._iface

    @property
    def domain(self) -> int:
        return self._domain

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._logged_first_sample = False
        self._thread = threading.Thread(
            target=self._run,
            name=f"PtpV2Slave-{self._iface or 'default'}-{self._domain}",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "PTP slave started (iface=%s, domain=%s)",
            self._iface or "default",
            self._domain,
        )

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _run(self) -> None:
        event_sock = None
        general_sock = None
        try:
            event_sock = _create_multicast_socket(PTP_EVENT_PORT, self._iface)
            general_sock = _create_multicast_socket(PTP_GENERAL_PORT, self._iface)
        except OSError as exc:
            logger.error("PTP socket setup failed: %s", exc)
            self.lock_changed.emit(False, str(exc))
            if event_sock is not None:
                event_sock.close()
            if general_sock is not None:
                general_sock.close()
            return

        utc_offset = DEFAULT_UTC_OFFSET
        ptp_timescale = False
        master_key: Optional[bytes] = None
        master_quality: Tuple[int, int, int, bytes] = (255, 255, 255, b"\xff" * 8)
        pending_sync: dict[tuple[bytes, int], tuple[float, float]] = {}
        last_sync_mono = 0.0
        last_announce_mono = 0.0
        last_delay_req_mono = 0.0
        delay_seq = 0
        locked = False

        sockets = [event_sock, general_sock]
        try:
            while not self._stop.is_set():
                readable, _, _ = select.select(sockets, [], [], 0.25)
                now_mono = time.monotonic()
                for sock in readable:
                    while True:
                        try:
                            data, _addr = sock.recvfrom(1500)
                        except (BlockingIOError, OSError):
                            break
                        recv_mono = time.monotonic()
                        header = parse_header(data)
                        if header is None or header.domain != self._domain:
                            continue
                        if header.message_type == MSG_ANNOUNCE:
                            last_announce_mono = recv_mono
                            utc = parse_announce_utc_offset(data)
                            if utc is not None:
                                utc_offset = utc
                            elif header.ptp_timescale:
                                utc_offset = DEFAULT_UTC_OFFSET
                            if (
                                ptp_timescale != header.ptp_timescale
                                or master_key is None
                            ):
                                logger.info(
                                    "PTP announce: master=%s timescale=%s utc_offset=%s",
                                    header.clock_identity.hex(),
                                    "PTP/TAI" if header.ptp_timescale else "ARB/UTC",
                                    utc_offset if header.ptp_timescale else 0,
                                )
                            ptp_timescale = header.ptp_timescale
                            quality = parse_announce_quality(data)
                            if master_key is None or quality < master_quality:
                                master_key = header.source_key
                                master_quality = quality
                                logger.info(
                                    "PTP master selected: %s", header.clock_identity.hex()
                                )
                            continue
                        if master_key is None or header.source_key != master_key:
                            continue
                        tai_utc = effective_utc_offset(ptp_timescale, utc_offset)
                        if header.message_type == MSG_SYNC:
                            last_sync_mono = recv_mono
                            if not header.two_step:
                                ts = parse_timestamp(data)
                                if ts is not None:
                                    self._emit_sample(
                                        ts, header.correction_ns, tai_utc, recv_mono
                                    )
                                    if not locked:
                                        locked = True
                                        self.lock_changed.emit(True, "")
                            else:
                                pending_sync[(header.source_key, header.sequence_id)] = (
                                    recv_mono,
                                    header.correction_ns,
                                )
                            continue
                        if header.message_type == MSG_FOLLOW_UP:
                            key = (header.source_key, header.sequence_id)
                            pending = pending_sync.pop(key, None)
                            ts = parse_timestamp(data)
                            if pending is None or ts is None:
                                continue
                            recv_at, corr = pending
                            last_sync_mono = recv_at
                            self._emit_sample(
                                ts, corr + header.correction_ns, tai_utc, recv_at
                            )
                            if not locked:
                                locked = True
                                self.lock_changed.emit(True, "")

                if last_sync_mono and master_key:
                    if (now_mono - last_delay_req_mono) >= DELAY_REQ_INTERVAL_S:
                        try:
                            delay_seq = (delay_seq + 1) & 0xFFFF
                            pkt = build_delay_req(
                                self._clock_identity, delay_seq, self._domain
                            )
                            event_sock.sendto(pkt, (PTP_MULTICAST, PTP_EVENT_PORT))
                            last_delay_req_mono = now_mono
                        except OSError as exc:
                            logger.debug("Delay_Req send failed: %s", exc)

                if locked and last_sync_mono and (now_mono - last_sync_mono) > UNLOCK_TIMEOUT_S:
                    locked = False
                    self.lock_changed.emit(False, "sync timeout")
                if (
                    last_announce_mono
                    and (now_mono - last_announce_mono) > UNLOCK_TIMEOUT_S * 2
                    and master_key is not None
                ):
                    master_key = None
                    master_quality = (255, 255, 255, b"\xff" * 8)
                    ptp_timescale = False
        finally:
            for sock in (event_sock, general_sock):
                if sock is not None:
                    _leave_group(sock, self._iface)
                    try:
                        sock.close()
                    except OSError:
                        pass

    def _emit_sample(
        self,
        ts: Tuple[int, int],
        correction_ns: float,
        utc_offset: int,
        recv_mono: float,
    ) -> None:
        unix = ptp_timestamp_to_unix(ts[0], ts[1], utc_offset)
        unix += correction_ns / 1_000_000_000.0
        if not self._logged_first_sample:
            self._logged_first_sample = True
            logger.info(
                "PTP sample: origin=%d.%09d correction_ns=%.0f utc_offset=%s unix=%.6f",
                ts[0],
                ts[1],
                correction_ns,
                utc_offset,
                unix,
            )
        try:
            ref = unix_to_local_datetime(unix)
        except (OSError, OverflowError, ValueError) as exc:
            logger.debug("PTP datetime conversion failed: %s", exc)
            return
        self.sample_ready.emit(ref, recv_mono)
