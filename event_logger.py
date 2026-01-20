#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# event_logger.py
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
Event Logger for OnAirScreen

This module provides event logging functionality for tracking
LED changes, AIR timer events, commands, and other system events.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types that can be logged"""
    LED_CHANGED = "led_changed"
    AIR_STARTED = "air_started"
    AIR_STOPPED = "air_stopped"
    AIR_RESET = "air_reset"
    TIMER_SET = "timer_set"
    COMMAND_RECEIVED = "command_received"
    SETTINGS_CHANGED = "settings_changed"
    WARNING_ADDED = "warning_added"
    WARNING_REMOVED = "warning_removed"
    SYSTEM_EVENT = "system_event"


class EventLogger:
    """
    Event logger for OnAirScreen
    
    Logs events to the Python logging system with structured information.
    Events are logged at INFO level for normal operations and WARNING/ERROR
    for important system events.
    """
    
    def __init__(self):
        """Initialize the event logger"""
        self._event_count = 0
    
    def log_led_changed(self, led_num: int, state: bool, source: str = "manual") -> None:
        """
        Log LED state change
        
        Args:
            led_num: LED number (1-4)
            state: New state (True = ON, False = OFF)
            source: Source of change ('manual', 'command', 'autoflash', etc.)
        """
        state_str = "ON" if state else "OFF"
        logger.info(f"EVENT: LED{led_num} changed to {state_str} (source: {source})")
        self._event_count += 1
    
    def log_air_started(self, air_num: int, source: str = "manual") -> None:
        """
        Log AIR timer start
        
        Args:
            air_num: AIR number (1-4)
            source: Source of change ('manual', 'command', etc.)
        """
        logger.info(f"EVENT: AIR{air_num} started (source: {source})")
        self._event_count += 1
    
    def log_air_stopped(self, air_num: int, source: str = "manual") -> None:
        """
        Log AIR timer stop
        
        Args:
            air_num: AIR number (1-4)
            source: Source of change ('manual', 'command', etc.)
        """
        logger.info(f"EVENT: AIR{air_num} stopped (source: {source})")
        self._event_count += 1
    
    def log_air_reset(self, air_num: int, source: str = "manual") -> None:
        """
        Log AIR timer reset
        
        Args:
            air_num: AIR number (1-4)
            source: Source of change ('manual', 'command', etc.)
        """
        logger.info(f"EVENT: AIR{air_num} reset (source: {source})")
        self._event_count += 1
    
    def log_timer_set(self, air_num: int, seconds: int, mode: str = "count_up") -> None:
        """
        Log timer value set
        
        Args:
            air_num: AIR number (3 or 4 for radio/stream timer)
            seconds: Timer value in seconds
            mode: Timer mode ('count_up' or 'count_down')
        """
        minutes = seconds // 60
        secs = seconds % 60
        logger.info(f"EVENT: Timer AIR{air_num} set to {minutes}:{secs:02d} (mode: {mode})")
        self._event_count += 1
    
    def log_command_received(self, command: str, value: str, source: str = "udp") -> None:
        """
        Log command received via network
        
        Args:
            command: Command name
            value: Command value
            source: Source of command ('udp', 'http', etc.)
        """
        logger.info(f"EVENT: Command received: {command}:{value} (source: {source})")
        self._event_count += 1
    
    def log_settings_changed(self, group: str, parameter: str, value: str) -> None:
        """
        Log settings change
        
        Args:
            group: Settings group name
            parameter: Parameter name
            value: New value
        """
        logger.info(f"EVENT: Settings changed: {group}.{parameter} = {value}")
        self._event_count += 1
    
    def log_warning_added(self, text: str, priority: int = 0) -> None:
        """
        Log warning added
        
        Args:
            text: Warning text
            priority: Warning priority (0-2)
        """
        logger.warning(f"EVENT: Warning added (priority {priority}): {text}")
        self._event_count += 1
    
    def log_warning_removed(self, priority: int = 0) -> None:
        """
        Log warning removed
        
        Args:
            priority: Warning priority (0-2)
        """
        logger.info(f"EVENT: Warning removed (priority {priority})")
        self._event_count += 1
    
    def log_system_event(self, event: str, details: Optional[str] = None) -> None:
        """
        Log system event
        
        Args:
            event: Event description
            details: Optional additional details
        """
        if details:
            logger.info(f"EVENT: System event: {event} - {details}")
        else:
            logger.info(f"EVENT: System event: {event}")
        self._event_count += 1
    
    def get_event_count(self) -> int:
        """
        Get total number of events logged
        
        Returns:
            Total event count
        """
        return self._event_count

