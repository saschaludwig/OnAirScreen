#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for livewire_address.py
"""

import pytest

from livewire_address import (
    LIVEWIRE_CHANNEL_MAX,
    LIVEWIRE_CHANNEL_MIN,
    LIVEWIRE_RTP_PORT,
    LivewireAddressError,
    channel_to_multicast,
    multicast_to_channel,
    validate_channel,
)


class TestValidateChannel:
    def test_valid_bounds(self):
        assert validate_channel(LIVEWIRE_CHANNEL_MIN) == 1
        assert validate_channel(LIVEWIRE_CHANNEL_MAX) == 32767

    def test_out_of_range(self):
        with pytest.raises(LivewireAddressError):
            validate_channel(0)
        with pytest.raises(LivewireAddressError):
            validate_channel(32768)

    def test_invalid_type(self):
        with pytest.raises(LivewireAddressError):
            validate_channel("abc")


class TestChannelToMulticast:
    def test_channel_27(self):
        assert channel_to_multicast(27) == "239.192.0.27"

    def test_channel_1212(self):
        assert channel_to_multicast(1212) == "239.192.4.188"

    def test_channel_1(self):
        assert channel_to_multicast(1) == "239.192.0.1"

    def test_channel_9999(self):
        # 9999 = 0x270F -> 239.192.39.15
        assert channel_to_multicast(9999) == "239.192.39.15"

    def test_rejects_invalid(self):
        with pytest.raises(LivewireAddressError):
            channel_to_multicast(0)


class TestMulticastToChannel:
    def test_roundtrip(self):
        for channel in (1, 27, 1212, 9999, 32767):
            assert multicast_to_channel(channel_to_multicast(channel)) == channel

    def test_rejects_below_base(self):
        with pytest.raises(LivewireAddressError):
            multicast_to_channel("239.191.255.255")

    def test_rejects_invalid_ip(self):
        with pytest.raises(LivewireAddressError):
            multicast_to_channel("not-an-ip")


class TestConstants:
    def test_rtp_port(self):
        assert LIVEWIRE_RTP_PORT == 5004
