#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
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


from PyQt6 import QtCore, QtGui, QtWidgets
import PyQt6.QtNetwork as QtNetwork
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)


class WeatherWidget(QtWidgets.QWidget):
    owm_languages = {"Arabic": "ar", "Bulgarian": "bg", "Catalan": "ca", "Czech": "cz", "German": "de",
                     "Greek": "el", "English": "en", "Persian (Farsi)": "fa", "Finnish": "fi", "French": "fr",
                     "Galician": "gl", "Croatian": "hr", "Hungarian": "hu", "Italian": "it", "Japanese": "ja",
                     "Korean": "kr", "Latvian": "la", "Lithuanian": "lt", "Macedonian": "mk", "Dutch": "nl",
                     "Polish": "pl", "Portuguese": "pt", "Romanian": "ro", "Russian": "ru", "Swedish": "se",
                     "Slovak": "sk", "Slovenian": "sl", "Spanish": "es", "Turkish": "tr", "Ukrainian": "ua",
                     "Vietnamese": "vi", "Chinese Simplified": "zh_cn", "Chinese Traditional": "zh_tw."}
    owm_units = {"Kelvin": "", "Celsius": "metric", "Fahrenheit": "imperial"}
    owm_units_abbrev = {"": "K", "metric": "°C", "imperial": "°F"}

    def __init__(self, parent=None):
        super(WeatherWidget, self).__init__(parent)
        self.nam = None
        self.bg = None
        self.widgetEnabled = None
        self.owmAPIKey = None
        self.owmCityID = None
        self.owmLanguage = None
        self.owmUnit = None
        self.readConfig()

        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_3.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(0)

        # spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        # self.verticalLayout.addItem(spacerItem)

        # city label
        self.cityLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.cityLabel.setFont(font)
        self.cityLabel.setStyleSheet("color: #fff;")
        self.cityLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        self.weatherLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        weatherfx = QtWidgets.QGraphicsDropShadowEffect()
        weatherfx.setBlurRadius(10)
        weatherfx.setColor(QtGui.QColor("#000"))
        weatherfx.setOffset(0, 0)
        self.weatherLabel.setGraphicsEffect(weatherfx)
        self.verticalLayout.addWidget(self.weatherLabel)

        # spacer
        spacer_item1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacer_item1)

        self.verticalLayout_3.addLayout(self.verticalLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)

        # weather icon
        self.weatherIcon = QtWidgets.QLabel(self)
        icon_pixmap = QtGui.QPixmap()
        self.weatherIcon.setPixmap(icon_pixmap)
        self.weatherIcon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_fx = QtWidgets.QGraphicsDropShadowEffect()
        icon_fx.setBlurRadius(20)
        icon_fx.setColor(QtGui.QColor("#000"))
        icon_fx.setOffset(0, 0)
        self.weatherIcon.setGraphicsEffect(icon_fx)
        self.horizontalLayout.addWidget(self.weatherIcon)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)

        # temperature label
        self.temperatureLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(45)
        font.setWeight(75)
        self.temperatureLabel.setFont(font)
        self.temperatureLabel.setStyleSheet("color: #fff;")
        self.temperatureLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        self.conditionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        condfx = QtWidgets.QGraphicsDropShadowEffect()
        condfx.setBlurRadius(10)
        condfx.setColor(QtGui.QColor("#000"))
        condfx.setOffset(0, 0)
        self.conditionLabel.setGraphicsEffect(condfx)
        self.verticalLayout_2.addWidget(self.conditionLabel)

        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        # set demo text
        self.setData("", "", "")
        self.updateWeather()

        # start timer for background update every 10 minutes
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.updateWeather)
        self.updateTimer.start(10 * 60 * 1000)

    def updateWeather(self) -> None:
        """Update weather data from OpenWeatherMap API"""
        if self.widgetEnabled and self.owmAPIKey:
            logger.debug("update weather called")
            self.makeOWMApiCall()
        else:
            logger.debug("Weather update skipped: widget disabled or no API key")

    def setData(self, city: str, temperature: str, condition: str, icon: str = "01d", background: str = None, label: str = "WEATHER") -> None:
        """
        Set weather data to display
        
        Args:
            city: City name
            temperature: Temperature string
            condition: Weather condition description
            icon: Weather icon code (default: "01d")
            background: Background image name (default: None)
            label: Label text (default: "WEATHER")
        """
        logger.debug(f"Weather: icon={icon}, background={background}")
        self.cityLabel.setText(city)
        self.temperatureLabel.setText(temperature)
        self.conditionLabel.setText(condition)
        self.weatherLabel.setText(label)
        self.setWeatherIcon(icon)
        self.setWeatherBackground(background)

    def setWeatherIcon(self, icon: str) -> None:
        """
        Set the weather icon
        
        Args:
            icon: Weather icon code (e.g., "01d")
        """
        icon_pixmap = QtGui.QPixmap(f":/weather/images/weather_icons/{icon}.png")
        icon_pixmap.setDevicePixelRatio(5)
        self.weatherIcon.setPixmap(icon_pixmap)

    def setWeatherBackground(self, background: str) -> None:
        """
        Set the weather background image
        
        Args:
            background: Background image name
        """
        self.bg = f":/weather_backgrounds/images/weather_backgrounds/{background}.jpg"
        self.repaint()

    def makeOWMApiCall(self) -> None:
        """Make API call to OpenWeatherMap to fetch current weather"""
        # Check if widget is enabled and API key is present
        if not self.widgetEnabled:
            logger.debug("OWM API call skipped: widget is disabled")
            return
        if not self.owmAPIKey or self.owmAPIKey.strip() == "":
            logger.debug("OWM API call skipped: no API key configured")
            return
        
        logger.debug("OWM API Call")
        url = "https://api.openweathermap.org/data/2.5/weather?id=" + self.owmCityID + "&units=" + self.owmUnit + "&lang=" + self.owmLanguage + "&appid=" + self.owmAPIKey
        req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        self.nam = QtNetwork.QNetworkAccessManager()
        self.nam.finished.connect(self.handleOWMResponse)
        self.nam.get(req)

    def handleOWMResponse(self, reply) -> None:
        """
        Handle response from OpenWeatherMap API
        
        Args:
            reply: QNetworkReply object containing the API response
        """
        er = reply.error()
        if er == QtNetwork.QNetworkReply.NetworkError.NoError:
            bytes_string = reply.readAll()
            reply_string = str(bytes_string, 'utf-8')
            try:
                weather_json = (json.loads(reply_string))
            except json.JSONDecodeError as e:
                error_string = f"Unexpected JSON payload in OWM Response: {reply_string}"
                logger.error(f"{error_string}: {e}")
                return
            
            # Validate JSON structure to prevent KeyError/IndexError
            try:
                if "weather" not in weather_json or len(weather_json["weather"]) == 0:
                    logger.error("OWM response missing weather array")
                    return
                if "main" not in weather_json:
                    logger.error("OWM response missing main data")
                    return
                if "name" not in weather_json:
                    logger.error("OWM response missing city name")
                    return
                
                main_weather = weather_json["weather"][0]["main"]
                condition = weather_json["weather"][0]["description"]
                city = weather_json["name"]
                unit_symbol = self.owm_units_abbrev.get(self.owmUnit, "°C")  # Default to °C if not found
                if unit_symbol is None:
                    unit_symbol = "°C"
                temp = "{:.0f}{}".format(weather_json["main"]["temp"], unit_symbol)
                icon = weather_json["weather"][0]["icon"]
                background = icon
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"OWM response has unexpected structure: {e}")
                return
            if self.owmLanguage == "de":
                label = "WETTER"
            else:
                label = "WEATHER"
            self.setData(city=city, condition=condition, temperature=temp, icon=icon, background=background,
                         label=label)
        else:
            error_string = f"Error occurred: {er}, {reply.errorString()}"
            logger.error(error_string)

    def readConfig(self) -> None:
        """Read weather widget configuration from QSettings"""
        settings = QtCore.QSettings(QtCore.QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("WeatherWidget")
        self.widgetEnabled = settings.value('owmWidgetEnabled', False, type=bool)
        self.owmAPIKey = settings.value('owmAPIKey', "")
        self.owmCityID = settings.value('owmCityID', "2643743")
        self.owmLanguage = self.owm_languages.get(settings.value('owmLanguage', "English"))
        self.owmUnit = self.owm_units.get(settings.value('owmUnit', "Celsius"))
        settings.endGroup()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self.width(), self.height(), QtGui.QPixmap(self.bg))
