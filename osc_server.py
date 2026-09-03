#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# osc_server.py
# This file is part of OnAirScreen
#
# OSC server for receiving commands and sending status
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
OSC daemon for OnAirScreen.

Receives Open Sound Control messages on a UDP listen port, maps them to the
existing COMMAND:VALUE API, and can push status to a configured send host
(Companion feedback) or reply to the UDP sender of a query.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Dict, Iterable, Optional, TYPE_CHECKING

from PySide6.QtCore import QSettings, QThread

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False
    Dispatcher = None  # type: ignore
    ThreadingOSCUDPServer = None  # type: ignore
    SimpleUDPClient = None  # type: ignore
    logging.getLogger(__name__).warning(
        "python-osc library not available. OSC support will be disabled."
    )

from defaults import (
    DEFAULT_OSC_ENABLED,
    DEFAULT_OSC_PORT,
    DEFAULT_OSC_SEND_HOST,
    DEFAULT_OSC_SEND_PORT,
)
from exceptions import OscError, OnAirScreenError, log_exception
from status_exporter import loudness_payload
from utils import settings_group

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)

OSC_PREFIX = "/oas"

_LED_SET_RE = re.compile(r"^/oas/led([1-4])$")
_AIR_SET_RE = re.compile(r"^/oas/air([1-4])$")
_AIR_RESET_RE = re.compile(r"^/oas/air([34])/reset$")
_TEXT_SET_RE = re.compile(r"^/oas/text/(now|next|warn)$")

_LED_STATE_RE = re.compile(r"^/oas/led([1-4])/state$")
_AIR_STATE_RE = re.compile(r"^/oas/air([1-4])/state$")
_AIR_TIME_RE = re.compile(r"^/oas/air([1-4])/time$")
_TEXT_STATE_RE = re.compile(r"^/oas/text/(now|next|warn)/state$")

_QUERY_ADDRESSES = frozenset({
    f"{OSC_PREFIX}/led{n}/state" for n in range(1, 5)
} | {
    f"{OSC_PREFIX}/air{n}/state" for n in range(1, 5)
} | {
    f"{OSC_PREFIX}/air{n}/time" for n in range(1, 5)
} | {
    f"{OSC_PREFIX}/air3/toh/state",
    f"{OSC_PREFIX}/warning/active",
    f"{OSC_PREFIX}/lufs/integrated/state",
    f"{OSC_PREFIX}/lufs/i",
    f"{OSC_PREFIX}/lufs/lra",
    f"{OSC_PREFIX}/status",
} | {
    f"{OSC_PREFIX}/text/{name}/state" for name in ("now", "next", "warn")
})


def osc_args_to_switch(args: tuple[Any, ...]) -> str:
    """
    Map OSC arguments to ON, OFF, TOGGLE, or RESET.

    No arguments means TOGGLE. Integers 0/1, floats with threshold 0.5,
    booleans, and strings (ON/OFF/TOGGLE/RESET/1/0) are accepted.
    """
    if not args:
        return "TOGGLE"

    value = args[0]
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, int) and not isinstance(value, bool):
        return "ON" if value != 0 else "OFF"
    if isinstance(value, float):
        return "ON" if value >= 0.5 else "OFF"
    if isinstance(value, str):
        text = value.strip().upper()
        if text in ("ON", "OFF", "TOGGLE", "RESET"):
            return text
        if text in ("1", "TRUE", "T"):
            return "ON"
        if text in ("0", "FALSE", "F"):
            return "OFF"
        return text
    return "TOGGLE"


def map_osc_to_command(address: str, args: tuple[Any, ...]) -> Optional[str]:
    """
    Map an OSC set-address and arguments to a COMMAND:VALUE string.

    Query/state addresses return None. Unknown addresses return None.
    """
    if address == f"{OSC_PREFIX}/air3/time":
        if not args:
            return None
        try:
            seconds = int(args[0])
        except (TypeError, ValueError):
            return None
        return f"AIR3TIME:{seconds}"

    if address in _QUERY_ADDRESSES or address.endswith("/state"):
        return None

    led_match = _LED_SET_RE.match(address)
    if led_match:
        switch = osc_args_to_switch(args)
        if switch == "RESET":
            switch = "TOGGLE"
        return f"LED{led_match.group(1)}:{switch}"

    reset_match = _AIR_RESET_RE.match(address)
    if reset_match:
        return f"AIR{reset_match.group(1)}:RESET"

    if address == f"{OSC_PREFIX}/air3/toh":
        return f"AIR3TOH:{osc_args_to_switch(args)}"

    if address == f"{OSC_PREFIX}/lufs/integrated/reset":
        return "LUFSI:RESET"

    if address == f"{OSC_PREFIX}/lufs/integrated":
        switch = osc_args_to_switch(args)
        if switch == "ON":
            return "LUFSI:START"
        if switch == "OFF":
            return "LUFSI:STOP"
        if switch == "TOGGLE":
            return "LUFSI:TOGGLE"
        if switch == "RESET":
            return "LUFSI:RESET"
        return f"LUFSI:{switch}"

    air_match = _AIR_SET_RE.match(address)
    if air_match:
        return f"AIR{air_match.group(1)}:{osc_args_to_switch(args)}"

    text_match = _TEXT_SET_RE.match(address)
    if text_match:
        text_type = text_match.group(1)
        payload = args[0] if args else ""
        if not isinstance(payload, str):
            payload = str(payload)
        if text_type == "warn":
            return f"WARN:{payload}"
        return f"{text_type.upper()}:{payload}"

    if address == f"{OSC_PREFIX}/command":
        if not args:
            return None
        payload = args[0]
        if not isinstance(payload, str):
            payload = str(payload)
        payload = payload.strip()
        return payload if payload else None

    return None


def iter_status_messages(
    status: dict[str, Any],
    specific_item: str | None = None,
) -> list[tuple[str, Any]]:
    """
    Build OSC status messages from get_status_json() output.

    Args:
        status: Status dictionary from MainScreen.get_status_json()
        specific_item: Optional item key (led1, air2, now, air3toh, ...)

    Returns:
        List of (osc_address, value) pairs. Integers 0/1 for booleans.
    """
    messages: list[tuple[str, Any]] = []

    def led_state(led_num: int) -> tuple[str, int]:
        on = bool(status["leds"][led_num]["status"])
        return (f"{OSC_PREFIX}/led{led_num}/state", 1 if on else 0)

    def air_state(air_num: int) -> list[tuple[str, Any]]:
        on = bool(status["air"][air_num]["status"])
        seconds = int(status["air"][air_num].get("seconds", 0) or 0)
        return [
            (f"{OSC_PREFIX}/air{air_num}/state", 1 if on else 0),
            (f"{OSC_PREFIX}/air{air_num}/time", seconds),
        ]

    def toh_state() -> tuple[str, int]:
        active = bool(status["air"][3].get("topOfHour", False))
        return (f"{OSC_PREFIX}/air3/toh/state", 1 if active else 0)

    def text_state(name: str) -> tuple[str, str]:
        return (f"{OSC_PREFIX}/text/{name}/state", str(status["texts"].get(name, "") or ""))

    def warning_active() -> tuple[str, int]:
        warn_text = status["texts"].get("warn", "") or ""
        return (f"{OSC_PREFIX}/warning/active", 1 if warn_text else 0)

    def lufs_messages() -> list[tuple[str, Any]]:
        running = bool(status.get("lufsIntegrated", False))
        return [
            (f"{OSC_PREFIX}/lufs/integrated/state", 1 if running else 0),
            (f"{OSC_PREFIX}/lufs/i", loudness_payload(status.get("lufsI"))),
            (f"{OSC_PREFIX}/lufs/lra", loudness_payload(status.get("lra"))),
        ]

    if specific_item is None:
        for led_num in range(1, 5):
            messages.append(led_state(led_num))
        for air_num in range(1, 5):
            messages.extend(air_state(air_num))
        messages.append(toh_state())
        for name in ("now", "next", "warn"):
            messages.append(text_state(name))
        messages.append(warning_active())
        messages.extend(lufs_messages())
        return messages

    if specific_item.startswith("led"):
        try:
            led_num = int(specific_item[3:])
        except ValueError:
            return messages
        if 1 <= led_num <= 4:
            messages.append(led_state(led_num))
        return messages

    if specific_item == "air3toh":
        messages.append(toh_state())
        messages.extend(air_state(3))
        return messages

    if specific_item.startswith("air"):
        try:
            air_num = int(specific_item[3:])
        except ValueError:
            return messages
        if 1 <= air_num <= 4:
            messages.extend(air_state(air_num))
        return messages

    if specific_item in ("now", "next", "warn"):
        messages.append(text_state(specific_item))
        if specific_item == "warn":
            messages.append(warning_active())
        return messages

    if specific_item in ("lufs", "lufsintegrated"):
        messages.extend(lufs_messages())
        return messages

    return messages


def is_query_address(address: str) -> bool:
    """Return True if the OSC address is a status query, not a set command."""
    return address in _QUERY_ADDRESSES


class OscDaemon(QThread):
    """
    OSC server thread.

    Listens for OSC commands, dispatches them on the GUI thread via
    command_signal, pushes status to a configured send host, and replies
    to query senders.
    """

    def __init__(self, main_screen: Optional["MainScreen"] = None) -> None:
        super().__init__()
        self.main_screen = main_screen
        self._stop_requested = False
        self._server: Any = None
        self._server_thread: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()
        self._applied_settings: Optional[Dict[str, Any]] = None
        self.listen_port = DEFAULT_OSC_PORT
        self.send_host = DEFAULT_OSC_SEND_HOST
        self.send_port = DEFAULT_OSC_SEND_PORT
        self._enabled = False

    def _read_osc_settings(self) -> Dict[str, Any]:
        """Read OSC settings from QSettings as a comparable snapshot."""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "OSC"):
            try:
                listen_port = int(settings.value("oscport", DEFAULT_OSC_PORT, type=int))
            except (ValueError, TypeError):
                listen_port = DEFAULT_OSC_PORT
            try:
                send_port = int(settings.value("oscsendport", DEFAULT_OSC_SEND_PORT, type=int))
            except (ValueError, TypeError):
                send_port = DEFAULT_OSC_SEND_PORT
            send_host = settings.value("oscsendhost", DEFAULT_OSC_SEND_HOST, type=str) or ""
            return {
                "enableosc": settings.value("enableosc", DEFAULT_OSC_ENABLED, type=bool),
                "oscport": listen_port,
                "oscsendhost": send_host.strip(),
                "oscsendport": send_port,
            }

    def _load_config(self) -> None:
        """Load OSC configuration from QSettings."""
        snapshot = self._read_osc_settings()
        self._enabled = bool(snapshot["enableosc"])
        self.listen_port = int(snapshot["oscport"])
        self.send_host = str(snapshot["oscsendhost"])
        self.send_port = int(snapshot["oscsendport"])
        self._applied_settings = snapshot

    def _is_enabled(self) -> bool:
        """Check if OSC is enabled in settings."""
        return bool(self._read_osc_settings()["enableosc"])

    def _sleep_interruptible(self, seconds: float, step: float = 0.1) -> bool:
        """Sleep up to seconds, returning immediately when stop is requested."""
        deadline = time.monotonic() + seconds
        while not self._stop_requested:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(step, remaining))
        return True

    def _emit_command(self, command: str) -> None:
        """Dispatch COMMAND:VALUE on the GUI thread."""
        if not self.main_screen:
            return
        command_bytes = command.encode("utf-8")
        if hasattr(self.main_screen, "command_signal") and self.main_screen.command_signal:
            self.main_screen.command_signal.command_received.emit(command_bytes, "osc")
        elif hasattr(self.main_screen, "command_handler"):
            logger.warning("OSC command executed without signal - may not work correctly for timers")
            self.main_screen.command_handler.parse_cmd(command_bytes)
        else:
            logger.error("No command handler available for OSC command")

    def _send_messages(self, host: str, port: int, messages: Iterable[tuple[str, Any]]) -> None:
        """Send OSC messages to host:port."""
        if not OSC_AVAILABLE or not host or not port:
            return
        try:
            client = SimpleUDPClient(host, port)
            with self._send_lock:
                for address, value in messages:
                    client.send_message(address, value)
        except Exception as e:
            error = OscError(f"Error sending OSC message to {host}:{port}: {e}")
            log_exception(logger, error)

    def _handle_query(self, address: str, client_address: tuple[str, int]) -> None:
        """Reply to an OSC query at the UDP sender address."""
        if not self.main_screen or not hasattr(self.main_screen, "get_status_json"):
            return
        try:
            status = self.main_screen.get_status_json()
        except Exception as e:
            error = OscError(f"Error reading status for OSC query: {e}")
            log_exception(logger, error)
            return

        if address == f"{OSC_PREFIX}/status":
            messages = iter_status_messages(status)
        else:
            messages = self._messages_for_query_address(address, status)

        if not messages:
            return
        host, port = client_address[0], int(client_address[1])
        self._send_messages(host, port, messages)

    def _messages_for_query_address(
        self,
        address: str,
        status: dict[str, Any],
    ) -> list[tuple[str, Any]]:
        """Resolve a single query address to status messages."""
        led_match = _LED_STATE_RE.match(address)
        if led_match:
            return iter_status_messages(status, f"led{led_match.group(1)}")

        if address == f"{OSC_PREFIX}/air3/toh/state":
            return iter_status_messages(status, "air3toh")[:1]

        air_state_match = _AIR_STATE_RE.match(address)
        if air_state_match:
            air_num = int(air_state_match.group(1))
            return [iter_status_messages(status, f"air{air_num}")[0]]

        air_time_match = _AIR_TIME_RE.match(address)
        if air_time_match:
            air_num = int(air_time_match.group(1))
            return [iter_status_messages(status, f"air{air_num}")[1]]

        text_match = _TEXT_STATE_RE.match(address)
        if text_match:
            name = text_match.group(1)
            return iter_status_messages(status, name)[:1]

        if address == f"{OSC_PREFIX}/warning/active":
            return [iter_status_messages(status, "warn")[-1]]

        if address == f"{OSC_PREFIX}/lufs/integrated/state":
            return [iter_status_messages(status, "lufs")[0]]

        if address == f"{OSC_PREFIX}/lufs/i":
            return [iter_status_messages(status, "lufs")[1]]

        if address == f"{OSC_PREFIX}/lufs/lra":
            return [iter_status_messages(status, "lufs")[2]]

        return []

    def _on_osc_message(self, client_address: tuple[str, int], address: str, *args: Any) -> None:
        """Handle an incoming OSC message (set or query)."""
        try:
            logger.debug("Received OSC %s %s from %s", address, args, client_address)
            command = map_osc_to_command(address, args)
            if command:
                self._emit_command(command)
                return
            if is_query_address(address):
                self._handle_query(address, client_address)
                return
            logger.debug("Ignoring unmapped OSC address: %s", address)
        except Exception as e:
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = OscError(f"Error processing OSC message: {e}")
                log_exception(logger, error)

    def publish_status(self, specific_item: str | None = None) -> None:
        """
        Push current status to the configured send host.

        Does nothing when OSC is disabled or send host is empty.
        """
        if not OSC_AVAILABLE or not self._applied_settings:
            return
        if not self._applied_settings.get("enableosc"):
            return
        host = self.send_host
        if not host:
            return
        if not self.main_screen or not hasattr(self.main_screen, "get_status_json"):
            return
        try:
            status = self.main_screen.get_status_json()
            messages = iter_status_messages(status, specific_item)
            self._send_messages(host, self.send_port, messages)
        except Exception as e:
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = OscError(f"Error publishing OSC status: {e}")
                log_exception(logger, error)

    def run(self) -> None:
        """Start the OSC UDP server in this thread."""
        if not OSC_AVAILABLE:
            logger.warning("OSC support not available, skipping OSC server startup")
            return

        if not self._is_enabled():
            logger.info("OSC is disabled in settings")
            return

        self._load_config()

        try:
            dispatcher = Dispatcher()
            dispatcher.set_default_handler(self._on_osc_message, needs_reply_address=True)
            self._server = ThreadingOSCUDPServer(("0.0.0.0", self.listen_port), dispatcher)
            logger.info("OSC server listening on UDP port %s", self.listen_port)
            if self.send_host:
                logger.info("OSC status push to %s:%s", self.send_host, self.send_port)

            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                name="OscUDPServer",
                daemon=True,
            )
            self._server_thread.start()
            self.publish_status()

            last_publish = time.monotonic()
            while not self._stop_requested:
                if self._sleep_interruptible(1.0):
                    break
                if time.monotonic() - last_publish >= 5.0:
                    self.publish_status()
                    last_publish = time.monotonic()
        except OSError as e:
            error = OscError(f"Failed to bind OSC listen port {self.listen_port}: {e}")
            log_exception(logger, error)
        except Exception as e:
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = OscError(f"Error in OSC server thread: {e}")
                log_exception(logger, error)
        finally:
            self._shutdown_server()
            logger.debug("OSC server thread finished")

    def _shutdown_server(self) -> None:
        """Stop the nested UDP server if it is running."""
        server = self._server
        self._server = None
        if server is not None:
            try:
                server.shutdown()
            except Exception as e:
                logger.debug("OSC server shutdown: %s", e)
            try:
                server.server_close()
            except Exception as e:
                logger.debug("OSC server close: %s", e)
        thread = self._server_thread
        self._server_thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def restart(self) -> None:
        """Restart the OSC server only when OSC settings changed."""
        new_settings = self._read_osc_settings()
        enabled = bool(new_settings["enableosc"])
        running = self.isRunning()

        if self._applied_settings == new_settings:
            if enabled and running:
                logger.debug("OSC settings unchanged, skipping restart")
                return
            if not enabled and not running:
                logger.debug("OSC still disabled, skipping restart")
                return

        logger.debug("Restarting OSC server...")
        self.stop()
        if self.isRunning():
            logger.debug("Waiting for OSC server thread to stop...")
            if not self.wait(3000):
                logger.warning("OSC server thread did not stop within timeout, forcing termination")
                self.terminate()
                self.wait(1000)

        self._stop_requested = False

        if enabled:
            logger.debug("Starting new OSC server thread...")
            self.start()
        else:
            self._applied_settings = new_settings
            logger.debug("OSC is disabled, not restarting server")

    def stop(self) -> None:
        """Stop the OSC server gracefully."""
        logger.debug("Stopping OSC server...")
        self._stop_requested = True
        self._shutdown_server()
        self.wait(3000)
