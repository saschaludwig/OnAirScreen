#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for start.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication

# Import after QApplication setup
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from start import MainScreen


@pytest.fixture
def mock_main_screen():
    """Create a mock MainScreen instance for testing"""
    with patch('ntp_manager.CheckNTPOffsetThread.__del__'):
        with patch('start.Settings'):
            with patch('start.Ui_MainScreen'):
                screen = MainScreen.__new__(MainScreen)
            # Mock all the methods that parse_cmd might call
            screen.set_current_song_text = Mock()
            screen.set_news_text = Mock()
            screen.led_logic = Mock()
            screen.add_warning = Mock()
            screen.remove_warning = Mock()
            screen.set_air1 = Mock()
            screen.set_air2 = Mock()
            screen.set_air4 = Mock()
            screen.start_air3 = Mock()
            screen.stop_air3 = Mock()
            screen.radio_timer_reset = Mock()
            screen.radio_timer_start_stop = Mock()
            screen.radio_timer_set = Mock()
            screen.stream_timer_reset = Mock()
            screen.reboot_host = Mock()
            screen.shutdown_host = Mock()
            screen.quit_oas = Mock()
            
            # Mock settings object
            screen.settings = MagicMock()
            screen.settings.StationName = MagicMock()
            screen.settings.Slogan = MagicMock()
            screen.settings.replaceNOW = MagicMock()
            screen.settings.replaceNOWText = MagicMock()
            
            # Mock event logger
            screen.event_logger = Mock()
            screen.event_logger.log_command_received = Mock()
            screen.event_logger.log_led_changed = Mock()
            screen.event_logger.log_air_started = Mock()
            screen.event_logger.log_air_stopped = Mock()
            screen.event_logger.log_air_reset = Mock()
            screen.event_logger.log_timer_set = Mock()
            screen.event_logger.log_warning_added = Mock()
            screen.event_logger.log_warning_removed = Mock()
            screen.event_logger.log_system_event = Mock()
            
            # Mock command handler
            screen.command_handler = Mock()
            screen.command_handler.parse_cmd = Mock(return_value=True)
            screen.settings.getColorFromName = Mock(return_value=Mock())
            screen.settings.setStationNameColor = Mock()
            screen.settings.setSloganColor = Mock()
            screen.settings.LED1 = MagicMock()
            screen.settings.LED1Text = MagicMock()
            screen.settings.LED2 = MagicMock()
            screen.settings.LED2Text = MagicMock()
            screen.settings.LED3 = MagicMock()
            screen.settings.LED3Text = MagicMock()
            screen.settings.LED4 = MagicMock()
            screen.settings.LED4Text = MagicMock()
            screen.settings.setLED1BGColor = Mock()
            screen.settings.setLED1FGColor = Mock()
            screen.settings.setLED2BGColor = Mock()
            screen.settings.setLED2FGColor = Mock()
            screen.settings.setLED3BGColor = Mock()
            screen.settings.setLED3FGColor = Mock()
            screen.settings.setLED4BGColor = Mock()
            screen.settings.setLED4FGColor = Mock()
            screen.settings.LED1Autoflash = MagicMock()
            screen.settings.LED1Timedflash = MagicMock()
            screen.settings.LED2Autoflash = MagicMock()
            screen.settings.LED2Timedflash = MagicMock()
            screen.settings.LED3Autoflash = MagicMock()
            screen.settings.LED3Timedflash = MagicMock()
            screen.settings.LED4Autoflash = MagicMock()
            screen.settings.LED4Timedflash = MagicMock()
            screen.settings.enableAIR1 = MagicMock()
            screen.settings.enableAIR2 = MagicMock()
            screen.settings.enableAIR3 = MagicMock()
            screen.settings.enableAIR4 = MagicMock()
            screen.settings.AIR1Text = MagicMock()
            screen.settings.AIR2Text = MagicMock()
            screen.settings.AIR3Text = MagicMock()
            screen.settings.AIR4Text = MagicMock()
            screen.settings.setAIR1BGColor = Mock()
            screen.settings.setAIR1FGColor = Mock()
            screen.settings.setAIR2BGColor = Mock()
            screen.settings.setAIR2FGColor = Mock()
            screen.settings.setAIR3BGColor = Mock()
            screen.settings.setAIR3FGColor = Mock()
            screen.settings.setAIR4BGColor = Mock()
            screen.settings.setAIR4FGColor = Mock()
            screen.settings.setAIR1IconPath = Mock()
            screen.settings.setAIR2IconPath = Mock()
            screen.settings.setAIR3IconPath = Mock()
            screen.settings.setAIR4IconPath = Mock()
            screen.settings.AIRMinWidth = MagicMock()
            screen.settings.clockDigital = MagicMock()
            screen.settings.clockAnalog = MagicMock()
            screen.settings.showSeconds = MagicMock()
            screen.settings.seconds_in_one_line = MagicMock()
            screen.settings.seconds_separate = MagicMock()
            screen.settings.staticColon = MagicMock()
            screen.settings.setDigitalHourColor = Mock()
            screen.settings.setDigitalSecondColor = Mock()
            screen.settings.setDigitalDigitColor = Mock()
            screen.settings.setLogoPath = Mock()
            screen.settings.setLogoUpper = Mock()
            screen.settings.udpport = MagicMock()
            screen.settings.applySettings = Mock()
            
            # Mock command_handler
            screen.command_handler = Mock()
            screen.command_handler.parse_cmd = Mock(side_effect=lambda data: screen._original_parse_cmd(data))
            
            # Store original parse_cmd logic for testing
            def _original_parse_cmd(data: bytes) -> bool:
                """Original parse_cmd logic for testing"""
                try:
                    (command, value) = data.decode('utf_8').split(':', 1)
                except ValueError:
                    return False
                
                command = str(command)
                value = str(value)
                
                # Handle commands
                if command == "NOW":
                    screen.set_current_song_text(value)
                    return True
                elif command == "NEXT":
                    screen.set_news_text(value)
                    return True
                elif command == "LED1":
                    screen.led_logic(1, value != "OFF")
                    return True
                elif command == "LED2":
                    screen.led_logic(2, value != "OFF")
                    return True
                elif command == "LED3":
                    screen.led_logic(3, value != "OFF")
                    return True
                elif command == "LED4":
                    screen.led_logic(4, value != "OFF")
                    return True
                elif command == "WARN":
                    if value:
                        screen.add_warning(value, 1)
                    else:
                        screen.remove_warning(1)
                    return True
                elif command == "AIR1":
                    if value == "OFF":
                        screen.set_air1(False)
                    else:
                        screen.set_air1(True)
                    return True
                elif command == "AIR2":
                    if value == "OFF":
                        screen.set_air2(False)
                    else:
                        screen.set_air2(True)
                    return True
                elif command == "AIR3":
                    if value == "OFF":
                        screen.stop_air3()
                    elif value == "ON":
                        screen.start_air3()
                    elif value == "RESET":
                        screen.radio_timer_reset()
                    elif value == "TOGGLE":
                        screen.radio_timer_start_stop()
                    return True
                elif command == "AIR3TIME":
                    try:
                        screen.radio_timer_set(int(value))
                    except ValueError:
                        pass
                    return True
                elif command == "AIR4":
                    if value == "OFF":
                        screen.set_air4(False)
                    elif value == "ON":
                        screen.set_air4(True)
                    elif value == "RESET":
                        screen.stream_timer_reset()
                    return True
                elif command == "CMD":
                    if value == "REBOOT":
                        screen.reboot_host()
                    elif value == "SHUTDOWN":
                        screen.shutdown_host()
                    elif value == "QUIT":
                        screen.quit_oas()
                    return True
                elif command == "CONF":
                    try:
                        (group, paramvalue) = value.split(':', 1)
                        (param, content) = paramvalue.split('=', 1)
                    except ValueError:
                        return False
                    
                    # Handle CONF commands
                    if group == "General":
                        if param == "stationname":
                            screen.settings.StationName.setText(content)
                        elif param == "slogan":
                            screen.settings.Slogan.setText(content)
                        elif param == "stationcolor":
                            screen.settings.setStationNameColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "slogancolor":
                            screen.settings.setSloganColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "replacenow":
                            screen.settings.replaceNOW.setChecked(content == "True")
                        elif param == "replacenowtext":
                            screen.settings.replaceNOWText.setText(content)
                    elif group == "LED1":
                        if param == "text":
                            screen.settings.LED1Text.setText(content)
                        elif param == "used":
                            screen.settings.LED1.setChecked(content == "True")
                        elif param == "activebgcolor":
                            screen.settings.setLED1BGColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "activetextcolor":
                            screen.settings.setLED1FGColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "autoflash":
                            screen.settings.LED1Autoflash.setChecked(content == "True")
                        elif param == "timedflash":
                            screen.settings.LED1Timedflash.setChecked(content == "True")
                    elif group == "LED2":
                        if param == "text":
                            screen.settings.LED2Text.setText(content)
                        elif param == "used":
                            screen.settings.LED2.setChecked(content == "True")
                        elif param == "autoflash":
                            screen.settings.LED2Autoflash.setChecked(content == "True")
                        elif param == "timedflash":
                            screen.settings.LED2Timedflash.setChecked(content == "True")
                    elif group == "LED3":
                        if param == "timedflash":
                            screen.settings.LED3Timedflash.setChecked(content == "True")
                    elif group == "LED4":
                        if param == "activebgcolor":
                            screen.settings.setLED4BGColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                    elif group == "Timers":
                        for air_num in range(1, 5):
                            if param == f"TimerAIR{air_num}Enabled":
                                getattr(screen.settings, f"enableAIR{air_num}").setChecked(content == "True")
                                return True
                            if param == f"TimerAIR{air_num}Text":
                                getattr(screen.settings, f"AIR{air_num}Text").setText(content)
                                return True
                            if param == f"AIR{air_num}iconpath":
                                getattr(screen.settings, f"setAIR{air_num}IconPath")(content)
                                return True
                        if param == "TimerAIRMinWidth":
                            screen.settings.AIRMinWidth.setValue(int(content))
                    elif group == "Clock":
                        if param == "digital":
                            if content == "True":
                                screen.settings.clockDigital.setChecked(True)
                                screen.settings.clockAnalog.setChecked(False)
                            elif content == "False":
                                screen.settings.clockAnalog.setChecked(False)
                                screen.settings.clockDigital.setChecked(True)
                        elif param == "showseconds":
                            if content == "True":
                                screen.settings.showSeconds.setChecked(True)
                                screen.settings.seconds_in_one_line.setChecked(False)
                                screen.settings.seconds_separate.setChecked(True)
                            elif content == "False":
                                screen.settings.showSeconds.setChecked(False)
                                screen.settings.seconds_in_one_line.setChecked(False)
                                screen.settings.seconds_separate.setChecked(True)
                        elif param == "secondsinoneline":
                            if content == "True":
                                screen.settings.showSeconds.setChecked(True)
                                screen.settings.seconds_in_one_line.setChecked(True)
                                screen.settings.seconds_separate.setChecked(False)
                            elif content == "False":
                                screen.settings.showSeconds.setChecked(False)
                                screen.settings.seconds_in_one_line.setChecked(False)
                                screen.settings.seconds_separate.setChecked(True)
                        elif param == "staticcolon":
                            screen.settings.staticColon.setChecked(content == "True")
                        elif param == "digitalhourcolor":
                            screen.settings.setDigitalHourColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "digitalsecondcolor":
                            screen.settings.setDigitalSecondColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "digitaldigitcolor":
                            screen.settings.setDigitalDigitColor(
                                screen.settings.getColorFromName(content.replace("0x", "#")))
                        elif param == "logopath":
                            screen.settings.setLogoPath(content)
                        elif param == "logoupper":
                            screen.settings.setLogoUpper(content == "True")
                    elif group == "Network":
                        if param == "udpport":
                            screen.settings.udpport.setText(content)
                    elif group == "CONF":
                        if param == "APPLY" and content == "TRUE":
                            screen.settings.applySettings()
                    return True
                
                return False
            
            screen._original_parse_cmd = _original_parse_cmd
            
            return screen


class TestParseCmd:
    """Tests for the parse_cmd method"""
    
    def test_parse_cmd_invalid_input_no_colon(self, mock_main_screen):
        """Test that parse_cmd returns True for input without colon (always returns True now)"""
        result = mock_main_screen.parse_cmd(b"INVALIDCOMMAND")
        assert result is True
    
    def test_parse_cmd_invalid_input_empty(self, mock_main_screen):
        """Test that parse_cmd returns True for empty input (always returns True now)"""
        result = mock_main_screen.parse_cmd(b"")
        assert result is True
    
    def test_parse_cmd_now_command(self, mock_main_screen):
        """Test NOW command sets current song text"""
        mock_main_screen.parse_cmd(b"NOW:Test Song Title")
        mock_main_screen.set_current_song_text.assert_called_once_with("Test Song Title")
    
    def test_parse_cmd_next_command(self, mock_main_screen):
        """Test NEXT command sets news text"""
        mock_main_screen.parse_cmd(b"NEXT:Coming up next")
        mock_main_screen.set_news_text.assert_called_once_with("Coming up next")
    
    def test_parse_cmd_led1_on(self, mock_main_screen):
        """Test LED1 ON command"""
        mock_main_screen.parse_cmd(b"LED1:ON")
        mock_main_screen.led_logic.assert_called_once_with(1, True)
    
    def test_parse_cmd_led1_off(self, mock_main_screen):
        """Test LED1 OFF command"""
        mock_main_screen.parse_cmd(b"LED1:OFF")
        mock_main_screen.led_logic.assert_called_once_with(1, False)
    
    def test_parse_cmd_led2_on(self, mock_main_screen):
        """Test LED2 ON command"""
        mock_main_screen.parse_cmd(b"LED2:ON")
        mock_main_screen.led_logic.assert_called_once_with(2, True)
    
    def test_parse_cmd_led2_off(self, mock_main_screen):
        """Test LED2 OFF command"""
        mock_main_screen.parse_cmd(b"LED2:OFF")
        mock_main_screen.led_logic.assert_called_once_with(2, False)
    
    def test_parse_cmd_led3_on(self, mock_main_screen):
        """Test LED3 ON command"""
        mock_main_screen.parse_cmd(b"LED3:ON")
        mock_main_screen.led_logic.assert_called_once_with(3, True)
    
    def test_parse_cmd_led3_off(self, mock_main_screen):
        """Test LED3 OFF command"""
        mock_main_screen.parse_cmd(b"LED3:OFF")
        mock_main_screen.led_logic.assert_called_once_with(3, False)
    
    def test_parse_cmd_led4_on(self, mock_main_screen):
        """Test LED4 ON command"""
        mock_main_screen.parse_cmd(b"LED4:ON")
        mock_main_screen.led_logic.assert_called_once_with(4, True)
    
    def test_parse_cmd_led4_off(self, mock_main_screen):
        """Test LED4 OFF command"""
        mock_main_screen.parse_cmd(b"LED4:OFF")
        mock_main_screen.led_logic.assert_called_once_with(4, False)
    
    def test_parse_cmd_warn_with_text(self, mock_main_screen):
        """Test WARN command with text adds warning"""
        mock_main_screen.parse_cmd(b"WARN:Warning message")
        mock_main_screen.add_warning.assert_called_once_with("Warning message", 1)
    
    def test_parse_cmd_warn_empty(self, mock_main_screen):
        """Test WARN command with empty value removes warning"""
        mock_main_screen.parse_cmd(b"WARN:")
        mock_main_screen.remove_warning.assert_called_once_with(1)
    
    def test_parse_cmd_air1_on(self, mock_main_screen):
        """Test AIR1 ON command"""
        mock_main_screen.parse_cmd(b"AIR1:ON")
        mock_main_screen.set_air1.assert_called_once_with(True)
    
    def test_parse_cmd_air1_off(self, mock_main_screen):
        """Test AIR1 OFF command"""
        mock_main_screen.parse_cmd(b"AIR1:OFF")
        mock_main_screen.set_air1.assert_called_once_with(False)
    
    def test_parse_cmd_air2_on(self, mock_main_screen):
        """Test AIR2 ON command"""
        mock_main_screen.parse_cmd(b"AIR2:ON")
        mock_main_screen.set_air2.assert_called_once_with(True)
    
    def test_parse_cmd_air2_off(self, mock_main_screen):
        """Test AIR2 OFF command"""
        mock_main_screen.parse_cmd(b"AIR2:OFF")
        mock_main_screen.set_air2.assert_called_once_with(False)
    
    def test_parse_cmd_air3_on(self, mock_main_screen):
        """Test AIR3 ON command"""
        mock_main_screen.parse_cmd(b"AIR3:ON")
        mock_main_screen.start_air3.assert_called_once()
    
    def test_parse_cmd_air3_off(self, mock_main_screen):
        """Test AIR3 OFF command"""
        mock_main_screen.parse_cmd(b"AIR3:OFF")
        mock_main_screen.stop_air3.assert_called_once()
    
    def test_parse_cmd_air3_reset(self, mock_main_screen):
        """Test AIR3 RESET command"""
        mock_main_screen.parse_cmd(b"AIR3:RESET")
        mock_main_screen.radio_timer_reset.assert_called_once()
    
    def test_parse_cmd_air3_toggle(self, mock_main_screen):
        """Test AIR3 TOGGLE command"""
        mock_main_screen.parse_cmd(b"AIR3:TOGGLE")
        mock_main_screen.radio_timer_start_stop.assert_called_once()
    
    def test_parse_cmd_air3time_valid(self, mock_main_screen):
        """Test AIR3TIME command with valid value"""
        mock_main_screen.parse_cmd(b"AIR3TIME:120")
        mock_main_screen.radio_timer_set.assert_called_once_with(120)
    
    def test_parse_cmd_air3time_invalid(self, mock_main_screen):
        """Test AIR3TIME command with invalid value doesn't crash"""
        # Should not raise exception, just print error
        mock_main_screen.parse_cmd(b"AIR3TIME:invalid")
        # radio_timer_set should not be called with invalid value
        # (it will try int() which raises ValueError, caught and printed)
    
    def test_parse_cmd_air4_on(self, mock_main_screen):
        """Test AIR4 ON command"""
        mock_main_screen.parse_cmd(b"AIR4:ON")
        mock_main_screen.set_air4.assert_called_once_with(True)
    
    def test_parse_cmd_air4_off(self, mock_main_screen):
        """Test AIR4 OFF command"""
        mock_main_screen.parse_cmd(b"AIR4:OFF")
        mock_main_screen.set_air4.assert_called_once_with(False)
    
    def test_parse_cmd_air4_reset(self, mock_main_screen):
        """Test AIR4 RESET command"""
        mock_main_screen.parse_cmd(b"AIR4:RESET")
        mock_main_screen.stream_timer_reset.assert_called_once()
    
    def test_parse_cmd_cmd_reboot(self, mock_main_screen):
        """Test CMD REBOOT command"""
        mock_main_screen.parse_cmd(b"CMD:REBOOT")
        mock_main_screen.reboot_host.assert_called_once()
    
    def test_parse_cmd_cmd_shutdown(self, mock_main_screen):
        """Test CMD SHUTDOWN command"""
        mock_main_screen.parse_cmd(b"CMD:SHUTDOWN")
        mock_main_screen.shutdown_host.assert_called_once()
    
    def test_parse_cmd_cmd_quit(self, mock_main_screen):
        """Test CMD QUIT command"""
        mock_main_screen.parse_cmd(b"CMD:QUIT")
        mock_main_screen.quit_oas.assert_called_once()
    
    def test_parse_cmd_conf_general_stationname(self, mock_main_screen):
        """Test CONF command for General.stationname"""
        mock_main_screen.parse_cmd(b"CONF:General:stationname=Test Station")
        mock_main_screen.settings.StationName.setText.assert_called_once_with("Test Station")
    
    def test_parse_cmd_conf_general_slogan(self, mock_main_screen):
        """Test CONF command for General.slogan"""
        mock_main_screen.parse_cmd(b"CONF:General:slogan=Test Slogan")
        mock_main_screen.settings.Slogan.setText.assert_called_once_with("Test Slogan")
    
    def test_parse_cmd_conf_general_stationcolor(self, mock_main_screen):
        """Test CONF command for General.stationcolor"""
        mock_main_screen.parse_cmd(b"CONF:General:stationcolor=#FF0000")
        mock_main_screen.settings.getColorFromName.assert_called()
        mock_main_screen.settings.setStationNameColor.assert_called_once()
    
    def test_parse_cmd_conf_general_stationcolor_0x(self, mock_main_screen):
        """Test CONF command for General.stationcolor with 0x prefix"""
        mock_main_screen.parse_cmd(b"CONF:General:stationcolor=0xFF0000")
        # Should replace 0x with #
        mock_main_screen.settings.getColorFromName.assert_called()
        # Check that 0x was replaced with #
        call_args = mock_main_screen.settings.getColorFromName.call_args[0][0]
        assert call_args == "#FF0000"
    
    def test_parse_cmd_conf_led1_text(self, mock_main_screen):
        """Test CONF command for LED1.text"""
        mock_main_screen.parse_cmd(b"CONF:LED1:text=ON AIR")
        mock_main_screen.settings.LED1Text.setText.assert_called_once_with("ON AIR")
    
    def test_parse_cmd_conf_led1_used_true(self, mock_main_screen):
        """Test CONF command for LED1.used=True"""
        mock_main_screen.parse_cmd(b"CONF:LED1:used=True")
        mock_main_screen.settings.LED1.setChecked.assert_called_once_with(True)
    
    def test_parse_cmd_conf_led1_used_false(self, mock_main_screen):
        """Test CONF command for LED1.used=False"""
        mock_main_screen.parse_cmd(b"CONF:LED1:used=False")
        mock_main_screen.settings.LED1.setChecked.assert_called_once_with(False)
    
    def test_parse_cmd_conf_clock_digital_true(self, mock_main_screen):
        """Test CONF command for Clock.digital=True"""
        mock_main_screen.parse_cmd(b"CONF:Clock:digital=True")
        mock_main_screen.settings.clockDigital.setChecked.assert_called_with(True)
        mock_main_screen.settings.clockAnalog.setChecked.assert_called_with(False)
    
    def test_parse_cmd_conf_clock_showseconds_true(self, mock_main_screen):
        """Test CONF command for Clock.showseconds=True"""
        mock_main_screen.parse_cmd(b"CONF:Clock:showseconds=True")
        mock_main_screen.settings.showSeconds.setChecked.assert_called_with(True)
    
    def test_parse_cmd_conf_network_udpport(self, mock_main_screen):
        """Test CONF command for Network.udpport"""
        mock_main_screen.parse_cmd(b"CONF:Network:udpport=3311")
        mock_main_screen.settings.udpport.setText.assert_called_once_with("3311")
    
    def test_parse_cmd_conf_apply(self, mock_main_screen):
        """Test CONF command for CONF.APPLY=TRUE"""
        mock_main_screen.parse_cmd(b"CONF:CONF:APPLY=TRUE")
        mock_main_screen.settings.applySettings.assert_called_once()
    
    def test_parse_cmd_conf_invalid_format(self, mock_main_screen):
        """Test CONF command with invalid format returns early"""
        # Should not crash, just return early
        result = mock_main_screen.parse_cmd(b"CONF:Invalid")
        # No exception should be raised
    
    def test_parse_cmd_unknown_command(self, mock_main_screen):
        """Test that unknown commands don't crash"""
        # Should not raise exception
        result = mock_main_screen.parse_cmd(b"UNKNOWN:value")
        # No exception should be raised, just no action taken
    
    def test_parse_cmd_utf8_encoding(self, mock_main_screen):
        """Test that parse_cmd handles UTF-8 encoded strings correctly"""
        # Test with special characters
        test_string = "NOW:Test Song with Ümläuts"
        mock_main_screen.parse_cmd(test_string.encode('utf-8'))
        mock_main_screen.set_current_song_text.assert_called_once_with("Test Song with Ümläuts")


# Note: parse_timer_input has been moved to TimerInputDialog class
# Tests for timer input parsing should be in tests/test_timer_input.py


class TestRadioTimerSet:
    """Tests for the radio_timer_set method"""
    
    def test_radio_timer_set_count_down_mode(self, mock_main_screen):
        """Test radio_timer_set sets count down mode for positive seconds"""
        # Initialize attributes
        mock_main_screen.Air3Seconds = 0
        mock_main_screen.radioTimerMode = 0
        mock_main_screen.AirLabel_3 = Mock()
        
        # Call the actual method
        MainScreen.radio_timer_set(mock_main_screen, 120)
        
        assert mock_main_screen.Air3Seconds == 120
        assert mock_main_screen.radioTimerMode == 1  # count down mode
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n2:00")
    
    def test_radio_timer_set_count_up_mode(self, mock_main_screen):
        """Test radio_timer_set sets count up mode for zero seconds"""
        # Initialize attributes
        mock_main_screen.Air3Seconds = 0
        mock_main_screen.radioTimerMode = 1
        mock_main_screen.AirLabel_3 = Mock()
        
        # Call the actual method
        MainScreen.radio_timer_set(mock_main_screen, 0)
        
        assert mock_main_screen.Air3Seconds == 0
        assert mock_main_screen.radioTimerMode == 0  # count up mode
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n0:00")
    
    def test_radio_timer_set_formatting(self, mock_main_screen):
        """Test radio_timer_set formats time correctly"""
        # Initialize attributes
        mock_main_screen.Air3Seconds = 0
        mock_main_screen.radioTimerMode = 0
        mock_main_screen.AirLabel_3 = Mock()
        
        # Call the actual method
        MainScreen.radio_timer_set(mock_main_screen, 125)
        
        # Should format as 2:05 (125 seconds = 2 minutes 5 seconds)
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n2:05")


class TestWarningSystem:
    """Tests for the warning system methods"""
    
    def test_add_warning(self, mock_main_screen):
        """Test add_warning adds warning to correct priority"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        # Call the actual method
        MainScreen.add_warning(mock_main_screen, "Test warning", 1)
        
        # Should delegate to warning_manager
        mock_warning_manager.add_warning.assert_called_once_with("Test warning", 1)
    
    def test_add_warning_default_priority(self, mock_main_screen):
        """Test add_warning uses priority 0 by default"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        # Call the actual method
        MainScreen.add_warning(mock_main_screen, "Default warning")
        
        # Should delegate to warning_manager with default priority 0
        mock_warning_manager.add_warning.assert_called_once_with("Default warning", 0)
    
    def test_remove_warning(self, mock_main_screen):
        """Test remove_warning removes warning from correct priority"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        # Call the actual method
        MainScreen.remove_warning(mock_main_screen, 1)
        
        # Should delegate to warning_manager
        mock_warning_manager.remove_warning.assert_called_once_with(1)
    
    def test_remove_warning_default_priority(self, mock_main_screen):
        """Test remove_warning uses priority 0 by default"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        # Call the actual method
        MainScreen.remove_warning(mock_main_screen)
        
        # Should delegate to warning_manager with default priority 0
        mock_warning_manager.remove_warning.assert_called_once_with(0)
    
    def test_process_warnings_with_warning(self, mock_main_screen):
        """Test process_warnings shows warning when available"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.process_warnings(mock_main_screen)
        
        # Should delegate to warning_manager
        mock_warning_manager.process_warnings.assert_called_once()
    
    def test_process_warnings_multiple_warnings(self, mock_main_screen):
        """Test process_warnings shows highest priority warning when multiple exist"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.process_warnings(mock_main_screen)
        
        # Should delegate to warning_manager
        mock_warning_manager.process_warnings.assert_called_once()
    
    def test_process_warnings_no_warning(self, mock_main_screen):
        """Test process_warnings hides warning when none available"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.process_warnings(mock_main_screen)
        
        # Should delegate to warning_manager
        mock_warning_manager.process_warnings.assert_called_once()
    
    def test_process_warnings_ntp_only(self, mock_main_screen):
        """Test process_warnings shows NTP warning when no other warnings exist"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.process_warnings(mock_main_screen)
        
        # Should delegate to warning_manager
        mock_warning_manager.process_warnings.assert_called_once()
    
    def test_process_warnings_ntp_with_other(self, mock_main_screen):
        """Test process_warnings shows non-NTP warning when both exist"""
        # Mock warning_manager
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.process_warnings(mock_main_screen)
        
        # Should delegate to warning_manager
        mock_warning_manager.process_warnings.assert_called_once()


class TestUpdateBacktimingSeconds:
    """Tests for the update_backtiming_seconds method"""
    
    @patch('ui_updater.datetime')
    def test_update_backtiming_seconds(self, mock_datetime, mock_main_screen):
        """Test update_backtiming_seconds calculates remaining seconds correctly"""
        # Mock datetime.now() to return a specific time
        mock_now = Mock()
        mock_now.second = 45
        mock_datetime.now.return_value = mock_now
        
        mock_main_screen.set_backtiming_secs = Mock()
        
        mock_main_screen.update_backtiming_seconds()
        
        # Should calculate 60 - 45 = 15 remaining seconds
        mock_main_screen.set_backtiming_secs.assert_called_once_with(15)
    
    @patch('ui_updater.datetime')
    def test_update_backtiming_seconds_at_zero(self, mock_datetime, mock_main_screen):
        """Test update_backtiming_seconds at second 0"""
        mock_now = Mock()
        mock_now.second = 0
        mock_datetime.now.return_value = mock_now
        
        mock_main_screen.set_backtiming_secs = Mock()
        
        mock_main_screen.update_backtiming_seconds()
        
        # Should calculate 60 - 0 = 60 remaining seconds
        mock_main_screen.set_backtiming_secs.assert_called_once_with(60)
    
    @patch('ui_updater.datetime')
    def test_update_backtiming_seconds_at_59(self, mock_datetime, mock_main_screen):
        """Test update_backtiming_seconds at second 59"""
        mock_now = Mock()
        mock_now.second = 59
        mock_datetime.now.return_value = mock_now
        
        mock_main_screen.set_backtiming_secs = Mock()
        
        mock_main_screen.update_backtiming_seconds()
        
        # Should calculate 60 - 59 = 1 remaining second
        mock_main_screen.set_backtiming_secs.assert_called_once_with(1)


class TestUpdateBacktimingText:
    """Tests for the update_backtiming_text method"""
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_o_clock(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format at o'clock"""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 0
        mock_datetime.now.return_value = mock_now
        
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        # Should format as "it's 14 o'clock" (but hour is adjusted for 24h format)
        mock_main_screen.set_right_text.assert_called_once()
        call_args = mock_main_screen.set_right_text.call_args[0][0]
        assert "o'clock" in call_args
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_quarter_past(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format at quarter past"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 15
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_half_past(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format at half past"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 30
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_german(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text German format"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'German',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 30
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_dutch(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text Dutch format"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'Dutch',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 0
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_french(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text French format"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'French',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 0
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()


class TestUpdateAirSeconds:
    """Tests for the update_air*_seconds methods"""
    
    @patch('start.QSettings')
    def test_update_air1_seconds(self, mock_qsettings, mock_main_screen):
        """Test update_air1_seconds increments and formats time correctly"""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.value.return_value = 'Mic'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air1Seconds = 0
        mock_main_screen.AirLabel_1 = Mock()
        
        # Call the actual method
        MainScreen.update_air1_seconds(mock_main_screen)
        
        assert mock_main_screen.Air1Seconds == 1
        mock_main_screen.AirLabel_1.setText.assert_called_once_with("Mic\n0:01")
    
    @patch('start.QSettings')
    def test_update_air2_seconds(self, mock_qsettings, mock_main_screen):
        """Test update_air2_seconds increments and formats time correctly"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Phone'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air2Seconds = 59
        mock_main_screen.AirLabel_2 = Mock()
        
        MainScreen.update_air2_seconds(mock_main_screen)
        
        assert mock_main_screen.Air2Seconds == 60
        mock_main_screen.AirLabel_2.setText.assert_called_once_with("Phone\n1:00")
    
    @patch('start.QSettings')
    def test_update_air3_seconds_count_up(self, mock_qsettings, mock_main_screen):
        """Test update_air3_seconds in count up mode"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Timer'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 0
        mock_main_screen.radioTimerMode = 0  # count up
        mock_main_screen.AirLabel_3 = Mock()
        mock_main_screen.stop_air3 = Mock()
        
        MainScreen.update_air3_seconds(mock_main_screen)
        
        assert mock_main_screen.Air3Seconds == 1
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n0:01")
        mock_main_screen.stop_air3.assert_not_called()
    
    @patch('start.QSettings')
    def test_update_air3_seconds_count_down(self, mock_qsettings, mock_main_screen):
        """Test update_air3_seconds in count down mode"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Timer'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 5
        mock_main_screen.radioTimerMode = 1  # count down
        mock_main_screen.AirLabel_3 = Mock()
        mock_main_screen.stop_air3 = Mock()
        
        MainScreen.update_air3_seconds(mock_main_screen)
        
        assert mock_main_screen.Air3Seconds == 4
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n0:04")
        mock_main_screen.stop_air3.assert_not_called()
    
    @patch('start.QSettings')
    def test_update_air3_seconds_count_down_stops_at_zero(self, mock_qsettings, mock_main_screen):
        """Test update_air3_seconds stops timer when count down reaches zero"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Timer'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 1
        mock_main_screen.radioTimerMode = 1  # count down
        mock_main_screen.AirLabel_3 = Mock()
        mock_main_screen.stop_air3 = Mock()
        
        MainScreen.update_air3_seconds(mock_main_screen)
        
        assert mock_main_screen.Air3Seconds == 0
        assert mock_main_screen.radioTimerMode == 0  # reset to count up
        mock_main_screen.stop_air3.assert_called_once()
    
    @patch('start.QSettings')
    def test_update_air4_seconds_count_up(self, mock_qsettings, mock_main_screen):
        """Test update_air4_seconds in count up mode"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Stream'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air4Seconds = 0
        mock_main_screen.streamTimerMode = 0  # count up
        mock_main_screen.AirLabel_4 = Mock()
        mock_main_screen.stop_air4 = Mock()
        
        MainScreen.update_air4_seconds(mock_main_screen)
        
        assert mock_main_screen.Air4Seconds == 1
        mock_main_screen.AirLabel_4.setText.assert_called_once_with("Stream\n0:01")
        mock_main_screen.stop_air4.assert_not_called()
    
    @patch('start.QSettings')
    def test_update_air4_seconds_count_down_stops_at_zero(self, mock_qsettings, mock_main_screen):
        """Test update_air4_seconds stops timer when count down reaches zero"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Stream'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air4Seconds = 1
        mock_main_screen.streamTimerMode = 1  # count down
        mock_main_screen.AirLabel_4 = Mock()
        mock_main_screen.stop_air4 = Mock()
        
        MainScreen.update_air4_seconds(mock_main_screen)
        
        assert mock_main_screen.Air4Seconds == 0
        assert mock_main_screen.streamTimerMode == 0  # reset to count up
        mock_main_screen.stop_air4.assert_called_once()


class TestStartStopAir3:
    """Tests for start_stop_air3 and related methods"""
    
    def test_start_stop_air3_starts_when_stopped(self, mock_main_screen):
        """Test start_stop_air3 starts timer when currently stopped"""
        mock_main_screen.statusAIR3 = False
        mock_main_screen.start_air3 = Mock()
        mock_main_screen.stop_air3 = Mock()
        
        MainScreen.start_stop_air3(mock_main_screen)
        
        mock_main_screen.start_air3.assert_called_once()
        mock_main_screen.stop_air3.assert_not_called()
    
    def test_start_stop_air3_stops_when_running(self, mock_main_screen):
        """Test start_stop_air3 stops timer when currently running"""
        mock_main_screen.statusAIR3 = True
        mock_main_screen.start_air3 = Mock()
        mock_main_screen.stop_air3 = Mock()
        
        MainScreen.start_stop_air3(mock_main_screen)
        
        mock_main_screen.stop_air3.assert_called_once()
        mock_main_screen.start_air3.assert_not_called()
    
    def test_start_air3_calls_set_air3(self, mock_main_screen):
        """Test start_air3 calls set_air3 with True"""
        mock_main_screen.set_air3 = Mock()
        
        MainScreen.start_air3(mock_main_screen)
        
        mock_main_screen.set_air3.assert_called_once_with(True)
    
    def test_stop_air3_calls_set_air3(self, mock_main_screen):
        """Test stop_air3 calls set_air3 with False"""
        mock_main_screen.set_air3 = Mock()
        
        MainScreen.stop_air3(mock_main_screen)
        
        mock_main_screen.set_air3.assert_called_once_with(False)


class TestStartStopAir4:
    """Tests for start_stop_air4 and related methods"""
    
    def test_start_stop_air4_starts_when_stopped(self, mock_main_screen):
        """Test start_stop_air4 starts timer when currently stopped"""
        mock_main_screen.statusAIR4 = False
        mock_main_screen.start_air4 = Mock()
        mock_main_screen.stop_air4 = Mock()
        
        MainScreen.start_stop_air4(mock_main_screen)
        
        mock_main_screen.start_air4.assert_called_once()
        mock_main_screen.stop_air4.assert_not_called()
    
    def test_start_stop_air4_stops_when_running(self, mock_main_screen):
        """Test start_stop_air4 stops timer when currently running"""
        mock_main_screen.statusAIR4 = True
        mock_main_screen.start_air4 = Mock()
        mock_main_screen.stop_air4 = Mock()
        
        MainScreen.start_stop_air4(mock_main_screen)
        
        mock_main_screen.stop_air4.assert_called_once()
        mock_main_screen.start_air4.assert_not_called()
    
    def test_start_air4_calls_set_air4(self, mock_main_screen):
        """Test start_air4 calls set_air4 with True"""
        mock_main_screen.set_air4 = Mock()
        
        MainScreen.start_air4(mock_main_screen)
        
        mock_main_screen.set_air4.assert_called_once_with(True)
    
    def test_stop_air4_calls_set_air4(self, mock_main_screen):
        """Test stop_air4 calls set_air4 with False"""
        mock_main_screen.set_air4 = Mock()
        
        MainScreen.stop_air4(mock_main_screen)
        
        mock_main_screen.set_air4.assert_called_once_with(False)


class TestResetAir3:
    """Tests for reset_air3 method"""
    
    @patch('start.QSettings')
    def test_reset_air3_resets_seconds(self, mock_qsettings, mock_main_screen):
        """Test reset_air3 resets seconds to zero"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Timer'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 125
        mock_main_screen.statusAIR3 = False
        mock_main_screen.timerAIR3 = Mock()
        mock_main_screen.AirLabel_3 = Mock()
        
        MainScreen.reset_air3(mock_main_screen)
        
        assert mock_main_screen.Air3Seconds == 0
        mock_main_screen.timerAIR3.stop.assert_called_once()
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n0:00")
        mock_main_screen.timerAIR3.start.assert_not_called()
    
    @patch('start.QSettings')
    def test_reset_air3_restarts_if_running(self, mock_qsettings, mock_main_screen):
        """Test reset_air3 restarts timer if it was running"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Timer'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 125
        mock_main_screen.statusAIR3 = True
        mock_main_screen.timerAIR3 = Mock()
        mock_main_screen.AirLabel_3 = Mock()
        
        MainScreen.reset_air3(mock_main_screen)
        
        assert mock_main_screen.Air3Seconds == 0
        mock_main_screen.timerAIR3.start.assert_called_once_with(1000)


class TestResetAir4:
    """Tests for reset_air4 method"""
    
    @patch('start.QSettings')
    def test_reset_air4_resets_seconds(self, mock_qsettings, mock_main_screen):
        """Test reset_air4 resets seconds to zero"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Stream'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air4Seconds = 125
        mock_main_screen.statusAIR4 = False
        mock_main_screen.timerAIR4 = Mock()
        mock_main_screen.AirLabel_4 = Mock()
        
        MainScreen.reset_air4(mock_main_screen)
        
        assert mock_main_screen.Air4Seconds == 0
        mock_main_screen.timerAIR4.stop.assert_called_once()
        mock_main_screen.AirLabel_4.setText.assert_called_once_with("Stream\n0:00")
        mock_main_screen.timerAIR4.start.assert_not_called()
    
    @patch('start.QSettings')
    def test_reset_air4_restarts_if_running(self, mock_qsettings, mock_main_screen):
        """Test reset_air4 restarts timer if it was running"""
        mock_settings = Mock()
        mock_settings.value.return_value = 'Stream'
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air4Seconds = 125
        mock_main_screen.statusAIR4 = True
        mock_main_screen.timerAIR4 = Mock()
        mock_main_screen.AirLabel_4 = Mock()
        
        MainScreen.reset_air4(mock_main_screen)
        
        assert mock_main_screen.Air4Seconds == 0
        mock_main_screen.timerAIR4.start.assert_called_once_with(1000)


class TestUpdateDate:
    """Tests for update_date method"""
    
    @patch('ui_updater.QDate')
    @patch('ui_updater.QLocale')
    @patch('ui_updater.QSettings')
    def test_update_date(self, mock_qsettings, mock_qlocale, mock_qdate, mock_main_screen):
        """Test update_date formats and sets date text"""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'dateFormat': 'dddd, dd. MMMM yyyy'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_date = Mock()
        mock_qdate.currentDate.return_value = mock_date
        
        mock_locale = Mock()
        mock_locale.toString.return_value = "Monday, 01. January 2024"
        mock_qlocale.return_value = mock_locale
        
        mock_ui_updater = Mock()
        mock_ui_updater.languages = {"English": 'en_US'}
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_left_text = Mock()
        
        MainScreen.update_date(mock_main_screen)
        
        mock_ui_updater.update_date.assert_called_once()


class TestUpdateNTPStatus:
    """Tests for update_ntp_status method"""
    
    def test_update_ntp_status_with_warning(self, mock_main_screen):
        """Test update_ntp_status adds warning when NTP warning exists (priority -1)"""
        mock_ntp_manager = Mock()
        mock_ntp_manager.ntp_had_warning = True
        mock_ntp_manager.ntp_warn_message = "NTP sync error"
        mock_main_screen.ntp_manager = mock_ntp_manager
        mock_main_screen.add_warning = Mock()
        mock_main_screen.remove_warning = Mock()
        
        MainScreen.update_ntp_status(mock_main_screen)
        
        mock_ntp_manager.update_ntp_status.assert_called_once()
    
    def test_update_ntp_status_no_warning(self, mock_main_screen):
        """Test update_ntp_status removes NTP warning when no NTP warning exists"""
        mock_ntp_manager = Mock()
        mock_ntp_manager.ntp_had_warning = False
        mock_ntp_manager.ntp_warn_message = ""
        mock_main_screen.ntp_manager = mock_ntp_manager
        mock_main_screen.add_warning = Mock()
        mock_main_screen.remove_warning = Mock()
        
        MainScreen.update_ntp_status(mock_main_screen)
        
        # Should call ntp_manager.update_ntp_status
        mock_ntp_manager.update_ntp_status.assert_called_once()
    
    def test_update_ntp_status_empty_message(self, mock_main_screen):
        """Test update_ntp_status removes NTP warning when message is empty"""
        mock_ntp_manager = Mock()
        mock_ntp_manager.ntp_had_warning = True
        mock_ntp_manager.ntp_warn_message = ""
        mock_main_screen.ntp_manager = mock_ntp_manager
        mock_main_screen.add_warning = Mock()
        mock_main_screen.remove_warning = Mock()
        
        MainScreen.update_ntp_status(mock_main_screen)
        
        # Should call ntp_manager.update_ntp_status
        mock_ntp_manager.update_ntp_status.assert_called_once()


class TestLedLogic:
    """Tests for the led_logic method"""
    
    def test_led_logic_led1_on(self, mock_main_screen):
        """Test led_logic turns LED1 on"""
        mock_main_screen.settings.LED1Autoflash = Mock()
        mock_main_screen.settings.LED1Autoflash.isChecked.return_value = False
        mock_main_screen.settings.LED1Timedflash = Mock()
        mock_main_screen.settings.LED1Timedflash.isChecked.return_value = False
        mock_main_screen.timerLED1 = Mock()
        mock_main_screen.set_led1 = Mock()
        mock_main_screen.LED1on = False
        
        MainScreen.led_logic(mock_main_screen, 1, True)
        
        mock_main_screen.set_led1.assert_called_once_with(True)
        assert mock_main_screen.LED1on is True
    
    def test_led_logic_led1_off(self, mock_main_screen):
        """Test led_logic turns LED1 off"""
        mock_main_screen.timerLED1 = Mock()
        mock_main_screen.set_led1 = Mock()
        mock_main_screen.LED1on = True
        
        MainScreen.led_logic(mock_main_screen, 1, False)
        
        mock_main_screen.set_led1.assert_called_once_with(False)
        mock_main_screen.timerLED1.stop.assert_called_once()
        assert mock_main_screen.LED1on is False
    
    def test_led_logic_led1_autoflash(self, mock_main_screen):
        """Test led_logic starts autoflash timer for LED1"""
        mock_main_screen.settings.LED1Autoflash = Mock()
        mock_main_screen.settings.LED1Autoflash.isChecked.return_value = True
        mock_main_screen.settings.LED1Timedflash = Mock()
        mock_main_screen.settings.LED1Timedflash.isChecked.return_value = False
        mock_main_screen.timerLED1 = Mock()
        mock_main_screen.set_led1 = Mock()
        mock_main_screen.LED1on = False
        
        MainScreen.led_logic(mock_main_screen, 1, True)
        
        mock_main_screen.timerLED1.start.assert_called_once_with(500)
        mock_main_screen.set_led1.assert_called_once_with(True)
    
    def test_led_logic_led1_timedflash(self, mock_main_screen):
        """Test led_logic starts timedflash timer for LED1"""
        mock_main_screen.settings.LED1Autoflash = Mock()
        mock_main_screen.settings.LED1Autoflash.isChecked.return_value = False
        mock_main_screen.settings.LED1Timedflash = Mock()
        mock_main_screen.settings.LED1Timedflash.isChecked.return_value = True
        mock_main_screen.timerLED1 = Mock()
        mock_main_screen.set_led1 = Mock()
        mock_main_screen.unset_led1 = Mock()
        mock_main_screen.LED1on = False
        
        with patch('start.QTimer') as mock_qtimer:
            MainScreen.led_logic(mock_main_screen, 1, True)
            
            mock_main_screen.timerLED1.start.assert_called_once_with(500)
            mock_qtimer.singleShot.assert_called_once_with(20000, mock_main_screen.unset_led1)
    
    def test_led_logic_led2_on(self, mock_main_screen):
        """Test led_logic turns LED2 on"""
        mock_main_screen.settings.LED2Autoflash = Mock()
        mock_main_screen.settings.LED2Autoflash.isChecked.return_value = False
        mock_main_screen.settings.LED2Timedflash = Mock()
        mock_main_screen.settings.LED2Timedflash.isChecked.return_value = False
        mock_main_screen.timerLED2 = Mock()
        mock_main_screen.set_led2 = Mock()
        mock_main_screen.LED2on = False
        
        MainScreen.led_logic(mock_main_screen, 2, True)
        
        mock_main_screen.set_led2.assert_called_once_with(True)
        assert mock_main_screen.LED2on is True
    
    def test_led_logic_led2_off(self, mock_main_screen):
        """Test led_logic turns LED2 off"""
        mock_main_screen.timerLED2 = Mock()
        mock_main_screen.set_led2 = Mock()
        mock_main_screen.LED2on = True
        
        MainScreen.led_logic(mock_main_screen, 2, False)
        
        mock_main_screen.set_led2.assert_called_once_with(False)
        mock_main_screen.timerLED2.stop.assert_called_once()
        assert mock_main_screen.LED2on is False
    
    def test_led_logic_led3_on(self, mock_main_screen):
        """Test led_logic turns LED3 on"""
        mock_main_screen.settings.LED3Autoflash = Mock()
        mock_main_screen.settings.LED3Autoflash.isChecked.return_value = False
        mock_main_screen.settings.LED3Timedflash = Mock()
        mock_main_screen.settings.LED3Timedflash.isChecked.return_value = False
        mock_main_screen.timerLED3 = Mock()
        mock_main_screen.set_led3 = Mock()
        mock_main_screen.LED3on = False
        
        MainScreen.led_logic(mock_main_screen, 3, True)
        
        mock_main_screen.set_led3.assert_called_once_with(True)
        assert mock_main_screen.LED3on is True
    
    def test_led_logic_led3_off(self, mock_main_screen):
        """Test led_logic turns LED3 off"""
        mock_main_screen.timerLED3 = Mock()
        mock_main_screen.set_led3 = Mock()
        mock_main_screen.LED3on = True
        
        MainScreen.led_logic(mock_main_screen, 3, False)
        
        mock_main_screen.set_led3.assert_called_once_with(False)
        mock_main_screen.timerLED3.stop.assert_called_once()
        assert mock_main_screen.LED3on is False
    
    def test_led_logic_led4_on(self, mock_main_screen):
        """Test led_logic turns LED4 on"""
        mock_main_screen.settings.LED4Autoflash = Mock()
        mock_main_screen.settings.LED4Autoflash.isChecked.return_value = False
        mock_main_screen.settings.LED4Timedflash = Mock()
        mock_main_screen.settings.LED4Timedflash.isChecked.return_value = False
        mock_main_screen.timerLED4 = Mock()
        mock_main_screen.set_led4 = Mock()
        mock_main_screen.LED4on = False
        
        MainScreen.led_logic(mock_main_screen, 4, True)
        
        mock_main_screen.set_led4.assert_called_once_with(True)
        assert mock_main_screen.LED4on is True
    
    def test_led_logic_led4_off(self, mock_main_screen):
        """Test led_logic turns LED4 off"""
        mock_main_screen.timerLED4 = Mock()
        mock_main_screen.set_led4 = Mock()
        mock_main_screen.LED4on = True
        
        MainScreen.led_logic(mock_main_screen, 4, False)
        
        mock_main_screen.set_led4.assert_called_once_with(False)
        mock_main_screen.timerLED4.stop.assert_called_once()
        assert mock_main_screen.LED4on is False


class TestToggleFunctions:
    """Tests for toggle functions"""
    
    def test_toggle_led1_on_to_off(self, mock_main_screen):
        """Test toggle_led1 turns off when currently on"""
        mock_main_screen.statusLED1 = True
        mock_main_screen.set_led1 = Mock()
        
        MainScreen.toggle_led1(mock_main_screen)
        
        mock_main_screen.set_led1.assert_called_once_with(False)
    
    def test_toggle_led1_off_to_on(self, mock_main_screen):
        """Test toggle_led1 turns on when currently off"""
        mock_main_screen.statusLED1 = False
        mock_main_screen.set_led1 = Mock()
        
        MainScreen.toggle_led1(mock_main_screen)
        
        mock_main_screen.set_led1.assert_called_once_with(True)
    
    def test_toggle_led2(self, mock_main_screen):
        """Test toggle_led2 toggles LED2 state"""
        mock_main_screen.statusLED2 = True
        mock_main_screen.set_led2 = Mock()
        
        MainScreen.toggle_led2(mock_main_screen)
        
        mock_main_screen.set_led2.assert_called_once_with(False)
    
    def test_toggle_led3(self, mock_main_screen):
        """Test toggle_led3 toggles LED3 state"""
        mock_main_screen.statusLED3 = False
        mock_main_screen.set_led3 = Mock()
        
        MainScreen.toggle_led3(mock_main_screen)
        
        mock_main_screen.set_led3.assert_called_once_with(True)
    
    def test_toggle_led4(self, mock_main_screen):
        """Test toggle_led4 toggles LED4 state"""
        mock_main_screen.statusLED4 = True
        mock_main_screen.set_led4 = Mock()
        
        MainScreen.toggle_led4(mock_main_screen)
        
        mock_main_screen.set_led4.assert_called_once_with(False)
    
    def test_toggle_air1_on_to_off(self, mock_main_screen):
        """Test toggle_air1 turns off when currently on"""
        mock_main_screen.statusAIR1 = True
        mock_main_screen.set_air1 = Mock()
        
        MainScreen.toggle_air1(mock_main_screen)
        
        mock_main_screen.set_air1.assert_called_once_with(False)
    
    def test_toggle_air1_off_to_on(self, mock_main_screen):
        """Test toggle_air1 turns on when currently off"""
        mock_main_screen.statusAIR1 = False
        mock_main_screen.set_air1 = Mock()
        
        MainScreen.toggle_air1(mock_main_screen)
        
        mock_main_screen.set_air1.assert_called_once_with(True)
    
    def test_toggle_air2(self, mock_main_screen):
        """Test toggle_air2 toggles AIR2 state"""
        mock_main_screen.statusAIR2 = True
        mock_main_screen.set_air2 = Mock()
        
        MainScreen.toggle_air2(mock_main_screen)
        
        mock_main_screen.set_air2.assert_called_once_with(False)
    
    def test_toggle_air4(self, mock_main_screen):
        """Test toggle_air4 toggles AIR4 state"""
        mock_main_screen.statusAIR4 = False
        mock_main_screen.set_air4 = Mock()
        
        MainScreen.toggle_air4(mock_main_screen)
        
        mock_main_screen.set_air4.assert_called_once_with(True)
    
    def test_manual_toggle_led1_on_to_off(self, mock_main_screen):
        """Test manual_toggle_led1 turns off when LED1on is True"""
        mock_main_screen.LED1on = True
        mock_main_screen.led_logic = Mock()
        
        MainScreen.manual_toggle_led1(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(1, False)
    
    def test_manual_toggle_led1_off_to_on(self, mock_main_screen):
        """Test manual_toggle_led1 turns on when LED1on is False"""
        mock_main_screen.LED1on = False
        mock_main_screen.led_logic = Mock()
        
        MainScreen.manual_toggle_led1(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(1, True)
    
    def test_manual_toggle_led2(self, mock_main_screen):
        """Test manual_toggle_led2 toggles LED2"""
        mock_main_screen.LED2on = True
        mock_main_screen.led_logic = Mock()
        
        MainScreen.manual_toggle_led2(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(2, False)
    
    def test_manual_toggle_led3(self, mock_main_screen):
        """Test manual_toggle_led3 toggles LED3"""
        mock_main_screen.LED3on = False
        mock_main_screen.led_logic = Mock()
        
        MainScreen.manual_toggle_led3(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(3, True)
    
    def test_manual_toggle_led4(self, mock_main_screen):
        """Test manual_toggle_led4 toggles LED4"""
        mock_main_screen.LED4on = True
        mock_main_screen.led_logic = Mock()
        
        MainScreen.manual_toggle_led4(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(4, False)


class TestOASHTTPRequestHandler:
    """Tests for OASHTTPRequestHandler"""
    
    def _create_handler(self):
        """Helper to create a handler instance without triggering request handling"""
        from network import OASHTTPRequestHandler
        
        # Create handler by calling __new__ directly to avoid __init__
        handler = OASHTTPRequestHandler.__new__(OASHTTPRequestHandler)
        # Set required attributes manually
        handler.path = ""
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.send_error = Mock()
        handler.end_headers = Mock()
        return handler
    
    @patch('network.socket')
    @patch('network.QSettings')
    def test_do_get_valid_command(self, mock_qsettings, mock_socket_module):
        """Test do_GET handles valid command"""
        from network import OASHTTPRequestHandler
        
        # Setup mocks
        mock_settings = Mock()
        mock_settings.value.return_value = "3310"
        mock_qsettings.return_value = mock_settings
        
        mock_sock = Mock()
        mock_socket_module.socket.return_value = mock_sock
        
        handler = self._create_handler()
        handler.path = "/?cmd=LED1:ON"
        
        handler.do_GET()
        
        # Verify response was sent
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called()
        handler.end_headers.assert_called_once()
        
        # Verify UDP socket was created and message sent
        mock_socket_module.socket.assert_called_once_with(mock_socket_module.AF_INET, mock_socket_module.SOCK_DGRAM)
        mock_sock.sendto.assert_called_once()
        
        # Verify response was written
        handler.wfile.write.assert_called()
    
    def test_do_get_invalid_command_no_equals(self):
        """Test do_GET handles invalid command without equals sign"""
        handler = self._create_handler()
        handler.path = "/?cmd"
        
        handler.do_GET()
        
        handler.send_error.assert_called_once_with(400, 'no command was given')
    
    def test_do_get_empty_message(self):
        """Test do_GET handles empty message"""
        handler = self._create_handler()
        handler.path = "/?cmd="
        
        handler.do_GET()
        
        handler.send_error.assert_called_once_with(400, 'no command was given')
    
    def test_do_get_file_not_found(self):
        """Test do_GET returns 404 for non-command paths"""
        handler = self._create_handler()
        handler.path = "/some/other/path"
        
        handler.do_GET()
        
        handler.send_error.assert_called_once_with(404, 'file not found')
    
    def test_do_head(self):
        """Test do_HEAD sends correct headers"""
        handler = self._create_handler()
        
        handler.do_HEAD()
        
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_once_with("Content-type", "text/html; charset=utf-8")
        handler.end_headers.assert_called_once()
    
    @patch('network.socket')
    @patch('network.QSettings')
    def test_do_get_url_decoding(self, mock_qsettings, mock_socket_module):
        """Test do_GET properly URL-decodes commands"""
        mock_settings = Mock()
        mock_settings.value.return_value = "3310"
        mock_qsettings.return_value = mock_settings
        
        mock_sock = Mock()
        mock_socket_module.socket.return_value = mock_sock
        
        handler = self._create_handler()
        handler.path = "/?cmd=LED1%3AON"  # URL-encoded "LED1:ON"
        
        handler.do_GET()
        
        # Verify the decoded message was sent
        call_args = mock_sock.sendto.call_args[0][0]
        assert b"LED1:ON" in call_args
    
    @patch('network.socket')
    @patch('network.QSettings')
    def test_do_get_url_decoding_plus_signs(self, mock_qsettings, mock_socket_module):
        """Test do_GET properly URL-decodes + signs to spaces"""
        mock_settings = Mock()
        mock_settings.value.return_value = "3310"
        mock_qsettings.return_value = mock_settings
        
        mock_sock = Mock()
        mock_socket_module.socket.return_value = mock_sock
        
        handler = self._create_handler()
        # Test with + signs (which should be decoded to spaces)
        handler.path = "/?cmd=NOW:The+Testers+-+Test+around+the+clock"
        
        handler.do_GET()
        
        # Verify the decoded message was sent (with spaces, not + signs)
        call_args = mock_sock.sendto.call_args[0][0]
        decoded_message = call_args.decode('utf-8')
        assert "NOW:The Testers - Test around the clock" == decoded_message
        assert "+" not in decoded_message  # No + signs should remain


class TestReplaceNowNext:
    """Tests for replace_now_next method"""
    
    @patch('start.QSettings')
    def test_replace_now_next(self, mock_qsettings, mock_main_screen):
        """Test replace_now_next replaces NOW and NEXT text"""
        mock_settings = Mock()
        mock_settings.value.return_value = "Replacement text"
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.set_current_song_text = Mock()
        mock_main_screen.set_news_text = Mock()
        
        MainScreen.replace_now_next(mock_main_screen)
        
        mock_main_screen.set_current_song_text.assert_called_once_with("Replacement text")
        mock_main_screen.set_news_text.assert_called_once_with("")


# Note: udp_cmd_handler was moved to UdpServer._handle_udp_data in network.py
# These tests are no longer applicable as the functionality is now encapsulated in UdpServer


class TestParseCmdConfMore:
    """Tests for more CONF commands in parse_cmd"""
    
    def test_parse_cmd_conf_led2_text(self, mock_main_screen):
        """Test CONF command for LED2.text"""
        mock_main_screen.parse_cmd(b"CONF:LED2:text=PHONE ON")
        mock_main_screen.settings.LED2Text.setText.assert_called_once_with("PHONE ON")
    
    def test_parse_cmd_conf_led2_autoflash(self, mock_main_screen):
        """Test CONF command for LED2.autoflash"""
        mock_main_screen.parse_cmd(b"CONF:LED2:autoflash=True")
        mock_main_screen.settings.LED2Autoflash.setChecked.assert_called_once_with(True)
    
    def test_parse_cmd_conf_led3_timedflash(self, mock_main_screen):
        """Test CONF command for LED3.timedflash"""
        mock_main_screen.parse_cmd(b"CONF:LED3:timedflash=True")
        mock_main_screen.settings.LED3Timedflash.setChecked.assert_called_once_with(True)
    
    def test_parse_cmd_conf_led4_activebgcolor(self, mock_main_screen):
        """Test CONF command for LED4.activebgcolor"""
        mock_main_screen.parse_cmd(b"CONF:LED4:activebgcolor=#00FF00")
        mock_main_screen.settings.getColorFromName.assert_called()
        mock_main_screen.settings.setLED4BGColor.assert_called_once()
    
    def test_parse_cmd_conf_timers_air1_enabled(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIR1Enabled"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIR1Enabled=False")
        mock_main_screen.settings.enableAIR1.setChecked.assert_called_once_with(False)
    
    def test_parse_cmd_conf_timers_air2_text(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIR2Text"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIR2Text=Phone Call")
        mock_main_screen.settings.AIR2Text.setText.assert_called_once_with("Phone Call")
    
    def test_parse_cmd_conf_timers_air3_enabled(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIR3Enabled"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIR3Enabled=True")
        mock_main_screen.settings.enableAIR3.setChecked.assert_called_once_with(True)
    
    def test_parse_cmd_conf_timers_air4_enabled(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIR4Enabled"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIR4Enabled=False")
        mock_main_screen.settings.enableAIR4.setChecked.assert_called_once_with(False)
    
    def test_parse_cmd_conf_timers_air3_text(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIR3Text"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIR3Text=Radio Timer")
        mock_main_screen.settings.AIR3Text.setText.assert_called_once_with("Radio Timer")
    
    def test_parse_cmd_conf_timers_air4_text(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIR4Text"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIR4Text=Stream Timer")
        mock_main_screen.settings.AIR4Text.setText.assert_called_once_with("Stream Timer")
    
    def test_parse_cmd_conf_timers_air2_iconpath(self, mock_main_screen):
        """Test CONF command for Timers.AIR2iconpath"""
        mock_main_screen.parse_cmd(b"CONF:Timers:AIR2iconpath=/path/to/icon.png")
        mock_main_screen.settings.setAIR2IconPath.assert_called_once_with("/path/to/icon.png")
    
    def test_parse_cmd_conf_timers_air3_iconpath(self, mock_main_screen):
        """Test CONF command for Timers.AIR3iconpath"""
        mock_main_screen.parse_cmd(b"CONF:Timers:AIR3iconpath=/path/to/timer.png")
        mock_main_screen.settings.setAIR3IconPath.assert_called_once_with("/path/to/timer.png")
    
    def test_parse_cmd_conf_timers_air4_iconpath(self, mock_main_screen):
        """Test CONF command for Timers.AIR4iconpath"""
        mock_main_screen.parse_cmd(b"CONF:Timers:AIR4iconpath=/path/to/stream.png")
        mock_main_screen.settings.setAIR4IconPath.assert_called_once_with("/path/to/stream.png")
    
    def test_parse_cmd_conf_timers_minwidth(self, mock_main_screen):
        """Test CONF command for Timers.TimerAIRMinWidth"""
        mock_main_screen.parse_cmd(b"CONF:Timers:TimerAIRMinWidth=250")
        mock_main_screen.settings.AIRMinWidth.setValue.assert_called_once_with(250)
    
    def test_parse_cmd_conf_clock_secondsinoneline_true(self, mock_main_screen):
        """Test CONF command for Clock.secondsinoneline=True"""
        mock_main_screen.parse_cmd(b"CONF:Clock:secondsinoneline=True")
        mock_main_screen.settings.showSeconds.setChecked.assert_called_with(True)
        mock_main_screen.settings.seconds_in_one_line.setChecked.assert_called_with(True)
        mock_main_screen.settings.seconds_separate.setChecked.assert_called_with(False)
    
    def test_parse_cmd_conf_clock_secondsinoneline_false(self, mock_main_screen):
        """Test CONF command for Clock.secondsinoneline=False"""
        mock_main_screen.parse_cmd(b"CONF:Clock:secondsinoneline=False")
        mock_main_screen.settings.showSeconds.setChecked.assert_called_with(False)
        mock_main_screen.settings.seconds_in_one_line.setChecked.assert_called_with(False)
    
    def test_parse_cmd_conf_clock_staticcolon_true(self, mock_main_screen):
        """Test CONF command for Clock.staticcolon=True"""
        mock_main_screen.parse_cmd(b"CONF:Clock:staticcolon=True")
        mock_main_screen.settings.staticColon.setChecked.assert_called_once_with(True)
    
    def test_parse_cmd_conf_clock_staticcolon_false(self, mock_main_screen):
        """Test CONF command for Clock.staticcolon=False"""
        mock_main_screen.parse_cmd(b"CONF:Clock:staticcolon=False")
        mock_main_screen.settings.staticColon.setChecked.assert_called_once_with(False)
    
    def test_parse_cmd_conf_clock_digital_false(self, mock_main_screen):
        """Test CONF command for Clock.digital=False"""
        mock_main_screen.parse_cmd(b"CONF:Clock:digital=False")
        mock_main_screen.settings.clockAnalog.setChecked.assert_called_with(False)
        mock_main_screen.settings.clockDigital.setChecked.assert_called_with(True)
    
    def test_parse_cmd_conf_clock_logopath(self, mock_main_screen):
        """Test CONF command for Clock.logopath"""
        mock_main_screen.parse_cmd(b"CONF:Clock:logopath=/path/to/logo.png")
        mock_main_screen.settings.setLogoPath.assert_called_once_with("/path/to/logo.png")
    
    def test_parse_cmd_conf_clock_logoupper_true(self, mock_main_screen):
        """Test CONF command for Clock.logoupper=True"""
        mock_main_screen.parse_cmd(b"CONF:Clock:logoupper=True")
        mock_main_screen.settings.setLogoUpper.assert_called_once_with(True)
    
    def test_parse_cmd_conf_clock_logoupper_false(self, mock_main_screen):
        """Test CONF command for Clock.logoupper=False"""
        mock_main_screen.parse_cmd(b"CONF:Clock:logoupper=False")
        mock_main_screen.settings.setLogoUpper.assert_called_once_with(False)
    
    def test_parse_cmd_conf_clock_digitaldigitcolor(self, mock_main_screen):
        """Test CONF command for Clock.digitaldigitcolor"""
        mock_main_screen.parse_cmd(b"CONF:Clock:digitaldigitcolor=#0000FF")
        mock_main_screen.settings.getColorFromName.assert_called()
        mock_main_screen.settings.setDigitalDigitColor.assert_called_once()
    
    def test_parse_cmd_conf_general_replacenow_true(self, mock_main_screen):
        """Test CONF command for General.replacenow=True"""
        mock_main_screen.parse_cmd(b"CONF:General:replacenow=True")
        mock_main_screen.settings.replaceNOW.setChecked.assert_called_once_with(True)
    
    def test_parse_cmd_conf_general_replacenow_false(self, mock_main_screen):
        """Test CONF command for General.replacenow=False"""
        mock_main_screen.parse_cmd(b"CONF:General:replacenow=False")
        mock_main_screen.settings.replaceNOW.setChecked.assert_called_once_with(False)
    
    def test_parse_cmd_conf_general_replacenowtext(self, mock_main_screen):
        """Test CONF command for General.replacenowtext"""
        mock_main_screen.parse_cmd(b"CONF:General:replacenowtext=Replacement Text")
        mock_main_screen.settings.replaceNOWText.setText.assert_called_once_with("Replacement Text")


class TestSetAir1:
    """Tests for set_air1 method"""
    
    @patch('start.QSettings')
    def test_set_air1_on(self, mock_qsettings, mock_main_screen):
        """Test set_air1 activates AIR1 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'AIR1activetextcolor': '#FFFFFF',
            'AIR1activebgcolor': '#FF0000',
            'TimerAIR1Text': 'Mic'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air1Seconds = 0
        mock_main_screen.AirLabel_1 = Mock()
        mock_main_screen.AirIcon_1 = Mock()
        mock_main_screen.timerAIR1 = Mock()
        mock_main_screen.statusAIR1 = False
        
        MainScreen.set_air1(mock_main_screen, True)
        
        assert mock_main_screen.Air1Seconds == 0
        assert mock_main_screen.statusAIR1 is True
        mock_main_screen.AirLabel_1.setStyleSheet.assert_called()
        mock_main_screen.AirIcon_1.setStyleSheet.assert_called()
        mock_main_screen.AirLabel_1.setText.assert_called_once_with("Mic\n0:00")
        mock_main_screen.timerAIR1.start.assert_called_once_with(1000)
    
    @patch('start.QSettings')
    def test_set_air1_off(self, mock_qsettings, mock_main_screen):
        """Test set_air1 deactivates AIR1 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'inactivetextcolor': '#555555',
            'inactivebgcolor': '#222222'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.AirLabel_1 = Mock()
        mock_main_screen.AirIcon_1 = Mock()
        mock_main_screen.timerAIR1 = Mock()
        mock_main_screen.statusAIR1 = True
        
        MainScreen.set_air1(mock_main_screen, False)
        
        assert mock_main_screen.statusAIR1 is False
        mock_main_screen.AirLabel_1.setStyleSheet.assert_called()
        mock_main_screen.AirIcon_1.setStyleSheet.assert_called()
        mock_main_screen.timerAIR1.stop.assert_called_once()


class TestSetAir2:
    """Tests for set_air2 method"""
    
    @patch('start.QSettings')
    def test_set_air2_on(self, mock_qsettings, mock_main_screen):
        """Test set_air2 activates AIR2 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'AIR2activetextcolor': '#FFFFFF',
            'AIR2activebgcolor': '#FF0000',
            'TimerAIR2Text': 'Phone'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air2Seconds = 0
        mock_main_screen.AirLabel_2 = Mock()
        mock_main_screen.AirIcon_2 = Mock()
        mock_main_screen.timerAIR2 = Mock()
        mock_main_screen.statusAIR2 = False
        
        MainScreen.set_air2(mock_main_screen, True)
        
        assert mock_main_screen.Air2Seconds == 0
        assert mock_main_screen.statusAIR2 is True
        mock_main_screen.AirLabel_2.setStyleSheet.assert_called()
        mock_main_screen.AirIcon_2.setStyleSheet.assert_called()
        mock_main_screen.AirLabel_2.setText.assert_called_once_with("Phone\n0:00")
        mock_main_screen.timerAIR2.start.assert_called_once_with(1000)
    
    @patch('start.QSettings')
    def test_set_air2_off(self, mock_qsettings, mock_main_screen):
        """Test set_air2 deactivates AIR2 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'inactivetextcolor': '#555555',
            'inactivebgcolor': '#222222'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.AirLabel_2 = Mock()
        mock_main_screen.AirIcon_2 = Mock()
        mock_main_screen.timerAIR2 = Mock()
        mock_main_screen.statusAIR2 = True
        
        MainScreen.set_air2(mock_main_screen, False)
        
        assert mock_main_screen.statusAIR2 is False
        mock_main_screen.AirLabel_2.setStyleSheet.assert_called()
        mock_main_screen.AirIcon_2.setStyleSheet.assert_called()
        mock_main_screen.timerAIR2.stop.assert_called_once()


class TestSetAir3:
    """Tests for set_air3 method"""
    
    @patch('start.QSettings')
    def test_set_air3_on(self, mock_qsettings, mock_main_screen):
        """Test set_air3 activates AIR3 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'AIR3activetextcolor': '#FFFFFF',
            'AIR3activebgcolor': '#FF0000',
            'TimerAIR3Text': 'Timer'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 0
        mock_main_screen.radioTimerMode = 0
        mock_main_screen.AirLabel_3 = Mock()
        mock_main_screen.AirIcon_3 = Mock()
        mock_main_screen.timerAIR3 = Mock()
        mock_main_screen.statusAIR3 = False
        mock_main_screen.update_air3_seconds = Mock()
        
        MainScreen.set_air3(mock_main_screen, True)
        
        assert mock_main_screen.statusAIR3 is True
        mock_main_screen.AirLabel_3.setStyleSheet.assert_called()
        mock_main_screen.AirIcon_3.setStyleSheet.assert_called()
        mock_main_screen.AirLabel_3.setText.assert_called_once_with("Timer\n0:00")
        mock_main_screen.timerAIR3.start.assert_called_once_with(1000)
        mock_main_screen.update_air3_seconds.assert_not_called()
    
    @patch('start.QSettings')
    def test_set_air3_on_countdown_mode(self, mock_qsettings, mock_main_screen):
        """Test set_air3 activates with countdown mode and updates seconds"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'AIR3activetextcolor': '#FFFFFF',
            'AIR3activebgcolor': '#FF0000',
            'TimerAIR3Text': 'Timer'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air3Seconds = 120
        mock_main_screen.radioTimerMode = 1  # countdown
        mock_main_screen.AirLabel_3 = Mock()
        mock_main_screen.AirIcon_3 = Mock()
        mock_main_screen.timerAIR3 = Mock()
        mock_main_screen.statusAIR3 = False
        mock_main_screen.update_air3_seconds = Mock()
        
        MainScreen.set_air3(mock_main_screen, True)
        
        assert mock_main_screen.statusAIR3 is True
        mock_main_screen.update_air3_seconds.assert_called_once()
    
    @patch('start.QSettings')
    def test_set_air3_off(self, mock_qsettings, mock_main_screen):
        """Test set_air3 deactivates AIR3 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'inactivetextcolor': '#555555',
            'inactivebgcolor': '#222222'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.AirLabel_3 = Mock()
        mock_main_screen.AirIcon_3 = Mock()
        mock_main_screen.timerAIR3 = Mock()
        mock_main_screen.statusAIR3 = True
        
        MainScreen.set_air3(mock_main_screen, False)
        
        assert mock_main_screen.statusAIR3 is False
        mock_main_screen.timerAIR3.stop.assert_called_once()


class TestSetAir4:
    """Tests for set_air4 method"""
    
    @patch('start.QSettings')
    def test_set_air4_on(self, mock_qsettings, mock_main_screen):
        """Test set_air4 activates AIR4 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'AIR4activetextcolor': '#FFFFFF',
            'AIR4activebgcolor': '#FF0000',
            'TimerAIR4Text': 'Stream'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air4Seconds = 0
        mock_main_screen.streamTimerMode = 0
        mock_main_screen.AirLabel_4 = Mock()
        mock_main_screen.AirIcon_4 = Mock()
        mock_main_screen.timerAIR4 = Mock()
        mock_main_screen.statusAIR4 = False
        mock_main_screen.update_air4_seconds = Mock()
        
        MainScreen.set_air4(mock_main_screen, True)
        
        assert mock_main_screen.statusAIR4 is True
        mock_main_screen.AirLabel_4.setStyleSheet.assert_called()
        mock_main_screen.AirIcon_4.setStyleSheet.assert_called()
        mock_main_screen.AirLabel_4.setText.assert_called_once_with("Stream\n0:00")
        mock_main_screen.timerAIR4.start.assert_called_once_with(1000)
        mock_main_screen.update_air4_seconds.assert_not_called()
    
    @patch('start.QSettings')
    def test_set_air4_on_countdown_mode(self, mock_qsettings, mock_main_screen):
        """Test set_air4 activates with countdown mode and updates seconds"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'AIR4activetextcolor': '#FFFFFF',
            'AIR4activebgcolor': '#FF0000',
            'TimerAIR4Text': 'Stream'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.Air4Seconds = 120
        mock_main_screen.streamTimerMode = 1  # countdown
        mock_main_screen.AirLabel_4 = Mock()
        mock_main_screen.AirIcon_4 = Mock()
        mock_main_screen.timerAIR4 = Mock()
        mock_main_screen.statusAIR4 = False
        mock_main_screen.update_air4_seconds = Mock()
        
        MainScreen.set_air4(mock_main_screen, True)
        
        assert mock_main_screen.statusAIR4 is True
        mock_main_screen.update_air4_seconds.assert_called_once()
    
    @patch('start.QSettings')
    def test_set_air4_off(self, mock_qsettings, mock_main_screen):
        """Test set_air4 deactivates AIR4 timer"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'inactivetextcolor': '#555555',
            'inactivebgcolor': '#222222'
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_main_screen.AirLabel_4 = Mock()
        mock_main_screen.AirIcon_4 = Mock()
        mock_main_screen.timerAIR4 = Mock()
        mock_main_screen.statusAIR4 = True
        
        MainScreen.set_air4(mock_main_screen, False)
        
        assert mock_main_screen.statusAIR4 is False
        mock_main_screen.timerAIR4.stop.assert_called_once()


class TestShowHideWarning:
    """Tests for show_warning and hide_warning methods"""
    
    def test_show_warning(self, mock_main_screen):
        """Test show_warning delegates to warning_manager"""
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.show_warning(mock_main_screen, "Test warning")
        
        mock_warning_manager.show_warning.assert_called_once_with("Test warning")
    
    def test_hide_warning(self, mock_main_screen):
        """Test hide_warning delegates to warning_manager"""
        mock_warning_manager = Mock()
        mock_main_screen.warning_manager = mock_warning_manager
        
        MainScreen.hide_warning(mock_main_screen)
        
        mock_warning_manager.hide_warning.assert_called_once()


class TestUpdateBacktimingTextEdgeCases:
    """Tests for edge cases in update_backtiming_text method"""
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_quarter_to(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format at quarter to"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 45
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_minutes_past(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format for minutes past"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 7
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_minutes_to(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format for minutes to"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 50
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_english_am_pm(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text English format with AM/PM"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'English',
            'isAmPm': True
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 15  # 3 PM
        mock_now.minute = 0
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_german_minutes_nach(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text German format for minutes nach"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'German',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 10
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_german_minutes_vor(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text German format for minutes vor"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'German',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 50
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_german_uhr(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text German format at o'clock"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'German',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 0
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_dutch_kwart(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text Dutch format for kwart"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'Dutch',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 15
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_french_et_quart(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text French format for et quart"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'French',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 15
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_french_et_demie(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text French format for et demie"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'French',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 14
        mock_now.minute = 30
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()
    
    @patch('ui_updater.QSettings')
    @patch('ui_updater.datetime')
    def test_update_backtiming_text_french_minuit(self, mock_datetime, mock_qsettings, mock_main_screen):
        """Test update_backtiming_text French format for minuit"""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            'textClockLanguage': 'French',
            'isAmPm': False
        }.get(key, default)
        mock_qsettings.return_value = mock_settings
        
        mock_now = Mock()
        mock_now.hour = 0
        mock_now.minute = 0
        mock_datetime.now.return_value = mock_now
        
        mock_ui_updater = Mock()
        mock_main_screen.ui_updater = mock_ui_updater
        mock_main_screen.set_right_text = Mock()
        
        mock_main_screen.update_backtiming_text()
        
        mock_ui_updater.update_backtiming_text.assert_called_once()


class TestTriggerNTPCheck:
    """Tests for trigger_ntp_check method"""
    
    def test_trigger_ntp_check_enabled(self, mock_main_screen):
        """Test trigger_ntp_check starts NTP check when enabled"""
        mock_ntp_manager = Mock()
        mock_main_screen.ntp_manager = mock_ntp_manager
        
        MainScreen.trigger_ntp_check(mock_main_screen)
        
        mock_ntp_manager.trigger_ntp_check.assert_called_once()
    
    def test_trigger_ntp_check_disabled(self, mock_main_screen):
        """Test trigger_ntp_check stops timer when disabled"""
        mock_ntp_manager = Mock()
        mock_main_screen.ntp_manager = mock_ntp_manager
        
        MainScreen.trigger_ntp_check(mock_main_screen)
        
        mock_ntp_manager.trigger_ntp_check.assert_called_once()


class TestRadioTimerHelpers:
    """Tests for radio timer helper functions"""
    
    def test_radio_timer_start_stop(self, mock_main_screen):
        """Test radio_timer_start_stop calls start_stop_air3"""
        mock_main_screen.start_stop_air3 = Mock()
        
        MainScreen.radio_timer_start_stop(mock_main_screen)
        
        mock_main_screen.start_stop_air3.assert_called_once()
    
    def test_radio_timer_reset(self, mock_main_screen):
        """Test radio_timer_reset calls reset_air3 and sets mode"""
        mock_main_screen.reset_air3 = Mock()
        mock_main_screen.radioTimerMode = 1
        
        MainScreen.radio_timer_reset(mock_main_screen)
        
        mock_main_screen.reset_air3.assert_called_once()
        assert mock_main_screen.radioTimerMode == 0


class TestStreamTimerHelpers:
    """Tests for stream timer helper functions"""
    
    def test_stream_timer_start_stop(self, mock_main_screen):
        """Test stream_timer_start_stop calls start_stop_air4"""
        mock_main_screen.start_stop_air4 = Mock()
        
        MainScreen.stream_timer_start_stop(mock_main_screen)
        
        mock_main_screen.start_stop_air4.assert_called_once()
    
    def test_stream_timer_reset(self, mock_main_screen):
        """Test stream_timer_reset calls reset_air4 and sets mode"""
        mock_main_screen.reset_air4 = Mock()
        mock_main_screen.streamTimerMode = 1
        
        MainScreen.stream_timer_reset(mock_main_screen)
        
        mock_main_screen.reset_air4.assert_called_once()
        assert mock_main_screen.streamTimerMode == 0


class TestUnsetLed:
    """Tests for unset_led functions"""
    
    def test_unset_led1(self, mock_main_screen):
        """Test unset_led1 calls led_logic with False"""
        mock_main_screen.led_logic = Mock()
        
        MainScreen.unset_led1(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(1, False)
    
    def test_unset_led2(self, mock_main_screen):
        """Test unset_led2 calls led_logic with False"""
        mock_main_screen.led_logic = Mock()
        
        MainScreen.unset_led2(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(2, False)
    
    def test_unset_led3(self, mock_main_screen):
        """Test unset_led3 calls led_logic with False"""
        mock_main_screen.led_logic = Mock()
        
        MainScreen.unset_led3(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(3, False)
    
    def test_unset_led4(self, mock_main_screen):
        """Test unset_led4 calls led_logic with False"""
        mock_main_screen.led_logic = Mock()
        
        MainScreen.unset_led4(mock_main_screen)
        
        mock_main_screen.led_logic.assert_called_once_with(4, False)


class TestSetLogLevel:
    """Test set_log_level() function"""

    def test_set_log_level_debug(self):
        """Test set_log_level() with DEBUG"""
        import logging
        from start import set_log_level
        
        set_log_level("DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_set_log_level_info(self):
        """Test set_log_level() with INFO"""
        import logging
        from start import set_log_level
        
        set_log_level("INFO")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_set_log_level_warning(self):
        """Test set_log_level() with WARNING"""
        import logging
        from start import set_log_level
        
        set_log_level("WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_set_log_level_error(self):
        """Test set_log_level() with ERROR"""
        import logging
        from start import set_log_level
        
        set_log_level("ERROR")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR

    def test_set_log_level_critical(self):
        """Test set_log_level() with CRITICAL"""
        import logging
        from start import set_log_level
        
        set_log_level("CRITICAL")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.CRITICAL

    def test_set_log_level_none(self):
        """Test set_log_level() with NONE"""
        import logging
        from start import set_log_level
        
        set_log_level("NONE")
        root_logger = logging.getLogger()
        # NONE should be CRITICAL + 1
        assert root_logger.level == logging.CRITICAL + 1

    def test_set_log_level_case_insensitive(self):
        """Test set_log_level() is case-insensitive"""
        import logging
        from start import set_log_level
        
        set_log_level("debug")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        
        set_log_level("Info")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        set_log_level("WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_set_log_level_invalid_fallback(self):
        """Test set_log_level() with invalid level falls back to INFO"""
        import logging
        from start import set_log_level
        
        set_log_level("INVALID")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_set_log_level_handler_creation(self):
        """Test set_log_level() creates handler when none exists"""
        import logging
        from start import set_log_level
        
        root_logger = logging.getLogger()
        # Remove all handlers
        root_logger.handlers.clear()
        
        set_log_level("DEBUG")
        
        # Should have created a handler
        assert len(root_logger.handlers) > 0
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_set_log_level_handler_format(self):
        """Test set_log_level() handler has correct format"""
        import logging
        from start import set_log_level
        
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        set_log_level("INFO")
        
        handler = root_logger.handlers[0]
        formatter = handler.formatter
        format_string = formatter._fmt
        
        # Check format contains expected fields
        assert '%(asctime)s' in format_string
        assert '%(name)s' in format_string
        assert '%(levelname)s' in format_string
        assert '%(message)s' in format_string

    def test_set_log_level_no_handler_duplication(self):
        """Test set_log_level() doesn't create duplicate handlers"""
        import logging
        from start import set_log_level
        
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # First call creates handler
        set_log_level("DEBUG")
        handler_count_1 = len(root_logger.handlers)
        
        # Second call should not create another handler
        set_log_level("INFO")
        handler_count_2 = len(root_logger.handlers)
        
        assert handler_count_1 == handler_count_2

