#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# cmdtest_multicast.py
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
Multicast Command Test Tool for OnAirScreen

This tool sends UDP commands via multicast to test OnAirScreen's multicast reception.
It can be used from any machine on the network to verify that multicast communication
is working correctly.

Usage:
    python utils/cmdtest_multicast.py LED1:ON
    python utils/cmdtest_multicast.py -m 239.194.0.1 -p 3310 "NOW:Test Song"
    python utils/cmdtest_multicast.py --multicast-address 239.194.0.1 --port 3310 "CONF:LED:led1color=#FF0000"
"""

import argparse
import socket
import sys
import os

# Add parent directory to path to import defaults
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from defaults import DEFAULT_MULTICAST_ADDRESS, DEFAULT_UDP_PORT
except ImportError:
    # Fallback if defaults module is not available
    DEFAULT_MULTICAST_ADDRESS = "239.194.0.1"
    DEFAULT_UDP_PORT = 3310

def send_multicast_command(message: str, multicast_address: str = DEFAULT_MULTICAST_ADDRESS, 
                          port: int = DEFAULT_UDP_PORT, ttl: int = 1, verbose: bool = True) -> bool:
    """
    Send a command via UDP multicast
    
    Args:
        message: Command message to send (e.g., "LED1:ON")
        multicast_address: Multicast address (default: from defaults.py)
        port: UDP port (default: from defaults.py)
        ttl: Time-to-live for multicast (1 = local network, higher = wider range)
        verbose: Print status information
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set socket options for multicast
        # SO_REUSEADDR allows multiple processes to bind to the same address
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set TTL for multicast (1 = local network only, 32 = site-local, 255 = global)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        
        # Enable multicast loopback (allows receiving own messages on same machine)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        
        # On some systems (especially macOS), we need to bind the socket before sending multicast
        # Bind to 0.0.0.0 (all interfaces) on a random port
        try:
            sock.bind(('0.0.0.0', 0))
        except OSError as bind_error:
            if bind_error.errno != 48:  # Address already in use
                if verbose:
                    print(f"Warning: Could not bind socket: {bind_error}", file=sys.stderr)
                # Continue anyway, some systems don't require binding
        
        # Encode message to bytes
        message_bytes = message.encode('utf-8')
        
        # Send multicast message
        bytes_sent = sock.sendto(message_bytes, (multicast_address, port))
        
        if verbose:
            print(f"Sent {bytes_sent} bytes via multicast to {multicast_address}:{port}")
            print(f"Message: {message}")
            print(f"TTL: {ttl} (1=local network, 32=site-local, 255=global)")
        
        sock.close()
        return True
        
    except socket.error as e:
        if verbose:
            print(f"Error sending multicast message: {e}", file=sys.stderr)
        return False
    except UnicodeEncodeError as e:
        if verbose:
            print(f"Error encoding message: {e}", file=sys.stderr)
        return False
    except Exception as e:
        if verbose:
            print(f"Unexpected error: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point for the multicast test tool"""
    parser = argparse.ArgumentParser(
        description='Send UDP commands to OnAirScreen via multicast.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s LED1:ON
  %(prog)s -m 239.194.0.1 -p 3310 "NOW:Test Song"
  %(prog)s --ttl 32 "CONF:LED:led1color=#FF0000"
  %(prog)s --silent "NEXT:Coming up next"
        """
    )
    
    parser.add_argument(
        '-m', '--multicast-address',
        type=str,
        default=DEFAULT_MULTICAST_ADDRESS,
        help=f'Multicast address (default: {DEFAULT_MULTICAST_ADDRESS})'
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=DEFAULT_UDP_PORT,
        help=f'UDP port (default: {DEFAULT_UDP_PORT})'
    )
    
    parser.add_argument(
        '--ttl',
        type=int,
        default=1,
        choices=[1, 32, 255],
        help='Time-to-live for multicast: 1=local network, 32=site-local, 255=global (default: 1)'
    )
    
    parser.add_argument(
        '-s', '--silent',
        action='store_true',
        help='Do not print any information, except for errors'
    )
    
    parser.add_argument(
        'message',
        type=str,
        help='Command message to send (e.g., "LED1:ON", "NOW:Test Song", "CONF:LED:led1color=#FF0000")'
    )
    
    args = parser.parse_args()
    
    # Validate multicast address
    try:
        addr_parts = args.multicast_address.split('.')
        if len(addr_parts) != 4:
            raise ValueError("Invalid IP address format")
        for part in addr_parts:
            num = int(part)
            if num < 0 or num > 255:
                raise ValueError("IP address parts must be between 0 and 255")
        # Check if it's a valid multicast address (224.0.0.0 to 239.255.255.255)
        first_octet = int(addr_parts[0])
        if first_octet < 224 or first_octet > 239:
            print(f"Warning: {args.multicast_address} is not in the multicast range (224.0.0.0-239.255.255.255)", 
                  file=sys.stderr)
    except ValueError as e:
        print(f"Error: Invalid multicast address '{args.multicast_address}': {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate port
    if args.port < 1 or args.port > 65535:
        print(f"Error: Port must be between 1 and 65535, got {args.port}", file=sys.stderr)
        sys.exit(1)
    
    # Send the message
    success = send_multicast_command(
        args.message,
        args.multicast_address,
        args.port,
        args.ttl,
        verbose=not args.silent
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

