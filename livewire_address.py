#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# livewire_address.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Axia Livewire channel number <-> multicast address helpers.

Standard Livewire audio streams use RTP/UDP on port 5004 with multicast
addresses derived from 239.192.0.0 + channel number.
"""

from __future__ import annotations

import ipaddress
from typing import Final

LIVEWIRE_RTP_PORT: Final[int] = 5004
LIVEWIRE_MULTICAST_BASE: Final[int] = 0xEFC00000  # 239.192.0.0
LIVEWIRE_CHANNEL_MIN: Final[int] = 1
LIVEWIRE_CHANNEL_MAX: Final[int] = 32767
LIVEWIRE_SAMPLE_RATE: Final[int] = 48000
LIVEWIRE_CHANNELS: Final[int] = 2


class LivewireAddressError(ValueError):
    """Invalid Livewire channel number or multicast address."""


def validate_channel(channel: int) -> int:
    """Return channel if it is in the valid Livewire range."""
    try:
        value = int(channel)
    except (TypeError, ValueError) as exc:
        raise LivewireAddressError(f"Invalid Livewire channel: {channel!r}") from exc
    if value < LIVEWIRE_CHANNEL_MIN or value > LIVEWIRE_CHANNEL_MAX:
        raise LivewireAddressError(
            f"Livewire channel must be {LIVEWIRE_CHANNEL_MIN}–{LIVEWIRE_CHANNEL_MAX}, got {value}"
        )
    return value


def channel_to_multicast(channel: int) -> str:
    """
    Convert a Livewire channel number to its standard multicast IPv4 address.

    Examples:
        27 -> 239.192.0.27
        1212 -> 239.192.4.188
    """
    value = validate_channel(channel)
    addr_int = LIVEWIRE_MULTICAST_BASE + value
    return str(ipaddress.IPv4Address(addr_int))


def multicast_to_channel(ip: str) -> int:
    """
    Convert a standard Livewire multicast address back to a channel number.

    Raises LivewireAddressError if the address is not in the Livewire base range
    or the resulting channel is out of range.
    """
    try:
        addr = ipaddress.IPv4Address(ip)
    except (ipaddress.AddressValueError, ValueError) as exc:
        raise LivewireAddressError(f"Invalid IPv4 address: {ip!r}") from exc

    addr_int = int(addr)
    if addr_int < LIVEWIRE_MULTICAST_BASE:
        raise LivewireAddressError(f"Address {ip} is below Livewire base 239.192.0.0")

    channel = addr_int - LIVEWIRE_MULTICAST_BASE
    return validate_channel(channel)
