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

This module handles logging configuration, log level management, a rotating
application log file, and an in-memory ring buffer for crash reports.
"""

from __future__ import annotations

import logging
import logging.handlers
import threading
from collections import deque
from pathlib import Path
from typing import Optional

# Global variable to store command-line log level (overrides settings)
# This will be set in the main block if --loglevel is provided
_command_line_log_level: Optional[str] = None

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 5
RINGBUFFER_LINES = 200

_file_handler: Optional[logging.Handler] = None
_ring_buffer_handler: Optional["RingBufferHandler"] = None


class RingBufferHandler(logging.Handler):
    """Keep the last N formatted log lines in memory for crash reports."""

    def __init__(self, maxlen: int = RINGBUFFER_LINES) -> None:
        super().__init__()
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            with self._lock:
                self._buffer.append(message)
        except Exception:
            self.handleError(record)

    def get_lines(self) -> list[str]:
        with self._lock:
            return list(self._buffer)


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
    
    _ensure_stream_handler(root_logger)
    _ensure_ring_buffer_handler(root_logger)

    for handler in root_logger.handlers:
        handler.setLevel(level)


def setup_file_logging(log_dir: Path) -> None:
    """
    Attach a rotating file handler for onairscreen.log.

    Safe to call more than once. The handler follows the current root log level,
    including NONE (nothing is written). Crash dumps are independent of this.
    """
    global _file_handler
    root_logger = logging.getLogger()
    if _file_handler is not None and _file_handler in root_logger.handlers:
        _file_handler.setLevel(root_logger.level)
        return

    log_path = Path(log_dir) / "onairscreen.log"
    try:
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError as error:
        logging.getLogger(__name__).warning(
            "Could not open log file %s: %s", log_path, error
        )
        return

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(root_logger.level)
    root_logger.addHandler(handler)
    _file_handler = handler


def get_recent_log_lines() -> list[str]:
    """Return the last formatted log lines from the in-memory ring buffer."""
    if _ring_buffer_handler is None:
        return []
    return _ring_buffer_handler.get_lines()


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


def _ensure_stream_handler(root_logger: logging.Logger) -> None:
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(handler)


def _ensure_ring_buffer_handler(root_logger: logging.Logger) -> None:
    global _ring_buffer_handler
    if _ring_buffer_handler is not None and _ring_buffer_handler in root_logger.handlers:
        return
    handler = RingBufferHandler(maxlen=RINGBUFFER_LINES)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(handler)
    _ring_buffer_handler = handler
