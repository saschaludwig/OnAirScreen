#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen Analog / Digital Clock implementation
# Copyright (c) 2012-2024 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# start.py
# This file is part of OnAirScreen
#
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
# This file is part of the examples of PyQt.
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

import time as pytime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor


class ClockWidget(QtWidgets.QWidget):
    digiDigitColor: QColor
    __pyqtSignals__ = ("timeChanged(QTime)", "timeZoneChanged(int)")

    # default color scheme
    # digiHourColor = QtGui.QColor(255, 0, 0, 255)
    # digiSecondColor = QtGui.QColor(255, 0, 0, 255)

    def __init__(self, parent=None):
        super(ClockWidget, self).__init__(parent)

        self.timeChanged = None
        self.timeZoneChanged = None
        
        # astrastudio color scheme
        self.digiHourColor = QtGui.QColor(50, 50, 255, 255)
        self.digiSecondColor = QtGui.QColor(255, 153, 0, 255)
        self.digiDigitColor = QtGui.QColor(50, 50, 255, 255)

        # analog mode colors
        self.hourColor = QtGui.QColor(190, 190, 190, 255)
        self.minuteColor = QtGui.QColor(220, 220, 220, 255)
        self.secondColor = QtGui.QColor(200, 200, 200, 255)
        self.circleColor = QtGui.QColor(220, 220, 220, 255)

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

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.resync_time()

    def resync_time(self):
        # sync local timer with system clock
        while QtCore.QTime.currentTime().msec() > 5:
            pytime.sleep(0.001)
        self.timer.start(500)

    def update_time(self):
        self.timeChanged.emit(QtCore.QTime.currentTime())

    @QtCore.pyqtSlot(int)
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

    timeZone = QtCore.pyqtProperty("int", get_time_zone, set_time_zone, reset_time_zone)

    @QtCore.pyqtSlot(int)
    def set_clock_mode(self, mode):
        if mode == 1:
            self.clockMode = 1
        else:
            self.clockMode = 0

    def reset_clock_code(self):
        self.clockMode = 1

    def get_clock_mode(self):
        return self.clockMode

    clockType = QtCore.pyqtProperty("int", get_clock_mode, set_clock_mode, reset_clock_code)

    @QtCore.pyqtSlot(bool)
    def set_am_pm(self, mode):
        self.isAmPm = mode

    def reset_am_pm(self):
        self.isAmPm = False

    def get_am_pm(self):
        return self.isAmPm

    clockAmPm = QtCore.pyqtProperty("int", get_am_pm, set_am_pm, reset_am_pm)

    @QtCore.pyqtSlot(bool)
    def set_show_seconds(self, value):
        self.showSeconds = value

    def reset_show_seconds(self):
        self.showSeconds = False

    def get_show_seconds(self):
        return self.showSeconds

    clockShowSeconds = QtCore.pyqtProperty("int", get_show_seconds, set_show_seconds, reset_show_seconds)

    @QtCore.pyqtSlot(bool)
    def set_one_line_time(self, value):
        self.one_line_time = value

    def reset_one_line_time(self):
        self.one_line_time = False

    def get_one_line_time(self):
        return self.one_line_time

    clockOneLineTime = QtCore.pyqtProperty("int", get_one_line_time, set_one_line_time, reset_one_line_time)

    @QtCore.pyqtSlot(bool)
    def set_static_colon(self, value):
        self.staticColon = value

    def reset_static_colon(self):
        self.staticColon = False

    def get_static_colon(self):
        return self.staticColon

    clockStaticColon = QtCore.pyqtProperty("int", get_static_colon, set_static_colon, reset_static_colon)

    @QtCore.pyqtSlot(QtGui.QColor)
    def set_digi_hour_color(self, color=QtGui.QColor(50, 50, 255, 255)):
        self.digiHourColor = color

    def reset_digi_hour_color(self):
        self.digiHourColor = QtGui.QColor(50, 50, 255, 255)

    def get_digi_hour_color(self):
        return self.digiHourColor

    colorDigiHour = QtCore.pyqtProperty(QtGui.QColor, get_digi_hour_color, set_digi_hour_color, reset_digi_hour_color)

    @QtCore.pyqtSlot(QtGui.QColor)
    def set_digi_second_color(self, color=QtGui.QColor(50, 50, 255, 255)):
        self.digiSecondColor = color

    def reset_digi_second_color(self):
        self.digiSecondColor = QtGui.QColor(50, 50, 255, 255)

    def get_digi_second_color(self):
        return self.digiSecondColor

    colorDigiSecond = QtCore.pyqtProperty(QtGui.QColor, get_digi_second_color, set_digi_second_color,
                                          reset_digi_second_color)

    @QtCore.pyqtSlot(QtGui.QColor)
    def set_digi_digit_color(self, color=QtGui.QColor(50, 50, 255, 255)):
        self.digiDigitColor = color

    def reset_digi_digit_color(self):
        self.digiDigitColor = QtGui.QColor(50, 50, 255, 255)

    def get_digi_digit_color(self):
        return self.digiDigitColor

    colorDigiDigit = QtCore.pyqtProperty(QtGui.QColor, get_digi_digit_color, set_digi_digit_color,
                                         reset_digi_digit_color)

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        self.time = QtCore.QTime.currentTime()

        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        if self.clockMode == 0:
            self.paint_analog(painter)
        else:
            self.paint_digital(painter)

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

        painter.setPen(QtCore.Qt.NoPen)
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

        painter.setPen(QtCore.Qt.NoPen)
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

    @QtCore.pyqtSlot(str)
    def set_logo(self, logo_file=""):
        self.image_path = logo_file
        self.image = QtGui.QImage(logo_file)

    def get_logo(self):
        return self.image_path

    def reset_logo(self):
        self.set_logo()

    logoFile = QtCore.pyqtProperty(str, get_logo, set_logo, reset_logo)

    @QtCore.pyqtSlot(bool)
    def set_logo_upper(self, state=True):
        self.logo_upper = state

    def get_logo_upper(self):
        return self.logoUpper

    def reset_logo_upper(self):
        self.set_logo_upper(False)

    logoUpper = QtCore.pyqtProperty(bool, get_logo_upper, set_logo_upper, reset_logo_upper)

    def paint_digital(self, painter):
        # digital clock mode
        time = self.time

        # draw digits and colon
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.digiDigitColor)
        painter.setPen(self.digiDigitColor)

        if self.isAmPm and time.hour() > 12:
            if time.hour() >= 12:
                hour_str = "%02d" % (time.hour() - 12)
            else:
                hour_str = "%02d" % time.hour()
        else:
            hour_str = "%02d" % time.hour()

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

            if self.showSeconds:
                second_str = "%02d" % time.second()
                self.draw_digit(painter, (digit_spacing * -0.3) + seconds_offset_x, digit_spacing_y,
                                int(second_str[0:1]), 0.8, 3)
                self.draw_digit(painter, (digit_spacing * 0.3) + seconds_offset_x, digit_spacing_y,
                                int(second_str[1:2]), 0.8, 3)

        dot_size = 1.6
        # set painter to 12 o'clock position
        painter.rotate(-90.0)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.digiHourColor)
        painter.setPen(self.digiHourColor)

        # draw hour marks
        painter.save()
        for i in range(12):
            painter.drawEllipse(QtCore.QPointF(95, 0), dot_size, dot_size)
            painter.rotate(30.0)
        painter.restore()

        painter.setPen(QtCore.Qt.NoPen)
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

            if (self.showSeconds and not self.one_line_time) or self.logo_upper:
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
                   slant=19.0):
        value = int(value)
        # draw dots from one 7segment digit
        dot_slant = dot_offset / slant  # horizontal slant of each row

        # decimal to segment conversion table
        segments = [0b0111111, 0b0000110, 0b1011011, 0b1001111, 0b1100110, 0b1101101, 0b1111101, 0b0000111, 0b1111111,
                    0b1101111]

        if segments[value] & 1 << 6:
            # segment g
            current_row = 0  # center row
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x - (dot_offset * 1.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x - (dot_offset * 0.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x + (dot_offset * 0.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x + (dot_offset * 1.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)

        if segments[value] & 1 << 0:
            # segment a
            current_row = 9  # top row
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x - (dot_offset * 1.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x - (dot_offset * 0.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x + (dot_offset * 0.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x + (dot_offset * 1.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)

        if segments[value] & 1 << 3:
            # segment d
            current_row = -9  # bottom row
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x - (dot_offset * 1.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x - (dot_offset * 0.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x + (dot_offset * 0.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)
            painter.drawEllipse(QtCore.QPointF(digit_start_pos_x + (dot_offset * 1.5) + (dot_slant * current_row),
                                               digit_start_pos_y - (dot_offset / 2 * current_row)), dot_size, dot_size)

        if segments[value] & 1 << 5:
            # segment f
            yOffset = -0.75
            xOffset = +0.75
            current_row = 1
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = 2
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = 3
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = 4
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)

        if segments[value] & 1 << 1:
            # segment b
            yOffset = -1.2
            xOffset = -0.5
            current_row = 1
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = 2
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = 3
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = 4
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)

        if segments[value] & 1 << 4:
            # segment e
            yOffset = +1.2
            xOffset = +0.5
            current_row = -1
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -2
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -3
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -4
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset - (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)

        if segments[value] & 1 << 2:
            # segment c
            yOffset = +0.75
            xOffset = -0.75
            current_row = -1
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -2
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -3
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)
            current_row = -4
            painter.drawEllipse(
                QtCore.QPointF(digit_start_pos_x - xOffset + (dot_offset * 2.0) + (dot_slant * 2 * current_row),
                               digit_start_pos_y - yOffset - (dot_offset * current_row)), dot_size, dot_size)


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
    sys.exit(app.exec_())
