#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# oas_osc_send.py
# This file is part of OnAirScreen
#
# Send an OSC message to OnAirScreen (set or query).
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

import argparse

from pythonosc.udp_client import SimpleUDPClient

parser = argparse.ArgumentParser(description="Send an OSC message to OnAirScreen.")
parser.add_argument(
    "-i", "--ip", type=str, default="127.0.0.1",
    help="OnAirScreen target IP (default: 127.0.0.1)",
)
parser.add_argument(
    "-p", "--port", type=int, default=8000,
    help="OnAirScreen OSC listen port (default: 8000)",
)
parser.add_argument("-s", "--silent", action="store_true", help="Do not print send details")
parser.add_argument("address", type=str, help="OSC address, e.g. /oas/led1")
parser.add_argument(
    "value", nargs="?", default=None,
    help="Optional OSC argument (int, float, or string). Omit for toggle/query.",
)
args = parser.parse_args()


def parse_value(raw: str):
    """Parse a CLI value as int, float, or string."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


client = SimpleUDPClient(args.ip, args.port)
if args.value is None:
    payload = None
    if not args.silent:
        print(f"IP: {args.ip} | PORT: {args.port} | Address: {args.address}")
    client.send_message(args.address, [])
else:
    payload = parse_value(args.value)
    if not args.silent:
        print(f"IP: {args.ip} | PORT: {args.port} | Address: {args.address} | Value: {payload}")
    client.send_message(args.address, payload)
