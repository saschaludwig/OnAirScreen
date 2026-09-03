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
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Hotkey Manager for OnAirScreen

This module handles keyboard shortcut bindings for the application.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence, QShortcut

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
        QShortcut(QKeySequence("T"), self.main_screen, self.main_screen.toggle_top_of_hour_countdown)
        
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

