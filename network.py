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
from typing import Optional, Callable, TYPE_CHECKING
from urllib.parse import unquote_plus, urlparse, parse_qs

from PyQt6.QtCore import QThread, QSettings
from PyQt6.QtNetwork import QUdpSocket, QHostAddress

from utils import settings_group
from settings_functions import versionString

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)

HOST = '0.0.0.0'


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
                port = int(settings.value('udpport', "3310"))
                if port < 1 or port > 65535:
                    logger.warning(f"Invalid UDP port {port}, using default 3310")
                    port = 3310
                    settings.setValue('udpport', "3310")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing UDP port: {e}, using default 3310")
                port = 3310
                settings.setValue('udpport', "3310")
            
            multicast_address = settings.value('multicast_address', "239.194.0.1")
            if not QHostAddress(multicast_address).isMulticast():
                logger.warning(f"Invalid multicast address {multicast_address}, using default 239.194.0.1")
                multicast_address = "239.194.0.1"
                settings.setValue('multicast_address', "239.194.0.1")

        try:
            bind_result = self.udpsock.bind(QHostAddress.SpecialAddress.AnyIPv4, int(port), QUdpSocket.BindFlag.ShareAddress)
            if not bind_result:
                error_msg = f"Failed to bind UDP socket to port {port}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info(f"UDP socket bound to port {port}")
        except Exception as e:
            logger.error(f"Error binding UDP socket to port {port}: {e}")
            raise
        
        if QHostAddress(multicast_address).isMulticast():
            try:
                join_result = self.udpsock.joinMulticastGroup(QHostAddress(multicast_address))
                if not join_result:
                    logger.warning(f"Failed to join multicast group {multicast_address}, continuing without multicast")
                else:
                    logger.info(f"{multicast_address} is Multicast, joined multicast group")
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
                            logger.error(f"Error in UDP command callback from {host}:{port}: {callback_error}")
                except OSError as socket_error:
                    logger.error(f"Socket error reading UDP datagram: {socket_error}")
                    break
                except Exception as read_error:
                    logger.error(f"Error reading UDP datagram: {read_error}")
                    break
        except Exception as e:
            logger.error(f"Unexpected error in UDP data handler: {e}")


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
                port = int(settings.value('httpport', "8010"))
                if port < 1 or port > 65535:
                    logger.warning(f"Invalid HTTP port {port}, using default 8010")
                    port = 8010
                    settings.setValue("httpport", "8010")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing HTTP port: {e}, using default 8010")
                port = 8010
                settings.setValue("httpport", "8010")

        try:
            # Pass main_screen reference and command_signal to handler class
            OASHTTPRequestHandler.main_screen = self.main_screen
            OASHTTPRequestHandler.command_signal = self.command_signal
            handler = OASHTTPRequestHandler
            self._server = HTTPServer((HOST, port), handler)
            logger.info(f"HTTP server started on {HOST}:{port}")
            self._server.serve_forever()
        except OSError as error:
            if error.errno == 98 or "Address already in use" in str(error):
                logger.error(f"HTTP Server port {port} is already in use. Please choose a different port or stop the conflicting service.")
            elif error.errno == 13 or "Permission denied" in str(error):
                logger.error(f"Permission denied binding to HTTP port {port}. Try using a port above 1024 or run with appropriate permissions.")
            else:
                logger.error(f"OS error starting HTTP Server on port {port}: {error}")
        except socket.error as socket_error:
            logger.error(f"Socket error starting HTTP Server on port {port}: {socket_error}")
        except Exception as error:
            logger.error(f"Unexpected error starting HTTP Server on port {port}: {error}", exc_info=True)

    def stop(self) -> None:
        """
        Stop HTTP server gracefully
        
        Shuts down the server, closes the socket, and waits for the thread to finish.
        Handles errors gracefully to allow cleanup even if server wasn't fully initialized.
        """
        try:
            if hasattr(self, '_server') and self._server:
                try:
                    self._server.shutdown()
                except Exception as shutdown_error:
                    logger.warning(f"Error shutting down HTTP server: {shutdown_error}")
                
                try:
                    if hasattr(self._server, 'socket') and self._server.socket:
                        self._server.socket.close()
                except Exception as close_error:
                    logger.warning(f"Error closing HTTP server socket: {close_error}")
                
                try:
                    self.wait()
                except Exception as wait_error:
                    logger.warning(f"Error waiting for HTTP server thread: {wait_error}")
            else:
                logger.debug("HTTP server not initialized, nothing to stop")
        except Exception as e:
            logger.error(f"Unexpected error stopping HTTP server: {e}")


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
                        logger.error(f"Encoding error encoding command '{message}': {encode_error}")
                        self.send_error(400, f'Invalid character encoding in command: {str(encode_error)}')
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
                        logger.error(f"JSON serialization error: {json_error}")
                        self.send_error(500, 'Error serializing response')
                        return
                    except (OSError, BrokenPipeError) as write_error:
                        logger.warning(f"Error writing response to client: {write_error}")
                        # Client may have disconnected, which is not critical
                    return
                except Exception as e:
                    logger.error(f"Error processing command: {e}", exc_info=True)
                    self.send_error(500, f'Error processing command: {str(e)}')
                    return
            
            # Fallback to UDP forwarding if MainScreen not available
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "Network"):
                try:
                    port = int(settings.value('udpport', "3310"))
                    if port < 1 or port > 65535:
                        logger.warning("Invalid UDP port in settings, using default 3310")
                        port = 3310
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing UDP port: {e}, using default 3310")
                    port = 3310

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.sendto(message.encode('utf-8'), ("127.0.0.1", port))
                except UnicodeEncodeError as encode_error:
                    logger.error(f"Encoding error sending UDP command: {encode_error}")
                    self.send_error(400, f'Invalid character encoding in command: {str(encode_error)}')
                    return
                except OSError as socket_error:
                    logger.error(f"Socket error sending UDP command to 127.0.0.1:{port}: {socket_error}")
                    self.send_error(500, f'Error forwarding command via UDP: {str(socket_error)}')
                    return
                finally:
                    sock.close()
            except Exception as udp_error:
                logger.error(f"Error forwarding command via UDP: {udp_error}")
                self.send_error(500, f'Error forwarding command via UDP: {str(udp_error)}')
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
                logger.error(f"Encoding error writing response: {encode_error}")
                # Response already sent, can't send error
            except Exception as write_error:
                logger.error(f"Unexpected error writing response: {write_error}")
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
                        logger.error(f"Encoding error encoding command '{message}': {encode_error}")
                        self.send_error(400, f'Invalid character encoding in command: {str(encode_error)}')
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
                        logger.error(f"JSON serialization error: {json_error}")
                        self.send_error(500, 'Error serializing response')
                        return
                    except (OSError, BrokenPipeError) as write_error:
                        logger.warning(f"Error writing response to client: {write_error}")
                        # Client may have disconnected, which is not critical
                    return
                except Exception as e:
                    logger.error(f"Error processing command: {e}", exc_info=True)
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
                    if port < 1 or port > 65535:
                        logger.warning("Invalid UDP port in settings, using default 3310")
                        port = 3310
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing UDP port: {e}, using default 3310")
                    port = 3310

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.sendto(message.encode('utf-8'), ("127.0.0.1", port))
                except UnicodeEncodeError as encode_error:
                    logger.error(f"Encoding error sending UDP command: {encode_error}")
                    raise
                except OSError as socket_error:
                    logger.error(f"Socket error sending UDP command to 127.0.0.1:{port}: {socket_error}")
                    raise
                finally:
                    sock.close()
            except Exception as udp_error:
                logger.error(f"Error forwarding command via UDP: {udp_error}")
                self.send_error(500, f'Error forwarding command via UDP: {str(udp_error)}')
                return

            try:
                response_data = json.dumps({'status': 'ok', 'command': message, 'method': 'udp_fallback'})
                self.wfile.write(response_data.encode('utf-8'))
            except (TypeError, ValueError) as json_error:
                logger.error(f"JSON serialization error: {json_error}")
                self.send_error(500, 'Error serializing response')
                return
            except (OSError, BrokenPipeError) as write_error:
                logger.warning(f"Error writing response to client: {write_error}")
                # Client may have disconnected, which is not critical
            except Exception as write_error:
                logger.error(f"Unexpected error writing response: {write_error}")
        except ValueError as value_error:
            logger.error(f"Value error in API command handler: {value_error}")
            self.send_error(400, f'Invalid command format: {str(value_error)}')
        except Exception as e:
            logger.error(f"Error in API command handler: {e}", exc_info=True)
            self.send_error(500, f'Error processing command: {str(e)}')
    
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
                logger.error(f"JSON serialization error for status: {json_error}")
                self.send_error(500, 'Error serializing status response')
                return
            except (OSError, BrokenPipeError) as write_error:
                logger.warning(f"Error writing status response to client: {write_error}")
                # Client may have disconnected, which is not critical
        except AttributeError as attr_error:
            logger.error(f"MainScreen missing required method or attribute: {attr_error}")
            self.send_error(500, f'Error getting status: MainScreen interface error')
        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            self.send_error(500, f'Error getting status: {str(e)}')
    
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
                logger.error(f"Encoding error writing Web-UI HTML: {encode_error}")
                self.send_error(500, 'Error encoding Web-UI content')
        except Exception as e:
            logger.error(f"Unexpected error serving Web-UI: {e}", exc_info=True)
            self.send_error(500, f'Error serving Web-UI: {str(e)}')
    
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
