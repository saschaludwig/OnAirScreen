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
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
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
    
    def exit_oas(self) -> None:
        """
        Exit the application with the same cleanup as keyboard quit.
        """
        self.main_screen.quit_oas()

