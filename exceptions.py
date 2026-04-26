#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# exceptions.py
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
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
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

"""
Custom Exceptions for OnAirScreen

This module defines a hierarchy of custom exceptions for consistent
error handling throughout the OnAirScreen application.
"""

import logging
from typing import Optional, Any


class OnAirScreenError(Exception):
    """
    Base exception for all OnAirScreen errors
    
    All custom exceptions in OnAirScreen should inherit from this class.
    """
    
    def __init__(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        """
        Initialize the exception
        
        Args:
            message: Error message
            context: Optional context dictionary with additional information
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return formatted error message with context"""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


# Network Errors

class NetworkError(OnAirScreenError):
    """Base exception for all network-related errors"""
    pass


class UdpError(NetworkError):
    """UDP-specific network errors"""
    pass


class HttpError(NetworkError):
    """HTTP-specific network errors with status code"""
    
    def __init__(self, message: str, status_code: int = 500, context: Optional[dict[str, Any]] = None) -> None:
        """
        Initialize HTTP error
        
        Args:
            message: Error message
            status_code: HTTP status code (default: 500)
            context: Optional context dictionary
        """
        super().__init__(message, context)
        self.status_code = status_code
    
    def __str__(self) -> str:
        """Return formatted error message with HTTP status code"""
        base_msg = super().__str__()
        return f"HTTP {self.status_code}: {base_msg}"


class WebSocketError(NetworkError):
    """WebSocket-specific network errors"""
    pass


class MqttError(NetworkError):
    """MQTT-specific network errors"""
    pass


class PortInUseError(NetworkError):
    """Port is already in use (errno 98)"""
    
    def __init__(self, port: int, protocol: str = "TCP") -> None:
        """
        Initialize port in use error
        
        Args:
            port: Port number that is in use
            protocol: Protocol name (TCP, UDP, etc.)
        """
        message = f"{protocol} port {port} is already in use"
        super().__init__(message, {"port": port, "protocol": protocol})
        self.port = port
        self.protocol = protocol


class PermissionDeniedError(NetworkError):
    """Permission denied for port binding (errno 13)"""
    
    def __init__(self, port: int, protocol: str = "TCP") -> None:
        """
        Initialize permission denied error
        
        Args:
            port: Port number that requires permission
            protocol: Protocol name (TCP, UDP, etc.)
        """
        message = f"Permission denied binding to {protocol} port {port}"
        super().__init__(message, {"port": port, "protocol": protocol})
        self.port = port
        self.protocol = protocol


# Command Errors

class CommandError(OnAirScreenError):
    """Base exception for all command-related errors"""
    pass


class CommandParseError(CommandError):
    """Error parsing a command"""
    
    def __init__(self, message: str, command_data: Optional[str] = None) -> None:
        """
        Initialize command parse error
        
        Args:
            message: Error message
            command_data: The command data that failed to parse
        """
        context = {"command_data": command_data} if command_data else {}
        super().__init__(message, context)
        self.command_data = command_data


class CommandValidationError(CommandError):
    """Error validating a command value"""
    
    def __init__(self, message: str, command: Optional[str] = None, value: Optional[str] = None) -> None:
        """
        Initialize command validation error
        
        Args:
            message: Error message
            command: Command name
            value: Invalid value
        """
        context = {}
        if command:
            context["command"] = command
        if value:
            context["value"] = value
        super().__init__(message, context)
        self.command = command
        self.value = value


class UnknownCommandError(CommandError):
    """Unknown command received"""
    
    def __init__(self, command: str) -> None:
        """
        Initialize unknown command error
        
        Args:
            command: Unknown command name
        """
        message = f"Unknown command: {command}"
        super().__init__(message, {"command": command})
        self.command = command


class InvalidCommandFormatError(CommandError):
    """Invalid command format"""
    
    def __init__(self, message: str, command_data: Optional[str] = None) -> None:
        """
        Initialize invalid command format error
        
        Args:
            message: Error message
            command_data: The command data with invalid format
        """
        context = {"command_data": command_data} if command_data else {}
        super().__init__(message, context)
        self.command_data = command_data


# Configuration Errors

class ConfigurationError(OnAirScreenError):
    """Base exception for all configuration-related errors"""
    pass


class SettingsError(ConfigurationError):
    """Error loading or saving settings"""
    pass


class InvalidConfigValueError(ConfigurationError):
    """Invalid configuration value"""
    
    def __init__(self, message: str, key: Optional[str] = None, value: Optional[Any] = None) -> None:
        """
        Initialize invalid config value error
        
        Args:
            message: Error message
            key: Configuration key
            value: Invalid value
        """
        context = {}
        if key:
            context["key"] = key
        if value is not None:
            context["value"] = value
        super().__init__(message, context)
        self.key = key
        self.value = value


# Validation Errors

class ValidationError(OnAirScreenError):
    """Base exception for all validation errors"""
    pass


class TextValidationError(ValidationError):
    """Error validating text input"""
    
    def __init__(self, message: str, field_name: Optional[str] = None, text: Optional[str] = None) -> None:
        """
        Initialize text validation error
        
        Args:
            message: Error message
            field_name: Name of the field being validated
            text: Invalid text
        """
        context = {}
        if field_name:
            context["field_name"] = field_name
        if text:
            context["text"] = text
        super().__init__(message, context)
        self.field_name = field_name
        self.text = text


class ColorValidationError(ValidationError):
    """Error validating color value"""
    
    def __init__(self, message: str, color_value: Optional[str] = None) -> None:
        """
        Initialize color validation error
        
        Args:
            message: Error message
            color_value: Invalid color value
        """
        context = {"color_value": color_value} if color_value else {}
        super().__init__(message, context)
        self.color_value = color_value


class ValueValidationError(ValidationError):
    """Error validating a value"""
    
    def __init__(self, message: str, value: Optional[Any] = None) -> None:
        """
        Initialize value validation error
        
        Args:
            message: Error message
            value: Invalid value
        """
        context = {"value": value} if value is not None else {}
        super().__init__(message, context)
        self.value = value


# API Errors

class ApiError(OnAirScreenError):
    """Base exception for all API-related errors"""
    pass


class WeatherApiError(ApiError):
    """OpenWeatherMap API error"""
    
    def __init__(self, message: str, api_response: Optional[str] = None) -> None:
        """
        Initialize weather API error
        
        Args:
            message: Error message
            api_response: API response data (if available)
        """
        context = {"api_response": api_response} if api_response else {}
        super().__init__(message, context)
        self.api_response = api_response


class JsonParseError(ApiError):
    """JSON parsing error"""
    
    def __init__(self, message: str, json_data: Optional[str] = None) -> None:
        """
        Initialize JSON parse error
        
        Args:
            message: Error message
            json_data: The JSON data that failed to parse
        """
        context = {"json_data": json_data} if json_data else {}
        super().__init__(message, context)
        self.json_data = json_data


class JsonSerializationError(ApiError):
    """JSON serialization error"""
    
    def __init__(self, message: str, data: Optional[Any] = None) -> None:
        """
        Initialize JSON serialization error
        
        Args:
            message: Error message
            data: The data that failed to serialize
        """
        context = {"data": str(data)} if data is not None else {}
        super().__init__(message, context)
        self.data = data


# Encoding Errors

class EncodingError(OnAirScreenError):
    """Encoding/decoding error (UTF-8, etc.)"""
    
    def __init__(self, message: str, encoding: str = "utf-8", data: Optional[bytes] = None) -> None:
        """
        Initialize encoding error
        
        Args:
            message: Error message
            encoding: Encoding name (default: utf-8)
            data: The data that failed to encode/decode
        """
        context = {"encoding": encoding}
        if data:
            context["data_length"] = len(data)
        super().__init__(message, context)
        self.encoding = encoding
        self.data = data


# Widget Errors

class WidgetError(OnAirScreenError):
    """Base exception for all widget-related errors"""
    pass


class WidgetAccessError(WidgetError):
    """Error accessing widget properties"""
    
    def __init__(self, message: str, widget_name: Optional[str] = None, attribute: Optional[str] = None) -> None:
        """
        Initialize widget access error
        
        Args:
            message: Error message
            widget_name: Name of the widget
            attribute: Attribute that failed to access
        """
        context = {}
        if widget_name:
            context["widget_name"] = widget_name
        if attribute:
            context["attribute"] = attribute
        super().__init__(message, context)
        self.widget_name = widget_name
        self.attribute = attribute


# Logging Helper Function

def log_exception(logger: logging.Logger, exception: Exception, context: Optional[dict[str, Any]] = None, 
                  use_exc_info: bool = True) -> None:
    """
    Log an exception consistently
    
    Args:
        logger: Logger instance to use
        exception: Exception to log
        context: Optional additional context dictionary
        use_exc_info: Whether to include exception traceback (default: True)
                     Set to False for expected validation errors
    
    This function provides consistent logging for all exceptions in OnAirScreen.
    For expected errors (like validation errors), set use_exc_info=False.
    For unexpected errors, use_exc_info=True (default).
    """
    # Build message with context
    message = str(exception)
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} (context: {context_str})"
    
    # Determine if we should use exc_info
    # Don't use exc_info for expected validation/command errors
    if isinstance(exception, (ValidationError, CommandValidationError, TextValidationError, 
                             ColorValidationError, ValueValidationError, CommandParseError,
                             InvalidCommandFormatError, UnknownCommandError)):
        use_exc_info = False
    
    # Log the exception
    if use_exc_info:
        logger.error(message, exc_info=True)
    else:
        logger.error(message)

