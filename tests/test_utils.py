#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for utils.py
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from utils import (
    TimerUpdateMessageBox,
    is_valid_instance_name,
    normalize_instance_name,
    host_address_is_ipv4,
    host_address_is_ipv6,
)
from defaults import DEFAULT_INSTANCE_NAME, MAX_INSTANCE_NAME_LENGTH


@pytest.fixture(scope="module")
def qapp():
    """Fixture for QApplication - created once per test module"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestTimerUpdateMessageBox:
    """Tests for the TimerUpdateMessageBox class"""
    
    def test_init(self, qapp):
        """Test that TimerUpdateMessageBox is initialized correctly"""
        json_reply = {
            'Message': 'Test message',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
        
        assert msgbox.json_reply == json_reply
        assert msgbox.time_to_wait == 10
        # windowTitle() and text() are set in QMessageBox,
        # but may only be available after show()
        # Instead we test the internal properties
        assert hasattr(msgbox, 'timer')
        assert msgbox.timer.interval() == 1000
    
    def test_init_default_timeout(self, qapp):
        """Test that default timeout is set correctly"""
        json_reply = {
            'Message': 'Test',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=5, json_reply=json_reply)
        assert msgbox.time_to_wait == 5
    
    def test_change_content_decrements_timer(self, qapp):
        """Test that change_content correctly decrements the time"""
        json_reply = {
            'Message': 'Test',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
        
        initial_time = msgbox.time_to_wait
        msgbox.change_content()
        
        assert msgbox.time_to_wait == initial_time - 1
    
    def test_change_content_updates_text(self, qapp):
        """Test that change_content updates the text"""
        json_reply = {
            'Message': 'Test message',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=5, json_reply=json_reply)
        
        msgbox.change_content()
        informative_text = msgbox.informativeText()
        
        assert "Test message" in informative_text
        assert "1.0.0" in informative_text
        assert "closing in 4 seconds" in informative_text
    
    def test_change_content_closes_at_zero(self, qapp):
        """Test that the MessageBox closes when time_to_wait <= 0"""
        json_reply = {
            'Message': 'Test',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=1, json_reply=json_reply)
        
        # Set time_to_wait to 1 and call change_content
        msgbox.time_to_wait = 1
        msgbox.change_content()
        
        # After the call, time_to_wait should be 0
        assert msgbox.time_to_wait == 0
    
    def test_timer_starts(self, qapp):
        """Test that the timer runs after initialization"""
        json_reply = {
            'Message': 'Test',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
        
        assert msgbox.timer.isActive()
        assert msgbox.timer.interval() == 1000  # 1 second
    
    def test_closeEvent_stops_timer(self, qapp):
        """Test that closeEvent stops the timer"""
        from PySide6.QtGui import QCloseEvent
        
        json_reply = {
            'Message': 'Test',
            'Version': '1.0.0',
            'URL': 'http://example.com'
        }
        msgbox = TimerUpdateMessageBox(timeout=10, json_reply=json_reply)
        
        # Timer should be active
        assert msgbox.timer.isActive()
        
        # Simulate closeEvent
        event = QCloseEvent()
        msgbox.closeEvent(event)
        
        # Timer should be stopped
        assert not msgbox.timer.isActive()
        assert event.isAccepted()


class TestInstanceName:
    """Tests for DNS hostname instance name validation."""

    def test_valid_names(self):
        """Typical location names and edge-length values are accepted."""
        assert is_valid_instance_name("Studio-1")
        assert is_valid_instance_name("Studio-1-Outside")
        assert is_valid_instance_name("A")
        assert is_valid_instance_name("a1")
        assert is_valid_instance_name("X" * MAX_INSTANCE_NAME_LENGTH)
        assert is_valid_instance_name("  Studio-1  ")

    def test_invalid_names(self):
        """Spaces, leading/trailing hyphens, dots, and empty values are rejected."""
        assert not is_valid_instance_name("")
        assert not is_valid_instance_name("   ")
        assert not is_valid_instance_name("Studio 1")
        assert not is_valid_instance_name("-Studio")
        assert not is_valid_instance_name("Studio-")
        assert not is_valid_instance_name("Studio.1")
        assert not is_valid_instance_name("Studio_1")
        assert not is_valid_instance_name("X" * (MAX_INSTANCE_NAME_LENGTH + 1))

    def test_normalize_keeps_valid_name(self):
        """Valid names are trimmed but otherwise unchanged."""
        assert normalize_instance_name("  Studio-1-Outside  ") == "Studio-1-Outside"

    def test_normalize_falls_back_to_default(self):
        """Invalid or non-string values become the default instance name."""
        assert normalize_instance_name("") == DEFAULT_INSTANCE_NAME
        assert normalize_instance_name("Studio 1") == DEFAULT_INSTANCE_NAME
        assert normalize_instance_name(None) == DEFAULT_INSTANCE_NAME
        assert normalize_instance_name(123) == DEFAULT_INSTANCE_NAME


class TestHostAddressFamily:
    """PySide6 toIPv4Address() returns int; classify via protocol() instead."""

    def test_ipv4_and_ipv6(self, qapp):
        from PySide6.QtNetwork import QHostAddress

        ipv4 = QHostAddress("192.168.1.10")
        ipv6 = QHostAddress("2001:db8::1")
        loopback = QHostAddress("127.0.0.1")

        assert host_address_is_ipv4(ipv4) is True
        assert host_address_is_ipv6(ipv4) is False
        assert host_address_is_ipv4(ipv6) is False
        assert host_address_is_ipv6(ipv6) is True
        assert host_address_is_ipv4(loopback) is True
        assert loopback.isLoopback() is True
        # PySide6 returns an int here, not a (value, ok) tuple
        assert isinstance(ipv4.toIPv4Address(), int)

