#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen Analog / Digital Clock implementation
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# clockwidget.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
# this file contains code from Riverbank Computing Limited
# and Nokia Corporation for details: see copyright notice below
#

#############################################################################
#
# Copyright (C) 2010 Riverbank Computing Limited.
# Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
# All rights reserved.
#
# This analog clock widget is based on the BSD-licensed analog clock
# example from Qt / PyQt.
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

import logging

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QRectF, QTime, Signal
from PySide6.QtGui import QColor

from defaults import TIME_SOURCE_LTC, TIME_SOURCE_NTP, TIME_SOURCE_PTP
from time_source import KIND_TIMECODE, TimeSample, get_current_sample

logger = logging.getLogger(__name__)

# Digital seconds LEDs use this radius in the scaled 200-unit clock space.
SECONDS_LED_DOT_SIZE = 1.6
# draw_digit top/bottom LED rows are ±9; y = center - (dot_offset / 2) * row
DIGIT_EXTENT_ROWS = 9
# SMPTE frame digits are half the seconds height, bottom-aligned.
FRAME_DIGIT_SCALE = 0.5
# LED radius a tick smaller than the height scale so the dots stay crisp.
FRAME_LED_SCALE = 0.3
# Center-to-center gap of the two FF digits, as a fraction of the seconds pair.
# 1.0 = same spacing as SS; raise this if the frame digits overlap.
FRAME_DIGIT_SPACING = 0.56
# Frame 7-segment digits use fewer LEDs per bar than HH:MM:SS.
FRAME_LEDS_PER_SEGMENT = 3


class ClockWidget(QtWidgets.QWidget):
    digiDigitColor: QColor
    timeChanged = Signal(QTime)
    timeZoneChanged = Signal(int)

    # default color scheme
    # digiHourColor = QtGui.QColor(255, 0, 0, 255)
    # digiSecondColor = QtGui.QColor(255, 0, 0, 255)

    def __init__(self, parent=None):
        super(ClockWidget, self).__init__(parent)

        # astrastudio color scheme
        self.digiHourColor = QtGui.QColor(50, 50, 255, 255)
        self.digiSecondColor = QtGui.QColor(255, 153, 0, 255)
        self.digiDigitColor = QtGui.QColor(50, 50, 255, 255)

        # analog mode colors
        self.hourColor = QtGui.QColor(190, 190, 190, 255)
        self.minuteColor = QtGui.QColor(220, 220, 220, 255)
        self.secondColor = QtGui.QColor(200, 200, 200, 255)
        self.circleColor = QtGui.QColor(220, 220, 220, 255)

        # Time-source lock LED (same radius as digital seconds LEDs)
        self.lockLedLockedColor = QtGui.QColor(0, 220, 0, 255)
        self.lockLedUnlockedColor = QtGui.QColor(220, 0, 0, 255)
        self.lockLedCaptionColor = QtGui.QColor(80, 80, 80, 255)

        self.image_path = ""

        self.set_logo()

        self.timeZoneOffset = 0
        self.clockMode = 1
        self.isAmPm = False
        self.showSeconds = False
        self.staticColon = False
        self.counter = 0
        self.one_line_time = False
        self.logo_upper = False
        self._sample = get_current_sample()
        self.time = QtCore.QTime(0, 0, 0)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._on_timer_timeout)
        self.resync_time()

    def _current_sample(self) -> TimeSample:
        """Latest TimeSample from the active time source."""
        sample = get_current_sample()
        if sample is not None:
            return sample
        if self._sample is not None:
            return self._sample
        return TimeSample.from_system()

    def _apply_sample(self, sample) -> None:
        """Store sample and a QTime view for existing paint helpers."""
        if sample is None:
            sample = TimeSample.from_system()
        self._sample = sample
        hour = int(sample.hours) % 24
        minute = int(sample.minutes) % 60
        second = int(sample.seconds) % 60
        msec = max(0, min(999, int(sample.milliseconds)))
        self.time = QtCore.QTime(hour, minute, second, msec)

    def _is_timecode_sample(self) -> bool:
        """True when the display shows SMPTE frames instead of a wall clock."""
        sample = self._sample
        if sample is None:
            return False
        return sample.kind == KIND_TIMECODE or sample.frames is not None

    def _shows_seconds_and_frames(self) -> bool:
        """Seconds (and frames, if present) are drawn in digital mode."""
        return self.showSeconds or self._is_timecode_sample()

    @staticmethod
    def _twelve_hour(hour_24: int) -> int:
        """Map 24-hour 0..23 to 12-hour 1..12."""
        return ((hour_24 - 1) % 12) + 1

    def _digital_hour(self) -> int:
        """Hour digits for digital mode (12-hour wall clock or 24-hour timecode)."""
        hour = self.time.hour()
        if self.isAmPm and not self._is_timecode_sample():
            return ClockWidget._twelve_hour(hour)
        return hour

    @staticmethod
    def _digit_bottom_y(center_y: float, dot_offset: float, dot_size: float) -> float:
        """Bottom edge of a 7-segment digit (LED center plus radius)."""
        return center_y + (DIGIT_EXTENT_ROWS / 2.0) * dot_offset + dot_size

    @staticmethod
    def _frame_digit_layout(seconds_y: float, seconds_dot_size: float, seconds_dot_offset: float):
        """Half-height frame digits whose bottom edge matches the seconds digits."""
        frame_dot_size = seconds_dot_size * FRAME_LED_SCALE
        frame_dot_offset = seconds_dot_offset * FRAME_DIGIT_SCALE
        bottom_y = ClockWidget._digit_bottom_y(seconds_y, seconds_dot_offset, seconds_dot_size)
        frames_y = bottom_y - (DIGIT_EXTENT_ROWS / 2.0) * frame_dot_offset - frame_dot_size
        return frames_y, frame_dot_size, frame_dot_offset

    def _smpte_frame_digits(self) -> str | None:
        """Two SMPTE frame digits, or None when the sample has no frame count."""
        sample = self._sample
        if sample is None:
            return None
        # Snapshot once: _sample can be replaced between a None-check and int().
        frames = sample.frames
        if frames is None:
            return None
        try:
            return "%02d" % (int(frames) % 100)
        except (TypeError, ValueError):
            return None

    def _milliseconds_until_next_clock_boundary(self) -> int:
        """Return milliseconds until the next required clock repaint boundary."""
        msec = self._current_sample().milliseconds
        if self.staticColon:
            delay = 1000 - msec
        elif msec < 500:
            delay = 500 - msec
        else:
            delay = 1000 - msec
        return delay if delay > 0 else 1

    def _schedule_next_clock_update(self) -> None:
        """Schedule the next repaint aligned to the active time sample."""
        sample = self._current_sample()
        if sample is None or not sample.running or sample.kind == KIND_TIMECODE:
            self.timer.stop()
            return
        self.timer.start(self._milliseconds_until_next_clock_boundary())

    def _on_timer_timeout(self) -> None:
        """Repaint the clock and schedule the next aligned update."""
        sample = self._current_sample()
        self.update()
        if sample is not None and sample.running:
            self._schedule_next_clock_update()
        else:
            self.timer.stop()

    @QtCore.Slot()
    def resync_time(self):
        """Sync clock repaints to the active time source."""
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(
                self, "resync_time", QtCore.Qt.ConnectionType.QueuedConnection
            )
            return
        sample = self._current_sample()
        self._apply_sample(sample)
        self.update()
        if sample is not None and sample.running and sample.kind != KIND_TIMECODE:
            self._schedule_next_clock_update()
        else:
            self.timer.stop()

    def ensure_timer_running(self) -> None:
        """Restart the clock timer if a wall-clock sample should be ticking."""
        sample = self._current_sample()
        if sample is None or not sample.running or sample.kind == KIND_TIMECODE:
            return
        if self.timer.isActive():
            return
        logger.warning("Clock repaint timer was stopped; restarting")
        self.resync_time()

    def update_time(self):
        sample = self._current_sample()
        self._apply_sample(sample)
        self.timeChanged.emit(self.time)

    @QtCore.Slot(int)
    def get_time_zone(self):
        return self.timeZoneOffset

    def set_time_zone(self, value):
        if value != self.timeZoneOffset:
            self.timeZoneOffset = value
            self.timeZoneChanged.emit(value)
            self.update()

    def reset_time_zone(self):
        if self.timeZoneOffset != 0:
            self.timeZoneOffset = 0
            self.timeZoneChanged.emit(0)
            self.update()

    timeZone = QtCore.Property("int", get_time_zone, set_time_zone, reset_time_zone)

    @QtCore.Slot(int)
    def set_clock_mode(self, mode):
        if mode == 1:
            self.clockMode = 1
        else:
            self.clockMode = 0

    def reset_clock_code(self):
        self.clockMode = 1

    def get_clock_mode(self):
        return self.clockMode

    clockType = QtCore.Property("int", get_clock_mode, set_clock_mode, reset_clock_code)

    @QtCore.Slot(bool)
    def set_am_pm(self, mode):
        self.isAmPm = mode

    def reset_am_pm(self):
        self.isAmPm = False

    def get_am_pm(self):
        return self.isAmPm

    clockAmPm = QtCore.Property("int", get_am_pm, set_am_pm, reset_am_pm)

    @QtCore.Slot(bool)
    def set_show_seconds(self, value):
        self.showSeconds = value

    def reset_show_seconds(self):
        self.showSeconds = False

    def get_show_seconds(self):
        return self.showSeconds

    clockShowSeconds = QtCore.Property("int", get_show_seconds, set_show_seconds, reset_show_seconds)

    @QtCore.Slot(bool)
    def set_one_line_time(self, value):
        self.one_line_time = value

    def reset_one_line_time(self):
        self.one_line_time = False

    def get_one_line_time(self):
        return self.one_line_time

    clockOneLineTime = QtCore.Property("int", get_one_line_time, set_one_line_time, reset_one_line_time)

    @QtCore.Slot(bool)
    def set_static_colon(self, value):
        self.staticColon = value
        self.resync_time()

    def reset_static_colon(self):
        self.staticColon = False

    def get_static_colon(self):
        return self.staticColon

    clockStaticColon = QtCore.Property("int", get_static_colon, set_static_colon, reset_static_colon)

    @QtCore.Slot(QtGui.QColor)
    def set_digi_hour_color(self, color=QtGui.QColor(50, 50, 255, 255)):
        self.digiHourColor = color

    def reset_digi_hour_color(self):
        self.digiHourColor = QtGui.QColor(50, 50, 255, 255)

    def get_digi_hour_color(self):
        return self.digiHourColor

    colorDigiHour = QtCore.Property(QtGui.QColor, get_digi_hour_color, set_digi_hour_color, reset_digi_hour_color)

    @QtCore.Slot(QtGui.QColor)
    def set_digi_second_color(self, color=QtGui.QColor(50, 50, 255, 255)):
        self.digiSecondColor = color

    def reset_digi_second_color(self):
        self.digiSecondColor = QtGui.QColor(50, 50, 255, 255)

    def get_digi_second_color(self):
        return self.digiSecondColor

    colorDigiSecond = QtCore.Property(QtGui.QColor, get_digi_second_color, set_digi_second_color,
                                          reset_digi_second_color)

    @QtCore.Slot(QtGui.QColor)
    def set_digi_digit_color(self, color=QtGui.QColor(50, 50, 255, 255)):
        self.digiDigitColor = color

    def reset_digi_digit_color(self):
        self.digiDigitColor = QtGui.QColor(50, 50, 255, 255)

    def get_digi_digit_color(self):
        return self.digiDigitColor

    colorDigiDigit = QtCore.Property(QtGui.QColor, get_digi_digit_color, set_digi_digit_color,
                                         reset_digi_digit_color)

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        self._apply_sample(self._current_sample())

        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        if self.clockMode == 0:
            self.paint_analog(painter)
        else:
            self.paint_digital(painter)
        painter.restore()
        self.paint_lock_led(painter)

    def paint_analog(self, painter):
        time = self.time
        # analog clock mode

        # add logo
        image_max_h = 40
        image_max_w = 100
        image = self.image
        image_w = image.width()
        image_h = image.height()

        if image_w > 0 and image_h > 1:
            painter.save()

            # logo position
            paint_x = 0
            if self.logo_upper:
                paint_y = -50
            else:
                paint_y = 50

            if image_w > image_h:
                # calculate height from aspect ratio
                paint_w = image_max_w
                paint_h = (float(image_h) / float(image_w)) * paint_w
            else:
                # calculate width from aspect ratio
                paint_h = image_max_h
                paint_w = (float(image_h) / float(image_w)) * paint_h

            painter.drawImage(QtCore.QRectF(paint_x - (paint_w / 2), paint_y - (paint_h / 2), paint_w, paint_h), image)
            painter.restore()

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.hourColor)
        # set hour hand length and minute hand length
        hhl = -70  # -50
        mhl = -80  # -75
        shl = -85  # -75

        # draw hour hand
        painter.save()
        painter.rotate(30.0 * (time.hour() + time.minute() / 60.0))
        painter.drawEllipse(-4, hhl, 8, 8)
        painter.drawRect(-4, 4, 8, hhl)
        painter.restore()

        painter.setPen(self.hourColor)

        for i in range(12):
            painter.drawRoundedRect(88, -1, 8, 2, 1.0, 1.0)
            painter.rotate(30.0)

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.minuteColor)

        # draw minute hand
        painter.save()
        painter.rotate(6.0 * (time.minute() + time.second() / 60.0))
        painter.drawEllipse(-3, mhl, 6, 6)
        painter.drawRect(-3, 3, 6, mhl)
        painter.restore()

        # draw second hand
        painter.setBrush(self.secondColor)
        painter.save()
        painter.rotate(6.0 * time.second())
        painter.drawEllipse(-1, shl, 2, 2)
        painter.drawRect(-1, 1, 2, shl)
        painter.restore()

        # draw center circle
        painter.setBrush(self.circleColor)
        painter.save()
        painter.drawEllipse(-6, -6, 12, 12)
        painter.restore()

        painter.setPen(self.minuteColor)

        for j in range(60):
            if (j % 5) != 0:
                painter.drawLine(92, 0, 96, 0)
            painter.rotate(6.0)
        # end analog clock mode

    @QtCore.Slot(str)
    def set_logo(self, logo_file=""):
        self.image_path = logo_file
        self.image = QtGui.QImage(logo_file)

    def get_logo(self):
        return self.image_path

    def reset_logo(self):
        self.set_logo()

    logoFile = QtCore.Property(str, get_logo, set_logo, reset_logo)

    @QtCore.Slot(bool)
    def set_logo_upper(self, state=True):
        self.logo_upper = state

    def get_logo_upper(self):
        return self.logoUpper

    def reset_logo_upper(self):
        self.set_logo_upper(False)

    logoUpper = QtCore.Property(bool, get_logo_upper, set_logo_upper, reset_logo_upper)

    def paint_digital(self, painter):
        # digital clock mode
        time = self.time

        # draw digits and colon
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.digiDigitColor)
        painter.setPen(self.digiDigitColor)

        hour_str = f"{self._digital_hour():02d}"

        minute_str = "%02d" % time.minute()
        second_str = "%02d" % time.second()

        if self.one_line_time:
            digit_spacing = 20
            dot_size = 1
            dot_offset = 3.5

            self.draw_digit(painter, digit_spacing * -3, 0, int(hour_str[0:1]), dot_size, dot_offset)
            self.draw_digit(painter, digit_spacing * -2, 0, int(hour_str[1:2]), dot_size, dot_offset)

            self.draw_colon(painter, digit_spacing * -1.25, 0, dot_size, dot_offset)
            self.draw_colon(painter, digit_spacing * 1.25, 0, dot_size, dot_offset)

            self.draw_digit(painter, digit_spacing * -0.5, 0, int(minute_str[0:1]), dot_size, dot_offset)
            self.draw_digit(painter, digit_spacing * 0.5, 0, int(minute_str[1:2]), dot_size, dot_offset)

            self.draw_digit(painter, digit_spacing * 2, 0, int(second_str[0:1]), dot_size, dot_offset)
            self.draw_digit(painter, digit_spacing * 3, 0, int(second_str[1:2]), dot_size, dot_offset)

            frame_str = self._smpte_frame_digits()
            if frame_str is not None:
                frames_y, frame_dot_size, frame_dot_offset = self._frame_digit_layout(
                    0, dot_size, dot_offset
                )
                frame_x0 = digit_spacing * 4.5
                frame_x1 = frame_x0 + digit_spacing * FRAME_DIGIT_SPACING
                self.draw_colon(
                    painter, digit_spacing * 3.75, frames_y, frame_dot_size, frame_dot_offset
                )
                self.draw_digit(
                    painter, frame_x0, frames_y, int(frame_str[0:1]),
                    frame_dot_size, frame_dot_offset,
                    leds_per_segment=FRAME_LEDS_PER_SEGMENT,
                )
                self.draw_digit(
                    painter, frame_x1, frames_y, int(frame_str[1:2]),
                    frame_dot_size, frame_dot_offset,
                    leds_per_segment=FRAME_LEDS_PER_SEGMENT,
                )

        else:
            digit_spacing = 28
            digit_spacing_y = 45
            seconds_offset_x = -3.5

            self.draw_digit(painter, digit_spacing * -2, 0, int(hour_str[0:1]))
            self.draw_digit(painter, digit_spacing * -1, 0, int(hour_str[1:2]))

            self.draw_colon(painter, 0, 0)

            minute_str = "%02d" % time.minute()
            self.draw_digit(painter, digit_spacing * 1, 0, int(minute_str[0:1]))
            self.draw_digit(painter, digit_spacing * 2, 0, int(minute_str[1:2]))

            if self._shows_seconds_and_frames():
                second_str = "%02d" % time.second()
                self.draw_digit(painter, (digit_spacing * -0.3) + seconds_offset_x, digit_spacing_y,
                                int(second_str[0:1]), 0.8, 3)
                self.draw_digit(painter, (digit_spacing * 0.3) + seconds_offset_x, digit_spacing_y,
                                int(second_str[1:2]), 0.8, 3)
                frame_str = self._smpte_frame_digits()
                if frame_str is not None:
                    frames_y, frame_dot_size, frame_dot_offset = self._frame_digit_layout(
                        digit_spacing_y, 0.8, 3
                    )
                    frame_x0 = (digit_spacing * 1.1) + seconds_offset_x
                    frame_x1 = frame_x0 + digit_spacing * 0.6 * FRAME_DIGIT_SPACING
                    self.draw_digit(
                        painter, frame_x0, frames_y,
                        int(frame_str[0:1]), frame_dot_size, frame_dot_offset,
                        leds_per_segment=FRAME_LEDS_PER_SEGMENT,
                    )
                    self.draw_digit(
                        painter, frame_x1, frames_y,
                        int(frame_str[1:2]), frame_dot_size, frame_dot_offset,
                        leds_per_segment=FRAME_LEDS_PER_SEGMENT,
                    )

        dot_size = SECONDS_LED_DOT_SIZE
        # set painter to 12 o'clock position
        painter.rotate(-90.0)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.digiHourColor)
        painter.setPen(self.digiHourColor)

        # draw hour marks
        painter.save()
        for i in range(12):
            painter.drawEllipse(QtCore.QPointF(95, 0), dot_size, dot_size)
            painter.rotate(30.0)
        painter.restore()

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.digiSecondColor)
        painter.setPen(self.digiSecondColor)

        # draw seconds
        painter.save()
        # draw zero second
        # painter.drawEllipse(QtCore.QPointF(88,0), dot_size, dot_size)
        # painter.rotate(6.0)
        second = time.second() + 1
        if second == 0:
            second = 60
        for j in range(0, second):
            painter.drawEllipse(QtCore.QPointF(88, 0), dot_size, dot_size)
            painter.rotate(6.0)
        painter.restore()

        # add logo
        image_max_h = 40
        image_max_w = 100
        image = self.image
        image_w = image.width()
        image_h = image.height()

        if image_w > 0 and image_h > 1:
            painter.save()
            painter.rotate(90)

            if (self._shows_seconds_and_frames() and not self.one_line_time) or self.logo_upper:
                # logo position and width when showing seconds
                paint_x = 0
                paint_y = -50
            else:
                # logo position and width without seconds
                paint_x = 0
                paint_y = 50

            if image_w > image_h:
                # calculate height from aspect ratio
                paint_w = image_max_w
                paint_h = (float(image_h) / float(image_w)) * paint_w
            else:
                # calculate width from aspect ratio
                paint_h = image_max_h
                paint_w = (float(image_h) / float(image_w)) * paint_h

            painter.drawImage(QtCore.QRectF(paint_x - (paint_w / 2), paint_y - (paint_h / 2), paint_w, paint_h), image)
            painter.restore()

        # end digital clock mode

    def _lock_led_color(self) -> QtGui.QColor:
        """Green when the active time source is locked, red otherwise."""
        sample = self._sample
        if sample is not None and sample.locked:
            return self.lockLedLockedColor
        return self.lockLedUnlockedColor

    def _lock_led_radius(self) -> float:
        """Pixel radius matching the digital seconds LEDs."""
        side = min(self.width(), self.height())
        if side <= 0:
            return SECONDS_LED_DOT_SIZE
        return SECONDS_LED_DOT_SIZE * (side / 200.0)

    def _lock_led_center(self) -> QtCore.QPointF:
        """Bottom-right widget corner, inset so the disc stays fully visible."""
        radius = self._lock_led_radius()
        return QtCore.QPointF(self.width() - radius, self.height() - radius)

    def _lock_led_caption(self) -> str:
        """Caption left of the LED."""
        sample = self._sample
        if sample is None:
            return "LOCAL"
        source = sample.source
        if source == TIME_SOURCE_PTP:
            return "PTP LOCK" if sample.locked else "PTP NOT LOCKED"
        if source == TIME_SOURCE_NTP:
            return "NTP LOCK" if sample.locked else "NTP NOT LOCKED"
        if source == TIME_SOURCE_LTC:
            return "LTC LOCK" if sample.locked else "LTC NOT LOCKED"
        return "LOCAL"

    def paint_lock_led(self, painter):
        """Draw lock status LED at the widget's bottom-right corner."""
        color = self._lock_led_color()
        radius = self._lock_led_radius()
        center = self._lock_led_center()
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(center, radius, radius)

        caption = self._lock_led_caption()
        if not caption:
            return
        diameter = radius * 2.0
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(max(1, int(round(diameter))))
        painter.setFont(font)
        painter.setPen(self.lockLedCaptionColor)
        gap = max(1.0, radius * 0.75)
        text_rect = QtCore.QRectF(
            0.0,
            center.y() - radius,
            center.x() - radius - gap,
            diameter,
        )
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
            caption,
        )

    def draw_colon(self, painter, digit_start_pos_x=0.0, digit_start_pos_y=0.0, dot_size=1.6, dot_offset=4.5, slant=15):
        # paint colon only half a second
        if self.time.msec() < 500 or self.staticColon:
            dot_slant = dot_offset / slant  # horizontal slant of each row
            current_row = +1.5
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x + (dot_slant * 2 * current_row),
                               digit_start_pos_y - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -1.2
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x + (dot_slant * 2 * current_row),
                               digit_start_pos_y - (dot_offset * current_row)), dot_size, dot_size)

    @staticmethod
    def draw_digit(painter, digit_start_pos_x=0.0, digit_start_pos_y=0.0, value=8, dot_size=1.6, dot_offset=5.0,
                   slant=19.0, leds_per_segment=4):
        value = int(value)
        leds_per_segment = 3 if int(leds_per_segment) <= 3 else 4
        # draw dots from one 7segment digit
        dot_slant = dot_offset / slant  # horizontal slant of each row

        # decimal to segment conversion table
        segments = [0b0111111, 0b0000110, 0b1011011, 0b1001111, 0b1100110, 0b1101101, 0b1111101, 0b0000111, 0b1111111,
                    0b1101111]
        mask = segments[value]

        if leds_per_segment == 3:
            h_xs = (-1.5, 0.0, 1.5)
            v_rows = (1.0, 2.5, 4.0)
        else:
            h_xs = (-1.5, -0.5, 0.5, 1.5)
            v_rows = (1, 2, 3, 4)

        # Vertical waist nudges were authored for hour digits (dot_offset=5).
        # Scale only Y so inner LEDs stay off the middle bar on small digits;
        # leave X unscaled so the outer corners keep their original gap.
        y_scale = (dot_offset / 5.0) if leds_per_segment == 3 else 1.0

        def draw_led(x, y):
            painter.drawEllipse(QtCore.QPointF(x, y), dot_size, dot_size)

        def draw_horizontal(row):
            for x_mul in h_xs:
                draw_led(
                    digit_start_pos_x + (dot_offset * x_mul) + (dot_slant * row),
                    digit_start_pos_y - (dot_offset / 2 * row),
                )

        def draw_vertical(sign, y_offset, x_offset, x_side):
            y_offset *= y_scale
            for row in v_rows:
                current_row = sign * row
                draw_led(
                    digit_start_pos_x - x_offset + (dot_offset * x_side)
                    + (dot_slant * 2 * current_row),
                    digit_start_pos_y - y_offset - (dot_offset * current_row),
                )

        if mask & 1 << 6:
            draw_horizontal(0)  # g, center
        if mask & 1 << 0:
            draw_horizontal(9)  # a, top
        if mask & 1 << 3:
            draw_horizontal(-9)  # d, bottom
        if mask & 1 << 5:
            draw_vertical(+1, -0.75, +0.75, -2.0)  # f
        if mask & 1 << 1:
            draw_vertical(+1, -1.2, -0.5, +2.0)  # b
        if mask & 1 << 4:
            draw_vertical(-1, +1.2, +0.5, -2.0)  # e
        if mask & 1 << 2:
            draw_vertical(-1, +0.75, -0.75, +2.0)  # c


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    widget = ClockWidget()
    widget.setStyleSheet("background-color:black;")
    widget.resize(500, 500)
    widget.set_clock_mode(1)
    widget.set_am_pm(False)
    widget.set_show_seconds(False)
    widget.set_static_colon(False)
    widget.set_one_line_time(True)
    widget.set_logo("images/astrastudio_transparent.png")
    widget.set_logo_upper(True)
    widget.show()
    sys.exit(app.exec())
