#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# crash_notice_dialog.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""Dialog shown on startup when the previous session crashed."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from crash_handler import (
    acknowledge_crash_notice,
    ensure_log_directory,
    should_show_crash_notice,
)
from exceptions import log_exception

logger = logging.getLogger(__name__)

DEFAULT_CRASH_NOTICE_TIMEOUT_MS = 30_000
_TICK_MS = 100


class CrashNoticeDialog(QDialog):
    """Modal notice that the previous session crashed; auto-closes after a timeout."""

    def __init__(
        self,
        parent: QWidget | None = None,
        timeout_ms: int = DEFAULT_CRASH_NOTICE_TIMEOUT_MS,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("OnAirScreen")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(420)

        timeout_ms = max(_TICK_MS, int(timeout_ms))
        self._timeout_ms = timeout_ms
        self._remaining_ms = timeout_ms

        message = QLabel(
            "The previous session ended with a crash.\n"
            "A report was written to the log folder."
        )
        message.setWordWrap(True)

        self._progress = QProgressBar()
        self._progress.setRange(0, timeout_ms)
        self._progress.setValue(timeout_ms)
        self._progress.setTextVisible(True)
        self._update_progress_format()

        open_button = QPushButton("Open log folder")
        open_button.clicked.connect(self._open_log_folder)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(open_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(message)
        layout.addWidget(self._progress)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._remaining_ms -= _TICK_MS
        if self._remaining_ms <= 0:
            self._timer.stop()
            self._progress.setValue(0)
            self.accept()
            return
        self._progress.setValue(self._remaining_ms)
        self._update_progress_format()

    def _update_progress_format(self) -> None:
        seconds = max(0, (self._remaining_ms + 999) // 1000)
        self._progress.setFormat(f"Closes in {seconds} s")

    def _open_log_folder(self) -> None:
        try:
            log_dir = ensure_log_directory()
        except OSError as error:
            log_exception(logger, error, use_exc_info=False)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))


def maybe_show_crash_notice(parent: QWidget | None = None) -> bool:
    """
    Show the crash notice if the previous session crashed, then acknowledge it.

    Returns True if the dialog was shown.
    """
    show = should_show_crash_notice()
    if show:
        dialog = CrashNoticeDialog(parent)
        dialog.exec()
    acknowledge_crash_notice()
    return show
