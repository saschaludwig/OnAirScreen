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
NTP Manager for OnAirScreen

This module manages NTP time synchronization checking and warnings.
"""

import logging
import socket
from typing import TYPE_CHECKING

import ntplib
from PyQt6.QtCore import QSettings, QTimer, QThread

from defaults import DEFAULT_NTP_CHECK_SERVER
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
        settings = QSettings(QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "NTP"):
            ntp_server = str(settings.value('ntpcheckserver', DEFAULT_NTP_CHECK_SERVER))
        max_deviation = 0.3
        c = ntplib.NTPClient()
        try:
            response = c.request(ntp_server)
            if response.offset > max_deviation or response.offset < -max_deviation:
                logger.warning(f"offset too big: {response.offset} while checking {ntp_server}")
                self.ntp_manager.ntp_warn_message = "Clock not NTP synchronized: offset too big"
                self.ntp_manager.ntp_had_warning = True
            else:
                if self.ntp_manager.ntp_had_warning:
                    self.ntp_manager.ntp_had_warning = False
        except socket.timeout:
            logger.error(f"NTP error: timeout while checking NTP {ntp_server}")
            self.ntp_manager.ntp_warn_message = "Clock not NTP synchronized"
            self.ntp_manager.ntp_had_warning = True
        except socket.gaierror:
            logger.error(f"NTP error: socket error while checking NTP {ntp_server}")
            self.ntp_manager.ntp_warn_message = "Clock not NTP synchronized"
            self.ntp_manager.ntp_had_warning = True
        except ntplib.NTPException as e:
            logger.error(f"NTP error: {e}")
            self.ntp_manager.ntp_warn_message = str(e)
            self.ntp_manager.ntp_had_warning = True

    def stop(self):
        self.quit()


class NTPManager:
    """
    Manages NTP time synchronization checking and warnings
    
    This class handles NTP offset checking, warning management,
    and provides methods for updating NTP status in the UI.
    """
    
    def __init__(self, main_screen: "MainScreen"):
        """
        Initialize NTP manager
        
        Args:
            main_screen: Reference to MainScreen instance for warning updates
        """
        self.main_screen = main_screen
        
        # NTP warning state
        self.ntp_had_warning = True
        self.ntp_warn_message = ""
        
        # Setup NTP Check Thread
        self.check_ntp_offset = CheckNTPOffsetThread(self)
        
        # Setup check NTP Timer
        self.timer_ntp = QTimer()
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
            ntp_check = settings.value('ntpcheck', True, type=bool)
        if not ntp_check:
            self.timer_ntp.stop()
            return
        else:
            self.timer_ntp.stop()
            self.check_ntp_offset.start()
            self.timer_ntp.start(60000)
    
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

