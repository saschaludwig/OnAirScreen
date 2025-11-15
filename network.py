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

import json
import logging
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote_plus, urlparse, parse_qs

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
    
    def __init__(self, main_screen=None, command_signal=None):
        """
        Initialize HTTP daemon
        
        Args:
            main_screen: Reference to MainScreen instance for status queries (optional)
            command_signal: Signal object for thread-safe command execution (optional)
        """
        super().__init__()
        self.main_screen = main_screen
        self.command_signal = command_signal
    
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
            # Pass main_screen reference and command_signal to handler class
            OASHTTPRequestHandler.main_screen = self.main_screen
            OASHTTPRequestHandler.command_signal = self.command_signal
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
    HTTP request handler for OnAirScreen commands and Web-UI
    
    Handles GET requests with command parameters and forwards them
    to the UDP command handler. Also serves the Web-UI and API endpoints.
    """
    server_version = f"OnAirScreen/{versionString}"
    main_screen = None  # Will be set by HttpDaemon
    command_signal = None  # Will be set by HttpDaemon

    def log_message(self, format, *args):
        """
        Override log_message to use different log levels based on path
        
        /api/status requests are logged at DEBUG level to reduce noise
        """
        # Check if this is a /api/status request by checking the path
        if hasattr(self, 'path') and '/api/status' in self.path:
            logger.debug(f"{self.address_string()} - {format % args}")
        elif len(args) > 0 and '/api/status' in str(args[0]):
            logger.debug(f"{self.address_string()} - {format % args}")
        else:
            # Use INFO level for other requests
            logger.info(f"{self.address_string()} - {format % args}")

    def do_HEAD(self):
        """Handle HEAD request"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        """Handle GET request with command, API, or Web-UI"""
        logger.debug(f"HTTP request path: {self.path}")
        
        # Parse URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API endpoint for status
        if path == '/api/status':
            self._handle_api_status()
            return
        
        # API endpoint for commands (REST-style)
        if path == '/api/command':
            self._handle_api_command(parsed_path.query)
            return
        
        # API endpoint for command (backward compatible)
        if path == '/' and parsed_path.query and parsed_path.query.startswith('cmd='):
            self._handle_command_api(parsed_path.query)
            return
        
        # Legacy command format: /?cmd=...
        if self.path.startswith('/?cmd'):
            query_string = str(self.path)[5:]  # Remove '/?cmd'
            self._handle_command_api(query_string)
            return
        
        # Web-UI
        if path == '/' or path == '/index.html':
            self._handle_web_ui()
            return
        
        self.send_error(404, 'file not found')
    
    def _handle_command_api(self, query_string: str) -> None:
        """Handle command API request (backward compatible)"""
        try:
            if '=' in query_string:
                cmd, message = query_string.split("=", 1)
                # URL-decode the message part (value after =)
                message = unquote_plus(message)
            else:
                self.send_error(400, 'no command was given')
                return
        except ValueError:
            self.send_error(400, 'no command was given')
            return

        if len(message) > 0:
            # Forward command directly to MainScreen if available
            if self.command_signal:
                try:
                    # Use signal to execute command in GUI thread
                    command_bytes = message.encode('utf-8')
                    self.command_signal.command_received.emit(command_bytes, "http")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'ok', 'command': message}).encode('utf-8'))
                    return
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    self.send_error(500, f'Error processing command: {str(e)}')
                    return
            
            # Fallback to UDP forwarding if MainScreen not available
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "Network"):
                try:
                    port = int(settings.value('udpport', "3310"))
                except (ValueError, TypeError):
                    logger.warning("Invalid UDP port in settings, using default 3310")
                    port = 3310

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), ("127.0.0.1", port))
            sock.close()

            # send file content to client
            self.wfile.write(message.encode())
            self.wfile.write("\n".encode())
        else:
            self.send_error(400, 'no command was given')
    
    def _handle_api_command(self, query_string: str) -> None:
        """Handle API command request (REST-style) - returns JSON"""
        try:
            # Parse query string: ?cmd=COMMAND:VALUE
            if not query_string or 'cmd=' not in query_string:
                self.send_error(400, 'Missing cmd parameter')
                return
            
            cmd, message = query_string.split("cmd=", 1)
            if cmd:  # There's something before cmd=
                # Handle case like ?cmd=LED1:ON
                message = query_string.split("cmd=", 1)[1]
            
            # URL-decode the message part
            message = unquote_plus(message)
            
            if not message:
                self.send_error(400, 'Empty command')
                return

            # Forward command directly to MainScreen if available
            if self.command_signal:
                try:
                    # Use signal to execute command in GUI thread
                    command_bytes = message.encode('utf-8')
                    self.command_signal.command_received.emit(command_bytes, "http")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'ok', 'command': message}).encode('utf-8'))
                    return
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    self.send_error(500, f'Error processing command: {str(e)}')
                    return
            
            # Fallback to UDP forwarding if MainScreen not available
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "Network"):
                try:
                    port = int(settings.value('udpport', "3310"))
                except (ValueError, TypeError):
                    logger.warning("Invalid UDP port in settings, using default 3310")
                    port = 3310

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), ("127.0.0.1", port))
            sock.close()

            self.wfile.write(json.dumps({'status': 'ok', 'command': message, 'method': 'udp_fallback'}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error in API command handler: {e}")
            self.send_error(500, f'Error processing command: {str(e)}')
    
    def _handle_api_status(self) -> None:
        """Handle API status request - returns JSON with current status"""
        if not self.main_screen:
            self.send_error(503, 'MainScreen not available')
            return
        
        try:
            status = self.main_screen.get_status_json()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            self.send_error(500, f'Error getting status: {str(e)}')
    
    def _handle_web_ui(self) -> None:
        """Handle Web-UI request - serves HTML interface"""
        html_content = self._get_web_ui_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _get_web_ui_html(self) -> str:
        """Load HTML content for Web-UI from template file"""
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'templates', 'web_ui.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Web UI template not found at {template_path}")
            return "<html><body><h1>Error: Web UI template not found</h1></body></html>"
        except Exception as e:
            logger.error(f"Error loading Web UI template: {e}")
            return f"<html><body><h1>Error loading Web UI: {e}</h1></body></html>"
