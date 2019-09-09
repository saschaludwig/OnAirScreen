#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2019 Sascha Ludwig, astrastudio.de
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
#############################################################################


from PyQt5 import QtCore, QtGui, QtWidgets


class WeatherWidget(QtWidgets.QWidget):

    # https://openweathermap.org/weather-conditions
    #":/weather_backgrounds/images/"
    conditions = {"Thunderstorm": {"bg": "thunder.jpg", "iconday": "thunder.svg"},
                  "Drizzle":      {"bg": "rain.jpg",    "iconday": "rainy-1.svg"},
                  "Rain":         {"bg": "rain.jpg",    "iconday": "rainy-6.svg"},
                  "Snow":         {"bg": "snow.jpg",    "iconday": "snowy-6.svg"},
                  "Mist":         {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Haze":         {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Dust":         {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Fog":          {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Sand":         {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Ash":          {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Squall":       {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Tornado":      {"bg": "fog.jpg",     "iconday": "thunder.svg"},
                  "Clear":        {"day":   {"bg": "clear_day.jpg", "icon": "day.svg"},
                                   "night": {"bg": "clear_night.jpg", "icon": "night.svg"}},
                  "Clouds":       {"day":   {"bg": "cloudy.jpg", "icon": "day.svg"},
                                   "night": {"bg": "clear_night.jpg", "icon": "night.svg"}},

                  }

    #print(conditions["Clear"]["day"]["icon"])
    #rain.jpg
    #clear_day.jpg
    #partly_cloudy_day.jpg
    #cloudy.jpg
    #fog.jpg
    #thunder.jpg
    #clear_night.jpg


    def __init__(self, parent=None):
        super(WeatherWidget, self).__init__(parent)
        self.setObjectName("WeatherWidget")
        # self.resize(221, 135)

        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_3.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        #spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #self.verticalLayout.addItem(spacerItem)

        # city label
        self.cityLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.cityLabel.setFont(font)
        self.cityLabel.setStyleSheet("color: #fff;")
        self.cityLabel.setAlignment(QtCore.Qt.AlignCenter)
        cityfx = QtWidgets.QGraphicsDropShadowEffect()
        cityfx.setBlurRadius(10)
        cityfx.setColor(QtGui.QColor("#000"))
        cityfx.setOffset(0, 0)
        self.cityLabel.setGraphicsEffect(cityfx)
        self.verticalLayout.addWidget(self.cityLabel)

        # weather label
        self.weatherLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.weatherLabel.setFont(font)
        self.weatherLabel.setStyleSheet("color: #fff")
        self.weatherLabel.setAlignment(QtCore.Qt.AlignCenter)
        weatherfx = QtWidgets.QGraphicsDropShadowEffect()
        weatherfx.setBlurRadius(10)
        weatherfx.setColor(QtGui.QColor("#000"))
        weatherfx.setOffset(0, 0)
        self.weatherLabel.setGraphicsEffect(weatherfx)
        self.verticalLayout.addWidget(self.weatherLabel)

        # spacer
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)

        self.verticalLayout_3.addLayout(self.verticalLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)

        # weather icon
        self.weatherIcon = QtWidgets.QLabel(self)
        iconPixmap = QtGui.QPixmap(":/weather/images/weather/rainy-1.svg")
        self.weatherIcon.setPixmap(iconPixmap)
        self.weatherIcon.setAlignment(QtCore.Qt.AlignCenter)
        self.horizontalLayout.addWidget(self.weatherIcon)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)

        # temperature label
        self.temperatureLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(42)
        self.temperatureLabel.setFont(font)
        self.temperatureLabel.setStyleSheet("color: #fff;")
        self.temperatureLabel.setAlignment(QtCore.Qt.AlignCenter)
        tempfx = QtWidgets.QGraphicsDropShadowEffect()
        tempfx.setBlurRadius(20)
        tempfx.setColor(QtGui.QColor("#000"))
        tempfx.setOffset(0, 0)
        self.temperatureLabel.setGraphicsEffect(tempfx)
        self.verticalLayout_2.addWidget(self.temperatureLabel)

        # condition label
        self.conditionLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.conditionLabel.setFont(font)
        self.conditionLabel.setStyleSheet("color: #fff")
        self.conditionLabel.setAlignment(QtCore.Qt.AlignCenter)
        condfx = QtWidgets.QGraphicsDropShadowEffect()
        condfx.setBlurRadius(10)
        condfx.setColor(QtGui.QColor("#000"))
        condfx.setOffset(0, 0)
        self.conditionLabel.setGraphicsEffect(condfx)
        self.verticalLayout_2.addWidget(self.conditionLabel)

        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        # set demo text
        self.cityLabel.setText("NEW YORK")
        self.weatherLabel.setText("WEATHER")
        self.temperatureLabel.setText("15°C")
        self.conditionLabel.setText("Light Rain")

        # QtCore.QMetaObject.connectSlotsByName(self)

    def paintEvent(self, event):
        print("paint")
        painter = QtGui.QPainter(self)
        #painter.drawPixmap(0, 0, self.width(), self.height(), QtGui.QPixmap(":/weather_backgrounds/images/rain.jpg"))
        painter.drawPixmap(0, 0, self.width(), self.height(), QtGui.QPixmap(":/weather_backgrounds/images/clear_day.jpg"))


import resources_rc
