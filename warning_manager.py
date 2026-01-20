#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# warning_manager.py
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
Warning Manager for OnAirScreen

This module manages warning messages with priority levels and displays
them in the UI.
"""

from typing import Callable, Optional
from PyQt6.QtWidgets import QLabel


class WarningManager:
    """
    Manages warning messages with priority levels
    
    Priority levels:
    - -1: NTP warnings (lowest priority, only shown if no other warnings)
    - 0: Normal/legacy warnings
    - 1: Medium priority warnings
    - 2: High priority warnings (highest priority)
    
    The manager displays the highest priority warning available,
    excluding NTP warnings if other warnings exist.
    """
    
    def __init__(self, 
                 label_warning: QLabel,
                 label_current_song: QLabel,
                 label_news: QLabel,
                 event_logger,
                 publish_mqtt_status_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the warning manager
        
        Args:
            label_warning: QLabel widget for displaying warning text
            label_current_song: QLabel widget for current song (hidden when warning shown)
            label_news: QLabel widget for news (hidden when warning shown)
            event_logger: EventLogger instance for logging warning events
            publish_mqtt_status_callback: Optional callback for publishing MQTT status
        """
        self.label_warning = label_warning
        self.label_current_song = label_current_song
        self.label_news = label_news
        self.event_logger = event_logger
        self.publish_mqtt_status = publish_mqtt_status_callback
        
        # init warning prio array (-1=NTP, 0=normal/legacy, 1=medium, 2=high)
        # Index mapping: 0=-1, 1=0, 2=1, 3=2
        self.warnings = ["", "", "", ""]
    
    @staticmethod
    def _priority_to_index(priority: int) -> int:
        """
        Convert priority to array index
        
        Priority -1 (NTP) -> Index 0
        Priority 0 (normal/legacy) -> Index 1
        Priority 1 (medium) -> Index 2
        Priority 2 (high) -> Index 3
        
        Args:
            priority: Warning priority level (-1 to 2)
            
        Returns:
            Array index (0 to 3)
        """
        return priority + 1
    
    def add_warning(self, text: str, priority: int = 0) -> None:
        """
        Add a warning message to the warning system
        
        Args:
            text: Warning message text
            priority: Warning priority level (-1=NTP, 0=normal/legacy, 1=medium, 2=high, default: 0)
        """
        # Convert priority to array index
        index = self._priority_to_index(priority)
        # Only log if warning actually changed
        old_text = self.warnings[index]
        self.warnings[index] = text
        if old_text != text:
            # Log warning added/updated event only if it changed
            if text:
                self.event_logger.log_warning_added(text, priority)
            elif old_text:
                # Warning was removed (text is now empty)
                self.event_logger.log_warning_removed(priority)
            # Note: process_warnings() is called by the timer in constant_update()
            # No need to call it here to avoid race conditions
    
    def remove_warning(self, priority: int = 0) -> None:
        """
        Remove warning message from the warning system
        
        Args:
            priority: Warning priority level (-1=NTP, 0=normal/legacy, 1=medium, 2=high, default: 0)
        """
        # Convert priority to array index
        index = self._priority_to_index(priority)
        # Only log if warning was actually present
        old_text = self.warnings[index]
        if old_text:
            self.warnings[index] = ""
            # Log warning removed event only if there was a warning
            self.event_logger.log_warning_removed(priority)
            # Note: process_warnings() is called by the timer in constant_update()
            # Publish MQTT status immediately after warning removal
            if self.publish_mqtt_status:
                self.publish_mqtt_status("warn")
            # No need to call it here to avoid race conditions
    
    def process_warnings(self) -> None:
        """
        Process all warnings and display the highest priority warning
        
        Checks all warning priority levels and displays the highest priority
        warning found (excluding NTP warnings if other warnings exist),
        or hides the warning label if no warnings are present.
        
        Priority order: 2 (high) > 1 (medium) > 0 (normal) > -1 (NTP)
        NTP warnings are only shown if no other warnings exist.
        """
        warning_available = False
        highest_warning = None
        highest_priority = -2  # Start below -1 to ensure we find something
        
        # Iterate through warnings in reverse priority order (2, 1, 0, -1)
        # Index mapping: 3=priority 2, 2=priority 1, 1=priority 0, 0=priority -1
        for index in range(3, -1, -1):  # 3, 2, 1, 0
            warning = self.warnings[index]
            if len(warning) > 0:
                priority = index - 1  # Convert index back to priority
                # Skip NTP warnings (-1) if we already found a higher priority warning
                if priority == -1 and highest_priority > -1:
                    continue
                highest_warning = warning
                highest_priority = priority
                warning_available = True
                # If we found a non-NTP warning, we're done (don't check lower priorities)
                if priority >= 0:
                    break
        
        if warning_available:
            self.show_warning(highest_warning)
        else:
            self.hide_warning()
    
    def show_warning(self, text: str) -> None:
        """
        Show warning message in the UI
        
        Hides current song and news labels and displays warning text with large font.
        
        Args:
            text: Warning message text to display
        """
        self.label_current_song.hide()
        self.label_news.hide()
        self.label_warning.setText(text)
        font = self.label_warning.font()
        font.setPointSize(45)
        self.label_warning.setFont(font)
        self.label_warning.show()
    
    def hide_warning(self, priority: int = 0) -> None:
        """
        Hide warning message and restore normal UI
        
        Args:
            priority: Warning priority level (0-2, default: 0, currently unused)
        """
        self.label_warning.hide()
        self.label_current_song.show()
        self.label_news.show()
        self.label_warning.setText("")
        self.label_warning.hide()
    
    def get_warnings(self) -> list:
        """
        Get all active warnings with their priorities
        
        Returns:
            List of dictionaries with 'priority' and 'text' keys
        """
        warnings = []
        # Iterate through priorities: -1 (NTP), 0 (normal), 1 (medium), 2 (high)
        for priority in range(-1, 3):  # Priorities -1, 0, 1, 2
            index = priority + 1  # Convert priority to index
            if 0 <= index < len(self.warnings) and self.warnings[index]:
                warnings.append({
                    'priority': priority,
                    'text': self.warnings[index]
                })
        return warnings

