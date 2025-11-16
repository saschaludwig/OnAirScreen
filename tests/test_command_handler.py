#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for command_handler.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtGui import QColor

from command_handler import CommandHandler


@pytest.fixture
def mock_main_screen():
    """Create a mock MainScreen instance for testing"""
    main_screen = Mock()
    
    # Mock text setting methods
    main_screen.set_current_song_text = Mock()
    main_screen.set_news_text = Mock()
    
    # Mock LED methods
    main_screen.led_logic = Mock()
    
    # Mock AIR methods
    main_screen.set_air1 = Mock()
    main_screen.set_air2 = Mock()
    main_screen.set_air4 = Mock()
    main_screen.start_air3 = Mock()
    main_screen.stop_air3 = Mock()
    main_screen.radio_timer_reset = Mock()
    main_screen.radio_timer_start_stop = Mock()
    main_screen.radio_timer_set = Mock()
    main_screen.stream_timer_reset = Mock()
    
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
            mock_logger.warning.assert_called_once()


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


class TestWarnCommand:
    """Test WARN command handler"""
    
    def test_warn_add(self, command_handler, mock_main_screen):
        """Test WARN command to add warning"""
        command_handler.parse_cmd(b"WARN:Test Warning")
        mock_main_screen.add_warning.assert_called_once_with("Test Warning", 1)
    
    def test_warn_remove(self, command_handler, mock_main_screen):
        """Test WARN command to remove warning"""
        command_handler.parse_cmd(b"WARN:")
        mock_main_screen.remove_warning.assert_called_once_with(1)
    
    def test_warn_empty_string(self, command_handler, mock_main_screen):
        """Test WARN command with empty string"""
        command_handler.parse_cmd(b"WARN:")
        mock_main_screen.remove_warning.assert_called_once_with(1)


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
        command_handler.parse_cmd(b"AIR2:START")
        mock_main_screen.set_air2.assert_called_once_with(True)
    
    def test_air2_off(self, command_handler, mock_main_screen):
        """Test AIR2 OFF command"""
        command_handler.parse_cmd(b"AIR2:OFF")
        mock_main_screen.set_air2.assert_called_once_with(False)


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

