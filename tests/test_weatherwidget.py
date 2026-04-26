#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for weatherwidget.py
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QByteArray
import PyQt6.QtNetwork as QtNetwork

# Import after QApplication setup
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from weatherwidget import WeatherWidget


@pytest.fixture
def weather_widget():
    """Create a WeatherWidget instance for testing"""
    with patch('weatherwidget.QtCore.QSettings'):
        with patch('utils.settings_group'):
            with patch.object(WeatherWidget, 'updateWeather'):
                widget = WeatherWidget()
                # Mock the UI components
                widget.cityLabel = Mock()
                widget.temperatureLabel = Mock()
                widget.conditionLabel = Mock()
                widget.weatherLabel = Mock()
                widget.weatherIcon = Mock()
                widget.updateTimer = Mock()
                widget.nam = None
                widget.bg = None
                # Mock methods that are called by setData
                widget.setWeatherIcon = Mock()
                widget.setWeatherBackground = Mock()
                # Ensure widget is disabled by default to prevent API calls
                widget.widgetEnabled = False
                widget.owmAPIKey = None
                return widget


class TestWeatherWidgetSetData:
    """Test setData() method"""

    def test_set_data_all_fields(self, weather_widget):
        """Test setData() with all fields"""
        weather_widget.setData("Berlin", "20°C", "Sunny", "01d", "01d", "WETTER")
        
        weather_widget.cityLabel.setText.assert_called_once_with("Berlin")
        weather_widget.temperatureLabel.setText.assert_called_once_with("20°C")
        weather_widget.conditionLabel.setText.assert_called_once_with("Sunny")
        weather_widget.weatherLabel.setText.assert_called_once_with("WETTER")
        weather_widget.setWeatherIcon.assert_called_once_with("01d")
        weather_widget.setWeatherBackground.assert_called_once_with("01d")

    def test_set_data_defaults(self, weather_widget):
        """Test setData() with default parameters"""
        weather_widget.setData("London", "15°C", "Cloudy")
        
        weather_widget.cityLabel.setText.assert_called_once_with("London")
        weather_widget.temperatureLabel.setText.assert_called_once_with("15°C")
        weather_widget.conditionLabel.setText.assert_called_once_with("Cloudy")
        weather_widget.weatherLabel.setText.assert_called_once_with("WEATHER")
        weather_widget.setWeatherIcon.assert_called_once_with("01d")
        weather_widget.setWeatherBackground.assert_called_once_with(None)


class TestWeatherWidgetSetWeatherIcon:
    """Test setWeatherIcon() method"""

    def test_set_weather_icon(self, weather_widget):
        """Test setWeatherIcon() with valid icon code"""
        # Restore the real method
        weather_widget.setWeatherIcon = WeatherWidget.setWeatherIcon.__get__(weather_widget, WeatherWidget)
        with patch('weatherwidget.QtGui.QPixmap') as mock_pixmap:
            mock_pixmap_instance = Mock()
            mock_pixmap.return_value = mock_pixmap_instance
            
            weather_widget.setWeatherIcon("02n")
            
            mock_pixmap.assert_called_once_with(":/weather/images/weather_icons/02n.png")
            mock_pixmap_instance.setDevicePixelRatio.assert_called_once_with(5)
            weather_widget.weatherIcon.setPixmap.assert_called_once_with(mock_pixmap_instance)


class TestWeatherWidgetSetWeatherBackground:
    """Test setWeatherBackground() method"""

    def test_set_weather_background(self, weather_widget):
        """Test setWeatherBackground() with background name"""
        # Restore the real method
        weather_widget.setWeatherBackground = WeatherWidget.setWeatherBackground.__get__(weather_widget, WeatherWidget)
        with patch.object(weather_widget, 'repaint') as mock_repaint:
            weather_widget.setWeatherBackground("01d")
            
            assert weather_widget.bg == ":/weather_backgrounds/images/weather_backgrounds/01d.jpg"
            mock_repaint.assert_called_once()

    def test_set_weather_background_none(self, weather_widget):
        """Test setWeatherBackground() with None"""
        # Restore the real method
        weather_widget.setWeatherBackground = WeatherWidget.setWeatherBackground.__get__(weather_widget, WeatherWidget)
        with patch.object(weather_widget, 'repaint') as mock_repaint:
            weather_widget.setWeatherBackground(None)
            
            assert weather_widget.bg == ":/weather_backgrounds/images/weather_backgrounds/None.jpg"
            mock_repaint.assert_called_once()


class TestWeatherWidgetUpdateWeather:
    """Test updateWeather() method"""

    def test_update_weather_enabled_with_key(self, weather_widget):
        """Test updateWeather() when widget is enabled and API key is present"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = "test_key"
        
        with patch.object(weather_widget, 'makeOWMApiCall') as mock_api_call:
            weather_widget.updateWeather()
            mock_api_call.assert_called_once()

    def test_update_weather_disabled(self, weather_widget):
        """Test updateWeather() when widget is disabled"""
        weather_widget.widgetEnabled = False
        weather_widget.owmAPIKey = "test_key"
        
        with patch.object(weather_widget, 'makeOWMApiCall') as mock_api_call:
            weather_widget.updateWeather()
            mock_api_call.assert_not_called()

    def test_update_weather_no_api_key(self, weather_widget):
        """Test updateWeather() when no API key is present"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = None
        
        with patch.object(weather_widget, 'makeOWMApiCall') as mock_api_call:
            weather_widget.updateWeather()
            mock_api_call.assert_not_called()

    def test_update_weather_empty_api_key(self, weather_widget):
        """Test updateWeather() when API key is empty string"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = ""
        
        with patch.object(weather_widget, 'makeOWMApiCall') as mock_api_call:
            weather_widget.updateWeather()
            mock_api_call.assert_not_called()


class TestWeatherWidgetMakeOWMApiCall:
    """Test makeOWMApiCall() method"""

    def test_make_owm_api_call_enabled_with_key(self, weather_widget):
        """Test makeOWMApiCall() when enabled and API key present"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = "test_key"
        weather_widget.owmCityID = "123456"
        weather_widget.owmUnit = "metric"
        weather_widget.owmLanguage = "en"
        
        with patch('weatherwidget.QtNetwork.QNetworkAccessManager') as mock_nam_class:
            with patch('weatherwidget.QtNetwork.QNetworkRequest') as mock_request_class:
                with patch('weatherwidget.QtCore.QUrl') as mock_url:
                    mock_nam = Mock()
                    mock_nam_class.return_value = mock_nam
                    mock_request = Mock()
                    mock_request_class.return_value = mock_request
                    mock_url_instance = Mock()
                    mock_url.return_value = mock_url_instance
                    
                    weather_widget.makeOWMApiCall()
                    
                    mock_url.assert_called_once()
                    mock_request_class.assert_called_once()
                    mock_nam_class.assert_called_once()
                    mock_nam.finished.connect.assert_called_once()
                    mock_nam.get.assert_called_once_with(mock_request)
                    assert weather_widget.nam == mock_nam

    def test_make_owm_api_call_disabled(self, weather_widget):
        """Test makeOWMApiCall() when widget is disabled"""
        weather_widget.widgetEnabled = False
        weather_widget.owmAPIKey = "test_key"
        
        with patch('weatherwidget.QtNetwork.QNetworkAccessManager') as mock_nam_class:
            weather_widget.makeOWMApiCall()
            mock_nam_class.assert_not_called()

    def test_make_owm_api_call_no_key(self, weather_widget):
        """Test makeOWMApiCall() when no API key"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = None
        
        with patch('weatherwidget.QtNetwork.QNetworkAccessManager') as mock_nam_class:
            weather_widget.makeOWMApiCall()
            mock_nam_class.assert_not_called()

    def test_make_owm_api_call_empty_key(self, weather_widget):
        """Test makeOWMApiCall() when API key is empty"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = ""
        
        with patch('weatherwidget.QtNetwork.QNetworkAccessManager') as mock_nam_class:
            weather_widget.makeOWMApiCall()
            mock_nam_class.assert_not_called()

    def test_make_owm_api_call_whitespace_key(self, weather_widget):
        """Test makeOWMApiCall() when API key is only whitespace"""
        weather_widget.widgetEnabled = True
        weather_widget.owmAPIKey = "   "
        
        with patch('weatherwidget.QtNetwork.QNetworkAccessManager') as mock_nam_class:
            weather_widget.makeOWMApiCall()
            mock_nam_class.assert_not_called()


class TestWeatherWidgetHandleOWMResponse:
    """Test handleOWMResponse() method"""

    def test_handle_owm_response_success(self, weather_widget):
        """Test handleOWMResponse() with successful response"""
        weather_widget.owmUnit = "metric"
        weather_widget.owmLanguage = "en"
        
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "name": "Berlin",
            "weather": [{
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }],
            "main": {
                "temp": 20.5
            }
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            
            mock_set_data.assert_called_once()
            call_args = mock_set_data.call_args
            assert call_args[1]['city'] == "Berlin"
            assert call_args[1]['condition'] == "clear sky"
            assert "20°C" in call_args[1]['temperature'] or "21°C" in call_args[1]['temperature']
            assert call_args[1]['icon'] == "01d"
            assert call_args[1]['background'] == "01d"
            assert call_args[1]['label'] == "WEATHER"

    def test_handle_owm_response_german_language(self, weather_widget):
        """Test handleOWMResponse() with German language"""
        weather_widget.owmUnit = "metric"
        weather_widget.owmLanguage = "de"
        
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "name": "Berlin",
            "weather": [{
                "main": "Clear",
                "description": "klarer Himmel",
                "icon": "01d"
            }],
            "main": {
                "temp": 20.5
            }
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            
            call_args = mock_set_data.call_args
            assert call_args[1]['label'] == "WETTER"

    def test_handle_owm_response_missing_weather_array(self, weather_widget):
        """Test handleOWMResponse() with missing weather array"""
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "name": "Berlin",
            "main": {
                "temp": 20.5
            }
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            mock_set_data.assert_not_called()

    def test_handle_owm_response_empty_weather_array(self, weather_widget):
        """Test handleOWMResponse() with empty weather array"""
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "name": "Berlin",
            "weather": [],
            "main": {
                "temp": 20.5
            }
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            mock_set_data.assert_not_called()

    def test_handle_owm_response_missing_main(self, weather_widget):
        """Test handleOWMResponse() with missing main data"""
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "name": "Berlin",
            "weather": [{
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }]
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            mock_set_data.assert_not_called()

    def test_handle_owm_response_missing_name(self, weather_widget):
        """Test handleOWMResponse() with missing city name"""
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "weather": [{
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }],
            "main": {
                "temp": 20.5
            }
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            mock_set_data.assert_not_called()

    def test_handle_owm_response_invalid_json(self, weather_widget):
        """Test handleOWMResponse() with invalid JSON"""
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        reply.readAll.return_value = QByteArray(b"invalid json {")
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            mock_set_data.assert_not_called()

    def test_handle_owm_response_network_error(self, weather_widget):
        """Test handleOWMResponse() with network error"""
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.ConnectionRefusedError
        reply.errorString.return_value = "Connection refused"
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            mock_set_data.assert_not_called()

    def test_handle_owm_response_fahrenheit_unit(self, weather_widget):
        """Test handleOWMResponse() with Fahrenheit unit"""
        weather_widget.owmUnit = "imperial"
        weather_widget.owmLanguage = "en"
        
        reply = Mock()
        reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        
        weather_data = {
            "name": "New York",
            "weather": [{
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }],
            "main": {
                "temp": 68.0
            }
        }
        reply_string = json.dumps(weather_data)
        reply.readAll.return_value = QByteArray(reply_string.encode('utf-8'))
        
        with patch.object(weather_widget, 'setData') as mock_set_data:
            weather_widget.handleOWMResponse(reply)
            
            call_args = mock_set_data.call_args
            assert "°F" in call_args[1]['temperature']

