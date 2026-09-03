#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# aoip_rtp.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Generic multicast RTP receiver for AoIP metering (Livewire / AES67).

No clock sync or playout — samples are decoded to stereo float32 and handed
to a callback for MeterEngine processing.
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
from collections import deque
from typing import Callable, Deque, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("OnAirScreen")

CODEC_L16 = "L16"
CODEC_L24 = "L24"
SUPPORTED_CODECS = (CODEC_L16, CODEC_L24)

_L16_SCALE = 1.0 / float(1 << 15)
_L24_SCALE = 1.0 / float(1 << 23)
_RTP_HEADER_MIN = 12
DEFAULT_BLOCK_FRAMES = 1024
METER_CHANNELS = 2
MAX_STREAM_CHANNELS = 64


def normalize_codec(codec: str) -> str:
    """Return L16 or L24; default L24."""
    value = (codec or CODEC_L24).strip().upper()
    if value in SUPPORTED_CODECS:
        return value
    return CODEC_L24


def _to_stereo(samples: np.ndarray) -> np.ndarray:
    """Map (N, C) PCM to stereo (N, 2) for the meter (ch0 + ch1; mono duplicated)."""
    if samples.size == 0:
        return np.zeros((0, METER_CHANNELS), dtype=np.float32)
    frames, channels = samples.shape
    stereo = np.empty((frames, METER_CHANNELS), dtype=np.float32)
    stereo[:, 0] = samples[:, 0]
    stereo[:, 1] = samples[:, 0] if channels < 2 else samples[:, 1]
    return stereo


def decode_l24(payload: bytes, channels: int = 2) -> np.ndarray:
    """
    Decode big-endian 24-bit signed interleaved PCM to stereo float32 [-1, 1].

    Truncates trailing incomplete frames. ``channels`` is the stream channel count.
    """
    channels = max(1, min(MAX_STREAM_CHANNELS, int(channels)))
    bytes_per_frame = 3 * channels
    usable = len(payload) - (len(payload) % bytes_per_frame)
    if usable <= 0:
        return np.zeros((0, METER_CHANNELS), dtype=np.float32)

    raw = np.frombuffer(payload, dtype=np.uint8, count=usable)
    frames = usable // bytes_per_frame
    packed = raw.reshape(frames, channels, 3)
    samples = (
        (packed[:, :, 0].astype(np.int32) << 16)
        | (packed[:, :, 1].astype(np.int32) << 8)
        | packed[:, :, 2].astype(np.int32)
    )
    samples = (samples << 8) >> 8
    return _to_stereo(samples.astype(np.float32) * np.float32(_L24_SCALE))


def decode_l16(payload: bytes, channels: int = 2) -> np.ndarray:
    """
    Decode big-endian 16-bit signed interleaved PCM to stereo float32 [-1, 1].
    """
    channels = max(1, min(MAX_STREAM_CHANNELS, int(channels)))
    bytes_per_frame = 2 * channels
    usable = len(payload) - (len(payload) % bytes_per_frame)
    if usable <= 0:
        return np.zeros((0, METER_CHANNELS), dtype=np.float32)

    frames = usable // bytes_per_frame
    samples = np.frombuffer(payload, dtype=">i2", count=frames * channels)
    samples = samples.reshape(frames, channels).astype(np.float32) * np.float32(_L16_SCALE)
    return _to_stereo(samples)


def decode_l24_stereo(payload: bytes) -> np.ndarray:
    """Decode Livewire-style L24 stereo (compat wrapper)."""
    return decode_l24(payload, channels=2)


def decode_pcm(payload: bytes, codec: str = CODEC_L24, channels: int = 2) -> np.ndarray:
    """Decode L16 or L24 interleaved PCM to stereo float32."""
    if normalize_codec(codec) == CODEC_L16:
        return decode_l16(payload, channels=channels)
    return decode_l24(payload, channels=channels)


def parse_rtp_payload(packet: bytes) -> Tuple[Optional[int], bytes]:
    """
    Strip RTP header and return (sequence_number, audio_payload).

    Returns (None, b"") if the packet is too short or not version 2 RTP.
    """
    if len(packet) < _RTP_HEADER_MIN:
        return None, b""

    first = packet[0]
    version = first >> 6
    if version != 2:
        return None, b""

    padding = bool(first & 0x20)
    extension = bool(first & 0x10)
    csrc_count = first & 0x0F
    header_len = _RTP_HEADER_MIN + (csrc_count * 4)
    if len(packet) < header_len:
        return None, b""

    seq = struct.unpack("!H", packet[2:4])[0]
    offset = header_len

    if extension:
        if len(packet) < offset + 4:
            return None, b""
        ext_len_words = struct.unpack("!H", packet[offset + 2 : offset + 4])[0]
        offset += 4 + (ext_len_words * 4)
        if len(packet) < offset:
            return None, b""

    payload = packet[offset:]
    if padding and payload:
        pad_len = payload[-1]
        if pad_len and pad_len <= len(payload):
            payload = payload[:-pad_len]

    return seq, payload


def list_ipv4_interfaces() -> List[Tuple[str, str]]:
    """
    Return (label, ipv4) pairs for local IPv4 interfaces suitable for IGMP join.

    Prefer PySide6 QNetworkInterface. Fall back to hostname resolution if Qt is
    unavailable.
    """
    results: List[Tuple[str, str]] = []
    seen: set[str] = set()

    try:
        from PySide6.QtNetwork import QAbstractSocket, QNetworkInterface

        for iface in QNetworkInterface.allInterfaces():
            flags = iface.flags()
            if not (flags & QNetworkInterface.InterfaceFlag.IsUp):
                continue
            if flags & QNetworkInterface.InterfaceFlag.IsLoopBack:
                continue
            name = iface.humanReadableName() or iface.name() or "iface"
            for entry in iface.addressEntries():
                addr = entry.ip()
                if addr.protocol() != QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                    continue
                ip_str = addr.toString()
                if not ip_str or ip_str.startswith("127.") or ip_str in seen:
                    continue
                seen.add(ip_str)
                results.append((f"{name} ({ip_str})", ip_str))
        if results:
            return results
    except Exception as exc:
        logger.debug("QNetworkInterface enum failed: %s", exc)

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip_str = info[4][0]
            if ip_str.startswith("127.") or ip_str in seen:
                continue
            seen.add(ip_str)
            results.append((ip_str, ip_str))
    except Exception as exc:
        logger.debug("getaddrinfo interface enum failed: %s", exc)

    return results


def _membership_request(group_ip: str, iface_ip: str) -> bytes:
    group = socket.inet_aton(group_ip)
    if iface_ip:
        return group + socket.inet_aton(iface_ip)
    return group + struct.pack("=I", socket.INADDR_ANY)


class MulticastRtpReceiver:
    """
    Background UDP multicast RTP receiver for AES67 / Livewire metering.

    Decoded float32 stereo frames are pushed through ``on_frames`` in blocks
    of approximately ``block_frames`` samples.
    """

    def __init__(
        self,
        multicast: str,
        port: int,
        on_frames: Callable[[np.ndarray], None],
        iface: str = "",
        codec: str = CODEC_L24,
        channels: int = 2,
        sample_rate: int = 48000,
        block_frames: int = DEFAULT_BLOCK_FRAMES,
        on_error: Optional[Callable[[str], None]] = None,
        log_name: str = "AoIP",
    ):
        self._multicast = str(multicast).strip()
        self._port = int(port)
        self._iface = (iface or "").strip()
        self._codec = normalize_codec(codec)
        self._channels = max(1, min(MAX_STREAM_CHANNELS, int(channels)))
        self._sample_rate = max(8000, int(sample_rate))
        self._block_frames = max(64, int(block_frames))
        self._on_frames = on_frames
        self._on_error = on_error
        self._log_name = log_name
        self._ring_max_frames = max(self._block_frames, int(self._sample_rate * 0.04))

        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ring: Deque[np.ndarray] = deque()
        self._ring_frames = 0
        self._ring_lock = threading.Lock()
        self._last_seq: Optional[int] = None

    @property
    def multicast(self) -> str:
        return self._multicast

    @property
    def port(self) -> int:
        return self._port

    @property
    def iface(self) -> str:
        return self._iface

    @property
    def codec(self) -> str:
        return self._codec

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Open the socket, join multicast, and start the receive thread."""
        self.stop()
        self._stop.clear()
        try:
            sock = self._create_socket()
        except Exception as exc:
            message = f"{self._log_name} socket setup failed: {exc}"
            logger.error(message)
            if self._on_error:
                self._on_error(message)
            return

        self._sock = sock
        self._thread = threading.Thread(
            target=self._run,
            name=f"{self._log_name}Receiver-{self._multicast}:{self._port}",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "%s capture started (multicast=%s:%s, codec=%s, ch=%s, sr=%s, iface=%s)",
            self._log_name,
            self._multicast,
            self._port,
            self._codec,
            self._channels,
            self._sample_rate,
            self._iface or "default",
        )

    def stop(self) -> None:
        """Leave the multicast group and stop the receive thread."""
        self._stop.set()
        sock = self._sock
        self._sock = None
        if sock is not None:
            try:
                self._leave_group(sock)
            except Exception as exc:
                logger.debug("%s leave group: %s", self._log_name, exc)
            try:
                sock.close()
            except Exception as exc:
                logger.debug("%s socket close: %s", self._log_name, exc)

        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

        with self._ring_lock:
            self._ring.clear()
            self._ring_frames = 0
        self._last_seq = None

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass

        sock.bind(("", self._port))
        sock.settimeout(0.25)

        try:
            mreq = _membership_request(self._multicast, self._iface)
        except OSError as exc:
            sock.close()
            raise ValueError(
                f"Invalid {self._log_name} multicast/interface: {self._multicast!r}/{self._iface!r}"
            ) from exc

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock

    def _leave_group(self, sock: socket.socket) -> None:
        try:
            mreq = _membership_request(self._multicast, self._iface)
        except OSError:
            return
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
        except OSError:
            pass

    def _run(self) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            while not self._stop.is_set():
                try:
                    data, _addr = sock.recvfrom(8192)
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop.is_set():
                        break
                    raise
                self._handle_packet(data)
                self._flush_ready_blocks()
        except Exception as exc:
            if not self._stop.is_set():
                message = f"{self._log_name} receive error: {exc}"
                logger.error(message)
                if self._on_error:
                    self._on_error(message)
        finally:
            self._flush_ready_blocks(force_partial=True)

    def _handle_packet(self, packet: bytes) -> None:
        seq, payload = parse_rtp_payload(packet)
        if seq is None or not payload:
            return

        if self._last_seq is not None:
            expected = (self._last_seq + 1) & 0xFFFF
            if seq != expected:
                gap = (seq - expected) & 0xFFFF
                if gap < 1000:
                    logger.debug(
                        "%s RTP sequence gap: expected %s got %s (gap=%s)",
                        self._log_name,
                        expected,
                        seq,
                        gap,
                    )
        self._last_seq = seq

        frames = decode_pcm(payload, codec=self._codec, channels=self._channels)
        if frames.size == 0:
            return

        with self._ring_lock:
            self._ring.append(frames)
            self._ring_frames += int(frames.shape[0])
            while self._ring_frames > self._ring_max_frames and self._ring:
                dropped = self._ring.popleft()
                self._ring_frames -= int(dropped.shape[0])

    def _flush_ready_blocks(self, force_partial: bool = False) -> None:
        while True:
            block = self._pop_block(force_partial=force_partial)
            if block is None:
                return
            try:
                self._on_frames(block)
            except Exception as exc:
                logger.error("%s on_frames callback error: %s", self._log_name, exc)

    def _pop_block(self, force_partial: bool = False) -> Optional[np.ndarray]:
        with self._ring_lock:
            if self._ring_frames < self._block_frames and not (
                force_partial and self._ring_frames > 0
            ):
                return None
            if self._ring_frames <= 0:
                return None

            target = self._block_frames if self._ring_frames >= self._block_frames else self._ring_frames
            parts: List[np.ndarray] = []
            need = target
            while need > 0 and self._ring:
                chunk = self._ring[0]
                n = int(chunk.shape[0])
                if n <= need:
                    parts.append(self._ring.popleft())
                    self._ring_frames -= n
                    need -= n
                else:
                    parts.append(chunk[:need])
                    self._ring[0] = chunk[need:]
                    self._ring_frames -= need
                    need = 0
            if not parts:
                return None
            return np.concatenate(parts, axis=0)
