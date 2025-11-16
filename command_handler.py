#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2025 Sascha Ludwig, astrastudio.de
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
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from start import MainScreen

logger = logging.getLogger(__name__)


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
            return False

        command = str(command)
        value = str(value)
        
        # Use command dispatch map for simple commands
        handler = self._get_command_handler(command)
        if handler:
            handler(value)
            return True
        
        # Handle complex commands
        if command == "CONF":
            return self._handle_conf_command(value)
        
        # Unknown command
        logger.warning(f"Unknown command: {command}")
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
            value: Command value ("ON" or "OFF")
        """
        self.main_screen.led_logic(led_num, value != "OFF")
    
    def _handle_warn_command(self, value: str) -> None:
        """
        Handle WARN command
        
        Args:
            value: Warning text (empty string to clear warning)
        """
        if value:
            self.main_screen.add_warning(value, 1)
        else:
            self.main_screen.remove_warning(1)
    
    def _handle_air_simple_command(self, air_num: int, value: str) -> None:
        """
        Handle simple AIR command (AIR1, AIR2)
        
        Args:
            air_num: AIR timer number (1 or 2)
            value: Command value ("OFF" to stop, any other value to start)
        """
        if value == "OFF":
            getattr(self.main_screen, f"set_air{air_num}")(False)
        else:
            getattr(self.main_screen, f"set_air{air_num}")(True)
    
    def _handle_air3_command(self, value: str) -> None:
        """
        Handle AIR3 command with multiple actions
        
        Args:
            value: Command action ("OFF", "ON", "RESET", or "TOGGLE")
        """
        if value == "OFF":
            self.main_screen.stop_air3()
        elif value == "ON":
            self.main_screen.start_air3()
        elif value == "RESET":
            self.main_screen.radio_timer_reset()
        elif value == "TOGGLE":
            self.main_screen.radio_timer_start_stop()
    
    def _handle_air3time_command(self, value: str) -> None:
        """
        Handle AIR3TIME command to set radio timer duration
        
        Args:
            value: Timer duration in seconds as string
            
        Raises:
            ValueError: If value cannot be converted to integer (logged, not raised)
        """
        try:
            self.main_screen.radio_timer_set(int(value))
        except ValueError as e:
            logger.error(f"ERROR: invalid value: {e}")
    
    def _handle_air4_command(self, value: str) -> None:
        """
        Handle AIR4 command
        
        Args:
            value: Command action ("OFF", "ON", or "RESET")
        """
        if value == "OFF":
            self.main_screen.set_air4(False)
        elif value == "ON":
            self.main_screen.set_air4(True)
        elif value == "RESET":
            self.main_screen.stream_timer_reset()
    
    def _handle_cmd_command(self, value: str) -> None:
        """
        Handle CMD command for system operations
        
        Args:
            value: Command action ("REBOOT", "SHUTDOWN", or "QUIT")
        """
        if value == "REBOOT":
            self.main_screen.reboot_host()
        elif value == "SHUTDOWN":
            self.main_screen.shutdown_host()
        elif value == "QUIT":
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
            logger.error(f"Error setting color for {setting_name}: {e}", exc_info=True)
    
    def _handle_conf_command(self, value: str) -> bool:
        """
        Handle CONF command (configuration updates)
        
        Args:
            value: Configuration string in format "GROUP:PARAM=VALUE"
            
        Returns:
            True if command was handled successfully, False otherwise
        """
        try:
            (group, paramvalue) = value.split(':', 1)
            (param, content) = paramvalue.split('=', 1)
        except ValueError:
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
            "stationname": lambda c: self.main_screen.settings.StationName.setText(c),
            "slogan": lambda c: self.main_screen.settings.Slogan.setText(c),
            "stationcolor": lambda c: self._handle_color_setting(
                c, lambda color: self.main_screen.settings.setStationNameColor(color), "stationcolor"),
            "slogancolor": lambda c: self._handle_color_setting(
                c, lambda color: self.main_screen.settings.setSloganColor(color), "slogancolor"),
            "replacenow": lambda c: self.main_screen.settings.replaceNOW.setChecked(c == "True"),
            "replacenowtext": lambda c: self.main_screen.settings.replaceNOWText.setText(c),
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
            "text": lambda c: getattr(self.main_screen.settings, f"LED{led_num}Text").setText(c),
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
                getattr(self.main_screen.settings, f"AIR{air_num}Text").setText(content)
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

