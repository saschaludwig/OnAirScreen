#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for crash_handler.py and persistent logging.
"""

import asyncio
import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crash_handler import (
    CRASH_FILE_PREFIX,
    CRASH_FILE_SUFFIX,
    FAULT_LOG_NAME,
    MAX_CRASH_FILES,
    PENDING_NOTICE_NAME,
    acknowledge_crash_notice,
    collect_environment_info,
    get_log_directory,
    install_asyncio_exception_handler,
    install_crash_hooks,
    mark_crash_for_next_start,
    set_log_directory_override,
    set_terminate_on_uncaught,
    should_show_crash_notice,
    uninstall_crash_hooks,
    write_crash_report,
)
from logging_config import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    RingBufferHandler,
    get_recent_log_lines,
    set_log_level,
    setup_file_logging,
)


SECRET_MARKERS = ("mqttpassword", "owmAPIKey", "updatekey")


@pytest.fixture
def log_dir(tmp_path):
    """Isolate crash/log files in a temp directory and restore hooks afterwards."""
    set_log_directory_override(tmp_path)
    set_terminate_on_uncaught(False)
    yield tmp_path
    uninstall_crash_hooks()
    set_terminate_on_uncaught(True)
    set_log_directory_override(None)


@pytest.fixture
def isolated_root_logger():
    """Save and restore the root logger so file/ring handlers do not leak."""
    import logging_config

    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    yield root
    for handler in list(root.handlers):
        if handler not in old_handlers:
            handler.close()
            root.removeHandler(handler)
    root.handlers.clear()
    for handler in old_handlers:
        root.addHandler(handler)
    root.setLevel(old_level)
    logging_config._file_handler = None
    logging_config._ring_buffer_handler = None


class TestLogDirectory:
    def test_override_used_when_set(self, log_dir):
        assert get_log_directory() == log_dir

    def test_macos_path(self, monkeypatch):
        set_log_directory_override(None)
        monkeypatch.setattr("crash_handler.platform.system", lambda: "Darwin")
        monkeypatch.setattr("crash_handler.Path.home", lambda: Path("/Users/demo"))
        assert get_log_directory() == Path("/Users/demo/Library/Logs/OnAirScreen")

    def test_windows_path_uses_localappdata(self, monkeypatch):
        set_log_directory_override(None)
        monkeypatch.setattr("crash_handler.platform.system", lambda: "Windows")
        monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\demo\AppData\Local")
        path = get_log_directory()
        assert path == Path(r"C:\Users\demo\AppData\Local") / "astrastudio" / "OnAirScreen" / "logs"

    def test_linux_path(self, monkeypatch):
        set_log_directory_override(None)
        monkeypatch.setattr("crash_handler.platform.system", lambda: "Linux")
        monkeypatch.setattr("crash_handler.Path.home", lambda: Path("/home/demo"))
        assert get_log_directory() == Path(
            "/home/demo/.local/share/astrastudio/OnAirScreen/logs"
        )


class TestCrashReport:
    def test_writes_crash_file_with_traceback(self, log_dir):
        path = write_crash_report(
            ValueError,
            ValueError("boom"),
            None,
            thread_name="MainThread",
            source="test",
        )
        assert path is not None
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "OnAirScreen crash report" in text
        assert "ValueError" in text
        assert "boom" in text
        assert "Thread: MainThread" in text
        assert "Source: test" in text
        assert "Version:" in text
        assert "Python:" in text

    def test_crash_report_contains_no_secrets(self, log_dir):
        path = write_crash_report(RuntimeError, RuntimeError("fail"), None)
        text = path.read_text(encoding="utf-8").lower()
        for marker in SECRET_MARKERS:
            assert marker.lower() not in text

    def test_environment_info_has_no_secrets(self):
        info = collect_environment_info()
        joined = " ".join(f"{k}={v}" for k, v in info.items()).lower()
        for marker in SECRET_MARKERS:
            assert marker.lower() not in joined
        assert "Version" in info
        assert "Frozen" in info

    def test_includes_recent_log_lines(self, log_dir, isolated_root_logger):
        isolated_root_logger.handlers.clear()
        set_log_level("INFO")
        logging.getLogger("crash_test").info("ring-buffer-line-xyz")
        path = write_crash_report(RuntimeError, RuntimeError("fail"), None)
        text = path.read_text(encoding="utf-8")
        assert "Last log lines" in text
        assert "ring-buffer-line-xyz" in text

    def test_prunes_old_crash_files(self, log_dir):
        for index in range(12):
            old = log_dir / f"{CRASH_FILE_PREFIX}old{index:02d}{CRASH_FILE_SUFFIX}"
            old.write_text("old", encoding="utf-8")
            os.utime(old, (index, index))
        write_crash_report(RuntimeError, RuntimeError("newest"), None)
        remaining = list(log_dir.glob(f"{CRASH_FILE_PREFIX}*{CRASH_FILE_SUFFIX}"))
        assert len(remaining) == MAX_CRASH_FILES
        newest_text = "\n".join(p.read_text(encoding="utf-8") for p in remaining)
        assert "newest" in newest_text


class TestCrashHooks:
    def test_sys_excepthook_writes_file(self, log_dir):
        install_crash_hooks(log_dir)
        sys.excepthook(ValueError, ValueError("hooked"), None)
        crashes = list(log_dir.glob(f"{CRASH_FILE_PREFIX}*{CRASH_FILE_SUFFIX}"))
        assert len(crashes) == 1
        assert "hooked" in crashes[0].read_text(encoding="utf-8")

    def test_sys_excepthook_terminates_after_write(self, log_dir, monkeypatch):
        install_crash_hooks(log_dir)
        terminate = MagicMock()
        monkeypatch.setattr("crash_handler._terminate_after_crash", terminate)
        sys.excepthook(ValueError, ValueError("hooked"), None)
        terminate.assert_called_once()

    def test_terminate_after_crash_raises_systemexit(self, log_dir):
        import crash_handler

        crash_handler.set_terminate_on_uncaught(True)
        try:
            with pytest.raises(SystemExit) as exc_info:
                crash_handler._terminate_after_crash(1)
            assert exc_info.value.code == 1
        finally:
            crash_handler.set_terminate_on_uncaught(False)

    def test_keyboard_interrupt_does_not_write_or_terminate(self, log_dir, monkeypatch):
        import crash_handler

        install_crash_hooks(log_dir)
        crash_handler._original_excepthook = lambda *args: None
        terminate = MagicMock()
        monkeypatch.setattr("crash_handler._terminate_after_crash", terminate)
        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
        assert list(log_dir.glob(f"{CRASH_FILE_PREFIX}*{CRASH_FILE_SUFFIX}")) == []
        terminate.assert_not_called()

    def test_thread_excepthook_does_not_terminate(self, log_dir, monkeypatch):
        import crash_handler

        install_crash_hooks(log_dir)
        crash_handler._original_thread_excepthook = lambda args: None
        terminate = MagicMock()
        monkeypatch.setattr("crash_handler._terminate_after_crash", terminate)
        args = MagicMock()
        args.exc_type = RuntimeError
        args.exc_value = RuntimeError("thread-fail")
        args.exc_traceback = None
        args.thread = threading.current_thread()
        threading.excepthook(args)
        crashes = list(log_dir.glob(f"{CRASH_FILE_PREFIX}*{CRASH_FILE_SUFFIX}"))
        assert len(crashes) == 1
        text = crashes[0].read_text(encoding="utf-8")
        assert "thread-fail" in text
        assert "threading.excepthook" in text
        terminate.assert_not_called()

    def test_faulthandler_opens_fault_log(self, log_dir):
        install_crash_hooks(log_dir)
        assert (log_dir / FAULT_LOG_NAME).exists()

    def test_asyncio_handler_does_not_terminate(self, log_dir, monkeypatch):
        terminate = MagicMock()
        monkeypatch.setattr("crash_handler._terminate_after_crash", terminate)
        loop = asyncio.new_event_loop()
        try:
            install_asyncio_exception_handler(loop)
            loop.call_exception_handler({"exception": ValueError("aio-fail")})
        finally:
            loop.close()
        crashes = list(log_dir.glob(f"{CRASH_FILE_PREFIX}*{CRASH_FILE_SUFFIX}"))
        assert len(crashes) == 1
        assert "aio-fail" in crashes[0].read_text(encoding="utf-8")
        terminate.assert_not_called()

    def test_install_is_idempotent(self, log_dir):
        install_crash_hooks(log_dir)
        first_hook = sys.excepthook
        install_crash_hooks(log_dir)
        assert sys.excepthook is first_hook


class TestFileLogging:
    def test_setup_file_logging_writes(self, log_dir, isolated_root_logger):
        isolated_root_logger.handlers.clear()
        set_log_level("INFO")
        setup_file_logging(log_dir)
        logging.getLogger("file_test").info("persisted-line")
        for handler in isolated_root_logger.handlers:
            handler.flush()
        log_file = log_dir / "onairscreen.log"
        assert log_file.exists()
        assert "persisted-line" in log_file.read_text(encoding="utf-8")

    def test_file_handler_is_rotating(self, log_dir, isolated_root_logger):
        isolated_root_logger.handlers.clear()
        set_log_level("INFO")
        setup_file_logging(log_dir)
        rotating = [
            h
            for h in isolated_root_logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(rotating) == 1
        assert rotating[0].maxBytes == LOG_MAX_BYTES
        assert rotating[0].backupCount == LOG_BACKUP_COUNT

    def test_setup_file_logging_does_not_duplicate(self, log_dir, isolated_root_logger):
        isolated_root_logger.handlers.clear()
        set_log_level("INFO")
        setup_file_logging(log_dir)
        count_after_first = len(isolated_root_logger.handlers)
        setup_file_logging(log_dir)
        assert len(isolated_root_logger.handlers) == count_after_first

    def test_none_level_does_not_write_info(self, log_dir, isolated_root_logger):
        isolated_root_logger.handlers.clear()
        set_log_level("NONE")
        setup_file_logging(log_dir)
        logging.getLogger("file_test").info("should-not-appear")
        for handler in isolated_root_logger.handlers:
            handler.flush()
        log_file = log_dir / "onairscreen.log"
        if log_file.exists():
            assert "should-not-appear" not in log_file.read_text(encoding="utf-8")

    def test_ring_buffer_captures_lines(self, isolated_root_logger):
        isolated_root_logger.handlers.clear()
        set_log_level("INFO")
        logging.getLogger("ring").warning("buffered-warning")
        lines = get_recent_log_lines()
        assert any("buffered-warning" in line for line in lines)
        assert any(isinstance(h, RingBufferHandler) for h in isolated_root_logger.handlers)


class TestCrashNoticeMarkers:
    def test_no_notice_on_fresh_log_dir(self, log_dir):
        assert should_show_crash_notice() is False

    def test_pending_marker_shows_notice(self, log_dir):
        mark_crash_for_next_start()
        assert (log_dir / PENDING_NOTICE_NAME).is_file()
        assert should_show_crash_notice() is True

    def test_acknowledge_clears_pending(self, log_dir):
        mark_crash_for_next_start()
        acknowledge_crash_notice()
        assert should_show_crash_notice() is False
        assert not (log_dir / PENDING_NOTICE_NAME).exists()

    def test_fault_log_growth_shows_notice(self, log_dir):
        acknowledge_crash_notice()
        assert should_show_crash_notice() is False
        fault = log_dir / FAULT_LOG_NAME
        fault.write_bytes(b"native dump\n")
        assert should_show_crash_notice() is True
        acknowledge_crash_notice()
        assert should_show_crash_notice() is False

    def test_terminate_marks_pending(self, log_dir):
        import crash_handler

        crash_handler.set_terminate_on_uncaught(True)
        try:
            with pytest.raises(SystemExit):
                crash_handler._terminate_after_crash(1)
            assert should_show_crash_notice() is True
        finally:
            crash_handler.set_terminate_on_uncaught(False)
