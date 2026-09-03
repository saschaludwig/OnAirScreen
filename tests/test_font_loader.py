#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for font_loader.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

from defaults import DEFAULT_FONT_NAME
from font_loader import get_fonts_dir, load_fonts, resolve_font_name

class TestResolveFontName:
    def test_maps_freesans_to_default(self):
        assert resolve_font_name("FreeSans") == DEFAULT_FONT_NAME

    def test_keeps_custom_family(self):
        assert resolve_font_name("Helvetica") == "Helvetica"

    def test_empty_and_none_use_default(self):
        assert resolve_font_name(None) == DEFAULT_FONT_NAME
        assert resolve_font_name("") == DEFAULT_FONT_NAME
        assert resolve_font_name("   ") == DEFAULT_FONT_NAME

    def test_unwraps_value_object(self):
        class ValueObject:
            def __init__(self, value):
                self._value = value

            def value(self):
                return self._value

        assert resolve_font_name(ValueObject("FreeSans")) == DEFAULT_FONT_NAME
        assert resolve_font_name(ValueObject("Arial")) == "Arial"


class TestGetFontsDir:
    def test_dev_path_is_next_to_module(self):
        font_dir = get_fonts_dir()
        assert os.path.basename(font_dir) == "fonts"
        assert os.path.isdir(font_dir)
        assert (Path(font_dir) / "Roboto-Regular.ttf").is_file()
        assert (Path(font_dir) / "NotoSans-Regular.ttf").is_file()

    def test_frozen_uses_meipass(self, tmp_path):
        meipass = tmp_path / "meipass"
        meipass.mkdir()
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(meipass), create=True):
                assert get_fonts_dir() == str(meipass / "fonts")


class TestLoadFonts:
    def test_registers_ttf_files(self, tmp_path):
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        (font_dir / "Roboto-Regular.ttf").write_bytes(b"fake")
        (font_dir / "LICENSE.txt").write_text("license")
        with patch("font_loader.get_fonts_dir", return_value=str(font_dir)):
            with patch("font_loader.QFontDatabase") as font_db:
                font_db.addApplicationFont.return_value = 1
                font_db.applicationFontFamilies.return_value = ["Roboto"]
                load_fonts()
                font_db.addApplicationFont.assert_called_once_with(
                    str(font_dir / "Roboto-Regular.ttf")
                )

    def test_missing_directory_is_logged(self, tmp_path):
        missing = tmp_path / "missing-fonts"
        with patch("font_loader.get_fonts_dir", return_value=str(missing)):
            with patch("font_loader.logger") as logger:
                load_fonts()
                logger.warning.assert_called()
