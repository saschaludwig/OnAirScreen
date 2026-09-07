#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for analog_classic.py (BSD analog ticks and hands)."""

import sys

from PySide6.QtCore import QTime
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

if not QApplication.instance():
    QApplication(sys.argv)

from analog_classic import (
    hour_hand_angle,
    minute_hand_angle,
    paint_classic_analog_marks_and_hands,
    second_hand_angle,
)


def test_hand_angles():
    time = QTime(3, 30, 15)
    assert hour_hand_angle(time) == 30.0 * (3 + 30 / 60.0)
    assert minute_hand_angle(time) == 6.0 * (30 + 15 / 60.0)
    assert second_hand_angle(time) == 6.0 * 15


def test_smooth_hand_angles_include_milliseconds():
    time = QTime(3, 30, 15, 500)
    assert second_hand_angle(time, smooth=True) == 6.0 * 15.5
    assert minute_hand_angle(time, smooth=True) == 6.0 * (30 + 15.5 / 60.0)
    assert second_hand_angle(time) == 6.0 * 15
    assert minute_hand_angle(time) == 6.0 * (30 + 15 / 60.0)


def test_paint_classic_analog_marks_and_hands_does_not_crash():
    image = QImage(200, 200, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0))
    painter = QPainter(image)
    painter.translate(100, 100)
    callback_called = []

    def after_hour_ticks(_painter):
        callback_called.append(True)

    paint_classic_analog_marks_and_hands(
        painter,
        QTime(10, 10, 30),
        QColor(255, 0, 0),
        QColor(0, 255, 0),
        QColor(0, 0, 255),
        QColor(255, 255, 255),
        after_hour_ticks=after_hour_ticks,
    )
    painter.end()
    assert callback_called == [True]
