#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
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
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Callable, TYPE_CHECKING, Set
from urllib.parse import unquote_plus, urlparse, parse_qs

from PyQt6.QtCore import QThread, QSettings, pyqtSignal, QObject
from PyQt6.QtNetwork import QUdpSocket, QHostAddress

from utils import settings_group
from settings_functions import versionString
from defaults import DEFAULT_UDP_PORT, DEFAULT_HTTP_PORT, DEFAULT_MULTICAST_ADDRESS
from exceptions import (
    UdpError, HttpError, WebSocketError, PortInUseError, PermissionDeniedError,
    CommandParseError, InvalidCommandFormatError, EncodingError, JsonSerializationError, log_exception
)

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.server import ServerConnection
    from websockets.exceptions import ConnectionClosed
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    ServerConnection = None  # type: ignore
    logger.warning("websockets library not available. WebSocket support will be disabled.")

HOST = '0.0.0.0'


class ReusableHTTPServer(HTTPServer):
    """
    HTTP Server with SO_REUSEADDR

    """
    def server_bind(self) -> None:
        """Override server_bind to set SO_REUSEADDR before binding"""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


class UdpServer:
    """
    UDP Server for receiving commands via multicast/unicast
    
    Handles UDP socket setup, multicast group joining, and command reception.
    """
    
    def __init__(self, command_callback: Callable[[bytes], None]) -> None:
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
                port = int(settings.value('udpport', str(DEFAULT_UDP_PORT)))
                if port < 1 or port > 65535:
                    logger.warning(f"Invalid UDP port {port}, using default {DEFAULT_UDP_PORT}")
                    port = DEFAULT_UDP_PORT
                    settings.setValue('udpport', str(DEFAULT_UDP_PORT))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing UDP port: {e}, using default {DEFAULT_UDP_PORT}")
                port = DEFAULT_UDP_PORT
                settings.setValue('udpport', str(DEFAULT_UDP_PORT))
            
            multicast_address = settings.value('multicast_address', DEFAULT_MULTICAST_ADDRESS)
            if not QHostAddress(multicast_address).isMulticast():
                logger.warning(f"Invalid multicast address {multicast_address}, using default {DEFAULT_MULTICAST_ADDRESS}")
                multicast_address = DEFAULT_MULTICAST_ADDRESS
                settings.setValue('multicast_address', DEFAULT_MULTICAST_ADDRESS)

        try:
            bind_result = self.udpsock.bind(QHostAddress.SpecialAddress.AnyIPv4, int(port), QUdpSocket.BindFlag.ShareAddress)
            if not bind_result:
                error_msg = f"Failed to bind UDP socket to port {port}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info(f"UDP socket bound to port {port}")
        except Exception as e:
            from exceptions import OnAirScreenError, UdpError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
                raise
            else:
                error = UdpError(f"Error binding UDP socket to port {port}: {e}")
                log_exception(logger, error)
                raise error
        
        if QHostAddress(multicast_address).isMulticast():
            try:
                from PyQt6.QtNetwork import QNetworkInterface
                interfaces = QNetworkInterface.allInterfaces()
                
                # Strategy: Join multicast group on multiple interfaces
                # 1. Join on loopback interface (for localhost testing)
                # 2. Join on all active non-loopback interfaces (for network multicast)
                loopback_interface = None
                active_interfaces = []
                
                for iface in interfaces:
                    flags = iface.flags()
                    # Check if interface is up and running
                    if flags & QNetworkInterface.InterfaceFlag.IsUp and flags & QNetworkInterface.InterfaceFlag.IsRunning:
                        if flags & QNetworkInterface.InterfaceFlag.IsLoopBack:
                            loopback_interface = iface
                        else:
                            # Only add interfaces that have at least one IPv4 address
                            # Use toIPv4Address() to check if address is IPv4 (returns tuple: (address, is_valid))
                            for entry in iface.addressEntries():
                                ipv4_result = entry.ip().toIPv4Address()
                                if len(ipv4_result) == 2 and ipv4_result[1]:  # IPv4 and valid
                                    active_interfaces.append(iface)
                                    break
                
                join_success = False
                
                # First, try to join on loopback interface (for localhost testing)
                # On macOS, this is often required for multicast loopback to work
                if loopback_interface:
                    try:
                        loopback_join = self.udpsock.joinMulticastGroup(
                            QHostAddress(multicast_address), 
                            loopback_interface
                        )
                        if loopback_join:
                            logger.info(f"{multicast_address} is Multicast, joined multicast group on loopback interface {loopback_interface.name()}")
                            join_success = True
                        else:
                            logger.debug(f"Failed to join multicast group {multicast_address} on loopback interface {loopback_interface.name()}")
                    except Exception as loopback_error:
                        logger.debug(f"Error joining multicast on loopback interface: {loopback_error}")
                
                # Then, join on all active network interfaces (for network multicast)
                for iface in active_interfaces:
                    try:
                        network_join = self.udpsock.joinMulticastGroup(
                            QHostAddress(multicast_address),
                            iface
                        )
                        if network_join:
                            logger.info(f"{multicast_address} is Multicast, joined multicast group on interface {iface.name()}")
                            join_success = True
                        else:
                            logger.debug(f"Failed to join multicast group {multicast_address} on interface {iface.name()}")
                    except Exception as iface_error:
                        logger.debug(f"Error joining multicast on interface {iface.name()}: {iface_error}")
                
                # Fallback: If no explicit interface joins worked, try default join
                # This joins on the default interface (usually the primary network interface)
                if not join_success:
                    logger.debug(f"No explicit interface joins succeeded, trying default join...")
                    default_join = self.udpsock.joinMulticastGroup(QHostAddress(multicast_address))
                    if default_join:
                        logger.info(f"{multicast_address} is Multicast, joined multicast group (default)")
                        join_success = True
                    else:
                        logger.warning(f"Failed to join multicast group {multicast_address} on any interface, continuing without multicast")
                elif not loopback_interface and not active_interfaces:
                    # If we have no interfaces but join_success is True, something unexpected happened
                    logger.warning(f"Multicast join reported success but no suitable interfaces found")
            except Exception as e:
                logger.warning(f"Error joining multicast group {multicast_address}: {e}, continuing without multicast")
        
        self.udpsock.readyRead.connect(self._handle_udp_data)
    
    def _handle_udp_data(self) -> None:
        """Handle incoming UDP datagrams"""
        try:
            while self.udpsock.hasPendingDatagrams():
                try:
                    pending_size = self.udpsock.pendingDatagramSize()
                    if pending_size <= 0:
                        logger.warning("Invalid UDP datagram size, skipping")
                        break
                    
                    data, host, port = self.udpsock.readDatagram(pending_size)
                    logger.info(f"Received UDP datagram from {host.toString()}:{port}, size: {len(data)} bytes, content: {data!r}")
                    if not data:
                        logger.debug("Received empty UDP datagram, skipping")
                        continue
                    
                    lines = data.splitlines()
                    for line in lines:
                        if not line:
                            continue
                        try:
                            # Mark command source as UDP for logging
                            if hasattr(self.command_callback, '__self__'):
                                # If callback is a method, we need to pass source info differently
                                # For now, we'll handle it in parse_cmd
                                self.command_callback(line)
                            else:
                                self.command_callback(line)
                        except Exception as callback_error:
                            error = CommandParseError(
                                f"Error in UDP command callback from {host}:{port}",
                                command_data=str(line) if line else None
                            )
                            log_exception(logger, error, {"host": str(host), "port": port})
                except OSError as socket_error:
                    error = UdpError(f"Socket error reading UDP datagram: {socket_error}")
                    log_exception(logger, error)
                    break
                except Exception as read_error:
                    error = UdpError(f"Error reading UDP datagram: {read_error}")
                    log_exception(logger, error)
                    break
        except Exception as e:
            error = UdpError(f"Unexpected error in UDP data handler: {e}")
            log_exception(logger, error)


class HttpDaemon(QThread):
    """
    HTTP server thread for handling HTTP-based commands
    
    Runs a simple HTTP server that accepts GET requests with commands
    and forwards them to the UDP command handler.
    """
    
    def __init__(self, main_screen: Optional["MainScreen"] = None, command_signal: Optional[object] = None) -> None:
        """
        Initialize HTTP daemon
        
        Args:
            main_screen: Reference to MainScreen instance for status queries (optional)
            command_signal: Signal object for thread-safe command execution (optional)
        """
        super().__init__()
        self.main_screen = main_screen
        self.command_signal = command_signal
    
    def run(self) -> None:
        """
        Start HTTP server in a separate thread
        
        Raises:
            OSError: If port is already in use or permission denied
            socket.error: If socket error occurs
        """
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Network"):
            try:
                port = int(settings.value('httpport', str(DEFAULT_HTTP_PORT)))
                if port < 1 or port > 65535:
                    logger.warning(f"Invalid HTTP port {port}, using default {DEFAULT_HTTP_PORT}")
                    port = DEFAULT_HTTP_PORT
                    settings.setValue("httpport", str(DEFAULT_HTTP_PORT))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing HTTP port: {e}, using default {DEFAULT_HTTP_PORT}")
                port = DEFAULT_HTTP_PORT
                settings.setValue("httpport", str(DEFAULT_HTTP_PORT))

        try:
            # Pass main_screen reference and command_signal to handler class
            OASHTTPRequestHandler.main_screen = self.main_screen
            OASHTTPRequestHandler.command_signal = self.command_signal
            handler = OASHTTPRequestHandler
            # Use ReusableHTTPServer to prevent TIME_WAIT issues
            self._server = ReusableHTTPServer((HOST, port), handler)
            
            logger.info(f"HTTP server started on {HOST}:{port}")
            self._server.serve_forever()
        except OSError as error:
            if error.errno == 98 or "Address already in use" in str(error):
                port_error = PortInUseError(port, "TCP")
                log_exception(logger, port_error)
            elif error.errno == 13 or "Permission denied" in str(error):
                perm_error = PermissionDeniedError(port, "TCP")
                log_exception(logger, perm_error)
            else:
                http_error = HttpError(f"OS error starting HTTP Server on port {port}: {error}", status_code=500)
                log_exception(logger, http_error)
        except socket.error as socket_error:
            http_error = HttpError(f"Socket error starting HTTP Server on port {port}: {socket_error}", status_code=500)
            log_exception(logger, http_error)
        except Exception as error:
            http_error = HttpError(f"Unexpected error starting HTTP Server on port {port}: {error}", status_code=500)
            log_exception(logger, http_error)

    def stop(self) -> None:
        """
        Stop HTTP server gracefully
        
        Shuts down the server, closes the socket, and waits for the thread to finish.
        Handles errors gracefully to allow cleanup even if server wasn't fully initialized.
        """
        try:
            if hasattr(self, '_server') and self._server:
                try:
                    # Shutdown the server (stops serve_forever)
                    self._server.shutdown()
                except Exception as shutdown_error:
                    logger.warning(f"Error shutting down HTTP server: {shutdown_error}")
                
                try:
                    # Close the socket explicitly to prevent TIME_WAIT
                    if hasattr(self._server, 'socket') and self._server.socket:
                        self._server.socket.close()
                except Exception as close_error:
                    logger.warning(f"Error closing HTTP server socket: {close_error}")
                
                # Wait for thread to finish with timeout
                try:
                    if not self.wait(3000):  # Wait up to 3 seconds
                        logger.warning("HTTP server thread did not finish within timeout")
                        # Force terminate if still running
                        if self.isRunning():
                            self.terminate()
                            self.wait(1000)
                except Exception as wait_error:
                    logger.warning(f"Error waiting for HTTP server thread: {wait_error}")
            else:
                logger.debug("HTTP server not initialized, nothing to stop")
        except Exception as e:
            from exceptions import OnAirScreenError, NetworkError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = NetworkError(f"Unexpected error stopping HTTP server: {e}")
                log_exception(logger, error)


def _exception_to_http_status(exception: Exception) -> int:
    """
    Map exception types to HTTP status codes
    
    Args:
        exception: Exception to map
        
    Returns:
        HTTP status code
    """
    from exceptions import (
        CommandValidationError, TextValidationError, CommandParseError,
        InvalidCommandFormatError, UnknownCommandError, PortInUseError,
        PermissionDeniedError, JsonSerializationError, HttpError
    )
    
    if isinstance(exception, HttpError):
        return exception.status_code
    elif isinstance(exception, (CommandValidationError, TextValidationError, 
                                  CommandParseError, InvalidCommandFormatError)):
        return 400  # Bad Request
    elif isinstance(exception, UnknownCommandError):
        return 404  # Not Found
    elif isinstance(exception, (PortInUseError, PermissionDeniedError)):
        return 503  # Service Unavailable
    elif isinstance(exception, JsonSerializationError):
        return 500  # Internal Server Error
    else:
        return 500  # Internal Server Error


class OASHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for OnAirScreen commands and Web-UI
    
    Handles GET requests with command parameters and forwards them
    to the UDP command handler. Also serves the Web-UI and API endpoints.
    """
    server_version = f"OnAirScreen/{versionString}"
    main_screen = None  # Will be set by HttpDaemon
    command_signal = None  # Will be set by HttpDaemon

    def log_message(self, format: str, *args: object) -> None:
        """
        Override log_message to use different log levels based on path
        
        /api/status requests are logged at DEBUG level to reduce noise
        
        Args:
            format: Log message format string
            *args: Arguments for format string
        """
        # Check if this is a /api/status request by checking the path
        if hasattr(self, 'path') and '/api/status' in self.path:
            logger.debug(f"{self.address_string()} - {format % args}")
        elif len(args) > 0 and '/api/status' in str(args[0]):
            logger.debug(f"{self.address_string()} - {format % args}")
        else:
            # Use INFO level for other requests
            logger.info(f"{self.address_string()} - {format % args}")

    def do_HEAD(self) -> None:
        """
        Handle HEAD request
        
        Returns basic headers for CORS and content type checks.
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self) -> None:
        """
        Handle GET request with command, API, or Web-UI
        
        Routes requests to appropriate handlers:
        - /api/status -> Status API
        - /api/command -> Command API (REST-style)
        - /?cmd=... or /cmd=... -> Legacy command format
        - / or /index.html -> Web-UI
        - Other paths -> 404 error
        """
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
        """
        Handle command API request (backward compatible format)
        
        Processes commands in format "cmd=COMMAND:VALUE" and forwards them
        to the command handler via signal or UDP fallback.
        
        Args:
            query_string: Query string containing command (e.g., "cmd=LED1:ON")
            
        Note:
            Falls back to UDP forwarding if MainScreen/signal not available
        """
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
                    try:
                        command_bytes = message.encode('utf-8')
                    except UnicodeEncodeError as encode_error:
                        error = EncodingError(
                            f"Encoding error encoding command: {encode_error}",
                            encoding="utf-8",
                            data=message.encode('utf-8', errors='ignore') if message else None
                        )
                        log_exception(logger, error, use_exc_info=False)
                        status_code = _exception_to_http_status(error)
                        self.send_error(status_code, str(error))
                        return
                    
                    if not self.command_signal:
                        logger.error("Command signal not available")
                        self.send_error(503, 'Command signal not available')
                        return
                    
                    self.command_signal.command_received.emit(command_bytes, "http")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    try:
                        response_json = json.dumps({'status': 'ok', 'command': message})
                        self.wfile.write(response_json.encode('utf-8'))
                    except (TypeError, ValueError) as json_error:
                        error = JsonSerializationError(
                            f"JSON serialization error: {json_error}",
                            data={'status': 'ok', 'command': message}
                        )
                        log_exception(logger, error, use_exc_info=False)
                        status_code = _exception_to_http_status(error)
                        self.send_error(status_code, str(error))
                        return
                    except (OSError, BrokenPipeError) as write_error:
                        logger.warning(f"Error writing response to client: {write_error}")
                        # Client may have disconnected, which is not critical
                    return
                except Exception as e:
                    from exceptions import OnAirScreenError
                    if isinstance(e, OnAirScreenError):
                        log_exception(logger, e)
                        status_code = _exception_to_http_status(e)
                        self.send_error(status_code, str(e))
                    else:
                        # Wrap unexpected exceptions
                        error = HttpError(f"Error processing command: {e}", status_code=500)
                        log_exception(logger, error)
                        self.send_error(500, str(error))
                    return
            
            # Fallback to UDP forwarding if MainScreen not available
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "Network"):
                try:
                    port = int(settings.value('udpport', str(DEFAULT_UDP_PORT)))
                    if port < 1 or port > 65535:
                        logger.warning(f"Invalid UDP port in settings, using default {DEFAULT_UDP_PORT}")
                        port = DEFAULT_UDP_PORT
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing UDP port: {e}, using default {DEFAULT_UDP_PORT}")
                    port = DEFAULT_UDP_PORT

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.sendto(message.encode('utf-8'), ("127.0.0.1", port))
                except UnicodeEncodeError as encode_error:
                    error = EncodingError(
                        f"Encoding error sending UDP command: {encode_error}",
                        encoding="utf-8",
                        data=message.encode('utf-8', errors='ignore') if message else None
                    )
                    log_exception(logger, error, use_exc_info=False)
                    status_code = _exception_to_http_status(error)
                    self.send_error(status_code, str(error))
                    return
                except OSError as socket_error:
                    error = UdpError(f"Socket error sending UDP command to 127.0.0.1:{port}: {socket_error}")
                    log_exception(logger, error)
                    status_code = _exception_to_http_status(error)
                    self.send_error(status_code, str(error))
                    return
                finally:
                    sock.close()
            except Exception as udp_error:
                from exceptions import OnAirScreenError
                if isinstance(udp_error, OnAirScreenError):
                    log_exception(logger, udp_error)
                    status_code = _exception_to_http_status(udp_error)
                    self.send_error(status_code, str(udp_error))
                else:
                    error = UdpError(f"Error forwarding command via UDP: {udp_error}")
                    log_exception(logger, error)
                    self.send_error(500, str(error))
                return

            # send file content to client
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            try:
                self.wfile.write(message.encode('utf-8'))
                self.wfile.write("\n".encode('utf-8'))
            except (OSError, BrokenPipeError) as write_error:
                logger.warning(f"Error writing response to client: {write_error}")
                # Client may have disconnected, which is not critical
            except UnicodeEncodeError as encode_error:
                error = EncodingError(
                    f"Encoding error writing response: {encode_error}",
                    encoding="utf-8"
                )
                log_exception(logger, error, use_exc_info=False)
                # Response already sent, can't send error
            except Exception as write_error:
                from exceptions import OnAirScreenError, HttpError
                if isinstance(write_error, OnAirScreenError):
                    log_exception(logger, write_error)
                else:
                    error = HttpError(f"Unexpected error writing response: {write_error}", status_code=500)
                    log_exception(logger, error)
        else:
            self.send_error(400, 'no command was given')
    
    def _handle_api_command(self, query_string: str) -> None:
        """
        Handle API command request (REST-style) - returns JSON
        
        Processes commands in format "?cmd=COMMAND:VALUE" and returns JSON response.
        
        Args:
            query_string: Query string containing command (e.g., "cmd=LED1:ON")
            
        Returns:
            JSON response with status and command information
            
        Note:
            Falls back to UDP forwarding if MainScreen/signal not available
        """
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
                    try:
                        command_bytes = message.encode('utf-8')
                    except UnicodeEncodeError as encode_error:
                        error = EncodingError(
                            f"Encoding error encoding command: {encode_error}",
                            encoding="utf-8",
                            data=message.encode('utf-8', errors='ignore') if message else None
                        )
                        log_exception(logger, error, use_exc_info=False)
                        status_code = _exception_to_http_status(error)
                        self.send_error(status_code, str(error))
                        return
                    
                    if not self.command_signal:
                        logger.error("Command signal not available")
                        self.send_error(503, 'Command signal not available')
                        return
                    
                    self.command_signal.command_received.emit(command_bytes, "http")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    try:
                        response_json = json.dumps({'status': 'ok', 'command': message})
                        self.wfile.write(response_json.encode('utf-8'))
                    except (TypeError, ValueError) as json_error:
                        error = JsonSerializationError(
                            f"JSON serialization error: {json_error}",
                            data={'status': 'ok', 'command': message}
                        )
                        log_exception(logger, error, use_exc_info=False)
                        status_code = _exception_to_http_status(error)
                        self.send_error(status_code, str(error))
                        return
                    except (OSError, BrokenPipeError) as write_error:
                        logger.warning(f"Error writing response to client: {write_error}")
                        # Client may have disconnected, which is not critical
                    return
                except Exception as e:
                    from exceptions import OnAirScreenError
                    if isinstance(e, OnAirScreenError):
                        log_exception(logger, e)
                        status_code = _exception_to_http_status(e)
                        self.send_error(status_code, str(e))
                    else:
                        # Wrap unexpected exceptions
                        error = HttpError(f"Error processing command: {e}", status_code=500)
                        log_exception(logger, error)
                        self.send_error(500, str(error))
                    return
            
            # Fallback to UDP forwarding if MainScreen not available
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "Network"):
                try:
                    port = int(settings.value('udpport', str(DEFAULT_UDP_PORT)))
                    if port < 1 or port > 65535:
                        logger.warning(f"Invalid UDP port in settings, using default {DEFAULT_UDP_PORT}")
                        port = DEFAULT_UDP_PORT
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing UDP port: {e}, using default {DEFAULT_UDP_PORT}")
                    port = DEFAULT_UDP_PORT

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.sendto(message.encode('utf-8'), ("127.0.0.1", port))
                except UnicodeEncodeError as encode_error:
                    error = EncodingError(
                        f"Encoding error sending UDP command: {encode_error}",
                        encoding="utf-8",
                        data=message.encode('utf-8', errors='ignore') if message else None
                    )
                    log_exception(logger, error, use_exc_info=False)
                    raise error
                except OSError as socket_error:
                    error = UdpError(f"Socket error sending UDP command to 127.0.0.1:{port}: {socket_error}")
                    log_exception(logger, error)
                    raise error
                finally:
                    sock.close()
            except Exception as udp_error:
                from exceptions import OnAirScreenError
                if isinstance(udp_error, OnAirScreenError):
                    log_exception(logger, udp_error)
                    status_code = _exception_to_http_status(udp_error)
                    self.send_error(status_code, str(udp_error))
                else:
                    error = UdpError(f"Error forwarding command via UDP: {udp_error}")
                    log_exception(logger, error)
                    self.send_error(500, str(error))
                return

            try:
                response_data = json.dumps({'status': 'ok', 'command': message, 'method': 'udp_fallback'})
                self.wfile.write(response_data.encode('utf-8'))
            except (TypeError, ValueError) as json_error:
                error = JsonSerializationError(
                    f"JSON serialization error: {json_error}",
                    data={'status': 'ok', 'command': message, 'method': 'udp_fallback'}
                )
                log_exception(logger, error, use_exc_info=False)
                status_code = _exception_to_http_status(error)
                self.send_error(status_code, str(error))
                return
            except (OSError, BrokenPipeError) as write_error:
                logger.warning(f"Error writing response to client: {write_error}")
                # Client may have disconnected, which is not critical
            except Exception as write_error:
                from exceptions import OnAirScreenError, HttpError
                if isinstance(write_error, OnAirScreenError):
                    log_exception(logger, write_error)
                else:
                    error = HttpError(f"Unexpected error writing response: {write_error}", status_code=500)
                    log_exception(logger, error)
        except ValueError as value_error:
            error = InvalidCommandFormatError(
                f"Value error in API command handler: {value_error}",
                command_data=query_string
            )
            log_exception(logger, error, use_exc_info=False)
            status_code = _exception_to_http_status(error)
            self.send_error(status_code, str(error))
        except Exception as e:
            from exceptions import OnAirScreenError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
                status_code = _exception_to_http_status(e)
                self.send_error(status_code, str(e))
            else:
                error = HttpError(f"Error in API command handler: {e}", status_code=500)
                log_exception(logger, error)
                self.send_error(500, str(error))
    
    def _handle_api_status(self) -> None:
        """
        Handle API status request - returns JSON with current status
        
        Returns current status of LEDs, AIR timers, and text fields.
        
        Returns:
            JSON response with current application status
            
        Raises:
            503: If MainScreen is not available
            500: If error occurs getting status
        """
        if not self.main_screen:
            self.send_error(503, 'MainScreen not available')
            return
        
        try:
            status = self.main_screen.get_status_json()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                status_json = json.dumps(status)
                self.wfile.write(status_json.encode('utf-8'))
            except (TypeError, ValueError) as json_error:
                error = JsonSerializationError(
                    f"JSON serialization error for status: {json_error}",
                    data=status
                )
                log_exception(logger, error, use_exc_info=False)
                status_code = _exception_to_http_status(error)
                self.send_error(status_code, str(error))
                return
            except (OSError, BrokenPipeError) as write_error:
                logger.warning(f"Error writing status response to client: {write_error}")
                # Client may have disconnected, which is not critical
        except AttributeError as attr_error:
            from exceptions import WidgetAccessError
            error = WidgetAccessError(
                f"MainScreen missing required method or attribute: {attr_error}",
                widget_name="MainScreen",
                attribute="get_status_json"
            )
            log_exception(logger, error, use_exc_info=False)
            status_code = _exception_to_http_status(error)
            self.send_error(status_code, str(error))
        except Exception as e:
            from exceptions import OnAirScreenError, HttpError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
                status_code = _exception_to_http_status(e)
                self.send_error(status_code, str(e))
            else:
                error = HttpError(f"Error getting status: {e}", status_code=500)
                log_exception(logger, error)
                self.send_error(500, str(error))
    
    def _handle_web_ui(self) -> None:
        """
        Handle Web-UI request - serves HTML interface
        
        Serves the Web-UI HTML template or fallback HTML if template is missing.
        
        Raises:
            500: If error occurs serving Web-UI
        """
        try:
            html_content = self._get_web_ui_html()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                self.wfile.write(html_content.encode('utf-8'))
            except (OSError, BrokenPipeError) as write_error:
                logger.warning(f"Error writing Web-UI HTML to client: {write_error}")
                # Client may have disconnected, which is not critical
            except UnicodeEncodeError as encode_error:
                error = EncodingError(
                    f"Encoding error writing Web-UI HTML: {encode_error}",
                    encoding="utf-8"
                )
                log_exception(logger, error, use_exc_info=False)
                self.send_error(500, 'Error encoding Web-UI content')
        except Exception as e:
            from exceptions import OnAirScreenError, HttpError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
                status_code = _exception_to_http_status(e)
                self.send_error(status_code, str(e))
            else:
                error = HttpError(f"Unexpected error serving Web-UI: {e}", status_code=500)
                log_exception(logger, error)
                self.send_error(500, str(error))
    
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
            from exceptions import OnAirScreenError, HttpError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = HttpError(f"Error loading Web UI template: {e}", status_code=500)
                log_exception(logger, error)
            return f"<html><body><h1>Error loading Web UI: {e}</h1></body></html>"


class WebSocketDaemon(QThread):
    """
    WebSocket server thread for real-time status updates
    
    Runs a WebSocket server that broadcasts status updates to connected clients.
    This allows the Web-UI to receive real-time updates instead of polling.
    """
    
    def __init__(self, main_screen: Optional["MainScreen"] = None) -> None:
        """
        Initialize WebSocket daemon
        
        Args:
            main_screen: Reference to MainScreen instance for status queries
        """
        super().__init__()
        self.main_screen = main_screen
        self.clients: Set = set()  # Set[ServerConnection] when websockets is available
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server = None
        self._stop_event = threading.Event()
        self._broadcast_task: Optional[asyncio.Task] = None
    
    def run(self) -> None:
        """
        Start WebSocket server in a separate thread with asyncio event loop
        
        Raises:
            OSError: If port is already in use or permission denied
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("WebSocket support not available, skipping WebSocket server startup")
            return
        
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "Network"):
            try:
                # Use HTTP port + 1 for WebSocket port (or same port if HTTP upgrade is used)
                http_port = int(settings.value('httpport', str(DEFAULT_HTTP_PORT)))
                ws_port = http_port + 1
                if ws_port > 65535:
                    ws_port = DEFAULT_HTTP_PORT + 1
            except (ValueError, TypeError):
                ws_port = DEFAULT_HTTP_PORT + 1
        
        # Create new event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            # Start WebSocket server using the new API
            # websockets.serve is now a coroutine that returns a Server
            async def start_ws_server():
                server = await websockets.serve(
                    self._handle_client,
                    HOST,
                    ws_port,
                    ping_interval=20,
                    ping_timeout=10
                )
                return server
            
            self._server = self._loop.run_until_complete(start_ws_server())
            logger.info(f"WebSocket server started on {HOST}:{ws_port}")
            
            # Start periodic status updates
            self._broadcast_task = self._loop.create_task(self._broadcast_status_periodically())
            
            # Run event loop
            self._loop.run_forever()
        except OSError as error:
            if error.errno == 98 or "Address already in use" in str(error):
                port_error = PortInUseError(ws_port, "WebSocket")
                log_exception(logger, port_error)
            elif error.errno == 13 or "Permission denied" in str(error):
                perm_error = PermissionDeniedError(ws_port, "WebSocket")
                log_exception(logger, perm_error)
            else:
                ws_error = WebSocketError(f"OS error starting WebSocket Server on port {ws_port}: {error}")
                log_exception(logger, ws_error)
        except Exception as error:
            ws_error = WebSocketError(f"Unexpected error starting WebSocket Server on port {ws_port}: {error}")
            log_exception(logger, ws_error)
        finally:
            if self._loop:
                self._loop.close()
    
    async def _handle_client(self, connection: ServerConnection) -> None:
        """
        Handle new WebSocket client connection
        
        Args:
            connection: ServerConnection instance (new websockets 15.0+ API)
        """
        # Add client to set
        self.clients.add(connection)
        logger.info(f"WebSocket client connected: {connection.remote_address}")
        
        try:
            # Send initial status
            if self.main_screen:
                status = self.main_screen.get_status_json()
                await connection.send(json.dumps(status))
            
            # Keep connection alive and handle incoming messages
            async for message in connection:
                # Echo back or handle commands if needed
                logger.debug(f"WebSocket message received: {message}")
        except ConnectionClosed:
            logger.debug(f"WebSocket client disconnected: {connection.remote_address}")
        except Exception as e:
            from exceptions import OnAirScreenError, WebSocketError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = WebSocketError(f"Error handling WebSocket client {connection.remote_address}: {e}")
                log_exception(logger, error)
        finally:
            # Remove client from set
            self.clients.discard(connection)
    
    async def _broadcast_status_periodically(self) -> None:
        """
        Broadcast status updates to all connected clients periodically
        """
        while not self._stop_event.is_set():
            try:
                if self.main_screen and self.clients:
                    status = self.main_screen.get_status_json()
                    message = json.dumps(status)
                    
                    # Send to all connected clients
                    disconnected = set()
                    for client in self.clients:
                        try:
                            await client.send(message)
                        except ConnectionClosed:
                            disconnected.add(client)
                        except Exception as e:
                            from exceptions import OnAirScreenError, WebSocketError
                            if isinstance(e, OnAirScreenError):
                                log_exception(logger, e, use_exc_info=False)
                            else:
                                error = WebSocketError(f"Error sending to WebSocket client: {e}")
                                log_exception(logger, error, use_exc_info=False)
                            disconnected.add(client)
                    
                    # Remove disconnected clients
                    self.clients -= disconnected
                
                # Wait 1 second before next update, but check stop event more frequently
                for _ in range(10):  # Check every 100ms
                    if self._stop_event.is_set():
                        break
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                # Task was cancelled, exit gracefully
                break
            except Exception as e:
                from exceptions import OnAirScreenError, WebSocketError
                if isinstance(e, OnAirScreenError):
                    log_exception(logger, e, use_exc_info=False)
                else:
                    error = WebSocketError(f"Error in periodic status broadcast: {e}")
                    log_exception(logger, error, use_exc_info=False)
                if not self._stop_event.is_set():
                    await asyncio.sleep(1.0)
    
    def broadcast_status(self) -> None:
        """
        Manually trigger status broadcast to all connected clients
        
        This can be called from the main thread to send immediate updates.
        """
        if self._loop and self._loop.is_running() and self.main_screen and self.clients:
            status = self.main_screen.get_status_json()
            message = json.dumps(status)
            
            # Schedule coroutine in event loop
            asyncio.run_coroutine_threadsafe(self._send_to_all_clients(message), self._loop)
    
    async def _send_to_all_clients(self, message: str) -> None:
        """
        Send message to all connected clients
        
        Args:
            message: JSON message to send
        """
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except (ConnectionClosed, Exception) as e:
                logger.debug(f"Error sending to client: {e}")
                disconnected.add(client)
        
        self.clients -= disconnected
    
    def stop(self) -> None:
        """
        Stop WebSocket server gracefully
        
        Shuts down the server, closes all connections, and waits for the thread to finish.
        """
        if not WEBSOCKETS_AVAILABLE:
            return
        
        try:
            self._stop_event.set()
            
            if self._loop and self._loop.is_running():
                # Stop the server and close all clients in one async function
                async def shutdown_all():
                    # Cancel the broadcast task first
                    if self._broadcast_task and not self._broadcast_task.done():
                        self._broadcast_task.cancel()
                        try:
                            await self._broadcast_task
                        except asyncio.CancelledError:
                            pass
                    
                    # Close all client connections
                    if self.clients:
                        for client in list(self.clients):
                            try:
                                await client.close()
                            except Exception as e:
                                logger.debug(f"Error closing client connection: {e}")
                        self.clients.clear()
                    
                    # Stop the server
                    if self._server:
                        self._server.close()
                        await self._server.wait_closed()
                
                # Run shutdown and wait for it to complete
                future = asyncio.run_coroutine_threadsafe(shutdown_all(), self._loop)
                try:
                    # Wait up to 2 seconds for shutdown to complete
                    future.result(timeout=2.0)
                except Exception as e:
                    logger.debug(f"Shutdown timeout or error: {e}")
                
                # Stop the event loop
                self._loop.call_soon_threadsafe(self._loop.stop)
            
            # Wait for thread to finish
            self.wait()
        except Exception as e:
            from exceptions import OnAirScreenError, WebSocketError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = WebSocketError(f"Error stopping WebSocket server: {e}")
                log_exception(logger, error)
