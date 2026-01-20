#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# hotkey_manager.py
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
Hotkey Manager for OnAirScreen

This module handles keyboard shortcut bindings for the application.
"""

from typing import TYPE_CHECKING

from PyQt6.QtGui import QKeySequence, QShortcut

if TYPE_CHECKING:
    from start import MainScreen


class HotkeyManager:
    """
    Manages keyboard shortcuts for OnAirScreen
    
    This class sets up all hotkey bindings for application control.
    """
    
    def __init__(self, main_screen: "MainScreen"):
        """
        Initialize hotkey manager and set up all shortcuts
        
        Args:
            main_screen: Reference to MainScreen instance
        """
        self.main_screen = main_screen
        self._setup_hotkeys()
    
    def _setup_hotkeys(self) -> None:
        """Setup all keyboard shortcuts"""
        # Fullscreen toggle
        QShortcut(QKeySequence("Ctrl+F"), self.main_screen, self.main_screen.toggle_full_screen)
        QShortcut(QKeySequence("F"), self.main_screen, self.main_screen.toggle_full_screen)
        QShortcut(QKeySequence(16777429), self.main_screen, self.main_screen.toggle_full_screen)  # 'Display' Key on OAS USB Keyboard
        QShortcut(QKeySequence(16777379), self.main_screen, self.main_screen.shutdown_host)  # 'Calculator' Key on OAS USB Keyboard
        
        # Quit application
        QShortcut(QKeySequence("Ctrl+Q"), self.main_screen, self.main_screen.quit_oas)
        QShortcut(QKeySequence("Q"), self.main_screen, self.main_screen.quit_oas)
        QShortcut(QKeySequence("Ctrl+C"), self.main_screen, self.main_screen.quit_oas)
        QShortcut(QKeySequence("ESC"), self.main_screen, self.main_screen.quit_oas)
        
        # Settings
        QShortcut(QKeySequence("Ctrl+S"), self.main_screen, self.main_screen.show_settings)
        QShortcut(QKeySequence("Ctrl+,"), self.main_screen, self.main_screen.show_settings)
        
        # Radio timer controls
        QShortcut(QKeySequence(" "), self.main_screen, self.main_screen.radio_timer_start_stop)
        QShortcut(QKeySequence(","), self.main_screen, self.main_screen.radio_timer_start_stop)
        QShortcut(QKeySequence("."), self.main_screen, self.main_screen.radio_timer_start_stop)
        QShortcut(QKeySequence("0"), self.main_screen, self.main_screen.radio_timer_reset)
        QShortcut(QKeySequence("R"), self.main_screen, self.main_screen.radio_timer_reset)
        
        # LED controls
        QShortcut(QKeySequence("1"), self.main_screen, self.main_screen.manual_toggle_led1)
        QShortcut(QKeySequence("2"), self.main_screen, self.main_screen.manual_toggle_led2)
        QShortcut(QKeySequence("3"), self.main_screen, self.main_screen.manual_toggle_led3)
        QShortcut(QKeySequence("4"), self.main_screen, self.main_screen.manual_toggle_led4)
        
        # AIR controls
        QShortcut(QKeySequence("M"), self.main_screen, self.main_screen.toggle_air1)
        QShortcut(QKeySequence("/"), self.main_screen, self.main_screen.toggle_air1)
        QShortcut(QKeySequence("P"), self.main_screen, self.main_screen.toggle_air2)
        QShortcut(QKeySequence("*"), self.main_screen, self.main_screen.toggle_air2)
        QShortcut(QKeySequence("S"), self.main_screen, self.main_screen.toggle_air4)
        
        # Other controls
        QShortcut(QKeySequence("I"), self.main_screen, self.main_screen.display_ips)
        QShortcut(QKeySequence("Alt+S"), self.main_screen, self.main_screen.stream_timer_reset)
        
        # Timer dialog
        QShortcut(QKeySequence("Enter"), self.main_screen, self.main_screen.get_timer_dialog)
        QShortcut(QKeySequence("Return"), self.main_screen, self.main_screen.get_timer_dialog)

