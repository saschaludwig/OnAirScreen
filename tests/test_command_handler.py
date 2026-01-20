#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for command_handler.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtGui import QColor

from command_handler import (
    CommandHandler,
    validate_text_input,
    validate_command_value,
    validate_led_value,
    validate_air_value,
    validate_air3time_value,
    validate_cmd_value,
    MAX_TEXT_LENGTH,
    MAX_CONFIG_LENGTH,
)


@pytest.fixture
def mock_main_screen():
    """Create a mock MainScreen instance for testing"""
    main_screen = Mock()
    
    # Mock text setting methods
    main_screen.set_current_song_text = Mock()
    main_screen.set_news_text = Mock()
    
    # Mock LED methods
    main_screen.led_logic = Mock()
    main_screen.toggle_led1 = Mock()
    main_screen.toggle_led2 = Mock()
    main_screen.toggle_led3 = Mock()
    main_screen.toggle_led4 = Mock()
    
    # Mock AIR methods
    main_screen.set_air1 = Mock()
    main_screen.set_air2 = Mock()
    main_screen.set_air4 = Mock()
    main_screen.toggle_air1 = Mock()
    main_screen.toggle_air2 = Mock()
    main_screen.start_air3 = Mock()
    main_screen.stop_air3 = Mock()
    main_screen.radio_timer_reset = Mock()
    main_screen.radio_timer_start_stop = Mock()
    main_screen.radio_timer_set = Mock()
    main_screen.stream_timer_reset = Mock()
    main_screen.start_stop_air4 = Mock()
    
    # Mock system commands
    main_screen.reboot_host = Mock()
    main_screen.shutdown_host = Mock()
    main_screen.quit_oas = Mock()
    
    # Mock warning methods
    main_screen.add_warning = Mock()
    main_screen.remove_warning = Mock()
    
    # Mock settings object
    main_screen.settings = MagicMock()
    main_screen.settings.StationName = MagicMock()
    main_screen.settings.Slogan = MagicMock()
    main_screen.settings.replaceNOW = MagicMock()
    main_screen.settings.replaceNOWText = MagicMock()
    main_screen.settings.getColorFromName = Mock(return_value=QColor(255, 255, 255))
    main_screen.settings.setStationNameColor = Mock()
    main_screen.settings.setSloganColor = Mock()
    main_screen.settings.setDigitalHourColor = Mock()
    main_screen.settings.setDigitalSecondColor = Mock()
    main_screen.settings.setDigitalDigitColor = Mock()
    main_screen.settings.setLogoPath = Mock()
    main_screen.settings.setLogoUpper = Mock()
    main_screen.settings.clockDigital = MagicMock()
    main_screen.settings.clockAnalog = MagicMock()
    main_screen.settings.showSeconds = MagicMock()
    main_screen.settings.seconds_in_one_line = MagicMock()
    main_screen.settings.seconds_separate = MagicMock()
    main_screen.settings.staticColon = MagicMock()
    main_screen.settings.udpport = MagicMock()
    main_screen.settings.AIRMinWidth = MagicMock()
    main_screen.settings.applySettings = Mock()
    
    # Mock LED settings
    for led_num in range(1, 5):
        setattr(main_screen.settings, f"LED{led_num}", MagicMock())
        setattr(main_screen.settings, f"LED{led_num}Text", MagicMock())
        setattr(main_screen.settings, f"LED{led_num}Autoflash", MagicMock())
        setattr(main_screen.settings, f"LED{led_num}Timedflash", MagicMock())
        setattr(main_screen.settings, f"setLED{led_num}BGColor", Mock())
        setattr(main_screen.settings, f"setLED{led_num}FGColor", Mock())
    
    # Mock AIR settings
    for air_num in range(1, 5):
        setattr(main_screen.settings, f"enableAIR{air_num}", MagicMock())
        setattr(main_screen.settings, f"AIR{air_num}Text", MagicMock())
        setattr(main_screen.settings, f"setAIR{air_num}BGColor", Mock())
        setattr(main_screen.settings, f"setAIR{air_num}FGColor", Mock())
        setattr(main_screen.settings, f"setAIR{air_num}IconPath", Mock())
    
    return main_screen


@pytest.fixture
def command_handler(mock_main_screen):
    """Create a CommandHandler instance for testing"""
    return CommandHandler(mock_main_screen)


class TestCommandHandlerInitialization:
    """Test CommandHandler initialization"""
    
    def test_init_stores_main_screen(self, command_handler, mock_main_screen):
        """Test that main_screen is stored"""
        assert command_handler.main_screen is mock_main_screen


class TestParseCmd:
    """Test parse_cmd method"""
    
    def test_parse_cmd_valid_command(self, command_handler, mock_main_screen):
        """Test parsing a valid command"""
        result = command_handler.parse_cmd(b"NOW:Test Song")
        assert result is True
        mock_main_screen.set_current_song_text.assert_called_once_with("Test Song")
    
    def test_parse_cmd_invalid_format(self, command_handler):
        """Test parsing invalid command format"""
        result = command_handler.parse_cmd(b"INVALID")
        assert result is False
    
    def test_parse_cmd_empty_string(self, command_handler):
        """Test parsing empty string"""
        result = command_handler.parse_cmd(b"")
        assert result is False
    
    def test_parse_cmd_no_colon(self, command_handler):
        """Test parsing command without colon"""
        result = command_handler.parse_cmd(b"NOW")
        assert result is False
    
    def test_parse_cmd_unknown_command(self, command_handler):
        """Test parsing unknown command"""
        with patch('command_handler.logger') as mock_logger:
            result = command_handler.parse_cmd(b"UNKNOWN:value")
            assert result is False
            # Now uses log_exception which calls logger.error (not warning)
            mock_logger.error.assert_called_once()


class TestSimpleCommands:
    """Test simple command handlers"""
    
    def test_now_command(self, command_handler, mock_main_screen):
        """Test NOW command"""
        command_handler.parse_cmd(b"NOW:Current Song")
        mock_main_screen.set_current_song_text.assert_called_once_with("Current Song")
    
    def test_next_command(self, command_handler, mock_main_screen):
        """Test NEXT command"""
        command_handler.parse_cmd(b"NEXT:Next Song")
        mock_main_screen.set_news_text.assert_called_once_with("Next Song")


class TestLedCommands:
    """Test LED command handlers"""
    
    def test_led1_on(self, command_handler, mock_main_screen):
        """Test LED1 ON command"""
        command_handler.parse_cmd(b"LED1:ON")
        mock_main_screen.led_logic.assert_called_once_with(1, True)
    
    def test_led1_off(self, command_handler, mock_main_screen):
        """Test LED1 OFF command"""
        command_handler.parse_cmd(b"LED1:OFF")
        mock_main_screen.led_logic.assert_called_once_with(1, False)
    
    def test_led2_on(self, command_handler, mock_main_screen):
        """Test LED2 ON command"""
        command_handler.parse_cmd(b"LED2:ON")
        mock_main_screen.led_logic.assert_called_once_with(2, True)
    
    def test_led3_off(self, command_handler, mock_main_screen):
        """Test LED3 OFF command"""
        command_handler.parse_cmd(b"LED3:OFF")
        mock_main_screen.led_logic.assert_called_once_with(3, False)
    
    def test_led4_on(self, command_handler, mock_main_screen):
        """Test LED4 ON command"""
        command_handler.parse_cmd(b"LED4:ON")
        mock_main_screen.led_logic.assert_called_once_with(4, True)
    
    def test_all_led_commands(self, command_handler, mock_main_screen):
        """Test all LED commands"""
        for led_num in range(1, 5):
            command_handler.parse_cmd(f"LED{led_num}:ON".encode())
            mock_main_screen.led_logic.assert_called_with(led_num, True)
    
    def test_led1_toggle(self, command_handler, mock_main_screen):
        """Test LED1 TOGGLE command"""
        command_handler.parse_cmd(b"LED1:TOGGLE")
        mock_main_screen.toggle_led1.assert_called_once()
    
    def test_led2_toggle(self, command_handler, mock_main_screen):
        """Test LED2 TOGGLE command"""
        command_handler.parse_cmd(b"LED2:TOGGLE")
        mock_main_screen.toggle_led2.assert_called_once()
    
    def test_led3_toggle(self, command_handler, mock_main_screen):
        """Test LED3 TOGGLE command"""
        command_handler.parse_cmd(b"LED3:TOGGLE")
        mock_main_screen.toggle_led3.assert_called_once()
    
    def test_led4_toggle(self, command_handler, mock_main_screen):
        """Test LED4 TOGGLE command"""
        command_handler.parse_cmd(b"LED4:TOGGLE")
        mock_main_screen.toggle_led4.assert_called_once()


class TestWarnCommand:
    """Test WARN command handler"""
    
    def test_warn_add_default_priority(self, command_handler, mock_main_screen):
        """Test WARN command to add warning with default priority (0)"""
        command_handler.parse_cmd(b"WARN:Test Warning")
        mock_main_screen.add_warning.assert_called_once_with("Test Warning", 0)
    
    def test_warn_add_priority_0(self, command_handler, mock_main_screen):
        """Test WARN command with explicit priority 0 (not allowed, text part is extracted)"""
        command_handler.parse_cmd(b"WARN:0:Test Warning")
        # Priority 0 cannot be explicitly set, so the text part is extracted and validated
        mock_main_screen.add_warning.assert_called_once_with("Test Warning", 0)
    
    def test_warn_add_priority_1(self, command_handler, mock_main_screen):
        """Test WARN command to add warning with priority 1"""
        command_handler.parse_cmd(b"WARN:1:Test Warning")
        mock_main_screen.add_warning.assert_called_once_with("Test Warning", 1)
    
    def test_warn_add_priority_2(self, command_handler, mock_main_screen):
        """Test WARN command to add warning with priority 2"""
        command_handler.parse_cmd(b"WARN:2:Test Warning")
        mock_main_screen.add_warning.assert_called_once_with("Test Warning", 2)
    
    def test_warn_remove_default_priority(self, command_handler, mock_main_screen):
        """Test WARN command to remove warning with default priority (0)"""
        command_handler.parse_cmd(b"WARN:")
        mock_main_screen.remove_warning.assert_called_once_with(0)
    
    def test_warn_remove_priority_1(self, command_handler, mock_main_screen):
        """Test WARN command to remove warning with priority 1"""
        command_handler.parse_cmd(b"WARN:1:")
        mock_main_screen.remove_warning.assert_called_once_with(1)
    
    def test_warn_invalid_priority(self, command_handler, mock_main_screen):
        """Test WARN command with invalid priority falls back to default"""
        command_handler.parse_cmd(b"WARN:5:Test Warning")
        mock_main_screen.add_warning.assert_called_once_with("5:Test Warning", 0)
    
    def test_warn_text_with_colon(self, command_handler, mock_main_screen):
        """Test WARN command with colon in text (not priority format)"""
        command_handler.parse_cmd(b"WARN:Error: Something went wrong")
        # Should be treated as regular text (not priority format)
        mock_main_screen.add_warning.assert_called_once_with("Error: Something went wrong", 0)


class TestAirSimpleCommands:
    """Test simple AIR command handlers (AIR1, AIR2)"""
    
    def test_air1_on(self, command_handler, mock_main_screen):
        """Test AIR1 ON command"""
        command_handler.parse_cmd(b"AIR1:ON")
        mock_main_screen.set_air1.assert_called_once_with(True)
    
    def test_air1_off(self, command_handler, mock_main_screen):
        """Test AIR1 OFF command"""
        command_handler.parse_cmd(b"AIR1:OFF")
        mock_main_screen.set_air1.assert_called_once_with(False)
    
    def test_air2_on(self, command_handler, mock_main_screen):
        """Test AIR2 ON command"""
        command_handler.parse_cmd(b"AIR2:ON")
        mock_main_screen.set_air2.assert_called_once_with(True)
    
    def test_air2_off(self, command_handler, mock_main_screen):
        """Test AIR2 OFF command"""
        command_handler.parse_cmd(b"AIR2:OFF")
        mock_main_screen.set_air2.assert_called_once_with(False)
    
    def test_air1_toggle(self, command_handler, mock_main_screen):
        """Test AIR1 TOGGLE command"""
        command_handler.parse_cmd(b"AIR1:TOGGLE")
        mock_main_screen.toggle_air1.assert_called_once()
    
    def test_air2_toggle(self, command_handler, mock_main_screen):
        """Test AIR2 TOGGLE command"""
        command_handler.parse_cmd(b"AIR2:TOGGLE")
        mock_main_screen.toggle_air2.assert_called_once()


class TestAir3Command:
    """Test AIR3 command handler"""
    
    def test_air3_off(self, command_handler, mock_main_screen):
        """Test AIR3 OFF command"""
        command_handler.parse_cmd(b"AIR3:OFF")
        mock_main_screen.stop_air3.assert_called_once()
    
    def test_air3_on(self, command_handler, mock_main_screen):
        """Test AIR3 ON command"""
        command_handler.parse_cmd(b"AIR3:ON")
        mock_main_screen.start_air3.assert_called_once()
    
    def test_air3_reset(self, command_handler, mock_main_screen):
        """Test AIR3 RESET command"""
        command_handler.parse_cmd(b"AIR3:RESET")
        mock_main_screen.radio_timer_reset.assert_called_once()
    
    def test_air3_toggle(self, command_handler, mock_main_screen):
        """Test AIR3 TOGGLE command"""
        command_handler.parse_cmd(b"AIR3:TOGGLE")
        mock_main_screen.radio_timer_start_stop.assert_called_once()


class TestAir3TimeCommand:
    """Test AIR3TIME command handler"""
    
    def test_air3time_valid(self, command_handler, mock_main_screen):
        """Test AIR3TIME command with valid value"""
        command_handler.parse_cmd(b"AIR3TIME:125")
        mock_main_screen.radio_timer_set.assert_called_once_with(125)
    
    def test_air3time_zero(self, command_handler, mock_main_screen):
        """Test AIR3TIME command with zero"""
        command_handler.parse_cmd(b"AIR3TIME:0")
        mock_main_screen.radio_timer_set.assert_called_once_with(0)
    
    def test_air3time_invalid(self, command_handler, mock_main_screen):
        """Test AIR3TIME command with invalid value"""
        with patch('command_handler.logger') as mock_logger:
            command_handler.parse_cmd(b"AIR3TIME:invalid")
            mock_logger.error.assert_called_once()
            # radio_timer_set should not be called with invalid value
            mock_main_screen.radio_timer_set.assert_not_called()


class TestAir4Command:
    """Test AIR4 command handler"""
    
    def test_air4_off(self, command_handler, mock_main_screen):
        """Test AIR4 OFF command"""
        command_handler.parse_cmd(b"AIR4:OFF")
        mock_main_screen.set_air4.assert_called_once_with(False)
    
    def test_air4_on(self, command_handler, mock_main_screen):
        """Test AIR4 ON command"""
        command_handler.parse_cmd(b"AIR4:ON")
        mock_main_screen.set_air4.assert_called_once_with(True)
    
    def test_air4_reset(self, command_handler, mock_main_screen):
        """Test AIR4 RESET command"""
        command_handler.parse_cmd(b"AIR4:RESET")
        mock_main_screen.stream_timer_reset.assert_called_once()
    
    def test_air4_toggle(self, command_handler, mock_main_screen):
        """Test AIR4 TOGGLE command"""
        command_handler.parse_cmd(b"AIR4:TOGGLE")
        mock_main_screen.start_stop_air4.assert_called_once()


class TestCmdCommand:
    """Test CMD command handler"""
    
    def test_cmd_reboot(self, command_handler, mock_main_screen):
        """Test CMD REBOOT command"""
        command_handler.parse_cmd(b"CMD:REBOOT")
        mock_main_screen.reboot_host.assert_called_once()
    
    def test_cmd_shutdown(self, command_handler, mock_main_screen):
        """Test CMD SHUTDOWN command"""
        command_handler.parse_cmd(b"CMD:SHUTDOWN")
        mock_main_screen.shutdown_host.assert_called_once()
    
    def test_cmd_quit(self, command_handler, mock_main_screen):
        """Test CMD QUIT command"""
        command_handler.parse_cmd(b"CMD:QUIT")
        mock_main_screen.quit_oas.assert_called_once()


class TestConfCommand:
    """Test CONF command handler"""
    
    def test_conf_invalid_format(self, command_handler):
        """Test CONF command with invalid format"""
        result = command_handler.parse_cmd(b"CONF:invalid")
        assert result is False
    
    def test_conf_unknown_group(self, command_handler):
        """Test CONF command with unknown group"""
        with patch('command_handler.logger') as mock_logger:
            result = command_handler.parse_cmd(b"CONF:UnknownGroup:param=value")
            assert result is False
            mock_logger.warning.assert_called_once()


class TestConfGeneral:
    """Test CONF General group handler"""
    
    def test_conf_general_stationname(self, command_handler, mock_main_screen):
        """Test CONF General stationname"""
        command_handler.parse_cmd(b"CONF:General:stationname=New Station")
        mock_main_screen.settings.StationName.setText.assert_called_once_with("New Station")
    
    def test_conf_general_slogan(self, command_handler, mock_main_screen):
        """Test CONF General slogan"""
        command_handler.parse_cmd(b"CONF:General:slogan=New Slogan")
        mock_main_screen.settings.Slogan.setText.assert_called_once_with("New Slogan")
    
    def test_conf_general_stationcolor(self, command_handler, mock_main_screen):
        """Test CONF General stationcolor"""
        command_handler.parse_cmd(b"CONF:General:stationcolor=#FF0000")
        mock_main_screen.settings.getColorFromName.assert_called()
        mock_main_screen.settings.setStationNameColor.assert_called_once()
    
    def test_conf_general_slogancolor(self, command_handler, mock_main_screen):
        """Test CONF General slogancolor"""
        command_handler.parse_cmd(b"CONF:General:slogancolor=#00FF00")
        mock_main_screen.settings.setSloganColor.assert_called_once()
    
    def test_conf_general_replacenow_true(self, command_handler, mock_main_screen):
        """Test CONF General replacenow=True"""
        command_handler.parse_cmd(b"CONF:General:replacenow=True")
        mock_main_screen.settings.replaceNOW.setChecked.assert_called_once_with(True)
    
    def test_conf_general_replacenow_false(self, command_handler, mock_main_screen):
        """Test CONF General replacenow=False"""
        command_handler.parse_cmd(b"CONF:General:replacenow=False")
        mock_main_screen.settings.replaceNOW.setChecked.assert_called_once_with(False)
    
    def test_conf_general_replacenowtext(self, command_handler, mock_main_screen):
        """Test CONF General replacenowtext"""
        command_handler.parse_cmd(b"CONF:General:replacenowtext=Replacement Text")
        mock_main_screen.settings.replaceNOWText.setText.assert_called_once_with("Replacement Text")


class TestConfLed:
    """Test CONF LED group handler"""
    
    def test_conf_led1_used_true(self, command_handler, mock_main_screen):
        """Test CONF LED1 used=True"""
        command_handler.parse_cmd(b"CONF:LED1:used=True")
        mock_main_screen.settings.LED1.setChecked.assert_called_once_with(True)
    
    def test_conf_led1_text(self, command_handler, mock_main_screen):
        """Test CONF LED1 text"""
        command_handler.parse_cmd(b"CONF:LED1:text=ON AIR")
        mock_main_screen.settings.LED1Text.setText.assert_called_once_with("ON AIR")
    
    def test_conf_led2_activebgcolor(self, command_handler, mock_main_screen):
        """Test CONF LED2 activebgcolor"""
        command_handler.parse_cmd(b"CONF:LED2:activebgcolor=#FF0000")
        mock_main_screen.settings.setLED2BGColor.assert_called_once()
    
    def test_conf_led3_activetextcolor(self, command_handler, mock_main_screen):
        """Test CONF LED3 activetextcolor"""
        command_handler.parse_cmd(b"CONF:LED3:activetextcolor=#FFFFFF")
        mock_main_screen.settings.setLED3FGColor.assert_called_once()
    
    def test_conf_led4_autoflash(self, command_handler, mock_main_screen):
        """Test CONF LED4 autoflash"""
        command_handler.parse_cmd(b"CONF:LED4:autoflash=True")
        mock_main_screen.settings.LED4Autoflash.setChecked.assert_called_once_with(True)
    
    def test_conf_led1_timedflash(self, command_handler, mock_main_screen):
        """Test CONF LED1 timedflash"""
        command_handler.parse_cmd(b"CONF:LED1:timedflash=False")
        mock_main_screen.settings.LED1Timedflash.setChecked.assert_called_once_with(False)


class TestConfTimers:
    """Test CONF Timers group handler"""
    
    def test_conf_timers_air1_enabled(self, command_handler, mock_main_screen):
        """Test CONF Timers TimerAIR1Enabled"""
        command_handler.parse_cmd(b"CONF:Timers:TimerAIR1Enabled=True")
        mock_main_screen.settings.enableAIR1.setChecked.assert_called_once_with(True)
    
    def test_conf_timers_air2_text(self, command_handler, mock_main_screen):
        """Test CONF Timers TimerAIR2Text"""
        command_handler.parse_cmd(b"CONF:Timers:TimerAIR2Text=Phone")
        mock_main_screen.settings.AIR2Text.setText.assert_called_once_with("Phone")
    
    def test_conf_timers_air3_activebgcolor(self, command_handler, mock_main_screen):
        """Test CONF Timers AIR3activebgcolor"""
        command_handler.parse_cmd(b"CONF:Timers:AIR3activebgcolor=#FF0000")
        mock_main_screen.settings.setAIR3BGColor.assert_called_once()
    
    def test_conf_timers_air4_activetextcolor(self, command_handler, mock_main_screen):
        """Test CONF Timers AIR4activetextcolor"""
        command_handler.parse_cmd(b"CONF:Timers:AIR4activetextcolor=#FFFFFF")
        mock_main_screen.settings.setAIR4FGColor.assert_called_once()
    
    def test_conf_timers_air1_iconpath(self, command_handler, mock_main_screen):
        """Test CONF Timers AIR1iconpath"""
        command_handler.parse_cmd(b"CONF:Timers:AIR1iconpath=/path/to/icon.png")
        mock_main_screen.settings.setAIR1IconPath.assert_called_once_with("/path/to/icon.png")
    
    def test_conf_timers_minwidth(self, command_handler, mock_main_screen):
        """Test CONF Timers TimerAIRMinWidth"""
        command_handler.parse_cmd(b"CONF:Timers:TimerAIRMinWidth=250")
        mock_main_screen.settings.AIRMinWidth.setValue.assert_called_once_with(250)


class TestConfClock:
    """Test CONF Clock group handler"""
    
    def test_conf_clock_digital_true(self, command_handler, mock_main_screen):
        """Test CONF Clock digital=True"""
        command_handler.parse_cmd(b"CONF:Clock:digital=True")
        mock_main_screen.settings.clockDigital.setChecked.assert_called_with(True)
    
    def test_conf_clock_showseconds_true(self, command_handler, mock_main_screen):
        """Test CONF Clock showseconds=True"""
        command_handler.parse_cmd(b"CONF:Clock:showseconds=True")
        mock_main_screen.settings.showSeconds.setChecked.assert_called_with(True)
    
    def test_conf_clock_staticcolon(self, command_handler, mock_main_screen):
        """Test CONF Clock staticcolon"""
        command_handler.parse_cmd(b"CONF:Clock:staticcolon=True")
        mock_main_screen.settings.staticColon.setChecked.assert_called_once_with(True)
    
    def test_conf_clock_digitalhourcolor(self, command_handler, mock_main_screen):
        """Test CONF Clock digitalhourcolor"""
        command_handler.parse_cmd(b"CONF:Clock:digitalhourcolor=#3232FF")
        mock_main_screen.settings.setDigitalHourColor.assert_called_once()
    
    def test_conf_clock_logopath(self, command_handler, mock_main_screen):
        """Test CONF Clock logopath"""
        command_handler.parse_cmd(b"CONF:Clock:logopath=/path/to/logo.png")
        mock_main_screen.settings.setLogoPath.assert_called_once_with("/path/to/logo.png")


class TestConfNetwork:
    """Test CONF Network group handler"""
    
    def test_conf_network_udpport(self, command_handler, mock_main_screen):
        """Test CONF Network udpport"""
        command_handler.parse_cmd(b"CONF:Network:udpport=3310")
        mock_main_screen.settings.udpport.setText.assert_called_once_with("3310")


class TestConfApply:
    """Test CONF APPLY handler"""
    
    def test_conf_apply_true(self, command_handler, mock_main_screen):
        """Test CONF APPLY command"""
        command_handler.parse_cmd(b"CONF:CONF:APPLY=TRUE")
        mock_main_screen.settings.applySettings.assert_called_once()
    
    def test_conf_apply_false(self, command_handler, mock_main_screen):
        """Test CONF APPLY command with FALSE"""
        command_handler.parse_cmd(b"CONF:CONF:APPLY=FALSE")
        mock_main_screen.settings.applySettings.assert_not_called()


class TestColorSetting:
    """Test _handle_color_setting method"""
    
    def test_color_setting_valid_hex(self, command_handler, mock_main_screen):
        """Test color setting with valid hex color"""
        valid_color = QColor(255, 0, 0)
        mock_main_screen.settings.getColorFromName.return_value = valid_color
        
        setter = Mock()
        command_handler._handle_color_setting("#FF0000", setter, "test_color")
        
        setter.assert_called_once()
        assert isinstance(setter.call_args[0][0], QColor)
    
    def test_color_setting_0x_prefix(self, command_handler, mock_main_screen):
        """Test color setting with 0x prefix"""
        valid_color = QColor(255, 0, 0)
        mock_main_screen.settings.getColorFromName.return_value = valid_color
        
        setter = Mock()
        command_handler._handle_color_setting("0xFF0000", setter, "test_color")
        
        mock_main_screen.settings.getColorFromName.assert_called()
        setter.assert_called_once()
    
    def test_color_setting_invalid_fallback(self, command_handler, mock_main_screen):
        """Test color setting with invalid color uses fallback"""
        invalid_color = QColor()
        white_color = QColor(255, 255, 255)
        mock_main_screen.settings.getColorFromName.side_effect = [invalid_color, white_color]
        
        setter = Mock()
        with patch('command_handler.logger') as mock_logger:
            command_handler._handle_color_setting("invalid", setter, "test_color")
            
            mock_logger.warning.assert_called_once()
            setter.assert_called_once()
            # Should use white as fallback
            assert setter.call_args[0][0] == white_color
    
    def test_color_setting_exception_handling(self, command_handler, mock_main_screen):
        """Test color setting exception handling"""
        mock_main_screen.settings.getColorFromName.side_effect = Exception("Test error")
        
        setter = Mock()
        with patch('command_handler.logger') as mock_logger:
            command_handler._handle_color_setting("#FF0000", setter, "test_color")
            
            mock_logger.error.assert_called_once()
            setter.assert_not_called()


class TestInputValidation:
    """Test input validation functions"""
    
    def test_validate_text_input_normal(self):
        """Test validate_text_input with normal text"""
        result = validate_text_input("Hello World", MAX_TEXT_LENGTH, "test")
        assert result == "Hello World"
    
    def test_validate_text_input_control_chars(self):
        """Test validate_text_input removes control characters"""
        text_with_control = "Hello\x00World\x1F"
        result = validate_text_input(text_with_control, MAX_TEXT_LENGTH, "test")
        assert result == "HelloWorld"
        assert "\x00" not in result
        assert "\x1F" not in result
    
    def test_validate_text_input_truncate(self):
        """Test validate_text_input truncates long text"""
        long_text = "A" * (MAX_TEXT_LENGTH + 100)
        result = validate_text_input(long_text, MAX_TEXT_LENGTH, "test")
        assert len(result) == MAX_TEXT_LENGTH
        assert result == "A" * MAX_TEXT_LENGTH
    
    def test_validate_text_input_dangerous_patterns(self):
        """Test validate_text_input removes dangerous patterns"""
        dangerous_text = "Hello <script>alert('xss')</script> World"
        result = validate_text_input(dangerous_text, MAX_TEXT_LENGTH, "test")
        # Dangerous patterns should be removed, but "alert" alone is not dangerous
        assert "<script" not in result.lower()
        # Test with javascript: pattern
        dangerous_text2 = "Hello javascript:alert('xss') World"
        result2 = validate_text_input(dangerous_text2, MAX_TEXT_LENGTH, "test")
        assert "javascript:" not in result2.lower()
    
    def test_validate_text_input_non_string(self):
        """Test validate_text_input converts non-string to string"""
        result = validate_text_input(12345, MAX_TEXT_LENGTH, "test")
        assert isinstance(result, str)
        assert result == "12345"
    
    def test_validate_command_value_now(self):
        """Test validate_command_value for NOW command"""
        result = validate_command_value("Test Song", "NOW")
        assert result == "Test Song"
    
    def test_validate_command_value_next(self):
        """Test validate_command_value for NEXT command"""
        result = validate_command_value("Next Item", "NEXT")
        assert result == "Next Item"
    
    def test_validate_command_value_warn(self):
        """Test validate_command_value for WARN command"""
        result = validate_command_value("Warning Message", "WARN")
        assert result == "Warning Message"
    
    def test_validate_command_value_conf(self):
        """Test validate_command_value for CONF command"""
        long_value = "A" * (MAX_CONFIG_LENGTH + 100)
        result = validate_command_value(long_value, "CONF")
        assert len(result) <= MAX_CONFIG_LENGTH
    
    def test_validate_led_value_on(self):
        """Test validate_led_value with ON"""
        assert validate_led_value("ON") is True
        assert validate_led_value("on") is True
        assert validate_led_value("On") is True
    
    def test_validate_led_value_off(self):
        """Test validate_led_value with OFF"""
        assert validate_led_value("OFF") is True
        assert validate_led_value("off") is True
        assert validate_led_value("Off") is True
    
    def test_validate_led_value_toggle(self):
        """Test validate_led_value with TOGGLE"""
        assert validate_led_value("TOGGLE") is True
        assert validate_led_value("toggle") is True
        assert validate_led_value("Toggle") is True
    
    def test_validate_led_value_invalid(self):
        """Test validate_led_value with invalid values"""
        assert validate_led_value("INVALID") is False
        assert validate_led_value("") is False
        assert validate_led_value("ONN") is False
    
    def test_validate_air_value_air1(self):
        """Test validate_air_value for AIR1"""
        assert validate_air_value("ON", 1) is True
        assert validate_air_value("OFF", 1) is True
        assert validate_air_value("TOGGLE", 1) is True
        assert validate_air_value("RESET", 1) is False
    
    def test_validate_air_value_air2(self):
        """Test validate_air_value for AIR2"""
        assert validate_air_value("ON", 2) is True
        assert validate_air_value("OFF", 2) is True
        assert validate_air_value("TOGGLE", 2) is True
        assert validate_air_value("RESET", 2) is False
    
    def test_validate_air_value_air3(self):
        """Test validate_air_value for AIR3"""
        assert validate_air_value("ON", 3) is True
        assert validate_air_value("OFF", 3) is True
        assert validate_air_value("RESET", 3) is True
        assert validate_air_value("TOGGLE", 3) is True
        assert validate_air_value("INVALID", 3) is False
    
    def test_validate_air_value_air4(self):
        """Test validate_air_value for AIR4"""
        assert validate_air_value("ON", 4) is True
        assert validate_air_value("OFF", 4) is True
        assert validate_air_value("RESET", 4) is True
        assert validate_air_value("TOGGLE", 4) is True
    
    def test_validate_air3time_value_valid(self):
        """Test validate_air3time_value with valid values"""
        assert validate_air3time_value("0") is True
        assert validate_air3time_value("60") is True
        assert validate_air3time_value("3600") is True
        assert validate_air3time_value("86400") is True  # 24 hours
    
    def test_validate_air3time_value_invalid(self):
        """Test validate_air3time_value with invalid values"""
        assert validate_air3time_value("-1") is False
        assert validate_air3time_value("86401") is False  # > 24 hours
        assert validate_air3time_value("abc") is False
        assert validate_air3time_value("") is False
    
    def test_validate_cmd_value_valid(self):
        """Test validate_cmd_value with valid values"""
        assert validate_cmd_value("REBOOT") is True
        assert validate_cmd_value("SHUTDOWN") is True
        assert validate_cmd_value("QUIT") is True
        assert validate_cmd_value("reboot") is True  # Case insensitive
        assert validate_cmd_value("shutdown") is True
    
    def test_validate_cmd_value_invalid(self):
        """Test validate_cmd_value with invalid values"""
        assert validate_cmd_value("INVALID") is False
        assert validate_cmd_value("") is False
        assert validate_cmd_value("RESTART") is False


class TestInputValidationIntegration:
    """Test input validation integration in parse_cmd"""
    
    def test_parse_cmd_now_with_control_chars(self, command_handler, mock_main_screen):
        """Test NOW command with control characters is sanitized"""
        command_handler.parse_cmd(b"NOW:Hello\x00World\x1F")
        # Should be sanitized (control chars removed)
        call_args = mock_main_screen.set_current_song_text.call_args[0][0]
        assert "\x00" not in call_args
        assert "\x1F" not in call_args
    
    def test_parse_cmd_next_long_text_truncated(self, command_handler, mock_main_screen):
        """Test NEXT command with very long text is truncated"""
        long_text = "A" * (MAX_TEXT_LENGTH + 100)
        command_handler.parse_cmd(f"NEXT:{long_text}".encode('utf-8'))
        call_args = mock_main_screen.set_news_text.call_args[0][0]
        assert len(call_args) == MAX_TEXT_LENGTH
    
    def test_parse_cmd_warn_with_dangerous_pattern(self, command_handler, mock_main_screen):
        """Test WARN command with dangerous pattern is sanitized"""
        dangerous_text = "Warning <script>alert('xss')</script>"
        command_handler.parse_cmd(f"WARN:{dangerous_text}".encode('utf-8'))
        call_args = mock_main_screen.add_warning.call_args[0][0]
        assert "<script" not in call_args.lower()
    
    def test_parse_cmd_led_invalid_value(self, command_handler, mock_main_screen):
        """Test LED command with invalid value is rejected"""
        command_handler.parse_cmd(b"LED1:INVALID")
        # Should not call led_logic
        mock_main_screen.led_logic.assert_not_called()
    
    def test_parse_cmd_air3_invalid_value(self, command_handler, mock_main_screen):
        """Test AIR3 command with invalid value is rejected"""
        command_handler.parse_cmd(b"AIR3:INVALID")
        # Should not call any AIR3 methods
        mock_main_screen.start_air3.assert_not_called()
        mock_main_screen.stop_air3.assert_not_called()
        mock_main_screen.radio_timer_reset.assert_not_called()
        mock_main_screen.radio_timer_start_stop.assert_not_called()
    
    def test_parse_cmd_air3time_invalid_value(self, command_handler, mock_main_screen):
        """Test AIR3TIME command with invalid value is rejected"""
        command_handler.parse_cmd(b"AIR3TIME:99999")  # > 86400
        # Should not call radio_timer_set
        mock_main_screen.radio_timer_set.assert_not_called()
    
    def test_parse_cmd_cmd_invalid_value(self, command_handler, mock_main_screen):
        """Test CMD command with invalid value is rejected"""
        command_handler.parse_cmd(b"CMD:INVALID")
        # Should not call any system commands
        mock_main_screen.reboot_host.assert_not_called()
        mock_main_screen.shutdown_host.assert_not_called()
        mock_main_screen.quit_oas.assert_not_called()
    
    def test_parse_cmd_conf_text_sanitized(self, command_handler, mock_main_screen):
        """Test CONF command with text parameter is sanitized"""
        dangerous_text = "Station\x00Name<script>"
        command_handler.parse_cmd(f"CONF:General:stationname={dangerous_text}".encode('utf-8'))
        # Should call setText with sanitized value
        call_args = mock_main_screen.settings.StationName.setText.call_args[0][0]
        assert "\x00" not in call_args
        assert "<script" not in call_args.lower()
    
    def test_parse_cmd_invalid_utf8(self, command_handler, mock_main_screen):
        """Test parse_cmd with invalid UTF-8 encoding"""
        # Invalid UTF-8 sequence
        invalid_utf8 = b'\xff\xfe\x00\x00'
        result = command_handler.parse_cmd(invalid_utf8)
        # Should return False and not crash
        assert result is False

