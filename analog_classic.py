#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# Copyright (C) 2010 Riverbank Computing Limited.
# Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
# All rights reserved.
#
# analog_classic.py
# Classic analog clock ticks and hands, based on the BSD-licensed analog
# clock example from Qt / PyQt.
#
# $QT_BEGIN_LICENSE:BSD$
# You may use this file under the terms of the BSD license as follows:
#
# "Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
#     the names of its contributors may be used to endorse or promote
#     products derived from this software without specific prior written
#     permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
# $QT_END_LICENSE$
#
#############################################################################

from PySide6 import QtCore


def hour_hand_angle(time):
    """Hour-hand angle in degrees (12-hour face)."""
    return 30.0 * ((time.hour() % 12) + time.minute() / 60.0)


def minute_hand_angle(time, smooth=False):
    """Minute-hand angle in degrees.

    When smooth is True, milliseconds are interpolated so the hand does not
    jump once per second.
    """
    seconds = time.second() + (time.msec() / 1000.0 if smooth else 0.0)
    return 6.0 * (time.minute() + seconds / 60.0)


def second_hand_angle(time, smooth=False):
    """Second-hand angle in degrees.

    Whole seconds by default; when smooth is True, milliseconds are included
    for a continuous sweep.
    """
    seconds = time.second() + (time.msec() / 1000.0 if smooth else 0.0)
    return 6.0 * seconds


def paint_classic_analog_marks_and_hands(
    painter,
    time,
    hour_color,
    minute_color,
    second_color,
    circle_color,
    after_hour_ticks=None,
):
    """Draw classic analog ticks and rectangular hands in the 200-unit clock space.

    Optional after_hour_ticks(painter) runs after the 12 hour marks (used for numerals).
    """
    painter.setPen(hour_color)
    painter.save()
    for _i in range(12):
        painter.drawRoundedRect(88, -1, 8, 2, 1.0, 1.0)
        painter.rotate(30.0)
    painter.restore()

    if after_hour_ticks is not None:
        after_hour_ticks(painter)

    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(hour_color)
    painter.save()
    painter.rotate(hour_hand_angle(time))
    painter.drawEllipse(-4, -70, 8, 8)
    painter.drawRect(-4, 4, 8, -70)
    painter.restore()

    painter.setBrush(minute_color)
    painter.save()
    painter.rotate(minute_hand_angle(time))
    painter.drawEllipse(-3, -80, 6, 6)
    painter.drawRect(-3, 3, 6, -80)
    painter.restore()

    painter.setBrush(second_color)
    painter.save()
    painter.rotate(second_hand_angle(time))
    painter.drawEllipse(-1, -85, 2, 2)
    painter.drawRect(-1, 1, 2, -85)
    painter.restore()

    painter.setBrush(circle_color)
    painter.drawEllipse(-6, -6, 12, 12)

    painter.setPen(minute_color)
    painter.save()
    for j in range(60):
        if (j % 5) != 0:
            painter.drawLine(92, 0, 96, 0)
        painter.rotate(6.0)
    painter.restore()
