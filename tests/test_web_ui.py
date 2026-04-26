#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Web-UI and API endpoints
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, mock_open
from PyQt6.QtWidgets import QApplication

# Import after QApplication setup
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from network import OASHTTPRequestHandler
from start import MainScreen


@pytest.fixture
def mock_main_screen():
    """Create a mock MainScreen instance for testing"""
    with patch('ntp_manager.CheckNTPOffsetThread.__del__'):
        with patch('start.Settings'):
            with patch('start.Ui_MainScreen'):
                screen = MainScreen.__new__(MainScreen)
                # Mock attributes needed for get_status_json
                # Use LED{num}on for logical status (not statusLED{num} which is visual)
                screen.LED1on = False
                screen.LED2on = True
                screen.LED3on = False
                screen.LED4on = True
                screen.statusAIR1 = True
                screen.statusAIR2 = False
                screen.statusAIR3 = True
                screen.statusAIR4 = False
                screen.Air1Seconds = 125
                screen.Air2Seconds = 0
                screen.Air3Seconds = 3600
                screen.Air4Seconds = 45
                screen.labelCurrentSong = Mock()
                screen.labelCurrentSong.text.return_value = "Current Song"
                screen.labelNews = Mock()
                screen.labelNews.text.return_value = "Next Item"
                screen.labelWarning = Mock()
                screen.labelWarning.text.return_value = "Warning Message"
                # Mock settings for autoflash access
                screen.settings = Mock()
                for i in range(1, 5):
                    autoflash_attr = f'LED{i}Autoflash'
                    setattr(screen.settings, autoflash_attr, Mock())
                    getattr(screen.settings, autoflash_attr).isChecked.return_value = False
                return screen


@pytest.fixture
def mock_handler():
    """Create a mock HTTP request handler"""
    handler = OASHTTPRequestHandler.__new__(OASHTTPRequestHandler)
    handler.path = ""
    handler.wfile = Mock()
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.send_error = Mock()
    handler.end_headers = Mock()
    handler.address_string = Mock(return_value="127.0.0.1")
    return handler


class TestAPIStatus:
    """Tests for /api/status endpoint"""
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_api_status_success(self, mock_settings_group, mock_qsettings, mock_handler, mock_main_screen):
        """Test /api/status returns correct JSON structure"""
        # Setup mocks for QSettings
        mock_settings = Mock()
        def settings_value_side_effect(key, default=None, **kwargs):
            if key == 'text':
                return 'LED1'  # Simplified for test
            elif 'TimerAIR' in str(key):
                return {
                    'TimerAIR1Text': 'Mic',
                    'TimerAIR2Text': 'Phone',
                    'TimerAIR3Text': 'Radio',
                    'TimerAIR4Text': 'Stream'
                }.get(key, default)
            return default
        
        mock_settings.value.side_effect = settings_value_side_effect
        mock_qsettings.return_value = mock_settings
        
        # Mock settings_group context manager
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        # Set main_screen
        OASHTTPRequestHandler.main_screen = mock_main_screen
        
        handler = mock_handler
        handler.path = "/api/status"
        
        handler.do_GET()
        
        # Verify response
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call('Content-type', 'application/json; charset=utf-8')
        handler.send_header.assert_any_call('Access-Control-Allow-Origin', '*')
        handler.end_headers.assert_called_once()
        
        # Verify JSON was written
        assert handler.wfile.write.called
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list if isinstance(call[0][0], bytes))
        status_data = json.loads(written_data.decode('utf-8'))
        
        # Verify structure
        assert 'leds' in status_data
        assert 'air' in status_data
        assert 'texts' in status_data
        assert 'version' in status_data
        assert 'distribution' in status_data
        
        # Verify all LEDs are present (JSON serializes integer keys as strings)
        for i in range(1, 5):
            assert str(i) in status_data['leds']
            assert 'status' in status_data['leds'][str(i)]
            assert 'text' in status_data['leds'][str(i)]
        
        # Verify all AIR timers are present (JSON serializes integer keys as strings)
        for i in range(1, 5):
            assert str(i) in status_data['air']
            assert 'status' in status_data['air'][str(i)]
            assert 'seconds' in status_data['air'][str(i)]
            assert 'text' in status_data['air'][str(i)]
        
        # Verify text data
        assert status_data['texts']['now'] == "Current Song"
        assert status_data['texts']['next'] == "Next Item"
        assert status_data['texts']['warn'] == "Warning Message"
    
    def test_api_status_no_main_screen(self, mock_handler):
        """Test /api/status returns 503 when main_screen is not available"""
        OASHTTPRequestHandler.main_screen = None
        
        handler = mock_handler
        handler.path = "/api/status"
        
        handler.do_GET()
        
        handler.send_error.assert_called_once_with(503, 'MainScreen not available')


class TestAPICommand:
    """Tests for /api/command endpoint"""
    
    def test_api_command_success_with_signal(self, mock_handler):
        """Test /api/command successfully processes command with signal"""
        mock_signal = Mock()
        mock_signal.command_received = Mock()
        OASHTTPRequestHandler.command_signal = mock_signal
        
        handler = mock_handler
        handler.path = "/api/command?cmd=LED1:ON"
        
        handler.do_GET()
        
        # Verify response
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call('Content-type', 'application/json; charset=utf-8')
        handler.send_header.assert_any_call('Access-Control-Allow-Origin', '*')
        handler.end_headers.assert_called_once()
        
        # Verify signal was emitted
        mock_signal.command_received.emit.assert_called_once()
        assert mock_signal.command_received.emit.call_args[0][0] == b"LED1:ON"
        assert mock_signal.command_received.emit.call_args[0][1] == "http"
        
        # Verify JSON response
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list if isinstance(call[0][0], bytes))
        response_data = json.loads(written_data.decode('utf-8'))
        assert response_data['status'] == 'ok'
        assert response_data['command'] == 'LED1:ON'
    
    def test_api_command_missing_cmd(self, mock_handler):
        """Test /api/command returns 400 when cmd parameter is missing"""
        handler = mock_handler
        handler.path = "/api/command"
        
        handler.do_GET()
        
        handler.send_error.assert_called_once_with(400, 'Missing cmd parameter')
    
    def test_api_command_empty_cmd(self, mock_handler):
        """Test /api/command returns 400 when cmd is empty"""
        handler = mock_handler
        handler.path = "/api/command?cmd="
        
        handler.do_GET()
        
        handler.send_error.assert_called_once_with(400, 'Empty command')
    
    @patch('network.socket')
    @patch('network.QSettings')
    def test_api_command_fallback_to_udp(self, mock_qsettings, mock_socket_module, mock_handler):
        """Test /api/command falls back to UDP when signal is not available"""
        OASHTTPRequestHandler.command_signal = None
        
        mock_settings = Mock()
        mock_settings.value.return_value = "3310"
        mock_qsettings.return_value = mock_settings
        
        mock_sock = Mock()
        mock_socket_module.socket.return_value = mock_sock
        
        handler = mock_handler
        handler.path = "/api/command?cmd=LED2:OFF"
        
        handler.do_GET()
        
        # Verify UDP fallback
        mock_socket_module.socket.assert_called_once()
        mock_sock.sendto.assert_called_once()
        assert b"LED2:OFF" in mock_sock.sendto.call_args[0][0]
        
        # Verify JSON response with method
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list if isinstance(call[0][0], bytes))
        response_data = json.loads(written_data.decode('utf-8'))
        assert response_data['status'] == 'ok'
        assert response_data['method'] == 'udp_fallback'


class TestWebUI:
    """Tests for Web-UI endpoint"""
    
    @patch('builtins.open', new_callable=mock_open, read_data="<html><body>Test HTML</body></html>")
    @patch('network.os.path.abspath')
    @patch('network.os.path.dirname')
    @patch('network.os.path.join')
    def test_web_ui_serves_html(self, mock_join, mock_dirname, mock_abspath, mock_file, mock_handler):
        """Test Web-UI serves HTML content from template file"""
        mock_abspath.return_value = "/path/to/network.py"
        mock_dirname.return_value = "/path/to"
        mock_join.return_value = "/path/to/templates/web_ui.html"
        
        handler = mock_handler
        handler.path = "/"
        
        handler.do_GET()
        
        # Verify response
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call('Content-type', 'text/html; charset=utf-8')
        handler.send_header.assert_any_call('Access-Control-Allow-Origin', '*')
        handler.end_headers.assert_called_once()
        
        # Verify HTML was written
        assert handler.wfile.write.called
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list if isinstance(call[0][0], bytes))
        assert b"<html>" in written_data
        assert b"Test HTML" in written_data
    
    def test_web_ui_index_html(self, mock_handler):
        """Test /index.html also serves Web-UI"""
        with patch('network.os.path.abspath'):
            with patch('network.os.path.dirname'):
                with patch('network.os.path.join'):
                    with patch('builtins.open', new_callable=mock_open, read_data="<html></html>"):
                        handler = mock_handler
                        handler.path = "/index.html"
                        
                        handler.do_GET()
                        
                        handler.send_response.assert_called_once_with(200)
                        handler.send_header.assert_any_call('Content-type', 'text/html; charset=utf-8')
    
    @patch('network.os.path.abspath')
    @patch('network.os.path.dirname')
    @patch('network.os.path.join')
    def test_web_ui_template_not_found(self, mock_join, mock_dirname, mock_abspath, mock_handler):
        """Test Web-UI returns error when template file is not found"""
        mock_abspath.return_value = "/path/to/network.py"
        mock_dirname.return_value = "/path/to"
        mock_join.return_value = "/path/to/templates/web_ui.html"
        
        handler = mock_handler
        handler.path = "/"
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            handler.do_GET()
        
        # Verify error HTML was written
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list if isinstance(call[0][0], bytes))
        assert b"Error: Web UI template not found" in written_data


class TestGetStatusJSON:
    """Tests for get_status_json method"""
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_get_status_json_structure(self, mock_settings_group, mock_qsettings, mock_main_screen):
        """Test get_status_json returns correct structure"""
        mock_settings = Mock()
        def settings_value_side_effect(key, default=None, **kwargs):
            if key == 'text':
                return 'LED1'
            return {
                'TimerAIR1Text': 'Mic',
                'TimerAIR2Text': 'Phone',
                'TimerAIR3Text': 'Radio',
                'TimerAIR4Text': 'Stream'
            }.get(key, default)
        mock_settings.value.side_effect = settings_value_side_effect
        mock_qsettings.return_value = mock_settings
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        status = MainScreen.get_status_json(mock_main_screen)
        
        # Verify structure
        assert isinstance(status, dict)
        assert 'leds' in status
        assert 'air' in status
        assert 'texts' in status
        assert 'version' in status
        assert 'distribution' in status
        
        # Verify all LEDs are present (keys are integers in Python dict)
        for i in range(1, 5):
            assert i in status['leds']
            assert 'status' in status['leds'][i]
            assert 'text' in status['leds'][i]
        
        # Verify all AIR timers are present
        for i in range(1, 5):
            assert i in status['air']
            assert 'status' in status['air'][i]
            assert 'seconds' in status['air'][i]
            assert 'text' in status['air'][i]
        
        # Verify texts
        assert 'now' in status['texts']
        assert 'next' in status['texts']
        assert 'warn' in status['texts']
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_get_status_json_led_values(self, mock_settings_group, mock_qsettings, mock_main_screen):
        """Test get_status_json returns correct LED values"""
        mock_settings = Mock()
        mock_settings.value.return_value = "LED1"
        mock_qsettings.return_value = mock_settings
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        status = MainScreen.get_status_json(mock_main_screen)
        
        # Keys are integers in Python dict, but JSON serializes them as strings
        assert status['leds'][1]['status'] is False
        assert status['leds'][2]['status'] is True
        assert status['leds'][3]['status'] is False
        assert status['leds'][4]['status'] is True
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_get_status_json_air_values(self, mock_settings_group, mock_qsettings, mock_main_screen):
        """Test get_status_json returns correct AIR timer values"""
        mock_settings = Mock()
        def settings_value_side_effect(key, default=None, **kwargs):
            return {
                'TimerAIR1Text': 'Mic',
                'TimerAIR2Text': 'Phone',
                'TimerAIR3Text': 'Radio',
                'TimerAIR4Text': 'Stream'
            }.get(key, default)
        mock_settings.value.side_effect = settings_value_side_effect
        mock_qsettings.return_value = mock_settings
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        status = MainScreen.get_status_json(mock_main_screen)
        
        # Keys are integers in Python dict
        assert status['air'][1]['status'] is True
        assert status['air'][1]['seconds'] == 125
        assert status['air'][2]['status'] is False
        assert status['air'][2]['seconds'] == 0
        assert status['air'][3]['status'] is True
        assert status['air'][3]['seconds'] == 3600
        assert status['air'][4]['status'] is False
        assert status['air'][4]['seconds'] == 45
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_get_status_json_text_values(self, mock_settings_group, mock_qsettings, mock_main_screen):
        """Test get_status_json returns correct text field values"""
        mock_settings = Mock()
        mock_settings.value.return_value = "default"
        mock_qsettings.return_value = mock_settings
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        status = MainScreen.get_status_json(mock_main_screen)
        
        assert status['texts']['now'] == "Current Song"
        assert status['texts']['next'] == "Next Item"
        assert status['texts']['warn'] == "Warning Message"
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_get_status_json_empty_texts(self, mock_settings_group, mock_qsettings):
        """Test get_status_json handles empty text fields"""
        with patch('ntp_manager.CheckNTPOffsetThread.__del__'):
            with patch('start.Settings'):
                with patch('start.Ui_MainScreen'):
                    screen = MainScreen.__new__(MainScreen)
                    # Use LED{num}on for logical status
                    screen.LED1on = False
                    screen.LED2on = False
                    screen.LED3on = False
                    screen.LED4on = False
                    screen.statusAIR1 = False
                    screen.statusAIR2 = False
                    screen.statusAIR3 = False
                    screen.statusAIR4 = False
                    screen.Air1Seconds = 0
                    screen.Air2Seconds = 0
                    screen.Air3Seconds = 0
                    screen.Air4Seconds = 0
                    screen.labelCurrentSong = Mock()
                    screen.labelCurrentSong.text.return_value = ""
                    screen.labelNews = Mock()
                    screen.labelNews.text.return_value = ""
                    screen.labelWarning = Mock()
                    screen.labelWarning.text.return_value = ""
                    # Mock settings for autoflash access
                    screen.settings = Mock()
                    for i in range(1, 5):
                        autoflash_attr = f'LED{i}Autoflash'
                        setattr(screen.settings, autoflash_attr, Mock())
                        getattr(screen.settings, autoflash_attr).isChecked.return_value = False
        
        mock_settings = Mock()
        mock_settings.value.return_value = "default"
        mock_qsettings.return_value = mock_settings
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        status = MainScreen.get_status_json(screen)
        
        assert status['texts']['now'] == ""
        assert status['texts']['next'] == ""
        assert status['texts']['warn'] == ""


class TestBackwardCompatibility:
    """Tests for backward compatible API endpoints"""
    
    def test_legacy_cmd_endpoint(self, mock_handler):
        """Test legacy /?cmd= endpoint still works"""
        mock_signal = Mock()
        mock_signal.command_received = Mock()
        OASHTTPRequestHandler.command_signal = mock_signal
        
        handler = mock_handler
        handler.path = "/?cmd=LED1:ON"
        
        handler.do_GET()
        
        # Verify signal was emitted
        mock_signal.command_received.emit.assert_called_once()
        assert mock_signal.command_received.emit.call_args[0][0] == b"LED1:ON"
        
        # Verify JSON response
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list if isinstance(call[0][0], bytes))
        response_data = json.loads(written_data.decode('utf-8'))
        assert response_data['status'] == 'ok'
    
    def test_legacy_cmd_endpoint_with_query(self, mock_handler):
        """Test legacy endpoint with query string format"""
        mock_signal = Mock()
        mock_signal.command_received = Mock()
        OASHTTPRequestHandler.command_signal = mock_signal
        
        handler = mock_handler
        handler.path = "/"
        # Simulate parsed_path.query
        from urllib.parse import urlparse
        parsed = urlparse("/?cmd=LED2:OFF")
        handler.path = parsed.path
        handler._parsed_query = parsed.query
        
        # We need to mock the urlparse in do_GET
        with patch('network.urlparse') as mock_parse:
            mock_parse.return_value = parsed
            handler.do_GET()
        
        # Verify signal was emitted
        mock_signal.command_received.emit.assert_called_once()


class TestCORSHeaders:
    """Tests for CORS headers in API responses"""
    
    @patch('start.QSettings')
    @patch('start.settings_group')
    def test_api_status_has_cors_headers(self, mock_settings_group, mock_qsettings, mock_handler, mock_main_screen):
        """Test /api/status includes CORS headers"""
        OASHTTPRequestHandler.main_screen = mock_main_screen
        
        mock_settings = Mock()
        mock_settings.value.return_value = "default"
        mock_qsettings.return_value = mock_settings
        mock_settings_group.return_value.__enter__ = Mock(return_value=mock_settings)
        mock_settings_group.return_value.__exit__ = Mock(return_value=None)
        
        handler = mock_handler
        handler.path = "/api/status"
        
        handler.do_GET()
        
        # Verify CORS header
        calls = [call[0] for call in handler.send_header.call_args_list]
        assert ('Access-Control-Allow-Origin', '*') in calls
    
    def test_api_command_has_cors_headers(self, mock_handler):
        """Test /api/command includes CORS headers"""
        mock_signal = Mock()
        mock_signal.command_received = Mock()
        OASHTTPRequestHandler.command_signal = mock_signal
        
        handler = mock_handler
        handler.path = "/api/command?cmd=LED1:ON"
        
        handler.do_GET()
        
        # Verify CORS header
        calls = [call[0] for call in handler.send_header.call_args_list]
        assert ('Access-Control-Allow-Origin', '*') in calls
    
    def test_web_ui_has_cors_headers(self, mock_handler):
        """Test Web-UI includes CORS headers"""
        with patch('network.os.path.abspath'):
            with patch('network.os.path.dirname'):
                with patch('network.os.path.join'):
                    with patch('builtins.open', new_callable=mock_open, read_data="<html></html>"):
                        handler = mock_handler
                        handler.path = "/"
                        
                        handler.do_GET()
                        
                        # Verify CORS header
                        calls = [call[0] for call in handler.send_header.call_args_list]
                        assert ('Access-Control-Allow-Origin', '*') in calls

