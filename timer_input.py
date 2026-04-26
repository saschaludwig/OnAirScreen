#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# timer_input.py
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
Timer Input Dialog for OnAirScreen

This module provides a dialog for entering timer values in various formats.
"""

import re
import logging
from typing import Callable, Optional
from PyQt6.QtWidgets import QDialog, QLineEdit, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, QObject

from exceptions import WidgetAccessError, ValueValidationError, log_exception

logger = logging.getLogger(__name__)


class TimerInputDialog(QDialog):
    """
    Dialog for entering timer values
    
    Supports formats:
    - "2,10" or "2.10" for 2 minutes 10 seconds
    - "30" for 30 seconds only
    """
    
    timer_set = pyqtSignal(int)  # Emitted with total seconds when timer is set
    
    def __init__(self, parent=None):
        """
        Initialize the timer input dialog
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.resize(200, 100)
        self.setWindowTitle("Please enter timer")
        
        self.timeEdit = QLineEdit("Enter timer here")
        self.timeEdit.selectAll()
        self.infoLabel = QLabel("Examples:\nenter 2,10 for 2:10 minutes\nenter 30 for 30 seconds")
        
        layout = QVBoxLayout()
        layout.addWidget(self.infoLabel)
        layout.addWidget(self.timeEdit)
        self.setLayout(layout)
        
        self.timeEdit.setFocus()
        self.timeEdit.returnPressed.connect(self._parse_and_emit)
    
    def _parse_and_emit(self) -> None:
        """Parse input and emit timer_set signal"""
        try:
            total_seconds = self._parse_timer_input()
            if total_seconds is not None:
                self.timer_set.emit(total_seconds)
                self.hide()
        except Exception as e:
            from exceptions import OnAirScreenError, WidgetError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = WidgetError(f"Error parsing timer input: {e}")
                log_exception(logger, error)
    
    def _parse_timer_input(self) -> Optional[int]:
        """
        Parse timer input from dialog and return total seconds
        
        Handles formats:
        - "2,10" or "2.10" for 2 minutes 10 seconds
        - "30" for 30 seconds only
        
        Returns:
            Total seconds, or None if input is invalid
        """
        # Get and validate input text
        try:
            text = str(self.timeEdit.text()).strip()
        except (AttributeError, RuntimeError) as e:
            error = WidgetAccessError(
                f"Error getting timer input text: {e}",
                widget_name="timeEdit",
                attribute="text"
            )
            log_exception(logger, error, use_exc_info=False)
            return None
        
        # Validate input is not empty
        if not text or text == "Enter timer here":
            logger.warning("parse_timer_input: Empty or default input, ignoring")
            return None
        
        minutes = 0
        seconds = 0
        parsed = False
        
        # Try comma format: "2,10" for 2 minutes 10 seconds
        if re.match('^[0-9]+,[0-9]+$', text):
            try:
                parts = text.split(",")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    # Validate seconds are in valid range (0-59)
                    if seconds < 0 or seconds >= 60:
                        logger.warning(f"parse_timer_input: Invalid seconds value {seconds}, must be 0-59")
                        return None
                    parsed = True
            except (ValueError, IndexError) as e:
                error = ValueValidationError(
                    f"parse_timer_input: Error parsing comma format '{text}': {e}",
                    value=text
                )
                log_exception(logger, error, use_exc_info=False)
                return None
        
        # Try dot format: "2.10" for 2 minutes 10 seconds
        elif re.match(r'^[0-9]+\.[0-9]+$', text):
            try:
                parts = text.split(".")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    # Validate seconds are in valid range (0-59)
                    if seconds < 0 or seconds >= 60:
                        logger.warning(f"parse_timer_input: Invalid seconds value {seconds}, must be 0-59")
                        return None
                    parsed = True
            except (ValueError, IndexError) as e:
                error = ValueValidationError(
                    f"parse_timer_input: Error parsing dot format '{text}': {e}",
                    value=text
                )
                log_exception(logger, error, use_exc_info=False)
                return None
        
        # Try seconds-only format: "30" for 30 seconds
        elif re.match('^[0-9]+$', text):
            try:
                seconds = int(text)
                if seconds < 0:
                    logger.warning(f"parse_timer_input: Negative seconds value {seconds}")
                    return None
                parsed = True
            except ValueError as e:
                logger.error(f"parse_timer_input: Error parsing seconds format '{text}': {e}")
                return None
        
        # If no format matched, show error
        if not parsed:
            logger.warning(f"parse_timer_input: Invalid input format '{text}'. Expected: '2,10', '2.10', or '30'")
            return None
        
        # Calculate total seconds
        total_seconds = (minutes * 60) + seconds
        
        # Validate total is reasonable (max 24 hours = 86400 seconds)
        if total_seconds > 86400:
            logger.warning(f"parse_timer_input: Timer value too large: {total_seconds} seconds (max 86400)")
            return None
        
        logger.info(f"parse_timer_input: Parsed timer to {minutes}:{seconds:02d} ({total_seconds} seconds)")
        return total_seconds

