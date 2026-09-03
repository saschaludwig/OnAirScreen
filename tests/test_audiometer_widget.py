#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Width and layout helpers for the audio meter widget."""

import pytest
from PySide6.QtWidgets import QApplication

from audiometer_widget import (
    AudioMeterWidget,
    DISPLAY_STYLE_SOLID,
    METER_WIDTH_MAX,
    METER_WIDTH_MIN,
    resolve_meter_width,
)
from meter_engine import (
    METER_LAYOUT_BOTH,
    METER_LAYOUT_LR,
    METER_LAYOUT_LUFS,
    MeterReadings,
    MeterUnit,
)


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


class TestBarPixmapCache:
    def test_builds_lr_and_lufs_pixmaps(self, qapp):
        widget = AudioMeterWidget()
        widget.set_layout(METER_LAYOUT_BOTH)
        widget.set_unit(MeterUnit.DBTP)
        widget.resize(widget.meter_width, 400)
        widget._ensure_bar_cache(360)
        assert widget._lr_fill_pm is not None and not widget._lr_fill_pm.isNull()
        assert widget._lr_dim_pm is not None and not widget._lr_dim_pm.isNull()
        assert widget._lr_overlay_pm is not None and not widget._lr_overlay_pm.isNull()
        assert widget._lufs_fill_pm is not None and not widget._lufs_fill_pm.isNull()
        cached = widget._lr_fill_pm
        widget._ensure_bar_cache(360)
        assert widget._lr_fill_pm is cached

    def test_invalidates_when_style_changes(self, qapp):
        widget = AudioMeterWidget()
        widget.set_layout(METER_LAYOUT_LR)
        widget._ensure_bar_cache(200)
        first = widget._lr_fill_pm
        widget.set_display_style(DISPLAY_STYLE_SOLID)
        widget._ensure_bar_cache(200)
        assert widget._lr_fill_pm is not first

    def test_lufs_only_skips_lr_pixmaps(self, qapp):
        widget = AudioMeterWidget()
        widget.set_layout(METER_LAYOUT_LUFS)
        widget._ensure_bar_cache(200)
        assert widget._lr_fill_pm is None
        assert widget._lufs_fill_pm is not None

    def test_set_levels_keeps_cache_and_stores_readings(self, qapp):
        widget = AudioMeterWidget()
        widget.set_layout(METER_LAYOUT_BOTH)
        widget._ensure_bar_cache(180)
        cached = widget._bar_cache_key
        readings = MeterReadings(
            left=-12.0,
            right=-18.0,
            max_true_peak_dbtp=-12.0,
            max_sample_peak_dbfs=-12.0,
            rms_left=-15.0,
            rms_right=-21.0,
            lufs_m=-23.0,
        )
        widget.set_levels(readings)
        assert widget._readings.left == pytest.approx(-12.0)
        assert widget._bar_cache_key == cached

