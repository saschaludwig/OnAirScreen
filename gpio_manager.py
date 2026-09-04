#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# gpio_manager.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Raspberry Pi GPIO inputs for OnAirScreen.

Mixer GPI contacts (via an optocoupler) are mapped to the same LED/AIR
commands as the UDP/HTTP API.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol, TYPE_CHECKING

from PySide6.QtCore import QObject, QSettings, Signal

from defaults import (
    DEFAULT_GPIO_DEBOUNCE_MS,
    DEFAULT_GPIO_ENABLED,
    GPIO_ACTIONS,
    GPIO_CHANNEL_COUNT,
    GPIO_MODES,
    GPIO_SAFE_BCM_PINS,
    default_gpio_channel,
    gpio_setting_key,
)
from utils import settings_group

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)


def debian_gpio_site_paths() -> list[str]:
    """Debian/Raspberry Pi OS dist-packages dirs that exist on this machine."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    candidates = (
        Path("/usr/lib/python3/dist-packages"),
        Path(f"/usr/lib/python{version}/dist-packages"),
        Path(f"/usr/local/lib/python{version}/dist-packages"),
    )
    return [str(path) for path in candidates if path.is_dir()]


def load_gpiozero_button() -> Optional[type]:
    """
    Return gpiozero.Button, or None.

    Packaged Raspberry Pi builds are PyInstaller freezes and do not bundle
    gpiozero. The Pi image and the .deb Depends install python3-gpiozero and
    python3-lgpio into Debian dist-packages; append those paths and retry.
    """
    try:
        from gpiozero import Button as GpioZeroButton
        return GpioZeroButton
    except ImportError:
        pass
    extra_paths = debian_gpio_site_paths()
    for path in extra_paths:
        if path not in sys.path:
            sys.path.append(path)
    if not extra_paths:
        return None
    try:
        from gpiozero import Button as GpioZeroButton
        return GpioZeroButton
    except ImportError:
        return None


GpioZeroButton = load_gpiozero_button()
GPIOZERO_AVAILABLE = GpioZeroButton is not None

_PI_MODEL_PATHS = (
    Path("/proc/device-tree/model"),
    Path("/sys/firmware/devicetree/base/model"),
)


def is_raspberry_pi() -> bool:
    """Return True when running on a Raspberry Pi board."""
    for model_path in _PI_MODEL_PATHS:
        try:
            text = model_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "raspberry pi" in text.lower():
            return True
    return False


def gpio_status_message(
    platform_available: Optional[bool] = None,
    library_available: Optional[bool] = None,
    enabled: bool = False,
) -> str:
    """Short status line for the GPIO settings tab."""
    on_pi = is_raspberry_pi() if platform_available is None else platform_available
    has_lib = GPIOZERO_AVAILABLE if library_available is None else library_available
    if not on_pi:
        return "GPIO not available on this platform."
    if not has_lib:
        return "gpiozero library not available."
    if enabled:
        return "GPIO enabled on Raspberry Pi."
    return "Raspberry Pi detected. GPIO inputs are ready."


def logical_active(raw_high: bool, invert: bool) -> bool:
    """Map a raw pin level to the logical active (contact closed) state."""
    return (not raw_high) if invert else raw_high


def command_for_event(
    action: str,
    mode: str,
    active: bool,
    custom_command: str = "",
) -> Optional[str]:
    """
    Return the API command for a GPIO event, or None when nothing should be sent.

    Level mode sends ON while the contact is closed and OFF when it opens.
    Edge modes send TOGGLE (or RESET / a custom command) on the matching edge.
    """
    action = (action or "LED1").strip()
    mode = (mode or "level").strip().lower()
    if mode not in GPIO_MODES:
        mode = "level"
    if action not in GPIO_ACTIONS:
        action = "LED1"

    if action == "CUSTOM":
        command = (custom_command or "").strip()
        if not command:
            return None
        if mode == "level":
            return command if active else None
        if mode == "rising":
            return command if active else None
        if mode == "falling":
            return command if not active else None
        return command

    if action.endswith("_RESET"):
        target = action.replace("_RESET", "")
        reset_cmd = f"{target}:RESET"
        if mode == "level":
            return reset_cmd if active else None
        if mode == "rising":
            return reset_cmd if active else None
        if mode == "falling":
            return reset_cmd if not active else None
        return reset_cmd

    if mode == "level":
        return f"{action}:{'ON' if active else 'OFF'}"
    if mode == "rising":
        return f"{action}:TOGGLE" if active else None
    if mode == "falling":
        return f"{action}:TOGGLE" if not active else None
    return f"{action}:TOGGLE"


class GpioInputHandle(Protocol):
    """One watched GPIO input."""

    when_pressed: Optional[Callable[[], None]]
    when_released: Optional[Callable[[], None]]

    def close(self) -> None:
        """Release the pin."""


class GpioBackend(Protocol):
    """Opens GPIO inputs. Tests inject a fake backend."""

    def open_input(self, pin: int, invert: bool, bounce_time: float) -> GpioInputHandle:
        """Watch pin; pressed means logical active after invert."""


@dataclass
class FakeGpioLine:
    """In-memory GPIO line for tests."""

    pin: int
    invert: bool
    when_pressed: Optional[Callable[[], None]] = None
    when_released: Optional[Callable[[], None]] = None
    _raw_high: bool = True
    closed: bool = False

    def __post_init__(self) -> None:
        self._raw_high = self.invert

    def close(self) -> None:
        self.closed = True
        self.when_pressed = None
        self.when_released = None

    def set_raw_high(self, high: bool) -> None:
        """Drive the electrical level and fire the matching callback."""
        if self.closed:
            return
        self._raw_high = bool(high)
        active = logical_active(self._raw_high, self.invert)
        callback = self.when_pressed if active else self.when_released
        if callback is not None:
            callback()


class FakeGpioBackend:
    """Test backend that records opened pins and exposes FakeGpioLine objects."""

    def __init__(self) -> None:
        self.lines: dict[int, FakeGpioLine] = {}

    def open_input(self, pin: int, invert: bool, bounce_time: float) -> FakeGpioLine:
        line = FakeGpioLine(pin=pin, invert=invert)
        self.lines[pin] = line
        return line

    def close_all(self) -> None:
        for line in self.lines.values():
            line.close()
        self.lines.clear()


class GpioZeroBackend:
    """gpiozero Button backend for Raspberry Pi hardware."""

    def open_input(self, pin: int, invert: bool, bounce_time: float) -> GpioInputHandle:
        if not GPIOZERO_AVAILABLE or GpioZeroButton is None:
            raise RuntimeError("gpiozero is not available")
        bounce = bounce_time if bounce_time > 0 else None
        button = GpioZeroButton(pin, pull_up=invert, bounce_time=bounce)
        return button  # type: ignore[return-value]


@dataclass
class GpioChannelConfig:
    """One configured GPIO input channel."""

    index: int
    enabled: bool = False
    pin: int = 17
    invert: bool = True
    mode: str = "level"
    action: str = "LED1"
    command: str = ""


@dataclass
class GpioConfig:
    """GPIO settings snapshot."""

    enabled: bool = False
    debounce_ms: int = DEFAULT_GPIO_DEBOUNCE_MS
    channels: list[GpioChannelConfig] = field(default_factory=list)


def _coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    if value is None:
        return default
    return bool(value)


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sanitize_pin(pin: int) -> int:
    if pin in GPIO_SAFE_BCM_PINS:
        return pin
    return GPIO_SAFE_BCM_PINS[0]


def _sanitize_mode(mode: str) -> str:
    mode = (mode or "").strip().lower()
    return mode if mode in GPIO_MODES else "level"


def _sanitize_action(action: str) -> str:
    action = (action or "").strip()
    return action if action in GPIO_ACTIONS else "LED1"


def read_gpio_config(settings: Optional[QSettings] = None) -> GpioConfig:
    """Load GPIO settings from QSettings."""
    settings = settings or QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
    with settings_group(settings, "GPIO"):
        enabled = _coerce_bool(settings.value("enabled", DEFAULT_GPIO_ENABLED), DEFAULT_GPIO_ENABLED)
        debounce_ms = max(
            0,
            _coerce_int(settings.value("debounce_ms", DEFAULT_GPIO_DEBOUNCE_MS), DEFAULT_GPIO_DEBOUNCE_MS),
        )
        channels: list[GpioChannelConfig] = []
        for index in range(1, GPIO_CHANNEL_COUNT + 1):
            defaults = default_gpio_channel(index)
            channels.append(
                GpioChannelConfig(
                    index=index,
                    enabled=_coerce_bool(
                        settings.value(gpio_setting_key(index, "enabled"), defaults["enabled"]),
                        defaults["enabled"],
                    ),
                    pin=_sanitize_pin(
                        _coerce_int(
                            settings.value(gpio_setting_key(index, "pin"), defaults["pin"]),
                            defaults["pin"],
                        )
                    ),
                    invert=_coerce_bool(
                        settings.value(gpio_setting_key(index, "invert"), defaults["invert"]),
                        defaults["invert"],
                    ),
                    mode=_sanitize_mode(
                        str(settings.value(gpio_setting_key(index, "mode"), defaults["mode"]) or defaults["mode"])
                    ),
                    action=_sanitize_action(
                        str(
                            settings.value(gpio_setting_key(index, "action"), defaults["action"])
                            or defaults["action"]
                        )
                    ),
                    command=str(
                        settings.value(gpio_setting_key(index, "command"), defaults["command"]) or ""
                    ).strip(),
                )
            )
    return GpioConfig(enabled=enabled, debounce_ms=debounce_ms, channels=channels)


class GpioManager(QObject):
    """
    Watch Raspberry Pi GPIO inputs and dispatch OnAirScreen API commands.

    gpiozero callbacks run off the Qt thread; commands are emitted via a
    queued Signal so parse_cmd always runs on the GUI thread.
    """

    command_received = Signal(bytes)
    status_changed = Signal(str)

    def __init__(
        self,
        main_screen: Optional["MainScreen"] = None,
        backend: Optional[GpioBackend] = None,
        platform_available: Optional[bool] = None,
        library_available: Optional[bool] = None,
    ) -> None:
        super().__init__()
        self.main_screen = main_screen
        self._injected_backend = backend
        self._backend: Optional[GpioBackend] = backend
        self._platform_available = (
            is_raspberry_pi() if platform_available is None else platform_available
        )
        self._library_available = (
            GPIOZERO_AVAILABLE if library_available is None else library_available
        )
        self._handles: list[GpioInputHandle] = []
        self._last_event_time: dict[int, float] = {}
        self._last_active: dict[int, Optional[bool]] = {}
        self._channels: dict[int, GpioChannelConfig] = {}
        self._debounce_s = DEFAULT_GPIO_DEBOUNCE_MS / 1000.0
        self._status = gpio_status_message(
            self._platform_available, self._library_available, enabled=False
        )
        self.command_received.connect(self._dispatch_command)

    @property
    def status(self) -> str:
        return self._status

    def start(self, settings: Optional[QSettings] = None) -> None:
        """Open configured pins according to current settings."""
        self.stop()
        config = read_gpio_config(settings)
        self._debounce_s = max(0, config.debounce_ms) / 1000.0
        self._channels = {channel.index: channel for channel in config.channels}

        if not config.enabled:
            self._set_status(
                gpio_status_message(
                    self._platform_available, self._library_available, enabled=False
                )
            )
            return

        backend = self._resolve_backend()
        if backend is None:
            return

        opened = 0
        used_pins: set[int] = set()
        for channel in config.channels:
            if not channel.enabled:
                continue
            if channel.pin in used_pins:
                logger.warning(
                    "GPIO GPI%s skipped: BCM pin %s already used",
                    channel.index,
                    channel.pin,
                )
                continue
            try:
                bounce = self._debounce_s if self._injected_backend is None else 0.0
                handle = backend.open_input(channel.pin, channel.invert, bounce)
            except Exception as exc:
                logger.warning(
                    "GPIO GPI%s on BCM %s could not be opened: %s",
                    channel.index,
                    channel.pin,
                    exc,
                )
                continue
            index = channel.index
            handle.when_pressed = lambda idx=index: self._on_edge(idx, True)
            handle.when_released = lambda idx=index: self._on_edge(idx, False)
            self._handles.append(handle)
            used_pins.add(channel.pin)
            opened += 1
            logger.info(
                "GPIO GPI%s watching BCM %s → %s (%s)",
                channel.index,
                channel.pin,
                channel.action,
                channel.mode,
            )

        if opened:
            self._set_status(f"GPIO active ({opened} input{'s' if opened != 1 else ''}).")
        else:
            self._set_status("GPIO enabled, but no inputs could be opened.")

    def stop(self) -> None:
        """Close all GPIO handles."""
        for handle in self._handles:
            try:
                handle.close()
            except Exception as exc:
                logger.debug("GPIO handle close failed: %s", exc)
        self._handles.clear()
        self._last_event_time.clear()
        self._last_active.clear()
        if isinstance(self._injected_backend, FakeGpioBackend):
            self._injected_backend.close_all()

    def restart(self) -> None:
        """Re-read settings and reopen pins."""
        self.start()

    def _resolve_backend(self) -> Optional[GpioBackend]:
        if self._injected_backend is not None:
            return self._injected_backend
        if not self._platform_available:
            self._set_status(
                gpio_status_message(False, self._library_available, enabled=True)
            )
            return None
        if not self._library_available:
            self._set_status(
                gpio_status_message(True, False, enabled=True)
            )
            return None
        try:
            self._backend = GpioZeroBackend()
            return self._backend
        except Exception as exc:
            logger.warning("GPIO backend could not be created: %s", exc)
            self._set_status("GPIO backend failed to start.")
            return None

    def _on_edge(self, index: int, active: bool) -> None:
        last_active = self._last_active.get(index)
        if last_active is not None and last_active is active:
            return
        now = time.monotonic()
        last_time = self._last_event_time.get(index, 0.0)
        if self._debounce_s > 0 and (now - last_time) < self._debounce_s:
            return
        self._last_event_time[index] = now
        self._last_active[index] = active
        channel = self._channels.get(index)
        if channel is None:
            return
        command = command_for_event(channel.action, channel.mode, active, channel.command)
        if not command:
            return
        logger.debug("GPIO GPI%s %s → %s", index, "closed" if active else "open", command)
        self.command_received.emit(command.encode("utf-8"))

    def _dispatch_command(self, data: bytes) -> None:
        if self.main_screen is None:
            return
        parse = getattr(self.main_screen, "_parse_cmd_with_source", None)
        if callable(parse):
            parse(data, "gpio")
            return
        self.main_screen.parse_cmd(data)

    def _set_status(self, text: str) -> None:
        self._status = text
        self.status_changed.emit(text)
        logger.info("GPIO: %s", text)
