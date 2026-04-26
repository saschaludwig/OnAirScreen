#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multicast Diagnosis Tool for OnAirScreen

This tool helps diagnose multicast issues by:
1. Testing if multicast sending works
2. Testing if multicast receiving works
3. Checking network interface configuration
4. Verifying multicast group joins

Usage:
    python utils/diagnose_multicast.py
"""

import sys
import socket
import time
import logging
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QUdpSocket, QHostAddress, QNetworkInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_multicast_send(multicast_address: str, port: int) -> bool:
    """Test if we can send multicast messages"""
    print("\n=== Testing Multicast Sending ===")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.bind(('0.0.0.0', 0))
        
        message = b'TEST_MULTICAST'
        bytes_sent = sock.sendto(message, (multicast_address, port))
        print(f"✓ Sent {bytes_sent} bytes to {multicast_address}:{port}")
        sock.close()
        return True
    except Exception as e:
        print(f"✗ Failed to send multicast: {e}")
        return False

def test_multicast_receive(multicast_address: str, port: int) -> bool:
    """Test if we can receive multicast messages"""
    print("\n=== Testing Multicast Reception ===")
    
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    received = []
    def callback():
        while udpsock.hasPendingDatagrams():
            size = udpsock.pendingDatagramSize()
            data, host, port = udpsock.readDatagram(size)
            received.append(data)
            print(f"✓ Received: {data!r} from {host}:{port}")
    
    udpsock = QUdpSocket()
    
    # Bind
    result = udpsock.bind(QHostAddress.SpecialAddress.AnyIPv4, port, QUdpSocket.BindFlag.ShareAddress)
    print(f"Bind result: {result}")
    if not result:
        print("✗ Failed to bind socket")
        return False
    
    # Join multicast groups
    interfaces = QNetworkInterface.allInterfaces()
    loopback_interface = None
    active_interfaces = []
    
    for iface in interfaces:
        flags = iface.flags()
        if flags & QNetworkInterface.InterfaceFlag.IsUp and flags & QNetworkInterface.InterfaceFlag.IsRunning:
            if flags & QNetworkInterface.InterfaceFlag.IsLoopBack:
                loopback_interface = iface
            else:
                for entry in iface.addressEntries():
                    ipv4_result = entry.ip().toIPv4Address()
                    if len(ipv4_result) == 2 and ipv4_result[1]:
                        active_interfaces.append(iface)
                        break
    
    join_success = False
    
    if loopback_interface:
        join1 = udpsock.joinMulticastGroup(QHostAddress(multicast_address), loopback_interface)
        print(f"Join on loopback ({loopback_interface.name()}): {join1}")
        if join1:
            join_success = True
    
    for iface in active_interfaces:
        join2 = udpsock.joinMulticastGroup(QHostAddress(multicast_address), iface)
        print(f"Join on {iface.name()}: {join2}")
        if join2:
            join_success = True
    
    if not join_success:
        print("✗ Failed to join multicast group on any interface")
        return False
    
    # Connect signal
    udpsock.readyRead.connect(callback)
    
    # Wait for socket to be ready
    for _ in range(20):
        QCoreApplication.processEvents()
        time.sleep(0.05)
    
    print(f"Socket state: {udpsock.state()}")
    
    # Send test message
    if not test_multicast_send(multicast_address, port):
        return False
    
    # Wait for reception
    print("Waiting for multicast message...")
    for i in range(50):
        QCoreApplication.processEvents()
        time.sleep(0.1)
        if len(received) > 0:
            print(f"✓ SUCCESS: Received message after {i * 0.1:.1f} seconds")
            udpsock.close()
            return True
    
    print(f"✗ FAILED: No message received after 5 seconds")
    print(f"  Has pending datagrams: {udpsock.hasPendingDatagrams()}")
    if udpsock.hasPendingDatagrams():
        print("  WARNING: Socket reports pending datagrams but signal didn't fire!")
        # Try manual read
        try:
            size = udpsock.pendingDatagramSize()
            data, host, port = udpsock.readDatagram(size)
            print(f"  Manual read successful: {data!r} from {host}:{port}")
        except Exception as e:
            print(f"  Manual read failed: {e}")
    
    udpsock.close()
    return False

def check_network_interfaces():
    """Check network interface configuration"""
    print("\n=== Network Interface Configuration ===")
    interfaces = QNetworkInterface.allInterfaces()
    
    for iface in interfaces:
        flags = iface.flags()
        is_up = bool(flags & QNetworkInterface.InterfaceFlag.IsUp)
        is_running = bool(flags & QNetworkInterface.InterfaceFlag.IsRunning)
        is_loopback = bool(flags & QNetworkInterface.InterfaceFlag.IsLoopBack)
        
        print(f"\nInterface: {iface.name()}")
        print(f"  Up: {is_up}, Running: {is_running}, Loopback: {is_loopback}")
        
        if is_up and is_running:
            addresses = []
            for entry in iface.addressEntries():
                addr = entry.ip()
                addr_str = addr.toString()
                ipv4_result = addr.toIPv4Address()
                if len(ipv4_result) == 2 and ipv4_result[1]:
                    addresses.append(addr_str)
            if addresses:
                print(f"  IPv4 addresses: {', '.join(addresses)}")

def main():
    """Main entry point"""
    print("=" * 60)
    print("OnAirScreen Multicast Diagnosis Tool")
    print("=" * 60)
    
    multicast_address = "239.194.0.1"
    port = 3310
    
    print(f"\nConfiguration:")
    print(f"  Multicast address: {multicast_address}")
    print(f"  Port: {port}")
    
    # Check network interfaces
    check_network_interfaces()
    
    # Test multicast reception
    success = test_multicast_receive(multicast_address, port)
    
    print("\n" + "=" * 60)
    if success:
        print("RESULT: ✓ Multicast is working correctly!")
    else:
        print("RESULT: ✗ Multicast is NOT working")
        print("\nPossible issues:")
        print("  1. Firewall blocking multicast")
        print("  2. Network interface not configured for multicast")
        print("  3. Qt signal not firing (check Qt event loop)")
        print("  4. Multicast group join failed silently")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())

