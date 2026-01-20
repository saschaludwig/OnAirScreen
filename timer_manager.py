#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# timer_manager.py
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
Timer Manager for OnAirScreen

This module manages timer objects and provides timer-related functionality
for AIR and LED timers.
"""

import logging
from typing import Callable, Optional

from PyQt6.QtCore import QTimer

logger = logging.getLogger(__name__)


class TimerManager:
    """
    Manages timer objects for AIR and LED functionality
    
    This class handles timer creation, starting, stopping, and provides
    callbacks for timer events.
    """
    
    def __init__(self, main_screen):
        """
        Initialize timer manager
        
        Args:
            main_screen: Reference to MainScreen instance for callbacks
        """
        self.main_screen = main_screen
        self._setup_timers()
    
    def _setup_timers(self) -> None:
        """Setup all timer objects"""
        # LED timers
        self.timerLED1 = QTimer()
        self.timerLED1.timeout.connect(self.main_screen.toggle_led1)
        self.timerLED2 = QTimer()
        self.timerLED2.timeout.connect(self.main_screen.toggle_led2)
        self.timerLED3 = QTimer()
        self.timerLED3.timeout.connect(self.main_screen.toggle_led3)
        self.timerLED4 = QTimer()
        self.timerLED4.timeout.connect(self.main_screen.toggle_led4)
        
        # AIR timers
        self.timerAIR1 = QTimer()
        self.timerAIR1.timeout.connect(self.main_screen.update_air1_seconds)
        self.timerAIR2 = QTimer()
        self.timerAIR2.timeout.connect(self.main_screen.update_air2_seconds)
        self.timerAIR3 = QTimer()
        self.timerAIR3.timeout.connect(self.main_screen.update_air3_seconds)
        self.timerAIR4 = QTimer()
        self.timerAIR4.timeout.connect(self.main_screen.update_air4_seconds)
    
    def get_led_timer(self, led_num: int) -> Optional[QTimer]:
        """
        Get LED timer for given LED number
        
        Args:
            led_num: LED number (1-4)
            
        Returns:
            QTimer instance or None if invalid
        """
        if led_num < 1 or led_num > 4:
            logger.warning(f"Invalid LED number: {led_num}")
            return None
        return getattr(self, f'timerLED{led_num}')
    
    def get_air_timer(self, air_num: int) -> Optional[QTimer]:
        """
        Get AIR timer for given AIR number
        
        Args:
            air_num: AIR number (1-4)
            
        Returns:
            QTimer instance or None if invalid
        """
        if air_num < 1 or air_num > 4:
            logger.warning(f"Invalid AIR number: {air_num}")
            return None
        return getattr(self, f'timerAIR{air_num}')

