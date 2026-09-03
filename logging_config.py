#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# logging_config.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Logging Configuration for OnAirScreen

This module handles logging configuration and log level management.
"""

import logging
from typing import Optional

# Global variable to store command-line log level (overrides settings)
# This will be set in the main block if --loglevel is provided
_command_line_log_level: Optional[str] = None


def set_log_level(log_level_str: str) -> None:
    """
    Set the global log level for all loggers
    
    Args:
        log_level_str: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL, NONE)
                      For NONE, logging is effectively disabled (CRITICAL+1)
    """
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "NONE": logging.CRITICAL + 1,  # Disables all logging
    }
    
    level = log_level_map.get(log_level_str.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Configure handler if not already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(handler)


def get_command_line_log_level() -> Optional[str]:
    """
    Get the command-line log level if set
    
    Returns:
        Command-line log level string or None if not set
    """
    return _command_line_log_level


def set_command_line_log_level(log_level: Optional[str]) -> None:
    """
    Set the command-line log level
    
    Args:
        log_level: Log level string or None to clear
    """
    global _command_line_log_level
    _command_line_log_level = log_level

