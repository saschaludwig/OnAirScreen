#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for crash_notice_dialog.py
"""

import time

import pytest
from PySide6.QtWidgets import QApplication

from crash_handler import (
    acknowledge_crash_notice,
    mark_crash_for_next_start,
    set_log_directory_override,
    should_show_crash_notice,
)
from crash_notice_dialog import CrashNoticeDialog, maybe_show_crash_notice


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def log_dir(tmp_path):
    set_log_directory_override(tmp_path)
    yield tmp_path
    acknowledge_crash_notice()
    set_log_directory_override(None)


class TestCrashNoticeDialog:
    def test_auto_closes_after_timeout(self, qapp, log_dir):
        dialog = CrashNoticeDialog(timeout_ms=300)
        dialog.show()
        deadline = time.monotonic() + 2.0
        while dialog.isVisible() and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.02)
        assert not dialog.isVisible()

    def test_maybe_show_when_pending(self, qapp, log_dir, monkeypatch):
        mark_crash_for_next_start()

        class FastDialog(CrashNoticeDialog):
            def __init__(self, parent=None, timeout_ms=10000):
                super().__init__(parent, timeout_ms=200)

        monkeypatch.setattr("crash_notice_dialog.CrashNoticeDialog", FastDialog)
        shown = maybe_show_crash_notice()
        assert shown is True
        assert should_show_crash_notice() is False

    def test_maybe_show_when_no_crash(self, qapp, log_dir):
        shown = maybe_show_crash_notice()
        assert shown is False
        assert should_show_crash_notice() is False
