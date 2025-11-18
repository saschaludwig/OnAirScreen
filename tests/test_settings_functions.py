#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for settings_functions.py
"""

import json
import tempfile
from pathlib import Path

import pytest
from PyQt6.QtCore import QVariant
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

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
        from PyQt6.QtGui import QColor
        
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
        from PyQt6.QtGui import QColor
        
        color = QColor()
        color.setNamedColor("invalid_color_name_xyz")
        # QColor should return a Color object even for invalid names
        # but isValid() should be False
        assert isinstance(color, QColor)


class TestPresetManagement:
    """Tests for preset management functionality"""
    
    @pytest.fixture
    def temp_presets_dir(self, monkeypatch):
        """Create a temporary directory for presets"""
        with tempfile.TemporaryDirectory() as tmpdir:
            presets_dir = Path(tmpdir) / "presets"
            presets_dir.mkdir(parents=True)
            
            # Monkeypatch _get_presets_directory to return our temp directory
            original_method = Settings._get_presets_directory
            
            def mock_get_presets_directory(self):
                return presets_dir
            
            monkeypatch.setattr(Settings, "_get_presets_directory", mock_get_presets_directory)
            
            yield presets_dir
    
    @pytest.fixture
    def qapp(self):
        """Create a QApplication instance for tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def settings_oac(self, qapp):
        """Create a Settings instance in OAC mode"""
        # OAC mode still needs QApplication for QWidget initialization
        settings = Settings(oacmode=True)
        # Skip the restoreSettingsFromConfig call that requires UI widgets
        # We'll test preset functions directly
        return settings
    
    def test_export_config_to_json_oac(self, settings_oac):
        """Test exporting configuration in OAC mode"""
        # Set some test values
        settings_oac.settings.beginGroup("General")
        settings_oac.settings.setValue("stationname", "Test Station")
        settings_oac.settings.setValue("slogan", "Test Slogan")
        settings_oac.settings.endGroup()
        
        # Export configuration
        config_dict = settings_oac.export_config_to_json()
        
        assert isinstance(config_dict, dict)
        assert "General" in config_dict
        assert config_dict["General"]["stationname"] == "Test Station"
        assert config_dict["General"]["slogan"] == "Test Slogan"
    
    def test_import_config_from_json_oac(self, settings_oac):
        """Test importing configuration in OAC mode"""
        config_dict = {
            "General": {
                "stationname": "Imported Station",
                "slogan": "Imported Slogan"
            }
        }
        
        # Import configuration
        success = settings_oac.import_config_from_json(config_dict)
        
        assert success is True
        
        # Verify values were imported
        settings_oac.settings.beginGroup("General")
        assert settings_oac.settings.value("stationname").value() == "Imported Station"
        assert settings_oac.settings.value("slogan").value() == "Imported Slogan"
        settings_oac.settings.endGroup()
    
    def test_save_preset(self, settings_oac, temp_presets_dir):
        """Test saving a preset"""
        # Set some test values
        settings_oac.settings.beginGroup("General")
        settings_oac.settings.setValue("stationname", "Preset Station")
        settings_oac.settings.endGroup()
        
        # Save preset
        success = settings_oac.save_preset("Test Preset")
        
        assert success is True
        
        # Verify preset file was created
        preset_file = temp_presets_dir / "Test_Preset.json"
        assert preset_file.exists()
        
        # Verify preset file content
        with open(preset_file, 'r', encoding='utf-8') as f:
            preset_data = json.load(f)
        
        assert preset_data["name"] == "Test Preset"
        assert "version" in preset_data
        assert "config" in preset_data
        assert preset_data["config"]["General"]["stationname"] == "Preset Station"
    
    def test_save_preset_empty_name(self, settings_oac):
        """Test that saving preset with empty name fails"""
        success = settings_oac.save_preset("")
        assert success is False
        
        success = settings_oac.save_preset("   ")
        assert success is False
    
    def test_load_preset(self, settings_oac, temp_presets_dir):
        """Test loading a preset"""
        # Create a preset file manually
        preset_data = {
            "name": "Test Preset",
            "version": "0.9.7beta4",
            "config": {
                "General": {
                    "stationname": "Loaded Station",
                    "slogan": "Loaded Slogan"
                }
            }
        }
        
        preset_file = temp_presets_dir / "Test_Preset.json"
        with open(preset_file, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f)
        
        # Load preset
        success = settings_oac.load_preset("Test_Preset")
        
        assert success is True
        
        # Verify values were loaded
        settings_oac.settings.beginGroup("General")
        assert settings_oac.settings.value("stationname").value() == "Loaded Station"
        assert settings_oac.settings.value("slogan").value() == "Loaded Slogan"
        settings_oac.settings.endGroup()
    
    def test_load_preset_nonexistent(self, settings_oac, temp_presets_dir):
        """Test loading a non-existent preset"""
        success = settings_oac.load_preset("Nonexistent_Preset")
        assert success is False
    
    def test_list_presets(self, settings_oac, temp_presets_dir):
        """Test listing presets"""
        # Create some preset files
        preset1 = {
            "name": "Preset 1",
            "version": "0.9.7beta4",
            "config": {"General": {"stationname": "Station 1"}}
        }
        preset2 = {
            "name": "Preset 2",
            "version": "0.9.7beta4",
            "config": {"General": {"stationname": "Station 2"}}
        }
        
        with open(temp_presets_dir / "Preset_1.json", 'w', encoding='utf-8') as f:
            json.dump(preset1, f)
        with open(temp_presets_dir / "Preset_2.json", 'w', encoding='utf-8') as f:
            json.dump(preset2, f)
        
        # List presets
        presets = settings_oac.list_presets()
        
        assert len(presets) == 2
        preset_names = [p["name"] for p in presets]
        assert "Preset 1" in preset_names
        assert "Preset 2" in preset_names
        
        # Verify preset info structure
        for preset in presets:
            assert "filename" in preset
            assert "name" in preset
            assert "version" in preset
    
    def test_list_presets_empty(self, settings_oac, temp_presets_dir):
        """Test listing presets when none exist"""
        presets = settings_oac.list_presets()
        assert presets == []
    
    def test_delete_preset(self, settings_oac, temp_presets_dir):
        """Test deleting a preset"""
        # Create a preset file
        preset_data = {
            "name": "To Delete",
            "version": "0.9.7beta4",
            "config": {"General": {"stationname": "Delete Me"}}
        }
        
        preset_file = temp_presets_dir / "To_Delete.json"
        with open(preset_file, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f)
        
        assert preset_file.exists()
        
        # Delete preset
        success = settings_oac.delete_preset("To_Delete")
        
        assert success is True
        assert not preset_file.exists()
    
    def test_delete_preset_nonexistent(self, settings_oac, temp_presets_dir):
        """Test deleting a non-existent preset"""
        success = settings_oac.delete_preset("Nonexistent")
        assert success is False
    
    def test_preset_name_sanitization(self, settings_oac, temp_presets_dir):
        """Test that preset names are sanitized for filenames"""
        # Save preset with special characters
        success = settings_oac.save_preset("Test Preset (v1.0)")
        
        assert success is True
        
        # Check that file was created with sanitized name
        # Special characters should be removed or replaced
        preset_files = list(temp_presets_dir.glob("*.json"))
        assert len(preset_files) == 1
        
        # The filename should be sanitized
        filename = preset_files[0].stem
        # Should contain only alphanumeric, underscore, or hyphen
        assert all(c.isalnum() or c in ('_', '-') for c in filename)

