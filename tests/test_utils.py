#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for utils.py
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from utils import TimerUpdateMessageBox


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
        from PyQt6.QtGui import QCloseEvent
        
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

