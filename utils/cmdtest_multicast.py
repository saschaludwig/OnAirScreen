#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
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

Troubleshooting:
    If sendto() succeeds but packets don't appear in tcpdump, check your firewall
    settings (e.g., LittleSnitch on macOS) - they may be blocking multicast traffic
    from Python processes.
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
        # Find a non-loopback network interface FIRST
        # On macOS, we need to use the interface index, not the IP address
        network_ip = None
        interface_index = None
        try:
            import subprocess
            import platform
            
            # On macOS, use netstat or ifconfig to get interface info
            if platform.system() == 'Darwin':
                # Try to get interface index using if_nametoindex
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=2)
                current_interface = None
                for line in result.stdout.split('\n'):
                    # Interface name is on a line without leading whitespace
                    if line and not line[0].isspace() and ':' in line:
                        current_interface = line.split(':')[0]
                    elif 'inet ' in line and '127.0.0.1' not in line and '::1' not in line:
                        parts = line.split()
                        if len(parts) > 1:
                            ip = parts[1]
                            # Use first valid network IP (not link-local 169.254.x.x)
                            if (ip.startswith('192.168.') or ip.startswith('10.') or 
                                ip.startswith('172.') or 
                                (not ip.startswith('169.254.') and not ip.startswith('127.'))):
                                network_ip = ip
                                # Try to get interface index
                                try:
                                    import ctypes
                                    import ctypes.util
                                    libc = ctypes.CDLL(ctypes.util.find_library('c'))
                                    libc.if_nametoindex.argtypes = [ctypes.c_char_p]
                                    libc.if_nametoindex.restype = ctypes.c_uint32
                                    if_index = libc.if_nametoindex(current_interface.encode('utf-8'))
                                    if if_index > 0:
                                        interface_index = if_index
                                except Exception:
                                    pass
                                break
            else:
                # On other systems, just get the IP
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=2)
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and '127.0.0.1' not in line and '::1' not in line:
                        parts = line.split()
                        if len(parts) > 1:
                            ip = parts[1]
                            if (ip.startswith('192.168.') or ip.startswith('10.') or 
                                ip.startswith('172.') or 
                                (not ip.startswith('169.254.') and not ip.startswith('127.'))):
                                network_ip = ip
                                break
        except Exception as e:
            if verbose:
                print(f"Warning: Could not determine network interface: {e}", file=sys.stderr)
        
        # Create UDP socket AFTER determining network interface
        # This ensures we can bind directly to the correct interface
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set socket options for multicast
        # SO_REUSEADDR allows multiple processes to bind to the same address
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set TTL for multicast (1 = local network only, 32 = site-local, 255 = global)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        
        # Disable multicast loopback to ensure messages go to network, not just localhost
        # This is important: with loopback enabled, messages might only go to localhost
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        
        # CRITICAL FIX: On macOS, binding to a specific IP and setting multicast interface
        # can cause the message to not be sent if there's a routing mismatch.
        # Instead, bind to 0.0.0.0 but DON'T set multicast interface - let the system choose
        # This matches how the UDP server in network.py works
        try:
            sock.bind(('0.0.0.0', 0))
        except OSError as bind_error:
            if bind_error.errno != 48:  # Address already in use
                if verbose:
                    print(f"Warning: Could not bind socket: {bind_error}", file=sys.stderr)
        
        # DON'T set multicast interface - let the system choose based on routing table
        # Setting it explicitly can cause routing issues on macOS
        
        # Debug: Print socket state before sending (only in verbose mode)
        # Most of this is removed for cleaner output
        
        # Encode message to bytes
        message_bytes = message.encode('utf-8')
        
        # Send multicast message with explicit error handling
        # CRITICAL FIX: On macOS, calling connect() before sendto() can help
        # establish proper routing, especially in different execution contexts
        bytes_sent = 0
        try:
            # CRITICAL: On macOS, connect() to multicast address helps establish routing
            # This is especially important when running from different contexts (terminal vs script)
            # However, if connect() fails, we need to recreate the socket as it may be in a bad state
            try:
                sock.connect((multicast_address, port))
                # Use send() instead of sendto() after connect()
                bytes_sent = sock.send(message_bytes)
            except OSError as connect_error:
                # If connect() fails, the socket may be in a bad state
                # Recreate the socket and use sendto() directly
                # (This is expected on some systems and OK)
                sock.close()
                
                # IMPORTANT: On macOS, when connect() fails, the socket state may be corrupted
                # We MUST recreate it completely to ensure proper routing
                
                # Recreate socket with same configuration
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
                
                # CRITICAL: On macOS, we need to bind to 0.0.0.0 and NOT set multicast interface
                # But we also need to ensure the socket is actually ready to send
                sock.bind(('0.0.0.0', 0))
                
                # Add a small delay to ensure socket is fully ready
                import time
                time.sleep(0.01)
                
                # CRITICAL: On macOS, after recreating socket, we may need to force
                # the system to actually send by using a different approach
                # Try using sendto() with explicit source address binding
                try:
                    # Force send by using sendto() with explicit address
                    # On some systems, this helps ensure the message is actually sent
                    bytes_sent = sock.sendto(message_bytes, (multicast_address, port))
                except OSError as send_err:
                    if verbose:
                        print(f"Send failed: {send_err}", file=sys.stderr)
                    raise
            
        except OSError as send_error:
            if verbose:
                print(f"Error sending multicast: {send_error}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
            raise
        
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

