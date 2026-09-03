#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# ltc_reader.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
USB-serial SMPTE LTC reader for the Leo Bodnar LBE-1110.

The device sends 8-byte packets over a USB CDC virtual serial port:

    hours, minutes, seconds, frames, reserved, reserved, 0x55, 0xAA
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

SYNC_BYTES = b"\x55\xaa"
FRAME_SIZE = 8
PAYLOAD_SIZE = 6
MAX_HOURS = 23
MAX_MINUTES = 59
MAX_SECONDS = 59
MAX_FRAMES = 29
STANDARD_FRAME_RATES = (24, 25, 30)
LEO_BODNAR_VID = 0x1DD2
SERIAL_READ_TIMEOUT_S = 0.05
SERIAL_READ_SIZE = 64
UNLOCK_TIMEOUT_S = 0.15
BUFFER_CAP = 64


@dataclass(frozen=True)
class LtcFrame:
    """One decoded LBE-1110 timecode packet."""

    hours: int
    minutes: int
    seconds: int
    frames: int
    reserved1: int = 0
    reserved2: int = 0


def pack_lbe1110_frame(
    hours: int,
    minutes: int,
    seconds: int,
    frames: int,
    reserved1: int = 0,
    reserved2: int = 0,
) -> bytes:
    """Build one 8-byte LBE-1110 packet (for tests)."""
    return bytes((hours, minutes, seconds, frames, reserved1, reserved2, 0x55, 0xAA))


def parse_lbe1110_buffer(data: bytes) -> Tuple[bytes, List[LtcFrame]]:
    """
    Extract complete LBE-1110 frames from a byte buffer.

    Frames are 8 bytes ending in ``0x55 0xAA``. Incomplete trailing bytes are
    returned as the remainder. Packets with out-of-range time fields are skipped
    but still consumed so the parser cannot stall.
    """
    found: List[LtcFrame] = []
    consumed = 0
    search_from = 0
    while True:
        sync = data.find(SYNC_BYTES, search_from)
        if sync < 0:
            break
        start = sync - PAYLOAD_SIZE
        if start < consumed:
            search_from = sync + len(SYNC_BYTES)
            continue
        payload = data[start:sync]
        hours, minutes, seconds, frames_n, reserved1, reserved2 = payload
        if (
            hours <= MAX_HOURS
            and minutes <= MAX_MINUTES
            and seconds <= MAX_SECONDS
            and frames_n <= MAX_FRAMES
        ):
            found.append(
                LtcFrame(
                    hours=hours,
                    minutes=minutes,
                    seconds=seconds,
                    frames=frames_n,
                    reserved1=reserved1,
                    reserved2=reserved2,
                )
            )
        consumed = sync + len(SYNC_BYTES)
        search_from = consumed
    return data[consumed:], found


def infer_frame_rate(highest_frame: int) -> float:
    """Snap ``highest_frame + 1`` up to 24, 25, or 30 fps."""
    candidate = int(highest_frame) + 1
    for rate in STANDARD_FRAME_RATES:
        if candidate <= rate:
            return float(rate)
    return 30.0


def ltc_milliseconds(frames: int, frame_rate: float) -> int:
    """Milliseconds within the second derived from the frame number."""
    if frame_rate <= 0:
        return 0
    return max(0, min(999, int(frames * 1000.0 / frame_rate)))


def _port_search_text(info: object) -> str:
    parts = [
        str(getattr(info, "description", "") or ""),
        str(getattr(info, "manufacturer", "") or ""),
        str(getattr(info, "product", "") or ""),
        str(getattr(info, "hwid", "") or ""),
    ]
    return " ".join(parts).upper()


def auto_select_port(ports: Optional[Sequence[object]] = None) -> str:
    """
    Pick an LBE-1110-like serial device.

    Preference: Leo Bodnar USB VID ``0x1DD2``, then description matching
    LBE-1110, then CDC / ttyACM / usbmodem, then the first listed port.
    """
    if ports is None:
        try:
            from serial.tools import list_ports

            infos: Sequence[object] = tuple(list_ports.comports())
        except Exception as exc:
            logger.debug("Serial port listing failed: %s", exc)
            return ""
    else:
        infos = ports
    if not infos:
        return ""
    for info in infos:
        if getattr(info, "vid", None) == LEO_BODNAR_VID:
            return str(getattr(info, "device", "") or "")
    for info in infos:
        blob = _port_search_text(info)
        if "LBE-1110" in blob or "LBE1110" in blob:
            return str(getattr(info, "device", "") or "")
    for info in infos:
        device = str(getattr(info, "device", "") or "").lower()
        blob = _port_search_text(info).lower()
        if "ttyacm" in device or "usbmodem" in device or "cdc" in blob:
            return str(getattr(info, "device", "") or "")
    return str(getattr(infos[0], "device", "") or "")


def list_serial_ports() -> List[Tuple[str, str]]:
    """Return ``(label, device)`` pairs for the LTC serial-port combo."""
    try:
        from serial.tools import list_ports

        infos = list(list_ports.comports())
    except Exception as exc:
        logger.debug("Serial port listing failed: %s", exc)
        return []
    result: List[Tuple[str, str]] = []
    for info in infos:
        device = str(getattr(info, "device", "") or "")
        if not device:
            continue
        description = str(getattr(info, "description", "") or "").strip()
        if description and description.lower() != "n/a":
            label = f"{device} ({description})"
        else:
            label = device
        result.append((label, device))
    return result


class LtcReader(QObject):
    """
    Background LBE-1110 reader. Emits timecode frames independent of the OS clock.
    """

    frame_ready = Signal(int, int, int, int, float, float)
    lock_changed = Signal(bool, str)

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self._port = (port or "").strip()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._resolved_port = ""

    @property
    def port(self) -> str:
        return self._port

    @property
    def resolved_port(self) -> str:
        return self._resolved_port

    @property
    def input_kind(self) -> str:
        return "serial"

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._resolved_port = ""
        self._thread = threading.Thread(
            target=self._run,
            name=f"LtcReader-{self._port or 'auto'}",
            daemon=True,
        )
        self._thread.start()
        logger.info("LTC reader started (port=%s)", self._port or "auto")

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _run(self) -> None:
        import serial

        port = self._port or auto_select_port()
        if not port:
            logger.warning("LTC reader: no serial port found")
            self.lock_changed.emit(False, "not connected")
            return
        try:
            ser = serial.Serial(port, timeout=SERIAL_READ_TIMEOUT_S)
        except (OSError, serial.SerialException) as exc:
            logger.error("LTC serial open failed (%s): %s", port, exc)
            self.lock_changed.emit(False, "not connected")
            return

        self._resolved_port = port
        logger.info("LTC reader connected to %s", port)
        buffer = b""
        last_frame_mono = 0.0
        locked = False
        highest_frame = 0
        try:
            while not self._stop.is_set():
                try:
                    chunk = ser.read(SERIAL_READ_SIZE)
                except (OSError, serial.SerialException) as exc:
                    logger.warning("LTC serial read failed: %s", exc)
                    if locked:
                        locked = False
                    self.lock_changed.emit(False, "not connected")
                    return
                now_mono = time.monotonic()
                if chunk:
                    buffer += chunk
                    buffer, frames = parse_lbe1110_buffer(buffer)
                    if len(buffer) > BUFFER_CAP:
                        buffer = buffer[-FRAME_SIZE:]
                    for frame in frames:
                        last_frame_mono = now_mono
                        if frame.frames > highest_frame:
                            highest_frame = frame.frames
                        frame_rate = infer_frame_rate(highest_frame)
                        self.frame_ready.emit(
                            frame.hours,
                            frame.minutes,
                            frame.seconds,
                            frame.frames,
                            frame_rate,
                            now_mono,
                        )
                        if not locked:
                            locked = True
                            self.lock_changed.emit(True, "")
                if locked and last_frame_mono and (now_mono - last_frame_mono) > UNLOCK_TIMEOUT_S:
                    locked = False
                    self.lock_changed.emit(False, "sync timeout")
        finally:
            try:
                ser.close()
            except OSError:
                pass
