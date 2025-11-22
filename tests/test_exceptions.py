#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for exceptions module
"""

import pytest
import logging
from unittest.mock import Mock, patch

from exceptions import (
    OnAirScreenError, NetworkError, UdpError, HttpError, WebSocketError, MqttError,
    PortInUseError, PermissionDeniedError, CommandError, CommandParseError,
    CommandValidationError, UnknownCommandError, InvalidCommandFormatError,
    ConfigurationError, SettingsError, InvalidConfigValueError, ValidationError,
    TextValidationError, ColorValidationError, ValueValidationError, ApiError,
    WeatherApiError, JsonParseError, JsonSerializationError, EncodingError,
    WidgetError, WidgetAccessError, log_exception
)


class TestOnAirScreenError:
    """Test base exception class"""
    
    def test_basic_exception(self):
        """Test basic exception creation"""
        error = OnAirScreenError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context == {}
    
    def test_exception_with_context(self):
        """Test exception with context"""
        error = OnAirScreenError("Test error", {"key": "value", "num": 42})
        assert "key=value" in str(error)
        assert "num=42" in str(error)
        assert error.context == {"key": "value", "num": 42}


class TestNetworkErrors:
    """Test network-related exceptions"""
    
    def test_udp_error(self):
        """Test UDP error"""
        error = UdpError("UDP connection failed")
        assert isinstance(error, NetworkError)
        assert isinstance(error, OnAirScreenError)
        assert str(error) == "UDP connection failed"
    
    def test_http_error(self):
        """Test HTTP error with status code"""
        error = HttpError("Not found", status_code=404)
        assert isinstance(error, NetworkError)
        assert error.status_code == 404
        assert "HTTP 404" in str(error)
    
    def test_websocket_error(self):
        """Test WebSocket error"""
        error = WebSocketError("WebSocket connection failed")
        assert isinstance(error, NetworkError)
    
    def test_mqtt_error(self):
        """Test MQTT error"""
        error = MqttError("MQTT connection failed")
        assert isinstance(error, NetworkError)
    
    def test_port_in_use_error(self):
        """Test port in use error"""
        error = PortInUseError(8080, "TCP")
        assert isinstance(error, NetworkError)
        assert error.port == 8080
        assert error.protocol == "TCP"
        assert "8080" in str(error)
        assert "TCP" in str(error)
    
    def test_permission_denied_error(self):
        """Test permission denied error"""
        error = PermissionDeniedError(80, "HTTP")
        assert isinstance(error, NetworkError)
        assert error.port == 80
        assert error.protocol == "HTTP"
        assert "80" in str(error)
        assert "HTTP" in str(error)


class TestCommandErrors:
    """Test command-related exceptions"""
    
    def test_command_parse_error(self):
        """Test command parse error"""
        error = CommandParseError("Invalid format", command_data="LED1:ON:EXTRA")
        assert isinstance(error, CommandError)
        assert error.command_data == "LED1:ON:EXTRA"
        assert "LED1:ON:EXTRA" in str(error)
    
    def test_command_validation_error(self):
        """Test command validation error"""
        error = CommandValidationError("Invalid value", command="LED1", value="INVALID")
        assert isinstance(error, CommandError)
        assert error.command == "LED1"
        assert error.value == "INVALID"
        assert "LED1" in str(error)
        assert "INVALID" in str(error)
    
    def test_unknown_command_error(self):
        """Test unknown command error"""
        error = UnknownCommandError("UNKNOWN")
        assert isinstance(error, CommandError)
        assert error.command == "UNKNOWN"
        assert "UNKNOWN" in str(error)
    
    def test_invalid_command_format_error(self):
        """Test invalid command format error"""
        error = InvalidCommandFormatError("Missing colon", command_data="LED1ON")
        assert isinstance(error, CommandError)
        assert error.command_data == "LED1ON"


class TestConfigurationErrors:
    """Test configuration-related exceptions"""
    
    def test_settings_error(self):
        """Test settings error"""
        error = SettingsError("Failed to load settings")
        assert isinstance(error, ConfigurationError)
    
    def test_invalid_config_value_error(self):
        """Test invalid config value error"""
        error = InvalidConfigValueError("Invalid port", key="httpport", value=-1)
        assert isinstance(error, ConfigurationError)
        assert error.key == "httpport"
        assert error.value == -1
        assert "httpport" in str(error)


class TestValidationErrors:
    """Test validation-related exceptions"""
    
    def test_text_validation_error(self):
        """Test text validation error"""
        error = TextValidationError("Text too long", field_name="NOW", text="x" * 1000)
        assert isinstance(error, ValidationError)
        assert error.field_name == "NOW"
        assert error.text == "x" * 1000
        assert "NOW" in str(error)
    
    def test_color_validation_error(self):
        """Test color validation error"""
        error = ColorValidationError("Invalid color", color_value="#GGGGGG")
        assert isinstance(error, ValidationError)
        assert error.color_value == "#GGGGGG"
    
    def test_value_validation_error(self):
        """Test value validation error"""
        error = ValueValidationError("Value out of range", value=99999)
        assert isinstance(error, ValidationError)
        assert error.value == 99999


class TestApiErrors:
    """Test API-related exceptions"""
    
    def test_weather_api_error(self):
        """Test weather API error"""
        error = WeatherApiError("API returned error", api_response='{"error": "invalid key"}')
        assert isinstance(error, ApiError)
        assert error.api_response == '{"error": "invalid key"}'
    
    def test_json_parse_error(self):
        """Test JSON parse error"""
        error = JsonParseError("Invalid JSON", json_data='{"invalid": json}')
        assert isinstance(error, ApiError)
        assert error.json_data == '{"invalid": json}'
    
    def test_json_serialization_error(self):
        """Test JSON serialization error"""
        error = JsonSerializationError("Cannot serialize", data={"key": object()})
        assert isinstance(error, ApiError)
        assert error.data is not None


class TestEncodingErrors:
    """Test encoding-related exceptions"""
    
    def test_encoding_error(self):
        """Test encoding error"""
        error = EncodingError("UTF-8 decode failed", encoding="utf-8", data=b'\xff\xfe')
        assert isinstance(error, OnAirScreenError)
        assert error.encoding == "utf-8"
        assert error.data == b'\xff\xfe'
        assert "utf-8" in str(error)


class TestWidgetErrors:
    """Test widget-related exceptions"""
    
    def test_widget_access_error(self):
        """Test widget access error"""
        error = WidgetAccessError("Widget not accessible", widget_name="labelCurrentSong", attribute="text")
        assert isinstance(error, WidgetError)
        assert error.widget_name == "labelCurrentSong"
        assert error.attribute == "text"
        assert "labelCurrentSong" in str(error)
        assert "text" in str(error)


class TestLogException:
    """Test log_exception helper function"""
    
    def test_log_exception_with_exc_info(self):
        """Test logging exception with exc_info"""
        logger = Mock(spec=logging.Logger)
        error = OnAirScreenError("Test error")
        
        log_exception(logger, error, use_exc_info=True)
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Test error" in call_args[0][0]
        assert call_args[1].get('exc_info') is True
    
    def test_log_exception_without_exc_info(self):
        """Test logging exception without exc_info"""
        logger = Mock(spec=logging.Logger)
        error = TextValidationError("Text too long", field_name="NOW")
        
        log_exception(logger, error, use_exc_info=False)
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Text too long" in call_args[0][0]
        # exc_info should not be in kwargs when False (or should be False)
        assert call_args[1].get('exc_info', False) is False
    
    def test_log_exception_auto_disable_exc_info_for_validation(self):
        """Test that validation errors automatically disable exc_info"""
        logger = Mock(spec=logging.Logger)
        error = CommandValidationError("Invalid value", command="LED1", value="INVALID")
        
        log_exception(logger, error, use_exc_info=True)  # Will be overridden to False
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        # exc_info should not be in kwargs when False (or should be False)
        assert call_args[1].get('exc_info', False) is False
    
    def test_log_exception_with_context(self):
        """Test logging exception with additional context"""
        logger = Mock(spec=logging.Logger)
        error = OnAirScreenError("Test error")
        context = {"source": "network", "port": 8080}
        
        log_exception(logger, error, context=context)
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "source=network" in call_args[0][0]
        assert "port=8080" in call_args[0][0]

