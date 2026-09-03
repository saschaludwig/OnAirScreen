#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for signal_handlers.py
"""

from unittest.mock import Mock, patch

from signal_handlers import _quit_on_air_screen, sigint_handler


@patch("signal_handlers.QTimer")
def test_sigint_handler_schedules_main_screen_quit(mock_timer):
    """Ctrl+C must not call QApplication.quit() directly."""
    with patch("signal_handlers.QApplication") as mock_qapp:
        sigint_handler()

    mock_timer.singleShot.assert_called_once()
    assert mock_timer.singleShot.call_args[0][0] == 0
    assert mock_timer.singleShot.call_args[0][1] is _quit_on_air_screen
    mock_qapp.quit.assert_not_called()
    mock_qapp.instance.return_value.quit.assert_not_called()


@patch("signal_handlers.QApplication")
def test_quit_on_air_screen_calls_quit_oas(mock_qapp):
    """SIGINT cleanup must go through MainScreen.quit_oas()."""
    screen = Mock()
    other = Mock(spec=[])
    mock_qapp.instance.return_value.topLevelWidgets.return_value = [other, screen]

    _quit_on_air_screen()

    screen.quit_oas.assert_called_once()
    mock_qapp.instance.return_value.quit.assert_not_called()


@patch("signal_handlers.QApplication")
def test_quit_on_air_screen_falls_back_to_app_quit(mock_qapp):
    """If MainScreen is missing, quit the QApplication instance."""
    mock_qapp.instance.return_value.topLevelWidgets.return_value = [Mock(spec=[])]

    _quit_on_air_screen()

    mock_qapp.instance.return_value.quit.assert_called_once()


@patch("signal_handlers.sys")
@patch("signal_handlers.QApplication")
def test_quit_on_air_screen_exits_without_app(mock_qapp, mock_sys):
    """Without a QApplication, SIGINT must still terminate."""
    mock_qapp.instance.return_value = None
    mock_sys.exit.side_effect = SystemExit(1)

    try:
        _quit_on_air_screen()
    except SystemExit:
        pass

    mock_sys.exit.assert_called_once_with(1)
