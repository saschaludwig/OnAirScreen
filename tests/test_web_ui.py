#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Web-UI and API endpoints
"""

import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from PySide6.QtWidgets import QApplication

# Import after QApplication setup
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from defaults import DEFAULT_INSTANCE_NAME
from network import OASHTTPRequestHandler
from start import MainScreen


class _FakeSettings:
    """QSettings stand-in that honours beginGroup/endGroup like the real API."""

    def __init__(self, values=None):
        self._group = ""
        self.values = dict(values or {})

    def beginGroup(self, name):
        self._group = f"{self._group}/{name}" if self._group else name

    def endGroup(self):
        if "/" in self._group:
            self._group = self._group.rsplit("/", 1)[0]
        else:
            self._group = ""

    def value(self, key, default=None, type=None, **kwargs):
        full_key = f"{self._group}/{key}" if self._group else key
        value = self.values.get(full_key, default)
        if type is not None and value is not None:
            return type(value)
        return value


@pytest.fixture(autouse=True)
def isolate_status_settings():
    """Keep StatusExporter off the developer's local OnAirScreen QSettings."""
    fake = _FakeSettings()
    with patch("status_exporter.QSettings", return_value=fake):
        yield fake


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
                screen.topOfHourActive = False
                screen.labelCurrentSong = Mock()
                screen.labelCurrentSong.text.return_value = "Current Song"
                screen.labelNews = Mock()
                screen.labelNews.text.return_value = "Next Item"
                screen.labelWarning = Mock()
                screen.labelWarning.text.return_value = "Warning Message"
                # Mock settings for autoflash/timedflash access
                screen.settings = Mock()
                for i in range(1, 5):
                    for suffix in ('Autoflash', 'Timedflash'):
                        attr = f'LED{i}{suffix}'
                        setattr(screen.settings, attr, Mock())
                        getattr(screen.settings, attr).isChecked.return_value = False
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
    
    def test_api_status_success(self, mock_handler, mock_main_screen):
        """Test /api/status returns correct JSON structure"""
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
        assert 'instance' in status_data
        
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
        assert status_data['silence'] is False
    
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
    
    def test_get_status_json_structure(self, mock_main_screen):
        """Test get_status_json returns correct structure"""
        status = MainScreen.get_status_json(mock_main_screen)
        
        # Verify structure
        assert isinstance(status, dict)
        assert 'leds' in status
        assert 'air' in status
        assert 'texts' in status
        assert 'version' in status
        assert 'distribution' in status
        assert 'instance' in status
        assert status['instance'] == DEFAULT_INSTANCE_NAME
        
        # Verify all LEDs are present (keys are integers in Python dict)
        for i in range(1, 5):
            assert i in status['leds']
            assert 'status' in status['leds'][i]
            assert 'text' in status['leds'][i]
            assert 'autoflash' in status['leds'][i]
            assert 'timedflash' in status['leds'][i]
        
        # Verify all AIR timers are present
        for i in range(1, 5):
            assert i in status['air']
            assert 'status' in status['air'][i]
            assert 'seconds' in status['air'][i]
            assert 'text' in status['air'][i]
            assert 'countDown' in status['air'][i]
        assert status['air'][1]['countDown'] is False
        assert status['air'][2]['countDown'] is False
        assert status['air'][3]['countDown'] is False
        assert status['air'][4]['countDown'] is False
        
        # Verify texts
        assert 'now' in status['texts']
        assert 'next' in status['texts']
        assert 'warn' in status['texts']
        assert 'silence' in status
        assert status['silence'] is False
        assert 'lufsIntegrated' in status
        assert status['lufsIntegrated'] is False
        assert 'lufsI' in status
        assert status['lufsI'] is None
        assert 'lra' in status
        assert status['lra'] is None

    def test_get_status_json_uses_configured_instance_name(
        self, isolate_status_settings, mock_main_screen
    ):
        """Instance name comes from QSettings, not a hardcoded factory default."""
        isolate_status_settings.values["General/instancename"] = "Control-Room-A"
        status = MainScreen.get_status_json(mock_main_screen)
        assert status['instance'] == "Control-Room-A"

    def test_get_status_json_led_values(self, mock_main_screen):
        """Test get_status_json returns correct LED values"""
        status = MainScreen.get_status_json(mock_main_screen)
        
        # Keys are integers in Python dict, but JSON serializes them as strings
        assert status['leds'][1]['status'] is False
        assert status['leds'][2]['status'] is True
        assert status['leds'][3]['status'] is False
        assert status['leds'][4]['status'] is True
        assert status['leds'][1]['autoflash'] is False
        assert status['leds'][1]['timedflash'] is False
    
    def test_get_status_json_led_timedflash(self, mock_main_screen):
        """Test get_status_json reports timedflash when enabled"""
        mock_main_screen.settings.LED4Timedflash.isChecked.return_value = True
        
        status = MainScreen.get_status_json(mock_main_screen)
        
        assert status['leds'][4]['timedflash'] is True
        assert status['leds'][4]['autoflash'] is False
        assert status['leds'][1]['timedflash'] is False
    
    def test_get_status_json_air_values(self, mock_main_screen):
        """Test get_status_json returns correct AIR timer values"""
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
        assert status['air'][1]['countDown'] is False
        assert status['air'][3]['countDown'] is False
        assert status['air'][4]['countDown'] is False
    
    def test_get_status_json_air_countdown(self, mock_main_screen):
        """countDown follows radioTimerMode (AIR3) and streamTimerMode (AIR4)."""
        mock_main_screen.radioTimerMode = 1
        mock_main_screen.streamTimerMode = 1

        status = MainScreen.get_status_json(mock_main_screen)

        assert status['air'][1]['countDown'] is False
        assert status['air'][2]['countDown'] is False
        assert status['air'][3]['countDown'] is True
        assert status['air'][4]['countDown'] is True
    
    def test_get_status_json_text_values(self, mock_main_screen):
        """Test get_status_json returns correct text field values"""
        status = MainScreen.get_status_json(mock_main_screen)
        
        assert status['texts']['now'] == "Current Song"
        assert status['texts']['next'] == "Next Item"
        assert status['texts']['warn'] == "Warning Message"
    
    def test_get_status_json_silence(self, mock_main_screen):
        """Test get_status_json reports the silence boolean independently of WARN text."""
        mock_main_screen._audio_silence_active = True
        mock_main_screen.labelWarning.text.return_value = ""

        status = MainScreen.get_status_json(mock_main_screen)

        assert status['silence'] is True
        assert status['texts']['warn'] == ""

    def test_get_status_json_lufs_i_and_lra(self, mock_main_screen):
        """I and LRA come from the engine snapshot, not the last audio block."""
        capture = Mock()
        capture.integrated_snapshot.return_value = (True, -23.14, -26.0, -20.8)
        mock_main_screen.audio_capture = capture

        status = MainScreen.get_status_json(mock_main_screen)

        assert status['lufsIntegrated'] is True
        assert status['lufsI'] == -23.1
        assert status['lra'] == 5.2

    def test_get_status_json_lufs_silence_is_null(self, mock_main_screen):
        """Silence-floor I/LRA is exported as JSON null."""
        capture = Mock()
        capture.integrated_snapshot.return_value = (False, -120.0, -120.0, -120.0)
        mock_main_screen.audio_capture = capture

        status = MainScreen.get_status_json(mock_main_screen)

        assert status['lufsIntegrated'] is False
        assert status['lufsI'] is None
        assert status['lra'] is None
    
    def test_get_status_json_empty_texts(self):
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
                    screen.topOfHourActive = False
                    screen.labelCurrentSong = Mock()
                    screen.labelCurrentSong.text.return_value = ""
                    screen.labelNews = Mock()
                    screen.labelNews.text.return_value = ""
                    screen.labelWarning = Mock()
                    screen.labelWarning.text.return_value = ""
                    # Mock settings for autoflash/timedflash access
                    screen.settings = Mock()
                    for i in range(1, 5):
                        for suffix in ('Autoflash', 'Timedflash'):
                            attr = f'LED{i}{suffix}'
                            setattr(screen.settings, attr, Mock())
                            getattr(screen.settings, attr).isChecked.return_value = False
        
        status = MainScreen.get_status_json(screen)
        
        assert status['texts']['now'] == ""
        assert status['texts']['next'] == ""
        assert status['texts']['warn'] == ""


class TestLoudnessJsonHelpers:
    """JSON/MQTT/OSC formatting for I and LRA."""

    def test_round_valid_and_null_at_floor(self):
        from status_exporter import json_lra, json_loudness, loudness_payload

        assert json_loudness(-23.14) == -23.1
        assert json_loudness(-120.0) is None
        assert json_lra(-26.0, -20.8) == 5.2
        assert json_lra(-120.0, -120.0) is None
        assert loudness_payload(-23.1) == "-23.1"
        assert loudness_payload(None) == ""


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
    
    def test_api_status_has_cors_headers(self, mock_handler, mock_main_screen):
        """Test /api/status includes CORS headers"""
        OASHTTPRequestHandler.main_screen = mock_main_screen
        
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


class TestWebUIWebSocketRecovery:
    """The Web-UI must return from HTTP polling to WebSocket after a reconnect."""

    @pytest.fixture
    def web_ui_html(self):
        template = Path(__file__).resolve().parent.parent / "templates" / "web_ui.html"
        return template.read_text(encoding="utf-8")

    def test_does_not_permanently_disable_websocket_on_error(self, web_ui_html):
        """A dropped WebSocket must not set a one-way useWebSocket=false flag."""
        assert "useWebSocket = false" not in web_ui_html
        assert "let useWebSocket" not in web_ui_html

    def test_reconnects_websocket_after_polling_fallback(self, web_ui_html):
        """Polling is a fallback; successful HTTP and WS close both retry WebSocket."""
        assert "function tryRestoreWebSocket" in web_ui_html
        assert "function scheduleWebSocketReconnect" in web_ui_html
        assert "function stopPolling" in web_ui_html
        assert "tryRestoreWebSocket();" in web_ui_html
        assert "scheduleWebSocketReconnect();" in web_ui_html
        assert "stopPolling();" in web_ui_html


class TestWebUIInstanceName:
    """The Web-UI must show which OnAirScreen instance is being controlled."""

    @pytest.fixture
    def web_ui_html(self):
        template = Path(__file__).resolve().parent.parent / "templates" / "web_ui.html"
        return template.read_text(encoding="utf-8")

    def test_displays_instance_name(self, web_ui_html):
        """Instance name is shown in the header, version box, and document title."""
        assert 'id="instanceName"' in web_ui_html
        assert 'id="instanceValue"' in web_ui_html
        assert "function applyStatusMeta" in web_ui_html
        assert "data.instance" in web_ui_html
        assert " · OnAirScreen" in web_ui_html


class TestWebUILiveControls:
    """Priority-1 live controls: AIR3 time, silence tile, NOW/NEXT prefill."""

    @pytest.fixture
    def web_ui_html(self):
        template = Path(__file__).resolve().parent.parent / "templates" / "web_ui.html"
        return template.read_text(encoding="utf-8")

    def test_air3_time_input_sends_air3time(self, web_ui_html):
        """AIR3 countdown can be set from the Web-UI as m:ss, m,ss, or seconds."""
        assert 'id="air3TimeInput"' in web_ui_html
        assert "function parseAirTimeToSeconds" in web_ui_html
        assert "function sendAir3Time" in web_ui_html
        assert "AIR3TIME:" in web_ui_html
        assert "MAX_AIR3_SECONDS = 86400" in web_ui_html

    def test_parse_air_time_to_seconds_formats(self, web_ui_html):
        """Parser accepts Companion m:ss, desktop m,ss / m.ss, and raw seconds."""
        start = web_ui_html.index("const MAX_AIR3_SECONDS")
        end = web_ui_html.index("function sendAir3Time")
        snippet = web_ui_html[start:end]
        script = snippet + """
        const cases = [
            ['2:05', 125],
            ['2,10', 130],
            ['2.10', 130],
            ['30', 30],
            ['0:00', 0],
            ['86400', 86400],
            ['2:60', null],
            ['86401', null],
            ['', null],
            ['abc', null],
            ['  2:05  ', 125]
        ];
        for (const [input, expected] of cases) {
            const got = parseAirTimeToSeconds(input);
            if (got !== expected) {
                console.error(JSON.stringify({input, expected, got}));
                process.exit(1);
            }
        }
        """
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout

    def test_silence_status_tile_uses_status_boolean(self, web_ui_html):
        """Silence is a status tile driven by data.silence, not a toggle."""
        assert "silenceItem.id = 'silenceStatus'" in web_ui_html
        assert "data.silence === true" in web_ui_html
        assert "silence-active" in web_ui_html
        assert "Silence" in web_ui_html

    def test_loudness_start_stop_uses_lufsi_commands(self, web_ui_html):
        """I+LRA session is started and stopped from the Web UI via LUFSI."""
        assert "function updateLoudnessControls" in web_ui_html
        assert "data.lufsIntegrated === true" in web_ui_html
        assert "sendCommand('LUFSI:START')" in web_ui_html
        assert "sendCommand('LUFSI:STOP')" in web_ui_html
        assert "sendCommand('LUFSI:RESET')" in web_ui_html
        assert 'id="lufsStartBtn"' in web_ui_html
        assert 'id="lufsStopBtn"' in web_ui_html
        assert "lufsItem.id = 'lufsStatus'" in web_ui_html
        assert "Loudness I+LRA" in web_ui_html
        assert "function formatLoudnessValue" in web_ui_html
        assert "formatLoudnessValue(data.lufsI, 'LUFS')" in web_ui_html
        assert "formatLoudnessValue(data.lra, 'LU')" in web_ui_html

    def test_prefill_now_next_skips_dirty_or_focused_inputs(self, web_ui_html):
        """NOW/NEXT inputs follow status unless the operator is editing them."""
        assert "function prefillTextInputs" in web_ui_html
        assert "textInputDirty" in web_ui_html
        assert "document.activeElement === input" in web_ui_html
        assert "textInputDirty.now = true" in web_ui_html
        assert "textInputDirty.next = true" in web_ui_html
        assert "textInputDirty.now = false" in web_ui_html
        assert "textInputDirty.next = false" in web_ui_html
        assert "input.value = '';" not in web_ui_html.split("function sendTextCommand")[1].split(
            "function clearWarning"
        )[0]


class TestWebUIUxExtras:
    """LED hotkeys 1-4, AIR3 count-up/down, persistent connection badge."""

    @pytest.fixture
    def web_ui_html(self):
        template = Path(__file__).resolve().parent.parent / "templates" / "web_ui.html"
        return template.read_text(encoding="utf-8")

    def test_led_hotkeys_ignore_text_fields_and_offline(self, web_ui_html):
        """Keys 1-4 toggle LEDs unless a field is focused or the UI is offline."""
        assert "function toggleLedFromKey" in web_ui_html
        assert "function isEditableTarget" in web_ui_html
        assert "e.key >= '1' && e.key <= '4'" in web_ui_html
        assert "if (connectionErrorShown)" in web_ui_html
        assert "INPUT" in web_ui_html
        assert "TEXTAREA" in web_ui_html
        assert "SELECT" in web_ui_html
        assert "isContentEditable" in web_ui_html

    def test_air3_shows_count_up_versus_countdown(self, web_ui_html):
        """AIR3 status and tooltip distinguish count-up from countdown."""
        assert "air.countDown === true" in web_ui_html
        assert "Countdown" in web_ui_html
        assert "Count-up" in web_ui_html

    def test_connection_badge_has_live_polling_offline(self, web_ui_html):
        """Connection state is always visible; the error modal remains for offline."""
        assert 'id="connectionValue"' in web_ui_html
        assert "function setConnectionState" in web_ui_html
        assert "setConnectionState('live')" in web_ui_html
        assert "setConnectionState('polling')" in web_ui_html
        assert "setConnectionState('offline')" in web_ui_html
        assert "connectionErrorModal" in web_ui_html

    def test_settings_gear_and_overlay(self, web_ui_html):
        assert 'id="settingsGear"' in web_ui_html
        assert 'class="top-right-controls"' in web_ui_html
        assert 'id="settingsOverlay"' in web_ui_html
        assert "function openSettingsOverlay" in web_ui_html
        assert "function initSettingsUi" in web_ui_html
        assert "/api/settings/schema" in web_ui_html
        assert "X-Settings-Token" in web_ui_html
        assert "if (settingsUiOpen)" in web_ui_html
        assert "function applySettingsEnablement" in web_ui_html
        assert "enabledWhen" in web_ui_html
        assert "enabledWhenAny" in web_ui_html
        assert "bbc_ppm" in web_ui_html
        assert "#settingsEditor" in web_ui_html
        assert "min-height: 0" in web_ui_html
        assert ".settings-secret-row input" in web_ui_html
        assert "settings-secret-toggle" in web_ui_html
        assert "if (!isUnchanged && value)" in web_ui_html
        assert "widget === 'livewire_source'" in web_ui_html
        assert "widget === 'aes67_stream'" in web_ui_html
        assert "/api/settings/aoip" in web_ui_html
        assert "Paste SDP" in web_ui_html
        assert "function refreshAoipStreams" in web_ui_html
        assert "function stopAoipDiscoveryPoll" in web_ui_html
        assert "field.hidden" in web_ui_html
