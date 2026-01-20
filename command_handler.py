#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# command_handler.py
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

"""
Command Handler for OnAirScreen

This module handles parsing and execution of commands received via UDP/HTTP.
"""

import logging
import re
from typing import Callable, Optional, TYPE_CHECKING

from exceptions import (
    CommandParseError, CommandValidationError, UnknownCommandError,
    InvalidCommandFormatError, EncodingError, TextValidationError,
    log_exception
)

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)

# Maximum length for text fields (NOW, NEXT, WARN)
MAX_TEXT_LENGTH = 500

# Maximum length for configuration values
MAX_CONFIG_LENGTH = 1000

# Control characters that should be removed from text input
CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')

# Dangerous characters/sequences that should be sanitized
DANGEROUS_PATTERNS = [
    re.compile(r'<script', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers like onclick=
]


def validate_text_input(text: str, max_length: int = MAX_TEXT_LENGTH, field_name: str = "text") -> str:
    """
    Validate and sanitize text input for NOW, NEXT, WARN commands
    
    Args:
        text: Input text to validate
        max_length: Maximum allowed length (default: MAX_TEXT_LENGTH)
        field_name: Name of field for logging purposes
        
    Returns:
        Sanitized text string
        
    Note:
        - Removes control characters
        - Truncates to max_length if necessary
        - Logs warnings for invalid input
    """
    if not isinstance(text, str):
        logger.warning(f"Invalid input type for {field_name}: {type(text)}, converting to string")
        text = str(text)
    
    # Remove control characters
    sanitized = CONTROL_CHAR_PATTERN.sub('', text)
    
    if sanitized != text:
        logger.warning(f"Control characters removed from {field_name} input")
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(sanitized):
            logger.warning(f"Potentially dangerous pattern detected in {field_name} input, removing")
            sanitized = pattern.sub('', sanitized)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        logger.warning(f"{field_name} input truncated from {len(sanitized)} to {max_length} characters")
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_command_value(value: str, command: str) -> str:
    """
    Validate command value based on command type
    
    Args:
        value: Command value to validate
        command: Command name (NOW, NEXT, WARN, etc.)
        
    Returns:
        Validated value string
    """
    if not isinstance(value, str):
        logger.warning(f"Invalid value type for command {command}: {type(value)}, converting to string")
        value = str(value)
    
    # Text commands need special validation
    if command in ("NOW", "NEXT", "WARN"):
        return validate_text_input(value, MAX_TEXT_LENGTH, command)
    
    # Configuration values
    if command == "CONF":
        # CONF values can be longer but still need basic sanitization
        sanitized = CONTROL_CHAR_PATTERN.sub('', value)
        if len(sanitized) > MAX_CONFIG_LENGTH:
            logger.warning(f"CONF value truncated from {len(sanitized)} to {MAX_CONFIG_LENGTH} characters")
            sanitized = sanitized[:MAX_CONFIG_LENGTH]
        return sanitized
    
    # For other commands, just remove control characters
    sanitized = CONTROL_CHAR_PATTERN.sub('', value)
    if sanitized != value:
        logger.warning(f"Control characters removed from {command} command value")
    
    return sanitized


def validate_led_value(value: str) -> bool:
    """
    Validate LED command value
    
    Args:
        value: LED command value (should be "ON", "OFF", or "TOGGLE")
        
    Returns:
        True if value is valid, False otherwise
    """
    return value.upper() in ("ON", "OFF", "TOGGLE")


def validate_air_value(value: str, air_num: int) -> bool:
    """
    Validate AIR command value
    
    Args:
        value: AIR command value
        air_num: AIR timer number (1-4)
        
    Returns:
        True if value is valid, False otherwise
    """
    if air_num in (1, 2):
        # AIR1 and AIR2 support ON, OFF, TOGGLE
        return value.upper() in ("ON", "OFF", "TOGGLE")
    elif air_num == 3:
        # AIR3 supports ON, OFF, RESET, TOGGLE
        return value.upper() in ("ON", "OFF", "RESET", "TOGGLE")
    elif air_num == 4:
        # AIR4 supports ON, OFF, RESET, TOGGLE
        return value.upper() in ("ON", "OFF", "RESET", "TOGGLE")
    return False


def validate_air3time_value(value: str) -> bool:
    """
    Validate AIR3TIME command value (must be a valid integer)
    
    Args:
        value: Timer duration as string
        
    Returns:
        True if value is valid integer, False otherwise
    """
    try:
        int_value = int(value)
        # Reasonable range: 0 to 24 hours (86400 seconds)
        return 0 <= int_value <= 86400
    except (ValueError, OverflowError):
        return False


def validate_cmd_value(value: str) -> bool:
    """
    Validate CMD command value
    
    Args:
        value: CMD command value (should be "REBOOT", "SHUTDOWN", or "QUIT")
        
    Returns:
        True if value is valid, False otherwise
    """
    return value.upper() in ("REBOOT", "SHUTDOWN", "QUIT")


class CommandHandler:
    """
    Handles parsing and execution of OnAirScreen commands
    
    This class processes commands in the format "COMMAND:VALUE" and dispatches
    them to appropriate handler methods.
    """
    
    def __init__(self, main_screen: "MainScreen") -> None:
        """
        Initialize the command handler
        
        Args:
            main_screen: Reference to MainScreen instance for executing commands
        """
        self.main_screen = main_screen
    
    def parse_cmd(self, data: bytes) -> bool:
        """
        Parse and execute a command from UDP/HTTP input
        
        Args:
            data: Command string in format "COMMAND:VALUE"
            
        Returns:
            True if command was parsed successfully, False otherwise
        """
        try:
            (command, value) = data.decode('utf_8').split(':', 1)
        except ValueError:
            error = InvalidCommandFormatError(
                "Invalid command format: missing colon separator",
                command_data=data.decode('utf-8', errors='replace')
            )
            log_exception(logger, error, use_exc_info=False)
            return False
        except UnicodeDecodeError as e:
            error = EncodingError(
                f"Invalid UTF-8 encoding in command: {e}",
                encoding="utf-8",
                data=data
            )
            log_exception(logger, error, use_exc_info=False)
            return False

        command = str(command).strip()
        value = str(value).strip()
        
        # Validate and sanitize command value
        try:
            value = validate_command_value(value, command)
        except Exception as e:
            from exceptions import OnAirScreenError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e, use_exc_info=False)
            else:
                error = CommandValidationError(
                    f"Error validating command value for {command}: {e}",
                    command=command,
                    value=value
                )
                log_exception(logger, error, use_exc_info=False)
            return False
        
        # Use command dispatch map for simple commands
        handler = self._get_command_handler(command)
        if handler:
            handler(value)
            return True
        
        # Handle complex commands
        if command == "CONF":
            return self._handle_conf_command(value)
        
        # Unknown command
        error = UnknownCommandError(command)
        log_exception(logger, error, use_exc_info=False)
        return False
    
    def _get_command_handler(self, command: str) -> Optional[Callable[[str], None]]:
        """
        Get command handler function for a given command
        
        Args:
            command: Command name
            
        Returns:
            Handler function or None if command not found
        """
        command_handlers = {
            "NOW": lambda v: self.main_screen.set_current_song_text(v),
            "NEXT": lambda v: self.main_screen.set_news_text(v),
            "LED1": lambda v: self._handle_led_command(1, v),
            "LED2": lambda v: self._handle_led_command(2, v),
            "LED3": lambda v: self._handle_led_command(3, v),
            "LED4": lambda v: self._handle_led_command(4, v),
            "WARN": lambda v: self._handle_warn_command(v),
            "AIR1": lambda v: self._handle_air_simple_command(1, v),
            "AIR2": lambda v: self._handle_air_simple_command(2, v),
            "AIR3": lambda v: self._handle_air3_command(v),
            "AIR3TIME": lambda v: self._handle_air3time_command(v),
            "AIR4": lambda v: self._handle_air4_command(v),
            "CMD": lambda v: self._handle_cmd_command(v),
        }
        return command_handlers.get(command)
    
    def _handle_led_command(self, led_num: int, value: str) -> None:
        """
        Handle LED command (LED1-4)
        
        Args:
            led_num: LED number (1-4)
            value: Command value ("ON", "OFF", or "TOGGLE")
        """
        if not validate_led_value(value):
            logger.warning(f"Invalid LED{led_num} command value: '{value}', expected 'ON', 'OFF', or 'TOGGLE'")
            return
        
        value_upper = value.upper()
        if value_upper == "TOGGLE":
            getattr(self.main_screen, f"toggle_led{led_num}")()
        else:
            self.main_screen.led_logic(led_num, value_upper != "OFF")
    
    def _handle_warn_command(self, value: str) -> None:
        """
        Handle WARN command
        
        Supports two formats:
        - WARN:Text (backward compatible, uses priority 0)
        - WARN:Prio:Text (explicit priority, where Prio is 1 or 2)
        
        Args:
            value: Warning text or "Prio:Text" format (already validated and sanitized)
                 Empty string clears warning at priority 0
        """
        if not value:
            # Clear warning at priority 0 (backward compatible)
            self.main_screen.remove_warning(0)
            return
        
        # Check if format is "Prio:Text"
        parts = value.split(':', 1)
        if len(parts) == 2 and parts[0].isdigit():
            try:
                priority = int(parts[0])
                if priority == 0:
                    # Priority 0 is only for backward compatibility (WARN:Text)
                    # If explicitly specified (WARN:0:Text), treat as regular text without priority
                    logger.warning("Priority 0 cannot be explicitly set. Use WARN:Text for priority 0. Treating as regular text.")
                    # Validate and sanitize the text part
                    text = validate_text_input(parts[1] if len(parts) > 1 else value, MAX_TEXT_LENGTH, "WARN")
                    self.main_screen.add_warning(text, 0)
                elif 1 <= priority <= 2:
                    text = parts[1] if len(parts) > 1 else ""
                    if text:
                        # Validate and sanitize the text part
                        text = validate_text_input(text, MAX_TEXT_LENGTH, f"WARN (priority {priority})")
                        self.main_screen.add_warning(text, priority)
                    else:
                        self.main_screen.remove_warning(priority)
                else:
                    logger.warning(f"Invalid WARN priority: {priority}, must be 1-2. Priority 0 is only for backward compatibility. Using default priority 0.")
                    # Validate and sanitize the full value as text
                    text = validate_text_input(value, MAX_TEXT_LENGTH, "WARN")
                    self.main_screen.add_warning(text, 0)
            except ValueError:
                # Not a valid priority format, treat as regular text
                text = validate_text_input(value, MAX_TEXT_LENGTH, "WARN")
                self.main_screen.add_warning(text, 0)
        else:
            # Backward compatible: just text, use priority 0
            # Value is already validated and sanitized by parse_cmd
            self.main_screen.add_warning(value, 0)
    
    def _handle_air_simple_command(self, air_num: int, value: str) -> None:
        """
        Handle simple AIR command (AIR1, AIR2)
        
        Args:
            air_num: AIR timer number (1 or 2)
            value: Command value ("OFF" to stop, "ON" to start, "TOGGLE" to toggle)
        """
        if not validate_air_value(value, air_num):
            logger.warning(f"Invalid AIR{air_num} command value: '{value}', expected 'ON', 'OFF', or 'TOGGLE'")
            return
        
        value_upper = value.upper()
        if value_upper == "TOGGLE":
            getattr(self.main_screen, f"toggle_air{air_num}")()
        elif value_upper == "OFF":
            getattr(self.main_screen, f"set_air{air_num}")(False)
        else:
            getattr(self.main_screen, f"set_air{air_num}")(True)
    
    def _handle_air3_command(self, value: str) -> None:
        """
        Handle AIR3 command with multiple actions
        
        Args:
            value: Command action ("OFF", "ON", "RESET", or "TOGGLE")
        """
        if not validate_air_value(value, 3):
            logger.warning(f"Invalid AIR3 command value: '{value}', expected 'ON', 'OFF', 'RESET', or 'TOGGLE'")
            return
        
        value_upper = value.upper()
        if value_upper == "OFF":
            self.main_screen.stop_air3()
        elif value_upper == "ON":
            self.main_screen.start_air3()
        elif value_upper == "RESET":
            self.main_screen.radio_timer_reset()
        elif value_upper == "TOGGLE":
            self.main_screen.radio_timer_start_stop()
    
    def _handle_air3time_command(self, value: str) -> None:
        """
        Handle AIR3TIME command to set radio timer duration
        
        Args:
            value: Timer duration in seconds as string
            
        Note:
            Validates that value is a valid integer in range 0-86400 (24 hours)
        """
        if not validate_air3time_value(value):
            logger.error(f"Invalid AIR3TIME value: '{value}', must be integer between 0 and 86400")
            return
        
        try:
            self.main_screen.radio_timer_set(int(value))
        except (ValueError, OverflowError) as e:
            error = CommandValidationError(
                f"ERROR: invalid AIR3TIME value: {e}",
                command="AIR3TIME",
                value=value
            )
            log_exception(logger, error, use_exc_info=False)
    
    def _handle_air4_command(self, value: str) -> None:
        """
        Handle AIR4 command
        
        Args:
            value: Command action ("OFF", "ON", "RESET", or "TOGGLE")
        """
        if not validate_air_value(value, 4):
            logger.warning(f"Invalid AIR4 command value: '{value}', expected 'ON', 'OFF', 'RESET', or 'TOGGLE'")
            return
        
        value_upper = value.upper()
        if value_upper == "OFF":
            self.main_screen.set_air4(False)
        elif value_upper == "ON":
            self.main_screen.set_air4(True)
        elif value_upper == "RESET":
            self.main_screen.stream_timer_reset()
        elif value_upper == "TOGGLE":
            self.main_screen.start_stop_air4()
    
    def _handle_cmd_command(self, value: str) -> None:
        """
        Handle CMD command for system operations
        
        Args:
            value: Command action ("REBOOT", "SHUTDOWN", or "QUIT")
        """
        if not validate_cmd_value(value):
            logger.warning(f"Invalid CMD command value: '{value}', expected 'REBOOT', 'SHUTDOWN', or 'QUIT'")
            return
        
        value_upper = value.upper()
        if value_upper == "REBOOT":
            self.main_screen.reboot_host()
        elif value_upper == "SHUTDOWN":
            self.main_screen.shutdown_host()
        elif value_upper == "QUIT":
            self.main_screen.quit_oas()
    
    def _handle_color_setting(self, color_str: str, setter_func: Callable[[object], None], setting_name: str) -> None:
        """
        Handle color setting with validation
        
        Args:
            color_str: Color string to validate and set
            setter_func: Function to call with validated QColor object
            setting_name: Name of setting for logging purposes
            
        Note:
            Uses white (#FFFFFF) as fallback if color validation fails
        """
        try:
            # Normalize 0x prefix to # (for backward compatibility)
            normalized = color_str.replace("0x", "#").replace("0X", "#")
            
            # Get color with validation (getColorFromName now validates)
            color = self.main_screen.settings.getColorFromName(normalized)
            
            # Check if color is valid
            if not color.isValid():
                logger.warning(f"Invalid color value '{color_str}' for {setting_name}, using default white")
                # Use white as fallback
                color = self.main_screen.settings.getColorFromName("#FFFFFF")
            
            # Set the color
            setter_func(color)
            logger.debug(f"Set {setting_name} to color '{normalized}'")
            
        except Exception as e:
            from exceptions import OnAirScreenError, ColorValidationError
            if isinstance(e, OnAirScreenError):
                log_exception(logger, e)
            else:
                error = ColorValidationError(f"Error setting color for {setting_name}: {e}", color_value=color_str)
                log_exception(logger, error)
    
    def _handle_conf_command(self, value: str) -> bool:
        """
        Handle CONF command (configuration updates)
        
        Args:
            value: Configuration string in format "GROUP:PARAM=VALUE" (already validated and sanitized)
            
        Returns:
            True if command was handled successfully, False otherwise
        """
        try:
            (group, paramvalue) = value.split(':', 1)
            (param, content) = paramvalue.split('=', 1)
        except ValueError:
            error = InvalidCommandFormatError(
                f"Invalid CONF command format: '{value}', expected 'GROUP:PARAM=VALUE'",
                command_data=value
            )
            log_exception(logger, error, use_exc_info=False)
            return False

        # Validate group and param names (basic sanitization)
        group = group.strip()
        param = param.strip()
        content = content.strip()
        
        if not group or not param:
            logger.warning(f"Invalid CONF command: empty group or param in '{value}'")
            return False

        group_handlers = {
            "General": self._handle_conf_general,
            "LED1": lambda p, c: self._handle_conf_led(1, p, c),
            "LED2": lambda p, c: self._handle_conf_led(2, p, c),
            "LED3": lambda p, c: self._handle_conf_led(3, p, c),
            "LED4": lambda p, c: self._handle_conf_led(4, p, c),
            "Timers": self._handle_conf_timers,
            "Clock": self._handle_conf_clock,
            "Network": self._handle_conf_network,
            "CONF": self._handle_conf_apply,
        }
        
        handler = group_handlers.get(group)
        if handler:
            handler(param, content)
            return True
        
        logger.warning(f"Unknown CONF group: {group}")
        return False
    
    def _handle_conf_general(self, param: str, content: str) -> None:
        """
        Handle CONF General group configuration
        
        Args:
            param: Parameter name (stationname, slogan, stationcolor, slogancolor, replacenow, replacenowtext)
            content: Parameter value
        """
        handlers = {
            "stationname": lambda c: self.main_screen.settings.StationName.setText(
                validate_text_input(c, MAX_TEXT_LENGTH, "stationname")),
            "slogan": lambda c: self.main_screen.settings.Slogan.setText(
                validate_text_input(c, MAX_TEXT_LENGTH, "slogan")),
            "stationcolor": lambda c: self._handle_color_setting(
                c, lambda color: self.main_screen.settings.setStationNameColor(color), "stationcolor"),
            "slogancolor": lambda c: self._handle_color_setting(
                c, lambda color: self.main_screen.settings.setSloganColor(color), "slogancolor"),
            "replacenow": lambda c: self.main_screen.settings.replaceNOW.setChecked(c == "True"),
            "replacenowtext": lambda c: self.main_screen.settings.replaceNOWText.setText(
                validate_text_input(c, MAX_TEXT_LENGTH, "replacenowtext")),
        }
        handler = handlers.get(param)
        if handler:
            handler(content)
    
    def _handle_conf_led(self, led_num: int, param: str, content: str) -> None:
        """
        Handle CONF LED group (LED1-4) configuration
        
        Args:
            led_num: LED number (1-4)
            param: Parameter name (used, text, activebgcolor, activetextcolor, autoflash, timedflash)
            content: Parameter value
        """
        handlers = {
            "used": lambda c: getattr(self.main_screen.settings, f"LED{led_num}").setChecked(c == "True"),
            "text": lambda c: getattr(self.main_screen.settings, f"LED{led_num}Text").setText(
                validate_text_input(c, MAX_TEXT_LENGTH, f"LED{led_num} text")),
            "activebgcolor": lambda c: self._handle_color_setting(
                c, lambda color: getattr(self.main_screen.settings, f"setLED{led_num}BGColor")(color),
                f"LED{led_num}.activebgcolor"),
            "activetextcolor": lambda c: self._handle_color_setting(
                c, lambda color: getattr(self.main_screen.settings, f"setLED{led_num}FGColor")(color),
                f"LED{led_num}.activetextcolor"),
            "autoflash": lambda c: getattr(self.main_screen.settings, f"LED{led_num}Autoflash").setChecked(c == "True"),
            "timedflash": lambda c: getattr(self.main_screen.settings, f"LED{led_num}Timedflash").setChecked(c == "True"),
        }
        handler = handlers.get(param)
        if handler:
            handler(content)
    
    def _handle_conf_timers(self, param: str, content: str) -> None:
        """
        Handle CONF Timers group configuration
        
        Args:
            param: Parameter name (TimerAIR[1-4]Enabled, TimerAIR[1-4]Text, 
                   AIR[1-4]activebgcolor, AIR[1-4]activetextcolor, AIR[1-4]iconpath, TimerAIRMinWidth)
            content: Parameter value
        """
        # Handle AIR enabled flags
        for air_num in range(1, 5):
            if param == f"TimerAIR{air_num}Enabled":
                getattr(self.main_screen.settings, f"enableAIR{air_num}").setChecked(content == "True")
                return
        
        # Handle AIR text
        for air_num in range(1, 5):
            if param == f"TimerAIR{air_num}Text":
                sanitized = validate_text_input(content, MAX_TEXT_LENGTH, f"AIR{air_num} text")
                getattr(self.main_screen.settings, f"AIR{air_num}Text").setText(sanitized)
                return
        
        # Handle AIR colors
        for air_num in range(1, 5):
            if param == f"AIR{air_num}activebgcolor":
                self._handle_color_setting(
                    content,
                    lambda color: getattr(self.main_screen.settings, f"setAIR{air_num}BGColor")(color),
                    f"AIR{air_num}.activebgcolor")
                return
            if param == f"AIR{air_num}activetextcolor":
                self._handle_color_setting(
                    content,
                    lambda color: getattr(self.main_screen.settings, f"setAIR{air_num}FGColor")(color),
                    f"AIR{air_num}.activetextcolor")
                return
        
        # Handle AIR icon paths
        for air_num in range(1, 5):
            if param == f"AIR{air_num}iconpath":
                getattr(self.main_screen.settings, f"setAIR{air_num}IconPath")(content)
                return
        
        # Handle TimerAIRMinWidth
        if param == "TimerAIRMinWidth":
            self.main_screen.settings.AIRMinWidth.setValue(int(content))
    
    def _handle_conf_clock(self, param: str, content: str) -> None:
        """
        Handle CONF Clock group configuration
        
        Args:
            param: Parameter name (digital, showseconds, secondsinoneline, staticcolon,
                   digitalhourcolor, digitalsecondcolor, digitaldigitcolor, logopath, logoupper)
            content: Parameter value
        """
        if param == "digital":
            if content == "True":
                self.main_screen.settings.clockDigital.setChecked(True)
                self.main_screen.settings.clockAnalog.setChecked(False)
            elif content == "False":
                self.main_screen.settings.clockAnalog.setChecked(False)
                self.main_screen.settings.clockDigital.setChecked(True)
        elif param == "showseconds":
            if content == "True":
                self.main_screen.settings.showSeconds.setChecked(True)
                self.main_screen.settings.seconds_in_one_line.setChecked(False)
                self.main_screen.settings.seconds_separate.setChecked(True)
            elif content == "False":
                self.main_screen.settings.showSeconds.setChecked(False)
                self.main_screen.settings.seconds_in_one_line.setChecked(False)
                self.main_screen.settings.seconds_separate.setChecked(True)
        elif param == "secondsinoneline":
            if content == "True":
                self.main_screen.settings.showSeconds.setChecked(True)
                self.main_screen.settings.seconds_in_one_line.setChecked(True)
                self.main_screen.settings.seconds_separate.setChecked(False)
            elif content == "False":
                self.main_screen.settings.showSeconds.setChecked(False)
                self.main_screen.settings.seconds_in_one_line.setChecked(False)
                self.main_screen.settings.seconds_separate.setChecked(True)
        elif param == "staticcolon":
            self.main_screen.settings.staticColon.setChecked(content == "True")
        elif param == "digitalhourcolor":
            self._handle_color_setting(
                content,
                lambda color: self.main_screen.settings.setDigitalHourColor(color),
                "digitalhourcolor")
        elif param == "digitalsecondcolor":
            self._handle_color_setting(
                content,
                lambda color: self.main_screen.settings.setDigitalSecondColor(color),
                "digitalsecondcolor")
        elif param == "digitaldigitcolor":
            self._handle_color_setting(
                content,
                lambda color: self.main_screen.settings.setDigitalDigitColor(color),
                "digitaldigitcolor")
        elif param == "logopath":
            self.main_screen.settings.setLogoPath(content)
        elif param == "logoupper":
            self.main_screen.settings.setLogoUpper(content == "True")
    
    def _handle_conf_network(self, param: str, content: str) -> None:
        """
        Handle CONF Network group configuration
        
        Args:
            param: Parameter name (udpport, httpport, multicast_address)
            content: Parameter value
        """
        if param == "udpport":
            self.main_screen.settings.udpport.setText(content)
    
    def _handle_conf_apply(self, param: str, content: str) -> None:
        """
        Handle CONF APPLY command to apply configuration changes
        
        Args:
            param: Must be "APPLY"
            content: Must be "TRUE" to trigger application of settings
        """
        if param == "APPLY" and content == "TRUE":
            self.main_screen.settings.applySettings()

