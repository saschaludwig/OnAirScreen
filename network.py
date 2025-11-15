#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# network.py
# This file is part of OnAirScreen
#
# You may use this file under the terms of the BSD license as follows:
#
# "Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
#
#############################################################################

"""
Network Module for OnAirScreen

This module handles UDP and HTTP network communication for receiving commands.
"""

import logging
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote_plus

from PyQt6.QtCore import QThread, QSettings
from PyQt6.QtNetwork import QUdpSocket, QHostAddress

from utils import settings_group
from settings_functions import versionString

logger = logging.getLogger(__name__)

HOST = '0.0.0.0'


class UdpServer:
    """
    UDP Server for receiving commands via multicast/unicast
    
    Handles UDP socket setup, multicast group joining, and command reception.
    """
    
    def __init__(self, command_callback):
        """
        Initialize UDP server
        
        Args:
            command_callback: Callback function to handle received commands (takes bytes)
        """
        self.command_callback = command_callback
        self.udpsock = QUdpSocket()
        self._setup_socket()
    
    def _setup_socket(self) -> None:
        """Setup UDP socket and join multicast group"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Network"):
            try:
                port = int(settings.value('udpport', "3310"))
            except ValueError:
                port = "3310"
                settings.setValue('udpport', "3310")
            multicast_address = settings.value('multicast_address', "239.194.0.1")
            if not QHostAddress(multicast_address).isMulticast():
                multicast_address = "239.194.0.1"
                settings.setValue('multicast_address', "239.194.0.1")

        self.udpsock.bind(QHostAddress.SpecialAddress.AnyIPv4, int(port), QUdpSocket.BindFlag.ShareAddress)
        if QHostAddress(multicast_address).isMulticast():
            logger.info(f"{multicast_address} is Multicast, joining multicast group")
            self.udpsock.joinMulticastGroup(QHostAddress(multicast_address))
        self.udpsock.readyRead.connect(self._handle_udp_data)
    
    def _handle_udp_data(self) -> None:
        """Handle incoming UDP datagrams"""
        while self.udpsock.hasPendingDatagrams():
            data, host, port = self.udpsock.readDatagram(self.udpsock.pendingDatagramSize())
            lines = data.splitlines()
            for line in lines:
                # Mark command source as UDP for logging
                if hasattr(self.command_callback, '__self__'):
                    # If callback is a method, we need to pass source info differently
                    # For now, we'll handle it in parse_cmd
                    self.command_callback(line)
                else:
                    self.command_callback(line)


class HttpDaemon(QThread):
    """
    HTTP server thread for handling HTTP-based commands
    
    Runs a simple HTTP server that accepts GET requests with commands
    and forwards them to the UDP command handler.
    """
    
    def run(self):
        """Start HTTP server"""
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Network"):
            try:
                port = int(settings.value('httpport', "8010"))
            except ValueError:
                port = 8010
                settings.setValue("httpport", "8010")

        try:
            handler = OASHTTPRequestHandler
            self._server = HTTPServer((HOST, port), handler)
            self._server.serve_forever()
        except OSError as error:
            logger.error(f"ERROR: Starting HTTP Server on port {port}: {error}")

    def stop(self):
        """Stop HTTP server"""
        self._server.shutdown()
        self._server.socket.close()
        self.wait()


class OASHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for OnAirScreen commands
    
    Handles GET requests with command parameters and forwards them
    to the UDP command handler.
    """
    server_version = f"OnAirScreen/{versionString}"

    def do_HEAD(self):
        """Handle HEAD request"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        """Handle GET request with command"""
        logger.debug(f"HTTP request path: {self.path}")
        if self.path.startswith('/?cmd'):
            try:
                # Parse the query string: /?cmd=COMMAND:VALUE
                # First split to get cmd=COMMAND:VALUE
                query_string = str(self.path)[5:]  # Remove '/?cmd'
                if '=' in query_string:
                    cmd, message = query_string.split("=", 1)
                    # URL-decode the message part (value after =)
                    # unquote_plus also decodes + signs to spaces
                    message = unquote_plus(message)
                else:
                    self.send_error(400, 'no command was given')
                    return
            except ValueError:
                self.send_error(400, 'no command was given')
                return

            if len(message) > 0:
                self.send_response(200)

                # send header first
                self.send_header('Content-type', 'text-html; charset=utf-8')
                self.end_headers()

                settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
                with settings_group(settings, "Network"):
                    port = int(settings.value('udpport', "3310"))

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(message.encode(), ("127.0.0.1", port))

                # send file content to client
                self.wfile.write(message.encode())
                self.wfile.write("\n".encode())
                return
            else:
                self.send_error(400, 'no command was given')
                return

        self.send_error(404, 'file not found')

