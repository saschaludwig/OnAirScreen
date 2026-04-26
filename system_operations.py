#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# system_operations.py
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
System Operations for OnAirScreen

This module handles system-level operations like reboot, shutdown, and application exit.
"""

import logging
import os
import subprocess
from typing import TYPE_CHECKING

from PyQt6.QtCore import QCoreApplication

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)


class SystemOperations:
    """
    Handles system-level operations for OnAirScreen
    
    This class provides methods for rebooting, shutting down the host system,
    and exiting the application.
    """
    
    def __init__(self, main_screen: "MainScreen"):
        """
        Initialize system operations
        
        Args:
            main_screen: Reference to MainScreen instance
        """
        self.main_screen = main_screen
    
    def reboot_host(self) -> None:
        """
        Reboot the host system safely using subprocess
        
        Displays a warning message and logs the event before attempting reboot.
        """
        self.main_screen.add_warning("SYSTEM REBOOT IN PROGRESS", 2)
        self.main_screen.event_logger.log_system_event("System reboot initiated")
        try:
            if os.name == "posix":
                # Use subprocess with explicit command list (no shell injection possible)
                subprocess.run(["sudo", "reboot"], check=False, timeout=5)
            elif os.name == "nt":
                # Windows: shutdown with explicit parameters
                subprocess.run(
                    ["shutdown", "/f", "/r", "/t", "0"],
                    check=False,
                    timeout=5
                )
            else:
                logger.warning(f"Unsupported OS for reboot: {os.name}")
        except subprocess.TimeoutExpired:
            logger.warning("Reboot command timed out (this may be expected)")
        except FileNotFoundError:
            logger.error("Reboot command not found on this system")
        except Exception as e:
            logger.error(f"Error executing reboot command: {e}")
            self.main_screen.event_logger.log_system_event(f"Reboot failed: {e}")
    
    def shutdown_host(self) -> None:
        """
        Shutdown the host system safely using subprocess
        
        Displays a warning message and logs the event before attempting shutdown.
        """
        self.main_screen.add_warning("SYSTEM SHUTDOWN IN PROGRESS", 2)
        self.main_screen.event_logger.log_system_event("System shutdown initiated")
        try:
            if os.name == "posix":
                # Use subprocess with explicit command list (no shell injection possible)
                subprocess.run(["sudo", "halt"], check=False, timeout=5)
            elif os.name == "nt":
                # Windows: shutdown with explicit parameters
                subprocess.run(
                    ["shutdown", "/f", "/s", "/t", "0"],
                    check=False,
                    timeout=5
                )
            else:
                logger.warning(f"Unsupported OS for shutdown: {os.name}")
        except subprocess.TimeoutExpired:
            logger.warning("Shutdown command timed out (this may be expected)")
        except FileNotFoundError:
            logger.error("Shutdown command not found on this system")
        except Exception as e:
            logger.error(f"Error executing shutdown command: {e}")
            self.main_screen.event_logger.log_system_event(f"Shutdown failed: {e}")
    
    @staticmethod
    def exit_oas() -> None:
        """
        Exit the application
        
        Static method to exit the QApplication instance.
        """
        QCoreApplication.instance().quit()

