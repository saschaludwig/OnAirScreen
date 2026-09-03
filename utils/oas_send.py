#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# oas_send.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

import argparse
import socket

parser = argparse.ArgumentParser(description='Send an UDP API command to OnAirScreen.')
parser.add_argument("-i", "--ip", type=str, help="OnAirScreen target IP (default: 127.0.0.1)", default="127.0.0.1")
parser.add_argument("-p", "--port", type=int, help="OnAirScreen target port (default: 3310)", default="3310")
parser.add_argument("-s", "--silent", help="do not print any information, except for errors", action='store_true')
parser.add_argument('message', type=str, help="API message to send")
args = parser.parse_args()

UDP_IP = args.ip
UDP_PORT = args.port
MESSAGE = args.message

if not args.silent:
    print("IP:", UDP_IP, "| PORT:", UDP_PORT, "| Message:", MESSAGE)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(bytes(MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
