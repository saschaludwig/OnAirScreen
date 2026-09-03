#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# font_loader.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Font Loader for OnAirScreen

This module handles loading fonts from the fonts directory.
"""

import logging
import os
import sys

from PySide6.QtGui import QFontDatabase

from defaults import DEFAULT_FONT_NAME

logger = logging.getLogger(__name__)

# Previous bundled family; map stored settings to the current default.
LEGACY_FONT_NAMES = frozenset({"FreeSans"})
FONT_FILE_EXTENSIONS = (".ttf", ".otf")


def get_fonts_dir() -> str:
    """
    Return the path to the bundled fonts directory.

    Frozen (PyInstaller) builds unpack data files into sys._MEIPASS.
    """
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "fonts")


def resolve_font_name(font_name: str | None) -> str:
    """
    Map a stored font family to a usable family name.

    FreeSans was the previous bundled default and is no longer shipped.
    Empty or missing names fall back to DEFAULT_FONT_NAME.
    """
    if hasattr(font_name, "value") and not isinstance(font_name, str):
        font_name = font_name.value()
    name = str(font_name).strip() if font_name else ""
    if not name or name in LEGACY_FONT_NAMES:
        return DEFAULT_FONT_NAME
    return name


def load_fonts() -> None:
    """
    Load fonts from the fonts/ directory.

    Registers all TrueType and OpenType files with Qt's font database
    for use throughout the application.
    """
    font_dir = get_fonts_dir()
    if not os.path.isdir(font_dir):
        logger.warning(f"Fonts directory not found: {font_dir}")
        return

    for font_file in sorted(os.listdir(font_dir)):
        if not font_file.lower().endswith(FONT_FILE_EXTENSIONS):
            continue
        font_path = os.path.join(font_dir, font_file)
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            logger.info(f"Loaded font: {font_file} -> {families}")
        else:
            logger.warning(f"Failed to load font: {font_file}")
