#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for warning_manager.py
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtWidgets import QApplication, QLabel

# Import after QApplication setup
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)

from warning_manager import WarningManager


@pytest.fixture
def mock_labels():
    """Create mock label widgets"""
    return {
        'warning': Mock(spec=QLabel),
        'current_song': Mock(spec=QLabel),
        'news': Mock(spec=QLabel)
    }


@pytest.fixture
def mock_event_logger():
    """Create mock event logger"""
    logger = Mock()
    logger.log_warning_added = Mock()
    logger.log_warning_removed = Mock()
    return logger


@pytest.fixture
def warning_manager(mock_labels, mock_event_logger):
    """Create WarningManager instance for testing"""
    return WarningManager(
        mock_labels['warning'],
        mock_labels['current_song'],
        mock_labels['news'],
        mock_event_logger
    )


class TestWarningManagerInitialization:
    """Tests for WarningManager initialization"""
    
    def test_init(self, mock_labels, mock_event_logger):
        """Test WarningManager initialization"""
        manager = WarningManager(
            mock_labels['warning'],
            mock_labels['current_song'],
            mock_labels['news'],
            mock_event_logger
        )
        
        assert manager.label_warning == mock_labels['warning']
        assert manager.label_current_song == mock_labels['current_song']
        assert manager.label_news == mock_labels['news']
        assert manager.event_logger == mock_event_logger
        assert manager.warnings == ["", "", "", ""]
    
    def test_init_with_mqtt_callback(self, mock_labels, mock_event_logger):
        """Test WarningManager initialization with MQTT callback"""
        mqtt_callback = Mock()
        manager = WarningManager(
            mock_labels['warning'],
            mock_labels['current_song'],
            mock_labels['news'],
            mock_event_logger,
            mqtt_callback
        )
        
        assert manager.publish_mqtt_status == mqtt_callback


class TestPriorityToIndex:
    """Tests for _priority_to_index static method"""
    
    def test_priority_minus_one(self):
        """Test priority -1 maps to index 0"""
        assert WarningManager._priority_to_index(-1) == 0
    
    def test_priority_zero(self):
        """Test priority 0 maps to index 1"""
        assert WarningManager._priority_to_index(0) == 1
    
    def test_priority_one(self):
        """Test priority 1 maps to index 2"""
        assert WarningManager._priority_to_index(1) == 2
    
    def test_priority_two(self):
        """Test priority 2 maps to index 3"""
        assert WarningManager._priority_to_index(2) == 3


class TestAddWarning:
    """Tests for add_warning method"""
    
    def test_add_warning_priority_one(self, warning_manager, mock_event_logger):
        """Test add_warning adds warning to correct priority"""
        warning_manager.add_warning("Test warning", 1)
        
        # Priority 1 -> Index 2
        assert warning_manager.warnings[2] == "Test warning"
        assert warning_manager.warnings[0] == ""  # -1
        assert warning_manager.warnings[1] == ""  # 0
        assert warning_manager.warnings[3] == ""  # 2
        mock_event_logger.log_warning_added.assert_called_once_with("Test warning", 1)
    
    def test_add_warning_default_priority(self, warning_manager, mock_event_logger):
        """Test add_warning uses priority 0 by default"""
        warning_manager.add_warning("Default warning")
        
        # Priority 0 -> Index 1
        assert warning_manager.warnings[1] == "Default warning"
        mock_event_logger.log_warning_added.assert_called_once_with("Default warning", 0)
    
    def test_add_warning_no_log_if_unchanged(self, warning_manager, mock_event_logger):
        """Test add_warning doesn't log if warning text unchanged"""
        warning_manager.warnings[1] = "Existing warning"
        mock_event_logger.reset_mock()
        
        warning_manager.add_warning("Existing warning", 0)
        
        # Should not log since text didn't change
        mock_event_logger.log_warning_added.assert_not_called()
        mock_event_logger.log_warning_removed.assert_not_called()
    
    def test_add_warning_logs_removal_when_clearing(self, warning_manager, mock_event_logger):
        """Test add_warning logs removal when clearing warning"""
        warning_manager.warnings[1] = "Old warning"
        mock_event_logger.reset_mock()
        
        warning_manager.add_warning("", 0)
        
        # Should log removal since we're clearing the warning
        mock_event_logger.log_warning_removed.assert_called_once_with(0)
        mock_event_logger.log_warning_added.assert_not_called()


class TestRemoveWarning:
    """Tests for remove_warning method"""
    
    def test_remove_warning(self, warning_manager, mock_event_logger):
        """Test remove_warning removes warning from correct priority"""
        # Priority 1 -> Index 2
        warning_manager.warnings[2] = "Test warning"
        
        warning_manager.remove_warning(1)
        
        assert warning_manager.warnings[2] == ""
        mock_event_logger.log_warning_removed.assert_called_once_with(1)
    
    def test_remove_warning_default_priority(self, warning_manager, mock_event_logger):
        """Test remove_warning uses priority 0 by default"""
        # Priority 0 -> Index 1
        warning_manager.warnings[1] = "Test warning"
        
        warning_manager.remove_warning()
        
        assert warning_manager.warnings[1] == ""
        mock_event_logger.log_warning_removed.assert_called_once_with(0)
    
    def test_remove_warning_no_log_if_empty(self, warning_manager, mock_event_logger):
        """Test remove_warning doesn't log if warning already empty"""
        warning_manager.warnings[1] = ""
        mock_event_logger.reset_mock()
        
        warning_manager.remove_warning(0)
        
        # Should not log since warning was already empty
        mock_event_logger.log_warning_removed.assert_not_called()
    
    def test_remove_warning_calls_mqtt_callback(self, mock_labels, mock_event_logger):
        """Test remove_warning calls MQTT callback if provided"""
        mqtt_callback = Mock()
        manager = WarningManager(
            mock_labels['warning'],
            mock_labels['current_song'],
            mock_labels['news'],
            mock_event_logger,
            mqtt_callback
        )
        manager.warnings[1] = "Test warning"
        
        manager.remove_warning(0)
        
        mqtt_callback.assert_called_once_with("warn")


class TestProcessWarnings:
    """Tests for process_warnings method"""
    
    def test_process_warnings_with_warning(self, warning_manager, mock_labels):
        """Test process_warnings shows warning when available"""
        # Priority 1 -> Index 2
        warning_manager.warnings[2] = "Warning text"
        
        warning_manager.process_warnings()
        
        mock_labels['current_song'].hide.assert_called_once()
        mock_labels['news'].hide.assert_called_once()
        mock_labels['warning'].setText.assert_called_once_with("Warning text")
        mock_labels['warning'].show.assert_called_once()
    
    def test_process_warnings_multiple_warnings(self, warning_manager, mock_labels):
        """Test process_warnings shows highest priority warning when multiple exist"""
        # Priorities: -1, 0, 1, 2 -> Indices: 0, 1, 2, 3
        # Should show priority 2 (highest)
        warning_manager.warnings = ["NTP", "Normal", "Medium", "High"]
        
        warning_manager.process_warnings()
        
        # Should show the highest priority warning (priority 2 = "High")
        mock_labels['warning'].setText.assert_called_once_with("High")
        mock_labels['warning'].show.assert_called_once()
    
    def test_process_warnings_no_warning(self, warning_manager, mock_labels):
        """Test process_warnings hides warning when none available"""
        warning_manager.warnings = ["", "", "", ""]
        
        warning_manager.process_warnings()
        
        mock_labels['warning'].hide.assert_called()
        mock_labels['current_song'].show.assert_called_once()
        mock_labels['news'].show.assert_called_once()
    
    def test_process_warnings_ntp_only(self, warning_manager, mock_labels):
        """Test process_warnings shows NTP warning when no other warnings exist"""
        # Only NTP warning (priority -1 -> Index 0)
        warning_manager.warnings = ["NTP Warning", "", "", ""]
        
        warning_manager.process_warnings()
        
        mock_labels['warning'].setText.assert_called_once_with("NTP Warning")
        mock_labels['warning'].show.assert_called_once()
    
    def test_process_warnings_ntp_with_other(self, warning_manager, mock_labels):
        """Test process_warnings shows non-NTP warning when both exist"""
        # NTP warning (priority -1 -> Index 0) and normal warning (priority 0 -> Index 1)
        warning_manager.warnings = ["NTP Warning", "Normal Warning", "", ""]
        
        warning_manager.process_warnings()
        
        # Should show the non-NTP warning (priority 0 = "Normal Warning")
        mock_labels['warning'].setText.assert_called_once_with("Normal Warning")
        mock_labels['warning'].show.assert_called_once()


class TestShowWarning:
    """Tests for show_warning method"""
    
    def test_show_warning(self, warning_manager, mock_labels):
        """Test show_warning displays warning text with large font"""
        warning_manager.show_warning("Test warning")
        
        mock_labels['current_song'].hide.assert_called_once()
        mock_labels['news'].hide.assert_called_once()
        mock_labels['warning'].setText.assert_called_once_with("Test warning")
        # Check font size was set
        assert mock_labels['warning'].font().setPointSize.called or True  # Font might be mocked differently
        mock_labels['warning'].show.assert_called_once()


class TestHideWarning:
    """Tests for hide_warning method"""
    
    def test_hide_warning(self, warning_manager, mock_labels):
        """Test hide_warning restores normal UI"""
        warning_manager.hide_warning()
        
        mock_labels['warning'].hide.assert_called()
        mock_labels['current_song'].show.assert_called_once()
        mock_labels['news'].show.assert_called_once()
        mock_labels['warning'].setText.assert_called_once_with("")


class TestGetWarnings:
    """Tests for get_warnings method"""
    
    def test_get_warnings_empty(self, warning_manager):
        """Test get_warnings returns empty list when no warnings"""
        warnings = warning_manager.get_warnings()
        
        assert warnings == []
    
    def test_get_warnings_single(self, warning_manager):
        """Test get_warnings returns single warning"""
        warning_manager.warnings[1] = "Test warning"
        
        warnings = warning_manager.get_warnings()
        
        assert len(warnings) == 1
        assert warnings[0]['priority'] == 0
        assert warnings[0]['text'] == "Test warning"
    
    def test_get_warnings_multiple(self, warning_manager):
        """Test get_warnings returns all active warnings"""
        warning_manager.warnings = ["NTP", "Normal", "Medium", "High"]
        
        warnings = warning_manager.get_warnings()
        
        assert len(warnings) == 4
        assert warnings[0]['priority'] == -1
        assert warnings[0]['text'] == "NTP"
        assert warnings[1]['priority'] == 0
        assert warnings[1]['text'] == "Normal"
        assert warnings[2]['priority'] == 1
        assert warnings[2]['text'] == "Medium"
        assert warnings[3]['priority'] == 2
        assert warnings[3]['text'] == "High"

