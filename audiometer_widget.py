#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# audiometer_widget.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################

"""
Audio meter widget: L/R bars, a programme LUFS bar, or both.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

from meter_engine import (
    LUFS_SILENCE,
    METER_LAYOUT_BOTH,
    METER_LAYOUT_LR,
    METER_LAYOUT_LUFS,
    MeterReadings,
    MeterUnit,
    floor_readings,
    normalize_lr_unit,
    normalize_meter_layout,
    normalize_meter_value,
)

# Meter fill rendering: continuous solid or 1px segments with 1px gaps
DISPLAY_STYLE_SOLID = "solid"
DISPLAY_STYLE_BARGRAPH = "bargraph"

# Layout chrome around the bars (margins, gaps, scale, LRA lane).
_METER_MARGIN_LEFT = 4
_METER_MARGIN_RIGHT = 2
_METER_BAR_GAP = 8
_LUFS_BAR_GAP = 6
_LRA_BAR_GAP = 2
_LRA_BAR_WIDTH = 4
_METER_SCALE_GAP = 3
_METER_SCALE_WIDTH = 20
_METER_MIN_BAR_WIDTH = 8
_METER_MAX_BAR_WIDTH = 40
_METER_FIXED_CHROME_LR = (
    _METER_MARGIN_LEFT
    + _METER_BAR_GAP
    + _METER_SCALE_GAP
    + _METER_SCALE_WIDTH
    + _METER_MARGIN_RIGHT
)  # 37
# Default matches the previous fixed 11px bars (37 + 2*11 = 59)
METER_WIDTH_DEFAULT = _METER_FIXED_CHROME_LR + 2 * 11  # 59
METER_WIDTH_MIN = _METER_FIXED_CHROME_LR + 2 * _METER_MIN_BAR_WIDTH  # 53
METER_WIDTH_MAX = _METER_FIXED_CHROME_LR + 2 * _METER_MAX_BAR_WIDTH  # 117
# Gap between the meter column and the left AIR LEDs (outside the meter widget)
METER_LED_GAP_PX = 2

LUFS_YELLOW_SPAN_LU = 9.0
_PEAK_OVERLAY_FACTOR = 0.55
_PEAK_PIP_FACTOR = 0.82
_PEAK_HOLD_TICK_PX = 2
_INTEGRATED_TICK_PX = 2
_LUFS_SHORT_TERM_COLOR = QtGui.QColor(180, 255, 210)
_LUFS_INTEGRATED_COLOR = QtGui.QColor(196, 92, 255)
_LUFS_LRA_COLOR = QtGui.QColor(255, 168, 40)
_PEAK_HOLD_COLOR = QtGui.QColor(255, 255, 255)
_PEAK_HOLD_CLIP_COLOR = QtGui.QColor(220, 40, 40)
_BG_COLOR = QtGui.QColor(10, 10, 10)
_BAR_TRACK_COLOR = QtGui.QColor(18, 18, 18)


def _chrome_and_bar_counts(layout: str) -> Tuple[int, int, int]:
    """Return (chrome_px, lr_bar_count, lufs_bar_count) for a layout."""
    layout = normalize_meter_layout(layout)
    if layout == METER_LAYOUT_LUFS:
        chrome = (
            _METER_MARGIN_LEFT
            + _LRA_BAR_GAP
            + _LRA_BAR_WIDTH
            + _METER_SCALE_GAP
            + _METER_SCALE_WIDTH
            + _METER_MARGIN_RIGHT
        )
        return chrome, 0, 1
    if layout == METER_LAYOUT_BOTH:
        chrome = (
            _METER_MARGIN_LEFT
            + _METER_BAR_GAP
            + _LUFS_BAR_GAP
            + _LRA_BAR_GAP
            + _LRA_BAR_WIDTH
            + _METER_SCALE_GAP
            + _METER_SCALE_WIDTH
            + _METER_MARGIN_RIGHT
        )
        return chrome, 2, 1
    return _METER_FIXED_CHROME_LR, 2, 0


def resolve_meter_width(
    requested_width: int,
    layout: str = METER_LAYOUT_LR,
) -> Tuple[int, int, int]:
    """
    Clamp a requested meter width and derive bar widths for the layout.

    Extra width beyond the fixed chrome is split evenly across visible bars.
    Returns (widget_width, lr_bar_width, lufs_bar_width).
    """
    layout = normalize_meter_layout(layout)
    chrome, n_lr, n_lufs = _chrome_and_bar_counts(layout)
    n_bars = max(1, n_lr + n_lufs)
    try:
        width = int(requested_width)
    except (TypeError, ValueError):
        width = METER_WIDTH_DEFAULT
    width = max(METER_WIDTH_MIN, min(METER_WIDTH_MAX, width))
    min_w = chrome + n_bars * _METER_MIN_BAR_WIDTH
    max_w = chrome + n_bars * _METER_MAX_BAR_WIDTH
    width = max(min_w, min(max_w, width))
    extra = width - chrome
    bar_width = extra // n_bars
    bar_width = max(_METER_MIN_BAR_WIDTH, min(_METER_MAX_BAR_WIDTH, bar_width))
    lr_width = bar_width if n_lr else 0
    lufs_width = bar_width if n_lufs else 0
    widget_width = chrome + n_lr * lr_width + n_lufs * lufs_width
    return widget_width, lr_width, lufs_width


class AudioMeterWidget(QtWidgets.QWidget):
    """Vertical L/R and/or programme LUFS meter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._unit = MeterUnit.DBFS
        self._layout_mode = METER_LAYOUT_LR
        self._display_style = DISPLAY_STYLE_BARGRAPH
        self._readings = floor_readings()
        self._peak_left = LUFS_SILENCE
        self._peak_right = LUFS_SILENCE
        self._peak_left_until = 0.0
        self._peak_right_until = 0.0
        self._clip_left_until = 0.0
        self._clip_right_until = 0.0
        self._peak_hold_enabled = True
        self._peak_hold_seconds = 1.5
        self._lufs_reference: Optional[float] = -23.0
        self._dbtp_ceiling: Optional[float] = -1.0
        self._requested_width = METER_WIDTH_DEFAULT
        self._meter_width, self._bar_width, self._lufs_bar_width = resolve_meter_width(
            METER_WIDTH_DEFAULT, METER_LAYOUT_LR
        )
        self.setFixedWidth(self._meter_width)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(self._meter_width, 400)

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(self._meter_width, 100)

    @property
    def meter_width(self) -> int:
        """Current meter widget width in pixels."""
        return self._meter_width

    @property
    def layout_mode(self) -> str:
        return self._layout_mode

    def set_meter_width(self, width: int) -> None:
        """Set overall meter width; visible bars grow/shrink to fill extra space."""
        self._requested_width = width
        self._apply_geometry()

    def set_layout(self, layout: str) -> None:
        """Set which tracks are drawn: lr, lufs, or both."""
        layout = normalize_meter_layout(layout)
        if layout == self._layout_mode:
            return
        self._layout_mode = layout
        self._apply_geometry()

    def _apply_geometry(self) -> None:
        meter_width, bar_width, lufs_width = resolve_meter_width(
            self._requested_width, self._layout_mode
        )
        if (
            meter_width == self._meter_width
            and bar_width == self._bar_width
            and lufs_width == self._lufs_bar_width
        ):
            self.update()
            return
        self._meter_width = meter_width
        self._bar_width = bar_width
        self._lufs_bar_width = lufs_width
        self.setFixedWidth(self._meter_width)
        self.updateGeometry()
        self.update()

    def set_unit(self, unit: MeterUnit | str) -> None:
        self._unit = normalize_lr_unit(unit)
        self._peak_left = self._readings.left
        self._peak_right = self._readings.right
        self._peak_left_until = 0.0
        self._peak_right_until = 0.0
        self.update()

    def set_display_style(self, style: str) -> None:
        """Set fill style: 'solid' or 'bargraph' (1px segments with 1px gaps)."""
        style = str(style).lower().strip()
        if style not in (DISPLAY_STYLE_SOLID, DISPLAY_STYLE_BARGRAPH):
            style = DISPLAY_STYLE_BARGRAPH
        self._display_style = style
        self.update()

    def set_peak_hold(self, enabled: bool, seconds: float = 1.5) -> None:
        """Enable/disable peak hold and set hold duration in seconds."""
        self._peak_hold_enabled = bool(enabled)
        self._peak_hold_seconds = max(0.1, float(seconds))
        if not self._peak_hold_enabled:
            self._peak_left = self._readings.left
            self._peak_right = self._readings.right
            self._peak_left_until = 0.0
            self._peak_right_until = 0.0
        self.update()

    def set_lufs_reference(self, value: Optional[float]) -> None:
        """Set LUFS target peg (None disables the marker)."""
        self._lufs_reference = None if value is None else float(value)
        self.update()

    def set_dbtp_ceiling(self, value: Optional[float]) -> None:
        """Set dBTP ceiling peg (typically TooLoud threshold)."""
        self._dbtp_ceiling = None if value is None else float(value)
        self.update()

    def set_levels(self, readings: MeterReadings) -> None:
        """Update displayed levels from a MeterEngine reading."""
        self._readings = readings
        now = time.monotonic()
        self._peak_left = self._update_peak_hold(
            readings.left, self._peak_left, "_peak_left_until", now
        )
        self._peak_right = self._update_peak_hold(
            readings.right, self._peak_right, "_peak_right_until", now
        )
        if readings.clip_left:
            self._clip_left_until = now + 0.2
        if readings.clip_right:
            self._clip_right_until = now + 0.2
        self.update()

    def _update_peak_hold(
        self,
        level: float,
        peak: float,
        until_attr: str,
        now: float,
    ) -> float:
        """Hold peak for the configured duration, then follow the current level."""
        if not self._peak_hold_enabled:
            setattr(self, until_attr, 0.0)
            return level
        if level >= peak:
            setattr(self, until_attr, now + self._peak_hold_seconds)
            return level
        if now >= float(getattr(self, until_attr)):
            setattr(self, until_attr, 0.0)
            return level
        return peak

    def clear_levels(self) -> None:
        running = self._readings.integrated_running
        frozen_i = self._readings.lufs_i
        frozen_low = self._readings.lra_low
        frozen_high = self._readings.lra_high
        self._readings = floor_readings(integrated_running=running)._replace(
            lufs_i=frozen_i if not running else LUFS_SILENCE,
            lra_low=frozen_low if not running else LUFS_SILENCE,
            lra_high=frozen_high if not running else LUFS_SILENCE,
        )
        self._peak_left = self._peak_right = LUFS_SILENCE
        self._peak_left_until = 0.0
        self._peak_right_until = 0.0
        self.update()

    def clear_integrated_markers(self) -> None:
        """Hide I and LRA on the meter; a running session keeps measuring."""
        self._readings = self._readings._replace(
            lufs_i=LUFS_SILENCE,
            lra_low=LUFS_SILENCE,
            lra_high=LUFS_SILENCE,
        )
        self.update()

    def _shows_lr(self) -> bool:
        return self._layout_mode in (METER_LAYOUT_LR, METER_LAYOUT_BOTH)

    def _shows_lufs(self) -> bool:
        return self._layout_mode in (METER_LAYOUT_LUFS, METER_LAYOUT_BOTH)

    def paintEvent(self, event):  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        rect = self.rect()
        painter.fillRect(rect, _BG_COLOR)

        top = rect.top() + 18
        bottom = rect.bottom() - 22
        height = max(1, bottom - top)
        x = _METER_MARGIN_LEFT
        left_x = right_x = lufs_x = lra_x = -1

        if self._shows_lr():
            left_x = x
            x = left_x + self._bar_width + _METER_BAR_GAP
            right_x = x
            x = right_x + self._bar_width
            if self._shows_lufs():
                x += _LUFS_BAR_GAP

        if self._shows_lufs():
            lufs_x = x
            x = lufs_x + self._lufs_bar_width + _LRA_BAR_GAP
            lra_x = x
            x = lra_x + _LRA_BAR_WIDTH

        scale_left = x + _METER_SCALE_GAP
        scale_right = rect.right() - _METER_MARGIN_RIGHT + 1

        now = time.monotonic()
        if self._shows_lr():
            use_rms = self._unit != MeterUnit.BBC_PPM
            self._draw_bar(
                painter,
                left_x,
                top,
                self._bar_width,
                height,
                self._readings.rms_left if use_rms else self._readings.left,
                self._peak_left,
                self._color_for_lr_fraction,
                overlay=self._readings.left if use_rms else None,
                hold_color=(
                    _PEAK_HOLD_CLIP_COLOR
                    if now < self._clip_left_until
                    else _PEAK_HOLD_COLOR
                ),
                scale_unit=self._unit,
            )
            self._draw_bar(
                painter,
                right_x,
                top,
                self._bar_width,
                height,
                self._readings.rms_right if use_rms else self._readings.right,
                self._peak_right,
                self._color_for_lr_fraction,
                overlay=self._readings.right if use_rms else None,
                hold_color=(
                    _PEAK_HOLD_CLIP_COLOR
                    if now < self._clip_right_until
                    else _PEAK_HOLD_COLOR
                ),
                scale_unit=self._unit,
            )
            if self._unit == MeterUnit.DBTP and self._dbtp_ceiling is not None:
                self._draw_peg(
                    painter,
                    left_x,
                    right_x + self._bar_width,
                    top,
                    height,
                    self._dbtp_ceiling,
                    QtGui.QColor(255, 120, 60),
                    self._unit,
                )

        if self._shows_lufs():
            self._draw_bar(
                painter,
                lufs_x,
                top,
                self._lufs_bar_width,
                height,
                self._readings.lufs_m,
                LUFS_SILENCE,
                self._color_for_lufs,
                draw_peak_hold=False,
                scale_unit=MeterUnit.LUFS,
            )
            self._draw_loudness_range(painter, lra_x, top, height)
            if self._lufs_reference is not None:
                self._draw_peg(
                    painter,
                    lufs_x,
                    lufs_x + self._lufs_bar_width,
                    top,
                    height,
                    self._lufs_reference,
                    QtGui.QColor(80, 180, 255),
                    MeterUnit.LUFS,
                )
            self._draw_tick(
                painter,
                lufs_x,
                self._lufs_bar_width,
                top,
                height,
                self._readings.lufs_s,
                _LUFS_SHORT_TERM_COLOR,
                MeterUnit.LUFS,
            )
            self._draw_tick(
                painter,
                lufs_x,
                self._lufs_bar_width,
                top,
                height,
                self._readings.lufs_i,
                _LUFS_INTEGRATED_COLOR,
                MeterUnit.LUFS,
            )

        self._draw_scale(painter, scale_left, scale_right, top, height)
        self._draw_labels(painter, left_x, right_x, lufs_x, bottom + 4)
        painter.end()

    def _draw_bar(
        self,
        painter: QtGui.QPainter,
        x: int,
        top: int,
        width: int,
        height: int,
        value: float,
        peak: float,
        color_for_fraction,
        overlay: Optional[float] = None,
        hold_color: Optional[QtGui.QColor] = None,
        draw_peak_hold: bool = True,
        scale_unit: MeterUnit = MeterUnit.DBFS,
    ) -> None:
        painter.fillRect(x, top, width, height, _BAR_TRACK_COLOR)
        filled = int(normalize_meter_value(value, scale_unit) * height)
        overlay_filled = (
            int(normalize_meter_value(overlay, scale_unit) * height)
            if overlay is not None
            else 0
        )
        bargraph = self._display_style == DISPLAY_STYLE_BARGRAPH
        x1, x2 = x + 1, x + width - 2

        for y_off in range(height):
            if bargraph and (y_off % 2) != 0:
                continue
            frac = y_off / max(1, height)
            color = self._dim_color(color_for_fraction(frac))
            y = top + height - 1 - y_off
            painter.setPen(color)
            painter.drawLine(x1, y, x2, y)

        if overlay is not None and overlay_filled > filled:
            pip_off = overlay_filled - 1
            if bargraph and (pip_off % 2) != 0:
                pip_off -= 1
            if pip_off < filled:
                pip_off = None
            for y_off in range(filled, overlay_filled):
                if bargraph and (y_off % 2) != 0:
                    continue
                y = top + height - 1 - y_off
                frac = y_off / max(1, height)
                factor = (
                    _PEAK_PIP_FACTOR if y_off == pip_off else _PEAK_OVERLAY_FACTOR
                )
                color = self._dim_color(color_for_fraction(frac), factor=factor)
                painter.setPen(color)
                painter.drawLine(x1, y, x2, y)

        if filled > 0:
            for y_off in range(filled):
                if bargraph and (y_off % 2) != 0:
                    continue
                frac = y_off / max(1, height)
                color = color_for_fraction(frac)
                y = top + height - 1 - y_off
                painter.setPen(color)
                painter.drawLine(x1, y, x2, y)

        if draw_peak_hold and self._peak_hold_enabled:
            peak_n = normalize_meter_value(peak, scale_unit)
            peak_y = top + height - int(peak_n * height)
            peak_y = max(top, min(top + height - _PEAK_HOLD_TICK_PX, peak_y))
            tick = hold_color if hold_color is not None else _PEAK_HOLD_COLOR
            painter.fillRect(x, peak_y, width, _PEAK_HOLD_TICK_PX, tick)

    def _dim_color(self, color: QtGui.QColor, factor: float = 0.22) -> QtGui.QColor:
        """Return a darker version of a meter zone color."""
        return QtGui.QColor(
            int(color.red() * factor),
            int(color.green() * factor),
            int(color.blue() * factor),
        )

    def _draw_peg(
        self,
        painter: QtGui.QPainter,
        left: int,
        right: int,
        top: int,
        height: int,
        value: float,
        color: QtGui.QColor,
        unit: MeterUnit,
    ) -> None:
        n = normalize_meter_value(value, unit)
        y = top + height - int(n * height)
        y = max(top, min(top + height - 1, y))
        painter.setPen(QtGui.QPen(color, 2))
        painter.drawLine(left, y, right, y)

    def _draw_tick(
        self,
        painter: QtGui.QPainter,
        x: int,
        width: int,
        top: int,
        height: int,
        value: float,
        color: QtGui.QColor,
        unit: MeterUnit,
    ) -> None:
        if value <= LUFS_SILENCE + 1.0:
            return
        n = normalize_meter_value(value, unit)
        y = top + height - int(n * height)
        y = max(top, min(top + height - _INTEGRATED_TICK_PX, y))
        painter.fillRect(x, y, width, _INTEGRATED_TICK_PX, color)

    def _draw_loudness_range(
        self,
        painter: QtGui.QPainter,
        x: int,
        top: int,
        height: int,
    ) -> None:
        low = self._readings.lra_low
        high = self._readings.lra_high
        has_span = high > LUFS_SILENCE + 1.0 and low > LUFS_SILENCE + 1.0
        if not has_span and not self._readings.integrated_running:
            return
        painter.fillRect(x, top, _LRA_BAR_WIDTH, height, _BAR_TRACK_COLOR)
        if not has_span:
            return
        y_high = top + height - int(normalize_meter_value(high, MeterUnit.LUFS) * height)
        y_low = top + height - int(normalize_meter_value(low, MeterUnit.LUFS) * height)
        y_high = max(top, min(top + height - 1, y_high))
        y_low = max(top, min(top + height, y_low))
        painter.setPen(_LUFS_LRA_COLOR)
        x2 = x + _LRA_BAR_WIDTH - 1
        for y in range(y_high, y_low):
            painter.drawLine(x, y, x2, y)

    def _color_for_lr_fraction(self, frac: float) -> QtGui.QColor:
        """frac 0=bottom/low, 1=top/high."""
        if self._unit == MeterUnit.BBC_PPM:
            if frac >= 5.0 / 6.0:
                return QtGui.QColor(220, 40, 40)
            return QtGui.QColor(40, 200, 60)
        if self._unit == MeterUnit.DBFS:
            if frac >= (-3.0 - (-60.0)) / 60.0:
                return QtGui.QColor(220, 40, 40)
            if frac >= (-12.0 - (-60.0)) / 60.0:
                return QtGui.QColor(220, 200, 40)
            return QtGui.QColor(40, 200, 60)
        if frac >= 0.9:
            return QtGui.QColor(220, 40, 40)
        if frac >= 0.7:
            return QtGui.QColor(220, 200, 40)
        return QtGui.QColor(40, 200, 60)

    def _color_for_lufs(self, frac: float) -> QtGui.QColor:
        """Green below the target peg, yellow to +9 LU, red above (EBU +9)."""
        reference = -23.0 if self._lufs_reference is None else float(self._lufs_reference)
        yellow_frac = (reference - (-60.0)) / 60.0
        red_frac = (reference + LUFS_YELLOW_SPAN_LU - (-60.0)) / 60.0
        if frac >= red_frac:
            return QtGui.QColor(220, 40, 40)
        if frac >= yellow_frac:
            return QtGui.QColor(220, 200, 40)
        return QtGui.QColor(40, 200, 60)

    def _scale_unit(self) -> MeterUnit:
        if self._layout_mode == METER_LAYOUT_LUFS:
            return MeterUnit.LUFS
        return self._unit

    def _scale_marks(self) -> List[Tuple[float, str]]:
        unit = self._scale_unit()
        if unit == MeterUnit.BBC_PPM:
            return [(float(m), str(m)) for m in range(1, 8)]
        if unit == MeterUnit.LUFS or self._shows_lufs():
            marks = [
                (0.0, "0"),
                (-6.0, "-6"),
                (-12.0, "-12"),
                (-18.0, "-18"),
                (-24.0, "-24"),
                (-36.0, "-36"),
                (-48.0, "-48"),
                (-60.0, "-60"),
            ]
            if self._lufs_reference is not None:
                ref = float(self._lufs_reference)
                if not any(abs(v - ref) < 0.05 for v, _ in marks):
                    marks.append((ref, f"{ref:.0f}"))
                    marks.sort(key=lambda item: item[0], reverse=True)
            return marks
        return [
            (0.0, "0"),
            (-6.0, "-6"),
            (-12.0, "-12"),
            (-18.0, "-18"),
            (-24.0, "-24"),
            (-36.0, "-36"),
            (-54.0, "-54"),
        ]

    def _draw_scale(
        self,
        painter: QtGui.QPainter,
        scale_left: int,
        scale_right: int,
        top: int,
        height: int,
    ) -> None:
        painter.setPen(QtGui.QColor(180, 180, 180))
        font = painter.font()
        font.setPointSize(11)
        painter.setFont(font)
        width = max(1, scale_right - scale_left)
        unit = self._scale_unit()
        for value, label in self._scale_marks():
            n = normalize_meter_value(value, unit)
            y = top + height - int(n * height)
            painter.drawText(
                scale_left,
                y - 7,
                width,
                14,
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def _draw_labels(
        self,
        painter: QtGui.QPainter,
        left_x: int,
        right_x: int,
        lufs_x: int,
        y: int,
    ) -> None:
        painter.setPen(QtGui.QColor(200, 200, 200))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        if self._shows_lr():
            painter.drawText(
                left_x, y, self._bar_width, 16, QtCore.Qt.AlignmentFlag.AlignHCenter, "L"
            )
            painter.drawText(
                right_x, y, self._bar_width, 16, QtCore.Qt.AlignmentFlag.AlignHCenter, "R"
            )
        if self._shows_lufs():
            painter.drawText(
                lufs_x,
                y,
                self._lufs_bar_width,
                16,
                QtCore.Qt.AlignmentFlag.AlignHCenter,
                "M",
            )

        unit_label = {
            MeterUnit.DBFS: "dBFS",
            MeterUnit.DBTP: "dBTP",
            MeterUnit.BBC_PPM: "PPM",
        }.get(self._unit, "")
        if self._layout_mode == METER_LAYOUT_LUFS:
            painter.drawText(
                self.rect().adjusted(0, 2, 0, 0),
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
                "LUFS",
            )
        elif self._layout_mode == METER_LAYOUT_BOTH:
            if left_x >= 0:
                painter.drawText(
                    left_x,
                    2,
                    self._bar_width * 2 + _METER_BAR_GAP,
                    16,
                    QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
                    unit_label,
                )
            if lufs_x >= 0:
                painter.drawText(
                    lufs_x,
                    2,
                    self._lufs_bar_width,
                    16,
                    QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
                    "LUFS",
                )
        else:
            painter.drawText(
                self.rect().adjusted(0, 2, 0, 0),
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
                unit_label,
            )
