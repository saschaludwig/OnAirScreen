#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for event_logger.py
"""

import pytest
import logging
from unittest.mock import patch, MagicMock

from event_logger import EventLogger, EventType


@pytest.fixture
def event_logger():
    """Create an EventLogger instance for testing"""
    return EventLogger()


class TestEventLoggerInitialization:
    """Test EventLogger initialization"""
    
    def test_init_creates_event_logger(self, event_logger):
        """Test that EventLogger is created"""
        assert isinstance(event_logger, EventLogger)
    
    def test_init_event_count_is_zero(self, event_logger):
        """Test that event count starts at zero"""
        assert event_logger.get_event_count() == 0


class TestLogLedChanged:
    """Test log_led_changed method"""
    
    @patch('event_logger.logger')
    def test_log_led_changed_on(self, mock_logger, event_logger):
        """Test logging LED changed to ON"""
        event_logger.log_led_changed(1, True, "manual")
        mock_logger.info.assert_called_once()
        assert "LED1" in mock_logger.info.call_args[0][0]
        assert "ON" in mock_logger.info.call_args[0][0]
        assert "manual" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_led_changed_off(self, mock_logger, event_logger):
        """Test logging LED changed to OFF"""
        event_logger.log_led_changed(2, False, "command")
        mock_logger.info.assert_called_once()
        assert "LED2" in mock_logger.info.call_args[0][0]
        assert "OFF" in mock_logger.info.call_args[0][0]
        assert "command" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_led_changed_all_numbers(self, mock_logger, event_logger):
        """Test logging LED changed for all LED numbers"""
        for led_num in range(1, 5):
            event_logger.log_led_changed(led_num, True, "autoflash")
        assert mock_logger.info.call_count == 4
        assert event_logger.get_event_count() == 4
    
    @patch('event_logger.logger')
    def test_log_led_changed_default_source(self, mock_logger, event_logger):
        """Test logging LED changed with default source"""
        event_logger.log_led_changed(1, True)
        assert "manual" in mock_logger.info.call_args[0][0]


class TestLogAirStarted:
    """Test log_air_started method"""
    
    @patch('event_logger.logger')
    def test_log_air_started(self, mock_logger, event_logger):
        """Test logging AIR started"""
        event_logger.log_air_started(1, "manual")
        mock_logger.info.assert_called_once()
        assert "AIR1" in mock_logger.info.call_args[0][0]
        assert "started" in mock_logger.info.call_args[0][0]
        assert "manual" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_air_started_all_numbers(self, mock_logger, event_logger):
        """Test logging AIR started for all AIR numbers"""
        for air_num in range(1, 5):
            event_logger.log_air_started(air_num, "command")
        assert mock_logger.info.call_count == 4
        assert event_logger.get_event_count() == 4
    
    @patch('event_logger.logger')
    def test_log_air_started_default_source(self, mock_logger, event_logger):
        """Test logging AIR started with default source"""
        event_logger.log_air_started(1)
        assert "manual" in mock_logger.info.call_args[0][0]


class TestLogAirStopped:
    """Test log_air_stopped method"""
    
    @patch('event_logger.logger')
    def test_log_air_stopped(self, mock_logger, event_logger):
        """Test logging AIR stopped"""
        event_logger.log_air_stopped(2, "command")
        mock_logger.info.assert_called_once()
        assert "AIR2" in mock_logger.info.call_args[0][0]
        assert "stopped" in mock_logger.info.call_args[0][0]
        assert "command" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_air_stopped_default_source(self, mock_logger, event_logger):
        """Test logging AIR stopped with default source"""
        event_logger.log_air_stopped(1)
        assert "manual" in mock_logger.info.call_args[0][0]


class TestLogAirReset:
    """Test log_air_reset method"""
    
    @patch('event_logger.logger')
    def test_log_air_reset(self, mock_logger, event_logger):
        """Test logging AIR reset"""
        event_logger.log_air_reset(3, "command")
        mock_logger.info.assert_called_once()
        assert "AIR3" in mock_logger.info.call_args[0][0]
        assert "reset" in mock_logger.info.call_args[0][0]
        assert "command" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_air_reset_default_source(self, mock_logger, event_logger):
        """Test logging AIR reset with default source"""
        event_logger.log_air_reset(1)
        assert "manual" in mock_logger.info.call_args[0][0]


class TestLogTimerSet:
    """Test log_timer_set method"""
    
    @patch('event_logger.logger')
    def test_log_timer_set_count_up(self, mock_logger, event_logger):
        """Test logging timer set in count_up mode"""
        event_logger.log_timer_set(3, 125, "count_up")
        mock_logger.info.assert_called_once()
        assert "AIR3" in mock_logger.info.call_args[0][0]
        assert "2:05" in mock_logger.info.call_args[0][0]
        assert "count_up" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_timer_set_count_down(self, mock_logger, event_logger):
        """Test logging timer set in count_down mode"""
        event_logger.log_timer_set(4, 90, "count_down")
        mock_logger.info.assert_called_once()
        assert "AIR4" in mock_logger.info.call_args[0][0]
        assert "1:30" in mock_logger.info.call_args[0][0]
        assert "count_down" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_timer_set_default_mode(self, mock_logger, event_logger):
        """Test logging timer set with default mode"""
        event_logger.log_timer_set(3, 60)
        assert "count_up" in mock_logger.info.call_args[0][0]
    
    @patch('event_logger.logger')
    def test_log_timer_set_zero_seconds(self, mock_logger, event_logger):
        """Test logging timer set with zero seconds"""
        event_logger.log_timer_set(3, 0)
        assert "0:00" in mock_logger.info.call_args[0][0]
    
    @patch('event_logger.logger')
    def test_log_timer_set_large_value(self, mock_logger, event_logger):
        """Test logging timer set with large value"""
        event_logger.log_timer_set(3, 3661)  # 1:01:01
        assert "61:01" in mock_logger.info.call_args[0][0]


class TestLogCommandReceived:
    """Test log_command_received method"""
    
    @patch('event_logger.logger')
    def test_log_command_received_udp(self, mock_logger, event_logger):
        """Test logging command received via UDP"""
        event_logger.log_command_received("LED1", "ON", "udp")
        mock_logger.info.assert_called_once()
        assert "LED1" in mock_logger.info.call_args[0][0]
        assert "ON" in mock_logger.info.call_args[0][0]
        assert "udp" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_command_received_http(self, mock_logger, event_logger):
        """Test logging command received via HTTP"""
        event_logger.log_command_received("NOW", "Test Song", "http")
        assert "http" in mock_logger.info.call_args[0][0]
    
    @patch('event_logger.logger')
    def test_log_command_received_default_source(self, mock_logger, event_logger):
        """Test logging command received with default source"""
        event_logger.log_command_received("LED1", "ON")
        assert "udp" in mock_logger.info.call_args[0][0]


class TestLogSettingsChanged:
    """Test log_settings_changed method"""
    
    @patch('event_logger.logger')
    def test_log_settings_changed(self, mock_logger, event_logger):
        """Test logging settings change"""
        event_logger.log_settings_changed("General", "stationname", "New Station")
        mock_logger.info.assert_called_once()
        assert "General" in mock_logger.info.call_args[0][0]
        assert "stationname" in mock_logger.info.call_args[0][0]
        assert "New Station" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1


class TestLogWarningAdded:
    """Test log_warning_added method"""
    
    @patch('event_logger.logger')
    def test_log_warning_added(self, mock_logger, event_logger):
        """Test logging warning added"""
        event_logger.log_warning_added("Test warning", 1)
        mock_logger.warning.assert_called_once()
        assert "Warning added" in mock_logger.warning.call_args[0][0]
        assert "Test warning" in mock_logger.warning.call_args[0][0]
        assert "priority 1" in mock_logger.warning.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_warning_added_default_priority(self, mock_logger, event_logger):
        """Test logging warning added with default priority"""
        event_logger.log_warning_added("Test warning")
        assert "priority 0" in mock_logger.warning.call_args[0][0]


class TestLogWarningRemoved:
    """Test log_warning_removed method"""
    
    @patch('event_logger.logger')
    def test_log_warning_removed(self, mock_logger, event_logger):
        """Test logging warning removed"""
        event_logger.log_warning_removed(2)
        mock_logger.info.assert_called_once()
        assert "Warning removed" in mock_logger.info.call_args[0][0]
        assert "priority 2" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_warning_removed_default_priority(self, mock_logger, event_logger):
        """Test logging warning removed with default priority"""
        event_logger.log_warning_removed()
        assert "priority 0" in mock_logger.info.call_args[0][0]


class TestLogSystemEvent:
    """Test log_system_event method"""
    
    @patch('event_logger.logger')
    def test_log_system_event_without_details(self, mock_logger, event_logger):
        """Test logging system event without details"""
        event_logger.log_system_event("Application started")
        mock_logger.info.assert_called_once()
        assert "System event" in mock_logger.info.call_args[0][0]
        assert "Application started" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1
    
    @patch('event_logger.logger')
    def test_log_system_event_with_details(self, mock_logger, event_logger):
        """Test logging system event with details"""
        event_logger.log_system_event("Error occurred", "Connection timeout")
        mock_logger.info.assert_called_once()
        assert "System event" in mock_logger.info.call_args[0][0]
        assert "Error occurred" in mock_logger.info.call_args[0][0]
        assert "Connection timeout" in mock_logger.info.call_args[0][0]
        assert event_logger.get_event_count() == 1


class TestGetEventCount:
    """Test get_event_count method"""
    
    @patch('event_logger.logger')
    def test_get_event_count_increments(self, mock_logger, event_logger):
        """Test that event count increments with each log"""
        assert event_logger.get_event_count() == 0
        event_logger.log_led_changed(1, True)
        assert event_logger.get_event_count() == 1
        event_logger.log_air_started(1)
        assert event_logger.get_event_count() == 2
        event_logger.log_command_received("LED1", "ON")
        assert event_logger.get_event_count() == 3
    
    @patch('event_logger.logger')
    def test_get_event_count_all_event_types(self, mock_logger, event_logger):
        """Test event count with all event types"""
        initial_count = event_logger.get_event_count()
        event_logger.log_led_changed(1, True)
        event_logger.log_air_started(1)
        event_logger.log_air_stopped(1)
        event_logger.log_air_reset(1)
        event_logger.log_timer_set(3, 60)
        event_logger.log_command_received("LED1", "ON")
        event_logger.log_settings_changed("General", "stationname", "Test")
        event_logger.log_warning_added("Test")
        event_logger.log_warning_removed()
        event_logger.log_system_event("Test event")
        
        assert event_logger.get_event_count() == initial_count + 10

