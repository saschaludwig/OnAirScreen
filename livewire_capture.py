#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# livewire_capture.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Receive Axia Livewire AoIP streams (RTP multicast L24/48kHz/stereo) for metering.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from aoip_rtp import (  # noqa: F401
    DEFAULT_BLOCK_FRAMES,
    CODEC_L24,
    MulticastRtpReceiver,
    decode_l24_stereo,
    list_ipv4_interfaces,
    parse_rtp_payload,
)
from livewire_address import (
    LIVEWIRE_CHANNELS,
    LIVEWIRE_RTP_PORT,
    LIVEWIRE_SAMPLE_RATE,
    channel_to_multicast,
    validate_channel,
)


class LivewireReceiver(MulticastRtpReceiver):
    """Multicast RTP receiver bound to a Livewire channel number."""

    def __init__(
        self,
        channel: int,
        on_frames: Callable[[np.ndarray], None],
        iface: str = "",
        block_frames: int = DEFAULT_BLOCK_FRAMES,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._channel = validate_channel(channel)
        super().__init__(
            multicast=channel_to_multicast(self._channel),
            port=LIVEWIRE_RTP_PORT,
            on_frames=on_frames,
            iface=iface,
            codec=CODEC_L24,
            channels=LIVEWIRE_CHANNELS,
            sample_rate=LIVEWIRE_SAMPLE_RATE,
            block_frames=block_frames,
            on_error=on_error,
            log_name="Livewire",
        )

    @property
    def channel(self) -> int:
        return self._channel
