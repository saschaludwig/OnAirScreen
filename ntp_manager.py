#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# ntp_manager.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
NTP Manager for OnAirScreen

This module manages NTP time synchronization checking and warnings.
"""

import logging
import socket
import time
from typing import TYPE_CHECKING, Optional

import ntplib
from PySide6.QtCore import QObject, QSettings, QThread, QTimer, Signal

from defaults import (
    DEFAULT_NTP_CHECK,
    DEFAULT_NTP_CHECK_SERVER,
    DEFAULT_TIME_SOURCE,
    TIME_SOURCE_NTP,
    TIME_SOURCE_PTP,
)
from exceptions import WidgetAccessError, log_exception
from utils import settings_group

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)


class CheckNTPOffsetThread(QThread):
    """
    Thread for checking NTP time synchronization offset
    
    Periodically checks the system clock against an NTP server
    and warns if the offset is too large.
    """

    def __init__(self, ntp_manager: "NTPManager"):
        """
        Initialize NTP check thread
        
        Args:
            ntp_manager: Reference to NTPManager instance
        """
        self.ntp_manager = ntp_manager
        QThread.__init__(self)
        self._initialized = True  # Mark that __init__ was called

    def __del__(self):
        try:
            # Only call wait() if the thread was properly initialized
            # This prevents errors when the object is created with __new__() in tests
            if hasattr(self, '_initialized') and self._initialized:
                self.wait()
        except (RuntimeError, AttributeError) as e:
            # Thread was never initialized or already destroyed
            # Log but don't raise - this is expected in some scenarios
            error = WidgetAccessError(
                f"Error accessing NTP check thread (thread may not be initialized): {e}",
                widget_name="checkNTPOffset",
                attribute="stop"
            )
            log_exception(logger, error, use_exc_info=False)
            pass

    def run(self):
        logger.debug("entered CheckNTPOffsetThread.run")
        generation = getattr(self.ntp_manager, "_poll_generation", 0)
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            ntp_server = str(settings.value('ntpcheckserver', DEFAULT_NTP_CHECK_SERVER))
        max_deviation = 0.3
        c = ntplib.NTPClient()
        try:
            response = c.request(ntp_server)
            if not self._generation_is_current(generation):
                return
            tx_time = getattr(response, "tx_time", None)
            delay = getattr(response, "delay", 0.0)
            try:
                ntp_unix = float(tx_time) + float(delay or 0.0) / 2.0
            except (TypeError, ValueError):
                ntp_unix = None
            if ntp_unix is not None:
                self.ntp_manager.sample_ready.emit(ntp_unix, time.monotonic())
            settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
            with settings_group(settings, "TimeSource"):
                source = settings.value("source", DEFAULT_TIME_SOURCE, type=str) or DEFAULT_TIME_SOURCE
            # When NTP is the display source, offset-vs-system is not a failure.
            if source == TIME_SOURCE_NTP:
                if self.ntp_manager.ntp_had_warning:
                    self.ntp_manager.ntp_had_warning = False
            else:
                offset = response.offset
                if source == TIME_SOURCE_PTP and ntp_unix is not None:
                    try:
                        from time_source import wall_datetime
                        offset = wall_datetime().timestamp() - ntp_unix
                    except (OSError, OverflowError, ValueError, TypeError):
                        offset = response.offset
                if offset > max_deviation or offset < -max_deviation:
                    logger.warning(f"offset too big: {offset} while checking {ntp_server}")
                    self.ntp_manager.ntp_warn_message = "Clock not NTP synchronized: offset too big"
                    self.ntp_manager.ntp_had_warning = True
                else:
                    if self.ntp_manager.ntp_had_warning:
                        self.ntp_manager.ntp_had_warning = False
        except socket.timeout:
            logger.error(f"NTP error: timeout while checking NTP {ntp_server}")
            self._mark_ntp_unreachable(generation)
        except socket.gaierror:
            logger.error(f"NTP error: socket error while checking NTP {ntp_server}")
            self._mark_ntp_unreachable(generation)
        except (OSError, ntplib.NTPException) as e:
            logger.error(f"NTP error: {e}")
            message = str(e) if isinstance(e, ntplib.NTPException) else None
            self._mark_ntp_unreachable(generation, message)

    def _generation_is_current(self, generation: int) -> bool:
        return getattr(self.ntp_manager, "_poll_generation", 0) == generation

    def _mark_ntp_unreachable(self, generation: int, message: Optional[str] = None) -> None:
        """Record an NTP poll failure and notify the time-source manager."""
        if not self._generation_is_current(generation):
            return
        self.ntp_manager.ntp_warn_message = message or "Clock not NTP synchronized"
        self.ntp_manager.ntp_had_warning = True
        self.ntp_manager.poll_failed.emit()

    def stop(self):
        self.quit()


class NTPManager(QObject):
    """
    Manages NTP time synchronization checking and warnings
    
    This class handles NTP offset checking, warning management,
    and provides methods for updating NTP status in the UI.
    """

    sample_ready = Signal(float, float)
    poll_failed = Signal()
    
    def __init__(self, main_screen: "MainScreen"):
        """
        Initialize NTP manager
        
        Args:
            main_screen: Reference to MainScreen instance for warning updates
        """
        super().__init__(main_screen)
        self.main_screen = main_screen
        
        # NTP warning state
        self.ntp_had_warning = True
        self.ntp_warn_message = ""
        self._force_poll = False
        self._poll_generation = 0
        
        # Setup NTP Check Thread
        self.check_ntp_offset = CheckNTPOffsetThread(self)
        
        # Setup check NTP Timer
        self.timer_ntp = QTimer(self)
        self.timer_ntp.timeout.connect(self.trigger_ntp_check)
        
        # Initialize NTP check state from settings
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            if settings.value('ntpcheck', True, type=bool):
                self.ntp_had_warning = True
                self.ntp_warn_message = "waiting for NTP status check"
        
        # Start initial check
        self.timer_ntp.start(1000)
    
    def trigger_ntp_check(self) -> None:
        """
        Trigger NTP offset check
        
        Checks if NTP checking is enabled and triggers NTP offset check.
        """
        logger.debug("NTP Check triggered")
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            ntp_check = settings.value('ntpcheck', DEFAULT_NTP_CHECK, type=bool)
        if not ntp_check and not self._force_poll:
            self.timer_ntp.stop()
            return
        else:
            self.timer_ntp.stop()
            self.check_ntp_offset.start()
            self.timer_ntp.start(60000)

    def apply_settings(self, force_poll: bool = False) -> None:
        """Start or stop NTP polling after settings were applied."""
        self._force_poll = force_poll
        self._poll_generation += 1
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            ntp_check = settings.value('ntpcheck', DEFAULT_NTP_CHECK, type=bool)
        if ntp_check or force_poll:
            if not self.ntp_warn_message:
                self.ntp_had_warning = True
                self.ntp_warn_message = "waiting for NTP status check"
            self.timer_ntp.start(1000)
        else:
            self.timer_ntp.stop()
            self.ntp_had_warning = False
            self.ntp_warn_message = ""
            self.main_screen.remove_warning(-1)
    
    def update_ntp_status(self) -> None:
        """
        Update NTP status warning (priority -1)
        
        Updates the warning system with current NTP status.
        """
        if self.ntp_had_warning and len(self.ntp_warn_message):
            self.main_screen.add_warning(self.ntp_warn_message, -1)
        else:
            self.main_screen.remove_warning(-1)
            self.ntp_warn_message = ""
    
    def stop(self) -> None:
        """Stop NTP checking"""
        self.check_ntp_offset.stop()
        self.timer_ntp.stop()

