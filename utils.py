#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# utils.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

import logging
import re
import webbrowser
from contextlib import contextmanager

from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtNetwork import QAbstractSocket, QHostAddress

from defaults import DEFAULT_INSTANCE_NAME, MAX_INSTANCE_NAME_LENGTH

logger = logging.getLogger(__name__)

# Single DNS hostname label: 1-32 chars, LDH, no leading/trailing hyphen.
INSTANCE_NAME_PATTERN = re.compile(
    rf"^[A-Za-z0-9](?:[A-Za-z0-9-]{{0,{MAX_INSTANCE_NAME_LENGTH - 2}}}[A-Za-z0-9])?$"
)
INSTANCE_NAME_REGEX = (
    f"^[A-Za-z0-9](?:[A-Za-z0-9-]{{0,{MAX_INSTANCE_NAME_LENGTH - 2}}}[A-Za-z0-9])?$"
)


def host_address_is_ipv4(address: QHostAddress) -> bool:
    """True if address is IPv4.

    PySide6's QHostAddress.toIPv4Address() returns an int, not the
    (value, ok) tuple that older PyQt6 code expected.
    """
    return address.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol


def host_address_is_ipv6(address: QHostAddress) -> bool:
    """True if address is IPv6."""
    return address.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv6Protocol


@contextmanager
def settings_group(settings: QSettings, group_name: str):
    """
    Context manager for QSettings group operations
    
    Ensures that endGroup() is always called, even if an exception occurs.
    
    Args:
        settings: QSettings instance
        group_name: Name of the group to begin
        
    Yields:
        QSettings instance with the group active
    """
    settings.beginGroup(group_name)
    try:
        yield settings
    finally:
        settings.endGroup()


def is_valid_instance_name(value: str) -> bool:
    """Return True if value is a valid 1-32 character DNS hostname label."""
    if not isinstance(value, str):
        return False
    return bool(INSTANCE_NAME_PATTERN.fullmatch(value.strip()))


def normalize_instance_name(value) -> str:
    """
    Return a valid instance name.

    Trims whitespace. Invalid, empty, or non-string values fall back to
    DEFAULT_INSTANCE_NAME and are logged.
    """
    if not isinstance(value, str):
        logger.warning(
            "Invalid instance name type %s, using default %s",
            type(value).__name__,
            DEFAULT_INSTANCE_NAME,
        )
        return DEFAULT_INSTANCE_NAME
    trimmed = value.strip()
    if is_valid_instance_name(trimmed):
        return trimmed
    logger.warning(
        "Invalid instance name %r, using default %s",
        value,
        DEFAULT_INSTANCE_NAME,
    )
    return DEFAULT_INSTANCE_NAME


class TimerUpdateMessageBox(QtWidgets.QMessageBox):
    def __init__(self, timeout=10, json_reply=None, parent=None):
        super(TimerUpdateMessageBox, self).__init__(parent)
        self.json_reply = json_reply
        self.time_to_wait = timeout
        
        # Set OnAirScreen app icon
        icon = QIcon()
        icon.addPixmap(QPixmap(":/oas_icon/images/oas_icon.png"), QIcon.Mode.Normal, QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setIconPixmap(QPixmap(":/oas_icon/images/oas_icon.png"))
        
        self.setWindowTitle("OnAirScreen Update Check")
        self.setText("OnAirScreen Update Check")
        self.setFixedWidth(200)
        self.setInformativeText(f"{self.json_reply['Message']}\n"
                                f"{self.json_reply['Version']}\n"
                                f"(closing in {timeout} seconds)")
        download_button = QtWidgets.QPushButton('Download')
        close_button = QtWidgets.QPushButton('Close')
        download_button.clicked.connect(self.download_latest_version)
        self.addButton(close_button, QtWidgets.QMessageBox.ButtonRole.NoRole)
        self.addButton(download_button, QtWidgets.QMessageBox.ButtonRole.ActionRole)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.change_content)
        self.timer.start()

    def change_content(self):
        self.time_to_wait -= 1
        self.setInformativeText(f"{self.json_reply['Message']}\n"
                                f"{self.json_reply['Version']}\n"
                                f"(closing in {self.time_to_wait} seconds)")
        if self.time_to_wait <= 0:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

    def download_latest_version(self):
        if self.json_reply['URL']:
            webbrowser.open(self.json_reply['URL'])
