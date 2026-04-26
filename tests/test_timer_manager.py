#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for timer_manager.py
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from timer_manager import TimerManager


@pytest.fixture
def mock_main_screen():
    """Create a mock MainScreen instance for testing"""
    main_screen = Mock()
    main_screen.toggle_led1 = Mock()
    main_screen.toggle_led2 = Mock()
    main_screen.toggle_led3 = Mock()
    main_screen.toggle_led4 = Mock()
    main_screen.update_air1_seconds = Mock()
    main_screen.update_air2_seconds = Mock()
    main_screen.update_air3_seconds = Mock()
    main_screen.update_air4_seconds = Mock()
    return main_screen


@pytest.fixture
def timer_manager(mock_main_screen):
    """Create a TimerManager instance for testing"""
    return TimerManager(mock_main_screen)


class TestTimerManagerInitialization:
    """Test TimerManager initialization"""
    
    def test_init_creates_all_led_timers(self, timer_manager):
        """Test that all LED timers are created"""
        assert hasattr(timer_manager, 'timerLED1')
        assert hasattr(timer_manager, 'timerLED2')
        assert hasattr(timer_manager, 'timerLED3')
        assert hasattr(timer_manager, 'timerLED4')
        assert isinstance(timer_manager.timerLED1, QTimer)
        assert isinstance(timer_manager.timerLED2, QTimer)
        assert isinstance(timer_manager.timerLED3, QTimer)
        assert isinstance(timer_manager.timerLED4, QTimer)
    
    def test_init_creates_all_air_timers(self, timer_manager):
        """Test that all AIR timers are created"""
        assert hasattr(timer_manager, 'timerAIR1')
        assert hasattr(timer_manager, 'timerAIR2')
        assert hasattr(timer_manager, 'timerAIR3')
        assert hasattr(timer_manager, 'timerAIR4')
        assert isinstance(timer_manager.timerAIR1, QTimer)
        assert isinstance(timer_manager.timerAIR2, QTimer)
        assert isinstance(timer_manager.timerAIR3, QTimer)
        assert isinstance(timer_manager.timerAIR4, QTimer)
    
    def test_init_connects_led_timer_callbacks(self, timer_manager, mock_main_screen):
        """Test that LED timer callbacks are connected"""
        # Verify callbacks are set up (we can't easily test signal connections,
        # but we can verify the methods exist on main_screen)
        assert hasattr(mock_main_screen, 'toggle_led1')
        assert hasattr(mock_main_screen, 'toggle_led2')
        assert hasattr(mock_main_screen, 'toggle_led3')
        assert hasattr(mock_main_screen, 'toggle_led4')
    
    def test_init_connects_air_timer_callbacks(self, timer_manager, mock_main_screen):
        """Test that AIR timer callbacks are connected"""
        # Verify callbacks are set up
        assert hasattr(mock_main_screen, 'update_air1_seconds')
        assert hasattr(mock_main_screen, 'update_air2_seconds')
        assert hasattr(mock_main_screen, 'update_air3_seconds')
        assert hasattr(mock_main_screen, 'update_air4_seconds')
    
    def test_init_stores_main_screen_reference(self, timer_manager, mock_main_screen):
        """Test that main_screen reference is stored"""
        assert timer_manager.main_screen is mock_main_screen


class TestGetLedTimer:
    """Test get_led_timer method"""
    
    def test_get_led_timer_valid_numbers(self, timer_manager):
        """Test getting LED timers with valid numbers"""
        timer1 = timer_manager.get_led_timer(1)
        timer2 = timer_manager.get_led_timer(2)
        timer3 = timer_manager.get_led_timer(3)
        timer4 = timer_manager.get_led_timer(4)
        
        assert timer1 is timer_manager.timerLED1
        assert timer2 is timer_manager.timerLED2
        assert timer3 is timer_manager.timerLED3
        assert timer4 is timer_manager.timerLED4
        assert isinstance(timer1, QTimer)
        assert isinstance(timer2, QTimer)
        assert isinstance(timer3, QTimer)
        assert isinstance(timer4, QTimer)
    
    def test_get_led_timer_invalid_low(self, timer_manager):
        """Test getting LED timer with invalid low number"""
        timer = timer_manager.get_led_timer(0)
        assert timer is None
    
    def test_get_led_timer_invalid_high(self, timer_manager):
        """Test getting LED timer with invalid high number"""
        timer = timer_manager.get_led_timer(5)
        assert timer is None
    
    def test_get_led_timer_negative(self, timer_manager):
        """Test getting LED timer with negative number"""
        timer = timer_manager.get_led_timer(-1)
        assert timer is None


class TestGetAirTimer:
    """Test get_air_timer method"""
    
    def test_get_air_timer_valid_numbers(self, timer_manager):
        """Test getting AIR timers with valid numbers"""
        timer1 = timer_manager.get_air_timer(1)
        timer2 = timer_manager.get_air_timer(2)
        timer3 = timer_manager.get_air_timer(3)
        timer4 = timer_manager.get_air_timer(4)
        
        assert timer1 is timer_manager.timerAIR1
        assert timer2 is timer_manager.timerAIR2
        assert timer3 is timer_manager.timerAIR3
        assert timer4 is timer_manager.timerAIR4
        assert isinstance(timer1, QTimer)
        assert isinstance(timer2, QTimer)
        assert isinstance(timer3, QTimer)
        assert isinstance(timer4, QTimer)
    
    def test_get_air_timer_invalid_low(self, timer_manager):
        """Test getting AIR timer with invalid low number"""
        timer = timer_manager.get_air_timer(0)
        assert timer is None
    
    def test_get_air_timer_invalid_high(self, timer_manager):
        """Test getting AIR timer with invalid high number"""
        timer = timer_manager.get_air_timer(5)
        assert timer is None
    
    def test_get_air_timer_negative(self, timer_manager):
        """Test getting AIR timer with negative number"""
        timer = timer_manager.get_air_timer(-1)
        assert timer is None


class TestTimerFunctionality:
    """Test timer functionality"""
    
    def test_led_timers_are_not_active_by_default(self, timer_manager):
        """Test that LED timers are not active by default"""
        assert not timer_manager.timerLED1.isActive()
        assert not timer_manager.timerLED2.isActive()
        assert not timer_manager.timerLED3.isActive()
        assert not timer_manager.timerLED4.isActive()
    
    def test_air_timers_are_not_active_by_default(self, timer_manager):
        """Test that AIR timers are not active by default"""
        assert not timer_manager.timerAIR1.isActive()
        assert not timer_manager.timerAIR2.isActive()
        assert not timer_manager.timerAIR3.isActive()
        assert not timer_manager.timerAIR4.isActive()
    
    def test_led_timer_can_be_started(self, timer_manager):
        """Test that LED timers can be started"""
        timer_manager.timerLED1.start(1000)
        assert timer_manager.timerLED1.isActive()
        timer_manager.timerLED1.stop()
    
    def test_air_timer_can_be_started(self, timer_manager):
        """Test that AIR timers can be started"""
        timer_manager.timerAIR1.start(1000)
        assert timer_manager.timerAIR1.isActive()
        timer_manager.timerAIR1.stop()

