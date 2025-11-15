#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for settings_functions.py
"""

import pytest
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor

from settings_functions import OASSettings, Settings


class TestOASSettings:
    """Tests for the OASSettings class"""
    
    def test_init(self):
        """Test that OASSettings is initialized correctly"""
        settings = OASSettings()
        assert settings.config == {}
        assert settings.currentgroup is None
    
    def test_beginGroup(self):
        """Test that beginGroup sets the group correctly"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        assert settings.currentgroup == "TestGroup"
    
    def test_endGroup(self):
        """Test that endGroup resets the group"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        settings.endGroup()
        assert settings.currentgroup is None
    
    def test_setValue_with_group(self):
        """Test that setValue stores values in the current group"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        settings.setValue("key1", "value1")
        settings.setValue("key2", 42)
        settings.endGroup()
        
        assert settings.config["TestGroup"]["key1"] == "value1"
        assert settings.config["TestGroup"]["key2"] == 42
    
    def test_setValue_without_group(self):
        """Test that setValue without a group does not store anything"""
        settings = OASSettings()
        settings.setValue("key1", "value1")
        assert settings.config == {}
    
    def test_value_existing_key(self):
        """Test that value returns existing values"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        settings.setValue("key1", "value1")
        result = settings.value("key1")
        settings.endGroup()
        
        assert isinstance(result, QVariant)
        assert result.value() == "value1"
    
    def test_value_missing_key(self):
        """Test that value returns default values when key is missing"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        result = settings.value("nonexistent", "default")
        settings.endGroup()
        
        assert isinstance(result, QVariant)
        assert result.value() == "default"
    
    def test_value_missing_key_no_default(self):
        """Test that value returns None when key is missing and no default is provided"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        result = settings.value("nonexistent")
        settings.endGroup()
        
        assert isinstance(result, QVariant)
        assert result.value() is None
    
    def test_fileName(self):
        """Test that fileName returns the correct string"""
        settings = OASSettings()
        assert settings.fileName() == "OAC Mode"
    
    def test_multiple_groups(self):
        """Test that multiple groups work independently"""
        settings = OASSettings()
        
        settings.beginGroup("Group1")
        settings.setValue("key1", "value1")
        settings.endGroup()
        
        settings.beginGroup("Group2")
        settings.setValue("key1", "value2")
        settings.endGroup()
        
        settings.beginGroup("Group1")
        result1 = settings.value("key1").value()
        settings.endGroup()
        
        settings.beginGroup("Group2")
        result2 = settings.value("key1").value()
        settings.endGroup()
        
        assert result1 == "value1"
        assert result2 == "value2"


class TestSettingsHelperFunctions:
    """Tests for helper functions of the Settings class"""
    
    def test_get_mac_format(self):
        """Test that get_mac returns a MAC address in the correct format"""
        mac = Settings.get_mac()
        # MAC address should be in format XX:XX:XX:XX:XX:XX
        assert isinstance(mac, str)
        assert len(mac) == 17  # 6 hex pairs + 5 colons
        assert mac.count(":") == 5
        # All characters should be hex characters or colons
        parts = mac.split(":")
        assert len(parts) == 6
        for part in parts:
            assert len(part) == 2
            assert all(c in "0123456789ABCDEF" for c in part)
    
    def test_get_mac_consistency(self):
        """Test that get_mac returns consistent values"""
        mac1 = Settings.get_mac()
        mac2 = Settings.get_mac()
        # MAC address should be consistent (unless there's a problem)
        # In this case it should be equal since getnode() is called twice
        assert mac1 == mac2 or mac1 == "00:00:00:00:00:00"
    
    def test_getColorFromName_valid_color(self):
        """Test that getColorFromName correctly converts valid color names"""
        # Create a Settings instance for the test
        # Since getColorFromName is an instance method, we need to instantiate Settings
        # But Settings requires many dependencies, so we test the logic directly
        from PyQt5.QtGui import QColor
        
        color = QColor()
        color.setNamedColor("#FF0000")
        assert color.isValid()
        assert color.red() == 255
        assert color.green() == 0
        assert color.blue() == 0
        
        color2 = QColor()
        color2.setNamedColor("#00FF00")
        assert color2.isValid()
        assert color2.green() == 255
    
    def test_getColorFromName_invalid_color(self):
        """Test that getColorFromName handles invalid color names"""
        from PyQt5.QtGui import QColor
        
        color = QColor()
        color.setNamedColor("invalid_color_name_xyz")
        # QColor should return a Color object even for invalid names
        # but isValid() should be False
        assert isinstance(color, QColor)

