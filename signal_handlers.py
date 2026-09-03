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

from PySide6.QtWidgets import QApplication


def sigint_handler(*args) -> None:
    """
    Handler for SIGINT signal (Ctrl+C)
    
    Gracefully quits the application when interrupted.
    """
    sys.stderr.write("\n")
    QApplication.quit()


def setup_signal_handlers() -> None:
    """
    Setup signal handlers for the application
    
    Registers SIGINT handler for graceful shutdown on Ctrl+C.
    """
    import signal
    signal.signal(signal.SIGINT, sigint_handler)

