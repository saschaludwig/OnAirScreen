#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Width and layout helpers for the audio meter widget."""

import pytest
from PySide6.QtWidgets import QApplication

from audiometer_widget import (
    AudioMeterWidget,
    METER_WIDTH_MAX,
    METER_WIDTH_MIN,
    resolve_meter_width,
)
from meter_engine import METER_LAYOUT_BOTH, METER_LAYOUT_LR, METER_LAYOUT_LUFS


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestResolveMeterWidth:
    def test_lr_default_range(self):
        width, lr, lufs = resolve_meter_width(79, METER_LAYOUT_LR)
        assert METER_WIDTH_MIN <= width <= METER_WIDTH_MAX
        assert lr >= 8
        assert lufs == 0

    def test_lufs_has_one_bar(self):
        width, lr, lufs = resolve_meter_width(79, METER_LAYOUT_LUFS)
        assert lr == 0
        assert lufs >= 8
        assert width >= METER_WIDTH_MIN

    def test_both_clamps_above_min_bar(self):
        width, lr, lufs = resolve_meter_width(53, METER_LAYOUT_BOTH)
        assert lr >= 8
        assert lufs >= 8
        assert width >= 53

    def test_extra_width_thickens_bars(self):
        narrow, lr_n, _ = resolve_meter_width(59, METER_LAYOUT_LR)
        wide, lr_w, _ = resolve_meter_width(117, METER_LAYOUT_LR)
        assert wide > narrow
        assert lr_w > lr_n


class TestDbtpCeiling:
    def test_none_clears_ceiling_peg(self, qapp):
        widget = AudioMeterWidget()
        widget.set_dbtp_ceiling(-1.0)
        assert widget._dbtp_ceiling == -1.0
        widget.set_dbtp_ceiling(None)
        assert widget._dbtp_ceiling is None
