#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# signal_handlers.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Signal Handlers for OnAirScreen

This module handles system signals for graceful application shutdown.
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def _quit_on_air_screen() -> None:
    """Quit via MainScreen so the QUITTING WARN is shown."""
    app = QApplication.instance()
    if app is None:
        sys.exit(1)
    for widget in app.topLevelWidgets():
        quit_oas = getattr(widget, "quit_oas", None)
        if callable(quit_oas):
            quit_oas()
            return
    app.quit()


def sigint_handler(*args) -> None:
    """
    Handler for SIGINT signal (Ctrl+C)

    Posts a MainScreen quit onto the event loop so the on-screen WARN can paint.
    """
    sys.stderr.write("\n")
    QTimer.singleShot(0, _quit_on_air_screen)


def setup_signal_handlers() -> None:
    """
    Setup signal handlers for the application
    
    Registers SIGINT handler for graceful shutdown on Ctrl+C.
    """
    import signal
    signal.signal(signal.SIGINT, sigint_handler)
