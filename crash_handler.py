#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# crash_handler.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Crash reporting and log-directory helpers for OnAirScreen.

Unhandled Python exceptions, thread failures, asyncio errors, and Qt fatal
messages are written to crash-*.txt. Native faults go to fault.log via
faulthandler. Settings and secrets are never dumped.
"""

from __future__ import annotations

import faulthandler
import logging
import os
import platform
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

LOG_FILE_NAME = "onairscreen.log"
FAULT_LOG_NAME = "fault.log"
CRASH_FILE_PREFIX = "crash-"
CRASH_FILE_SUFFIX = ".txt"
MAX_CRASH_FILES = 10

_log_directory_override: Optional[Path] = None
_hooks_installed = False
_qt_handler_installed = False
_original_excepthook = None
_original_thread_excepthook = None
_fault_log_file: Optional[TextIO] = None


def set_log_directory_override(path: Optional[Path]) -> None:
    """Override the log directory (used by tests). Pass None to restore default."""
    global _log_directory_override
    _log_directory_override = Path(path) if path is not None else None


def get_log_directory() -> Path:
    """
    Return the platform-specific directory for application logs.

    macOS:  ~/Library/Logs/OnAirScreen
    Windows: %LOCALAPPDATA%/astrastudio/OnAirScreen/logs
    Linux:  ~/.local/share/astrastudio/OnAirScreen/logs
    """
    if _log_directory_override is not None:
        return _log_directory_override

    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Library" / "Logs" / "OnAirScreen"
    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "astrastudio" / "OnAirScreen" / "logs"
        return home / "AppData" / "Local" / "astrastudio" / "OnAirScreen" / "logs"
    return home / ".local" / "share" / "astrastudio" / "OnAirScreen" / "logs"


def ensure_log_directory() -> Path:
    """Create the log directory if needed and return it."""
    log_dir = get_log_directory()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def collect_environment_info() -> dict[str, str]:
    """Collect non-secret runtime info for crash reports. Never includes settings."""
    info = {
        "Time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "Version": _safe_import_attr("version", "versionString", "unknown"),
        "Distribution": _safe_import_attr("distribution", "distributionString", "unknown"),
        "Frozen": "yes" if getattr(sys, "frozen", False) else "no",
        "Python": sys.version.replace("\n", " "),
        "PySide6": "unavailable",
        "Qt": "unavailable",
        "OS": f"{platform.system()} {platform.release()}",
        "Platform": platform.platform(),
    }
    try:
        import PySide6
        info["PySide6"] = getattr(PySide6, "__version__", "unknown")
        from PySide6.QtCore import qVersion
        info["Qt"] = qVersion()
    except Exception:
        pass
    return info


def write_crash_report(
    exc_type: Optional[type[BaseException]],
    exc_value: Optional[BaseException],
    exc_tb,
    thread_name: Optional[str] = None,
    source: str = "exception",
) -> Optional[Path]:
    """
    Write a crash report file. Never includes settings or secrets.

    Returns the path of the written file, or None if writing failed.
    """
    try:
        log_dir = ensure_log_directory()
    except OSError as error:
        print(f"Could not create log directory: {error}", file=sys.stderr)
        _print_traceback_to_stderr(exc_type, exc_value, exc_tb)
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    crash_path = log_dir / f"{CRASH_FILE_PREFIX}{stamp}{CRASH_FILE_SUFFIX}"
    if crash_path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        crash_path = log_dir / f"{CRASH_FILE_PREFIX}{stamp}{CRASH_FILE_SUFFIX}"

    lines = [
        "OnAirScreen crash report",
        "========================",
        f"Source: {source}",
    ]
    if thread_name:
        lines.append(f"Thread: {thread_name}")
    for key, value in collect_environment_info().items():
        lines.append(f"{key}: {value}")
    lines.append("")
    lines.append("Traceback")
    lines.append("---------")
    if exc_type is not None:
        lines.extend(
            traceback.format_exception(exc_type, exc_value, exc_tb)
        )
    else:
        lines.append("(no Python traceback)")
    lines.append("")
    lines.append("Last log lines")
    lines.append("--------------")
    recent = _recent_log_lines()
    if recent:
        lines.extend(recent)
    else:
        lines.append("(none)")
    lines.append("")

    text = "\n".join(lines)
    try:
        crash_path.write_text(text, encoding="utf-8")
    except OSError as error:
        print(f"Could not write crash report: {error}", file=sys.stderr)
        _print_traceback_to_stderr(exc_type, exc_value, exc_tb)
        return None

    _prune_old_crash_files(log_dir)
    print(f"Crash report written to: {crash_path}", file=sys.stderr)
    return crash_path


def install_crash_hooks(log_dir: Optional[Path] = None) -> None:
    """
    Install sys.excepthook, threading.excepthook, and faulthandler.

    Safe to call more than once. Crash dumps are always written, independent
    of the configured log level.
    """
    global _hooks_installed, _original_excepthook, _original_thread_excepthook
    global _fault_log_file

    if log_dir is None:
        try:
            log_dir = ensure_log_directory()
        except OSError as error:
            print(f"Could not create log directory: {error}", file=sys.stderr)
            log_dir = None

    if not _hooks_installed:
        _original_excepthook = sys.excepthook
        sys.excepthook = _excepthook
        _original_thread_excepthook = threading.excepthook
        threading.excepthook = _thread_excepthook
        _hooks_installed = True

    if log_dir is not None:
        _enable_faulthandler(log_dir)


def install_qt_message_handler() -> None:
    """Install a Qt message handler that records fatal Qt messages as crashes."""
    global _qt_handler_installed
    if _qt_handler_installed:
        return
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:
        return

    def _qt_message_handler(mode, context, message: str) -> None:
        qt_logger = logging.getLogger("Qt")
        if mode == QtMsgType.QtFatalMsg:
            qt_logger.critical("%s", message)
            write_crash_report(
                RuntimeError,
                RuntimeError(f"Qt fatal: {message}"),
                None,
                thread_name="Qt",
                source="qt-fatal",
            )
        elif mode == QtMsgType.QtCriticalMsg:
            qt_logger.error("%s", message)
        elif mode == QtMsgType.QtWarningMsg:
            qt_logger.warning("%s", message)
        elif mode == QtMsgType.QtInfoMsg:
            qt_logger.info("%s", message)
        else:
            qt_logger.debug("%s", message)

    qInstallMessageHandler(_qt_message_handler)
    _qt_handler_installed = True


def install_asyncio_exception_handler(loop) -> None:
    """Install an asyncio loop exception handler that writes crash reports."""

    def _handler(loop, context: dict) -> None:
        exception = context.get("exception")
        if exception is not None:
            write_crash_report(
                type(exception),
                exception,
                exception.__traceback__,
                thread_name="asyncio",
                source="asyncio",
            )
        else:
            message = context.get("message", "unknown asyncio error")
            write_crash_report(
                RuntimeError,
                RuntimeError(message),
                None,
                thread_name="asyncio",
                source="asyncio",
            )
        loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


def uninstall_crash_hooks() -> None:
    """Restore previous exception hooks. Used by tests."""
    global _hooks_installed, _fault_log_file
    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
    if _original_thread_excepthook is not None:
        threading.excepthook = _original_thread_excepthook
    if _fault_log_file is not None:
        try:
            faulthandler.disable()
        except Exception:
            pass
        try:
            _fault_log_file.close()
        except Exception:
            pass
        _fault_log_file = None
    _hooks_installed = False


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    write_crash_report(exc_type, exc_value, exc_tb, source="sys.excepthook")
    if _original_excepthook is not None:
        _original_excepthook(exc_type, exc_value, exc_tb)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_tb)


def _thread_excepthook(args) -> None:
    thread_name = None
    if getattr(args, "thread", None) is not None:
        thread_name = args.thread.name
    write_crash_report(
        args.exc_type,
        args.exc_value,
        args.exc_traceback,
        thread_name=thread_name,
        source="threading.excepthook",
    )
    if _original_thread_excepthook is not None:
        _original_thread_excepthook(args)


def _enable_faulthandler(log_dir: Path) -> None:
    global _fault_log_file
    if _fault_log_file is not None:
        return
    fault_path = log_dir / FAULT_LOG_NAME
    try:
        _fault_log_file = open(fault_path, "a", encoding="utf-8")
        faulthandler.enable(file=_fault_log_file, all_threads=True)
    except OSError as error:
        print(f"Could not enable faulthandler: {error}", file=sys.stderr)
        _fault_log_file = None


def _prune_old_crash_files(log_dir: Path) -> None:
    crash_files = sorted(
        log_dir.glob(f"{CRASH_FILE_PREFIX}*{CRASH_FILE_SUFFIX}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_file in crash_files[MAX_CRASH_FILES:]:
        try:
            old_file.unlink()
        except OSError:
            pass


def _recent_log_lines() -> list[str]:
    try:
        from logging_config import get_recent_log_lines
        return get_recent_log_lines()
    except Exception:
        return []


def _safe_import_attr(module_name: str, attr: str, default: str) -> str:
    try:
        module = __import__(module_name)
        value = getattr(module, attr, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def _print_traceback_to_stderr(exc_type, exc_value, exc_tb) -> None:
    if exc_type is not None:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)
