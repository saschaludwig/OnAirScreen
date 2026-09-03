#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for osc_server.py
"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication

import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from osc_server import (
    OscDaemon,
    OSC_PREFIX,
    is_query_address,
    iter_status_messages,
    map_osc_to_command,
    osc_args_to_switch,
)


def sample_status(**overrides):
    """Build a get_status_json()-shaped dict for tests."""
    status = {
        "leds": {
            1: {"status": False, "text": "LED1"},
            2: {"status": True, "text": "LED2"},
            3: {"status": False, "text": "LED3"},
            4: {"status": False, "text": "LED4"},
        },
        "air": {
            1: {"status": False, "seconds": 0, "text": "Mic"},
            2: {"status": False, "seconds": 0, "text": "Phone"},
            3: {"status": True, "seconds": 12, "text": "Radio", "topOfHour": True},
            4: {"status": False, "seconds": 0, "text": "Stream"},
        },
        "texts": {"now": "Song", "next": "Next", "warn": "Alert"},
    }
    status.update(overrides)
    return status


class TestOscArgsToSwitch:
    """OSC argument mapping to ON/OFF/TOGGLE/RESET."""

    def test_no_args_is_toggle(self):
        assert osc_args_to_switch(()) == "TOGGLE"

    def test_int_on_off(self):
        assert osc_args_to_switch((1,)) == "ON"
        assert osc_args_to_switch((0,)) == "OFF"

    def test_float_threshold(self):
        assert osc_args_to_switch((0.5,)) == "ON"
        assert osc_args_to_switch((0.49,)) == "OFF"

    def test_bool(self):
        assert osc_args_to_switch((True,)) == "ON"
        assert osc_args_to_switch((False,)) == "OFF"

    def test_string(self):
        assert osc_args_to_switch(("ON",)) == "ON"
        assert osc_args_to_switch(("off",)) == "OFF"
        assert osc_args_to_switch(("toggle",)) == "TOGGLE"
        assert osc_args_to_switch(("RESET",)) == "RESET"
        assert osc_args_to_switch(("1",)) == "ON"
        assert osc_args_to_switch(("0",)) == "OFF"


class TestMapOscToCommand:
    """Set-address mapping onto COMMAND:VALUE."""

    def test_led_integer(self):
        assert map_osc_to_command("/oas/led1", (1,)) == "LED1:ON"
        assert map_osc_to_command("/oas/led4", (0,)) == "LED4:OFF"

    def test_led_no_args_toggle(self):
        assert map_osc_to_command("/oas/led2", ()) == "LED2:TOGGLE"

    def test_air_and_reset(self):
        assert map_osc_to_command("/oas/air1", (1,)) == "AIR1:ON"
        assert map_osc_to_command("/oas/air3/reset", ()) == "AIR3:RESET"
        assert map_osc_to_command("/oas/air4/reset", ("PRESS",)) == "AIR4:RESET"

    def test_air3_toh_and_time(self):
        assert map_osc_to_command("/oas/air3/toh", (1,)) == "AIR3TOH:ON"
        assert map_osc_to_command("/oas/air3/time", (90,)) == "AIR3TIME:90"
        assert map_osc_to_command("/oas/air3/time", ()) is None

    def test_text_and_command(self):
        assert map_osc_to_command("/oas/text/now", ("Hello",)) == "NOW:Hello"
        assert map_osc_to_command("/oas/text/warn", ("1:Boom",)) == "WARN:1:Boom"
        assert map_osc_to_command("/oas/command", ("LED1:ON",)) == "LED1:ON"

    def test_lufs_integrated(self):
        assert map_osc_to_command("/oas/lufs/integrated", (1,)) == "LUFSI:START"
        assert map_osc_to_command("/oas/lufs/integrated", (0,)) == "LUFSI:STOP"
        assert map_osc_to_command("/oas/lufs/integrated", ()) == "LUFSI:TOGGLE"
        assert map_osc_to_command("/oas/lufs/integrated", ("RESET",)) == "LUFSI:RESET"
        assert map_osc_to_command("/oas/lufs/integrated/reset", ()) == "LUFSI:RESET"
        assert map_osc_to_command("/oas/lufs/integrated/state", ()) is None
        assert map_osc_to_command("/oas/lufs/i", ()) is None
        assert map_osc_to_command("/oas/lufs/lra", ()) is None

    def test_query_addresses_are_not_commands(self):
        assert map_osc_to_command("/oas/led1/state", ()) is None
        assert map_osc_to_command("/oas/status", ()) is None
        assert map_osc_to_command("/unknown", (1,)) is None

    def test_is_query_address(self):
        assert is_query_address("/oas/led1/state")
        assert is_query_address("/oas/status")
        assert is_query_address("/oas/lufs/integrated/state")
        assert is_query_address("/oas/lufs/i")
        assert is_query_address("/oas/lufs/lra")
        assert not is_query_address("/oas/led1")


class TestIterStatusMessages:
    """Status dict to OSC address/value pairs."""

    def test_full_status_includes_companion_types(self):
        messages = dict(iter_status_messages(sample_status()))
        assert messages[f"{OSC_PREFIX}/led1/state"] == 0
        assert messages[f"{OSC_PREFIX}/led2/state"] == 1
        assert messages[f"{OSC_PREFIX}/air3/state"] == 1
        assert messages[f"{OSC_PREFIX}/air3/time"] == 12
        assert messages[f"{OSC_PREFIX}/air3/toh/state"] == 1
        assert messages[f"{OSC_PREFIX}/text/now/state"] == "Song"
        assert messages[f"{OSC_PREFIX}/warning/active"] == 1
        assert messages[f"{OSC_PREFIX}/lufs/integrated/state"] == 0
        assert messages[f"{OSC_PREFIX}/lufs/i"] == ""
        assert messages[f"{OSC_PREFIX}/lufs/lra"] == ""

    def test_lufs_values_are_formatted_strings(self):
        messages = dict(iter_status_messages(sample_status(
            lufsIntegrated=True,
            lufsI=-23.1,
            lra=5.2,
        )))
        assert messages[f"{OSC_PREFIX}/lufs/integrated/state"] == 1
        assert messages[f"{OSC_PREFIX}/lufs/i"] == "-23.1"
        assert messages[f"{OSC_PREFIX}/lufs/lra"] == "5.2"

    def test_specific_lufs_includes_values(self):
        messages = dict(iter_status_messages(sample_status(lufsI=-18.0, lra=7.0), "lufs"))
        assert set(messages) == {
            "/oas/lufs/integrated/state",
            "/oas/lufs/i",
            "/oas/lufs/lra",
        }
        assert messages["/oas/lufs/i"] == "-18.0"

    def test_specific_led_and_text(self):
        messages = iter_status_messages(sample_status(), "led2")
        assert messages == [("/oas/led2/state", 1)]
        warn = dict(iter_status_messages(sample_status(), "warn"))
        assert warn["/oas/text/warn/state"] == "Alert"
        assert warn["/oas/warning/active"] == 1

    def test_query_lufs_addresses_resolve(self):
        daemon = OscDaemon()
        status = sample_status(lufsIntegrated=True, lufsI=-23.1, lra=5.2)
        assert daemon._messages_for_query_address("/oas/lufs/integrated/state", status) == [
            ("/oas/lufs/integrated/state", 1)
        ]
        assert daemon._messages_for_query_address("/oas/lufs/i", status) == [
            ("/oas/lufs/i", "-23.1")
        ]
        assert daemon._messages_for_query_address("/oas/lufs/lra", status) == [
            ("/oas/lufs/lra", "5.2")
        ]


@pytest.fixture
def mock_main_screen():
    """MainScreen mock with command signal and status."""
    main_screen = Mock()
    main_screen.command_handler = Mock()
    main_screen.command_signal = Mock()
    main_screen.command_signal.command_received = Mock()
    main_screen.get_status_json = Mock(return_value=sample_status())
    return main_screen


class TestOscDaemon:
    """OscDaemon command dispatch, push, query, restart."""

    @patch("osc_server.OSC_AVAILABLE", True)
    def test_set_emits_command_signal(self, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon._on_osc_message(("127.0.0.1", 12345), "/oas/led1", 1)
        mock_main_screen.command_signal.command_received.emit.assert_called_once_with(
            b"LED1:ON", "osc"
        )

    @patch("osc_server.OSC_AVAILABLE", True)
    def test_toggle_without_args(self, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon._on_osc_message(("127.0.0.1", 12345), "/oas/air3")
        mock_main_screen.command_signal.command_received.emit.assert_called_once_with(
            b"AIR3:TOGGLE", "osc"
        )

    @patch("osc_server.SimpleUDPClient")
    @patch("osc_server.OSC_AVAILABLE", True)
    def test_push_requires_send_host(self, mock_client_class, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon._applied_settings = {"enableosc": True}
        daemon.send_host = ""
        daemon.send_port = 9000
        daemon.publish_status("led1")
        mock_client_class.assert_not_called()

        daemon.send_host = "192.168.1.10"
        daemon.publish_status("led1")
        mock_client_class.assert_called_once_with("192.168.1.10", 9000)
        mock_client_class.return_value.send_message.assert_called_with("/oas/led1/state", 0)

    @patch("osc_server.SimpleUDPClient")
    @patch("osc_server.OSC_AVAILABLE", True)
    def test_query_replies_to_sender_without_send_host(self, mock_client_class, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon._applied_settings = {"enableosc": True}
        daemon.send_host = ""
        daemon._on_osc_message(("10.0.0.5", 7000), "/oas/led2/state")
        mock_main_screen.command_signal.command_received.emit.assert_not_called()
        mock_client_class.assert_called_once_with("10.0.0.5", 7000)
        mock_client_class.return_value.send_message.assert_called_with("/oas/led2/state", 1)

    @patch("osc_server.SimpleUDPClient")
    @patch("osc_server.OSC_AVAILABLE", True)
    def test_status_query_sends_all(self, mock_client_class, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon._on_osc_message(("10.0.0.5", 7000), "/oas/status")
        sent = [call.args[0] for call in mock_client_class.return_value.send_message.call_args_list]
        assert "/oas/led1/state" in sent
        assert "/oas/air3/toh/state" in sent
        assert "/oas/text/now/state" in sent

    @patch("osc_server.OSC_AVAILABLE", False)
    def test_run_skips_when_library_missing(self, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon.run()
        assert daemon._server is None

    @patch("osc_server.OSC_AVAILABLE", True)
    def test_run_skips_when_disabled(self, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon._read_osc_settings = Mock(return_value={
            "enableosc": False,
            "oscport": 8000,
            "oscsendhost": "",
            "oscsendport": 9000,
        })
        daemon.run()
        assert daemon._server is None

    @patch("osc_server.OSC_AVAILABLE", True)
    def test_restart_skips_when_settings_unchanged(self, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon.stop = Mock()
        daemon.start = Mock()
        daemon.isRunning = Mock(return_value=True)
        snapshot = {
            "enableosc": True,
            "oscport": 8000,
            "oscsendhost": "127.0.0.1",
            "oscsendport": 9000,
        }
        daemon._applied_settings = snapshot
        daemon._read_osc_settings = Mock(return_value=snapshot.copy())
        daemon.restart()
        daemon.stop.assert_not_called()
        daemon.start.assert_not_called()

    @patch("osc_server.OSC_AVAILABLE", True)
    def test_restart_when_settings_changed(self, mock_main_screen):
        daemon = OscDaemon(mock_main_screen)
        daemon.stop = Mock()
        daemon.start = Mock()
        daemon.isRunning = Mock(return_value=False)
        daemon.wait = Mock(return_value=True)
        daemon._applied_settings = {
            "enableosc": False,
            "oscport": 8000,
            "oscsendhost": "",
            "oscsendport": 9000,
        }
        daemon._read_osc_settings = Mock(return_value={
            "enableosc": True,
            "oscport": 8000,
            "oscsendhost": "127.0.0.1",
            "oscsendport": 9000,
        })
        daemon.restart()
        daemon.stop.assert_called_once()
        daemon.start.assert_called_once()
