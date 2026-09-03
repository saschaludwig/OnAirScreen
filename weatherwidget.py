#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# start.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################


from PySide6 import QtCore, QtGui, QtWidgets
import PySide6.QtNetwork as QtNetwork
import json
import logging

from exceptions import JsonParseError, WeatherApiError, log_exception

# Configure logging
logger = logging.getLogger(__name__)


def format_owm_city_label(place: dict) -> str:
    """Format a geocoding result as 'Berlin, DE' or 'London, US (Kentucky)'."""
    name = str(place.get("name") or "").strip()
    country = str(place.get("country") or "").strip()
    state = str(place.get("state") or "").strip()
    if name and country and state:
        return f"{name}, {country} ({state})"
    if name and country:
        return f"{name}, {country}"
    return name


def parse_owm_geocode_results(payload: str) -> list[tuple[str, dict]]:
    """Parse Geocoding API JSON into (label, {lat, lon}) pairs."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    results: list[tuple[str, dict]] = []
    for place in data:
        if not isinstance(place, dict):
            continue
        lat = place.get("lat")
        lon = place.get("lon")
        if lat is None or lon is None:
            continue
        try:
            coords = {"lat": float(lat), "lon": float(lon)}
        except (TypeError, ValueError):
            continue
        label = format_owm_city_label(place)
        if not label:
            continue
        results.append((label, coords))
    return results


def extract_owm_city_id(payload: str) -> str | None:
    """Extract city ID from a Current Weather API JSON body."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    city_id = data.get("id")
    if city_id is None:
        return None
    return str(city_id)


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
        self.verticalLayout_3.setContentsMargins(6, 6, 6, 6)
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
        self.cityLabel.setFont(font)
        self.cityLabel.setStyleSheet("color: #fff;")
        self.cityLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._apply_drop_shadow(self.cityLabel, 10)
        self.verticalLayout.addWidget(self.cityLabel)

        # weather label
        self.weatherLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.weatherLabel.setFont(font)
        self.weatherLabel.setStyleSheet("color: #fff")
        self.weatherLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._apply_drop_shadow(self.weatherLabel, 10)
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
        self._apply_drop_shadow(self.weatherIcon, 20)
        self.horizontalLayout.addWidget(self.weatherIcon)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)

        # temperature label
        self.temperatureLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(45)
        font.setBold(True)
        self.temperatureLabel.setFont(font)
        self.temperatureLabel.setStyleSheet("color: #fff;")
        self.temperatureLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._apply_drop_shadow(self.temperatureLabel, 20)
        self.verticalLayout_2.addWidget(self.temperatureLabel)

        # condition label
        self.conditionLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.conditionLabel.setFont(font)
        self.conditionLabel.setStyleSheet("color: #fff")
        self.conditionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._apply_drop_shadow(self.conditionLabel, 10)
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

    @staticmethod
    def _apply_drop_shadow(widget: QtWidgets.QWidget, blur_radius: float) -> None:
        """Attach a drop-shadow glow, parented so PySide6 keeps the effect alive."""
        effect = QtWidgets.QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur_radius)
        effect.setColor(QtGui.QColor(0, 0, 0, 220))
        effect.setOffset(0, 0)
        widget.setGraphicsEffect(effect)

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
                error = JsonParseError(
                    f"Unexpected JSON payload in OWM Response: {e}",
                    json_data=reply_string[:500] if len(reply_string) > 500 else reply_string
                )
                log_exception(logger, error, use_exc_info=False)
                return
            
            # Validate JSON structure to prevent KeyError/IndexError
            try:
                if "weather" not in weather_json or len(weather_json["weather"]) == 0:
                    error = WeatherApiError(
                        "OWM response missing weather array",
                        api_response=reply_string[:500] if len(reply_string) > 500 else reply_string
                    )
                    log_exception(logger, error, use_exc_info=False)
                    return
                if "main" not in weather_json:
                    error = WeatherApiError(
                        "OWM response missing main data",
                        api_response=reply_string[:500] if len(reply_string) > 500 else reply_string
                    )
                    log_exception(logger, error, use_exc_info=False)
                    return
                if "name" not in weather_json:
                    error = WeatherApiError(
                        "OWM response missing city name",
                        api_response=reply_string[:500] if len(reply_string) > 500 else reply_string
                    )
                    log_exception(logger, error, use_exc_info=False)
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
                error = WeatherApiError(
                    f"OWM response has unexpected structure: {e}",
                    api_response=reply_string[:500] if len(reply_string) > 500 else reply_string
                )
                log_exception(logger, error, use_exc_info=False)
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
        from utils import settings_group
        settings = QtCore.QSettings(QtCore.QSettings.Scope.UserScope, "astrastudio", "OnAirScreen")
        with settings_group(settings, "WeatherWidget"):
            self.widgetEnabled = settings.value('owmWidgetEnabled', False, type=bool)
            self.owmAPIKey = settings.value('owmAPIKey', "")
            self.owmCityID = settings.value('owmCityID', "2643743")
            self.owmLanguage = self.owm_languages.get(settings.value('owmLanguage', "English"))
            self.owmUnit = self.owm_units.get(settings.value('owmUnit', "Celsius"))

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self.width(), self.height(), QtGui.QPixmap(self.bg))
