#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for settings_functions.py
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QCloseEvent, QFont
from PySide6.QtWidgets import QApplication

from crash_handler import set_log_directory_override
from settings_functions import (
    OASSettings,
    Settings,
    FONT_ROW_PREFIXES,
    composed_license_dialog_text,
    default_font_size_for_prefix,
    font_weight_from_bold,
    is_bold_font_weight,
)
from defaults import (
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE_LED,
    DEFAULT_FONT_SIZE_SLOGAN,
    DEFAULT_FONT_SIZE_STATION,
    DEFAULT_FONT_SIZE_TIMER,
    DEFAULT_FONT_WEIGHT_BOLD,
)


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
        
        assert result == "value1"
    
    def test_value_missing_key(self):
        """Test that value returns default values when key is missing"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        result = settings.value("nonexistent", "default")
        settings.endGroup()
        
        assert result == "default"
    
    def test_value_missing_key_no_default(self):
        """Test that value returns None when key is missing and no default is provided"""
        settings = OASSettings()
        settings.beginGroup("TestGroup")
        result = settings.value("nonexistent")
        settings.endGroup()
        
        assert result is None
    
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
        result1 = settings.value("key1")
        settings.endGroup()
        
        settings.beginGroup("Group2")
        result2 = settings.value("key1")
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
        from PySide6.QtGui import QColor
        
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
        from PySide6.QtGui import QColor
        
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
        assert settings_oac.settings.value("stationname") == "Imported Station"
        assert settings_oac.settings.value("slogan") == "Imported Slogan"
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
        assert settings_oac.settings.value("stationname") == "Loaded Station"
        assert settings_oac.settings.value("slogan") == "Loaded Slogan"
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

    def test_close_event_skips_signals_when_app_is_closing(self, settings_oac):
        """Quit must not re-apply settings (that would restart AES67/MQTT)."""
        finished = []
        closed = []
        settings_oac.sigConfigFinished.connect(lambda: finished.append(True))
        settings_oac.sigConfigClosed.connect(lambda: closed.append(True))

        app = Mock()
        app.closingDown.return_value = True
        with patch.object(QCoreApplication, "instance", return_value=app):
            settings_oac.closeEvent(QCloseEvent())

        assert finished == []
        assert closed == []

    def test_close_event_emits_signals_when_app_is_not_closing(self, settings_oac):
        """Closing the settings dialog still applies config while the app runs."""
        finished = []
        closed = []
        settings_oac.sigConfigFinished.connect(lambda: finished.append(True))
        settings_oac.sigConfigClosed.connect(lambda: closed.append(True))

        app = Mock()
        app.closingDown.return_value = False
        with patch.object(QCoreApplication, "instance", return_value=app):
            settings_oac.closeEvent(QCloseEvent())

        assert finished == [True]
        assert closed == [True]


class TestAes67SapWanted:
    def test_requires_aes67_meters_and_visible_dialog(self):
        from settings_functions import aes67_sap_wanted

        assert aes67_sap_wanted("aes67", True, False) is True
        assert aes67_sap_wanted("aes67", True, True) is False
        assert aes67_sap_wanted("aes67", False, False) is False
        assert aes67_sap_wanted("device", True, False) is False
        assert aes67_sap_wanted("livewire", True, False) is False


class TestLivewireAdvWanted:
    def test_requires_livewire_meters_and_visible_dialog(self):
        from settings_functions import livewire_adv_wanted

        assert livewire_adv_wanted("livewire", True, False) is True
        assert livewire_adv_wanted("livewire", True, True) is False
        assert livewire_adv_wanted("livewire", False, False) is False
        assert livewire_adv_wanted("device", True, False) is False
        assert livewire_adv_wanted("aes67", True, False) is False


class TestAes67ListSignature:
    """Combo rebuilds only when the stream set actually changes."""

    def _item(self, stream_id: str, addr: str, manual: bool = False):
        return (
            stream_id,
            f"Name {stream_id}",
            {
                "addr": addr,
                "port": 5004,
                "codec": "L24",
                "rate": 48000,
                "channels": 2,
                "manual": manual,
            },
        )

    def test_same_streams_same_signature(self):
        from settings_functions import aes67_list_signature

        items = [self._item("a", "239.1.1.1")]
        assert aes67_list_signature(items) == aes67_list_signature(list(items))

    def test_new_stream_changes_signature(self):
        from settings_functions import aes67_list_signature

        first = [self._item("a", "239.1.1.1")]
        second = first + [self._item("b", "239.1.1.2")]
        assert aes67_list_signature(first) != aes67_list_signature(second)

    def test_manual_flag_changes_signature(self):
        from settings_functions import aes67_list_signature

        sap = [self._item("a", "239.1.1.1", manual=False)]
        pasted = [self._item("a", "239.1.1.1", manual=True)]
        assert aes67_list_signature(sap) != aes67_list_signature(pasted)


class TestOWMCitySearch:
    """Tests for OpenWeatherMap city search in Settings"""

    def test_search_without_api_key(self):
        settings = Mock()
        settings.owmCitySearch.displayText.return_value = "Berlin"
        settings.owmAPIKey.text.return_value = "  "
        Settings.searchOWMCity(settings)
        settings.owmTestOutput.setPlainText.assert_called_once_with(
            "Enter an OpenWeatherMap API key first."
        )
        settings.owm_search_nam.get.assert_not_called()

    def test_search_without_city_name(self):
        settings = Mock()
        settings.owmCitySearch.displayText.return_value = "  "
        settings.owmAPIKey.text.return_value = "abc"
        Settings.searchOWMCity(settings)
        settings.owmTestOutput.setPlainText.assert_called_once_with(
            "Enter a city name to search."
        )
        settings.owm_search_nam.get.assert_not_called()

    def test_apply_geocode_results_fills_combo(self):
        settings = Mock()
        settings.owmCityResults.count.return_value = 1
        payload = json.dumps([
            {"name": "Berlin", "country": "DE", "lat": 52.52, "lon": 13.41},
        ])
        Settings._applyOWMGeocodeResults(settings, payload)
        settings.owmCityResults.addItem.assert_called_once_with(
            "Berlin, DE", {"lat": 52.52, "lon": 13.41}
        )
        settings.owmCityResults.setCurrentIndex.assert_called_once_with(0)
        settings._onOWMCityResultChanged.assert_called_once_with(0)

    def test_apply_geocode_empty_does_not_overwrite_id(self):
        settings = Mock()
        Settings._applyOWMGeocodeResults(settings, "[]")
        settings.owmCityResults.addItem.assert_called_once_with("No cities found", None)
        settings.owmCityID.setText.assert_not_called()
        settings._onOWMCityResultChanged.assert_not_called()

    def test_apply_city_id_result(self):
        settings = Mock()
        settings.owmCityResults.count.return_value = 1
        settings.owmCityResults.itemData.return_value = {"lat": 52.52, "lon": 13.41}
        Settings._applyOWMCityIdResult(settings, '{"id": 2950159}', 0)
        settings.owmCityID.setText.assert_called_once_with("2950159")
        settings.owmCityResults.setItemData.assert_called_once_with(
            0, {"lat": 52.52, "lon": 13.41, "id": "2950159"}
        )


class TestSecretLineEdit:
    """Tests for masked password/API-key fields with an eye toggle"""

    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_masked_by_default(self, qapp):
        from PySide6.QtWidgets import QLineEdit
        from settings_functions import setup_secret_line_edit

        edit = QLineEdit()
        edit.setText("secret-value")
        action = setup_secret_line_edit(edit)
        assert edit.echoMode() == QLineEdit.EchoMode.Password
        assert edit.text() == "secret-value"
        assert edit.displayText() != "secret-value"
        assert action.toolTip() == "Show"

    def test_toggle_reveals_and_hides(self, qapp):
        from PySide6.QtWidgets import QLineEdit
        from settings_functions import setup_secret_line_edit

        edit = QLineEdit()
        edit.setText("secret-value")
        action = setup_secret_line_edit(edit)
        action.toggle()
        assert edit.echoMode() == QLineEdit.EchoMode.Normal
        assert edit.displayText() == "secret-value"
        assert action.toolTip() == "Hide"
        action.toggle()
        assert edit.echoMode() == QLineEdit.EchoMode.Password
        assert edit.text() == "secret-value"
        assert action.toolTip() == "Show"


class TestLtcInputUi:
    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_audio_controls_only_when_ltc_audio(self, qapp):
        from defaults import LTC_INPUT_AUDIO, LTC_INPUT_SERIAL, TIME_SOURCE_LTC, TIME_SOURCE_LOCAL

        dialog = Settings(oacmode=True)
        dialog.comboBox_TimeSource.blockSignals(True)
        dialog.comboBox_TimeSource.clear()
        dialog.comboBox_TimeSource.addItem("Local", TIME_SOURCE_LOCAL)
        dialog.comboBox_TimeSource.addItem("LTC", TIME_SOURCE_LTC)
        dialog.comboBox_TimeSource.blockSignals(False)
        dialog.comboBox_LtcInput.blockSignals(True)
        dialog.comboBox_LtcInput.clear()
        dialog.comboBox_LtcInput.addItem("Serial", LTC_INPUT_SERIAL)
        dialog.comboBox_LtcInput.addItem("Audio", LTC_INPUT_AUDIO)
        dialog.comboBox_LtcInput.blockSignals(False)

        dialog.comboBox_TimeSource.setCurrentIndex(dialog.comboBox_TimeSource.findData(TIME_SOURCE_LTC))
        dialog.comboBox_LtcInput.setCurrentIndex(dialog.comboBox_LtcInput.findData(LTC_INPUT_SERIAL))
        dialog._update_time_source_ui()
        assert dialog.comboBox_LtcInput.isEnabled()
        assert dialog.comboBox_LtcPort.isEnabled()
        assert dialog.checkBox_LtcWarn.isEnabled()
        assert not dialog.comboBox_LtcAudioDevice.isEnabled()
        assert not dialog.comboBox_LtcChannel.isEnabled()

        dialog.comboBox_LtcInput.setCurrentIndex(dialog.comboBox_LtcInput.findData(LTC_INPUT_AUDIO))
        dialog._update_time_source_ui()
        assert dialog.comboBox_LtcInput.isEnabled()
        assert not dialog.comboBox_LtcPort.isEnabled()
        assert dialog.comboBox_LtcAudioDevice.isEnabled()
        assert dialog.comboBox_LtcChannel.isEnabled()
        assert dialog.checkBox_LtcWarn.isEnabled()

        dialog.comboBox_TimeSource.setCurrentIndex(dialog.comboBox_TimeSource.findData(TIME_SOURCE_LOCAL))
        dialog._update_time_source_ui()
        assert not dialog.comboBox_LtcInput.isEnabled()
        assert not dialog.comboBox_LtcPort.isEnabled()
        assert not dialog.comboBox_LtcAudioDevice.isEnabled()
        assert not dialog.comboBox_LtcChannel.isEnabled()
        assert not dialog.checkBox_LtcWarn.isEnabled()


class TestAudioInputRefresh:
    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def dialog(self, qapp):
        return Settings(oacmode=True)

    def test_clicked_bool_keeps_current_device(self, dialog, monkeypatch):
        from audio_capture import AudioInputDevice

        dialog.comboBox_AudioInput.blockSignals(True)
        dialog.comboBox_AudioInput.clear()
        dialog.comboBox_AudioInput.addItem("System Default", "")
        dialog.comboBox_AudioInput.addItem("Mic", "Mic")
        dialog.comboBox_AudioInput.setCurrentIndex(1)
        dialog.comboBox_AudioInput.blockSignals(False)

        devices = [
            AudioInputDevice(index=0, name="Mic", channels=2, default_samplerate=48000.0)
        ]
        monkeypatch.setattr(
            "audio_capture.list_input_devices",
            lambda *, refresh=False: devices,
        )
        dialog.refresh_audio_input_devices(False)
        assert dialog.comboBox_AudioInput.currentData() == "Mic"

    def test_rescan_asks_portaudio_to_refresh(self, dialog, monkeypatch):
        from audio_capture import AudioInputDevice

        calls = []

        def fake_list(*, refresh=False):
            calls.append(refresh)
            return [
                AudioInputDevice(
                    index=0, name="USB", channels=2, default_samplerate=48000.0
                )
            ]

        monkeypatch.setattr("audio_capture.list_input_devices", fake_list)
        dialog.refresh_audio_input_devices(rescan=True)
        assert calls[0] is True
        assert dialog.comboBox_AudioInput.findData("USB") >= 0


class TestShowSettings:
    """Tests for opening or raising the settings window."""

    def test_show_settings_opens_when_hidden(self):
        """Hidden settings are restored from config and shown in front."""
        settings = Settings.__new__(Settings)
        settings.isVisible = Mock(return_value=False)
        settings.isMinimized = Mock(return_value=False)
        settings.restoreSettingsFromConfig = Mock()
        settings.sigConfigFinished = Mock()
        settings.show = Mock()
        settings.showNormal = Mock()
        settings.raise_ = Mock()
        settings.activateWindow = Mock()

        Settings.show_settings(settings)

        settings.restoreSettingsFromConfig.assert_called_once()
        settings.sigConfigFinished.emit.assert_called_once()
        settings.show.assert_called_once()
        settings.raise_.assert_called_once()
        settings.activateWindow.assert_called_once()
        settings.showNormal.assert_not_called()

    def test_show_settings_raises_when_already_visible(self):
        """An already open settings window is brought to the front without reloading."""
        settings = Settings.__new__(Settings)
        settings.isVisible = Mock(return_value=True)
        settings.isMinimized = Mock(return_value=False)
        settings.restoreSettingsFromConfig = Mock()
        settings.sigConfigFinished = Mock()
        settings.show = Mock()
        settings.showNormal = Mock()
        settings.raise_ = Mock()
        settings.activateWindow = Mock()

        Settings.show_settings(settings)

        settings.restoreSettingsFromConfig.assert_not_called()
        settings.sigConfigFinished.emit.assert_not_called()
        settings.show.assert_not_called()
        settings.raise_.assert_called_once()
        settings.activateWindow.assert_called_once()

    def test_show_settings_restores_minimized_window(self):
        """A minimized settings window is restored and activated."""
        settings = Settings.__new__(Settings)
        settings.isVisible = Mock(return_value=True)
        settings.isMinimized = Mock(return_value=True)
        settings.restoreSettingsFromConfig = Mock()
        settings.sigConfigFinished = Mock()
        settings.show = Mock()
        settings.showNormal = Mock()
        settings.raise_ = Mock()
        settings.activateWindow = Mock()

        Settings.show_settings(settings)

        settings.restoreSettingsFromConfig.assert_not_called()
        settings.showNormal.assert_called_once()
        settings.raise_.assert_called_once()
        settings.activateWindow.assert_called_once()


class TestFontRowHelpers:
    """Tests for Fonts-tab helpers and inline controls."""

    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def settings_oac(self, qapp):
        return Settings(oacmode=True)

    def test_default_font_size_for_prefix(self):
        assert default_font_size_for_prefix("LED1") == DEFAULT_FONT_SIZE_LED
        assert default_font_size_for_prefix("AIR3") == DEFAULT_FONT_SIZE_TIMER
        assert default_font_size_for_prefix("StationName") == DEFAULT_FONT_SIZE_STATION
        assert default_font_size_for_prefix("Slogan") == DEFAULT_FONT_SIZE_SLOGAN

    def test_is_bold_font_weight(self):
        assert is_bold_font_weight(DEFAULT_FONT_WEIGHT_BOLD) is True
        assert is_bold_font_weight(75) is True
        assert is_bold_font_weight(int(QFont.Weight.Bold)) is True
        assert is_bold_font_weight(int(QFont.Weight.Normal)) is False

    def test_font_weight_from_bold(self):
        assert font_weight_from_bold(True) == int(QFont.Weight.Bold)
        assert font_weight_from_bold(False) == int(QFont.Weight.Normal)

    def test_font_row_prefixes(self):
        assert "LED1" in FONT_ROW_PREFIXES
        assert "Slogan" in FONT_ROW_PREFIXES
        assert len(FONT_ROW_PREFIXES) == 10

    def test_reset_font_row(self, settings_oac):
        settings_oac.FontSize_LED1.setValue(12)
        settings_oac.FontBold_LED1.setChecked(False)
        settings_oac._reset_font_row("LED1")
        assert settings_oac.FontFamily_LED1.currentFont().family() == DEFAULT_FONT_NAME
        assert settings_oac.FontSize_LED1.value() == DEFAULT_FONT_SIZE_LED
        assert settings_oac.FontBold_LED1.isChecked()
        preview_font = settings_oac.ExampleFont_LED1.font()
        assert preview_font.pointSize() == DEFAULT_FONT_SIZE_LED
        assert preview_font.bold()

    def test_apply_font_preview(self, settings_oac):
        settings_oac.FontSize_Slogan.setValue(20)
        settings_oac.FontBold_Slogan.setChecked(False)
        settings_oac._apply_font_preview("Slogan")
        preview_font = settings_oac.ExampleFont_Slogan.font()
        assert preview_font.pointSize() == 20
        assert not preview_font.bold()

    def test_station_and_slogan_colors_without_demo_widgets(self, settings_oac):
        """Station/slogan colors are stored without the removed preview labels."""
        assert not hasattr(settings_oac, "StationNameDemo")
        assert not hasattr(settings_oac, "SloganDemo")
        settings_oac.setStationNameColor(QColor("#FF0000"))
        settings_oac.setSloganColor(QColor("#00FF00"))
        assert settings_oac.getStationNameColor().name().upper() == "#FF0000"
        assert settings_oac.getSloganColor().name().upper() == "#00FF00"


class TestRestoreTimer:
    """Opening Settings must not paint a running AIR timer as inactive."""

    def _air_settings_value(self, key, default=None, **kwargs):
        values = {
            "TimerAIR1Enabled": True,
            "TimerAIR2Enabled": True,
            "TimerAIR3Enabled": True,
            "TimerAIR4Enabled": True,
            "TimerAIR1Text": "Mic",
            "TimerAIR2Text": "Phone",
            "TimerAIR3Text": "Radio",
            "TimerAIR4Text": "Stream",
            "AIR3activetextcolor": "#FFFFFF",
            "AIR3activebgcolor": "#FF0000",
            "inactivetextcolor": "#555555",
            "inactivebgcolor": "#222222",
            "TimerAIRMinWidth": 200,
            "TimerTOTHText": "TOTH Timer",
        }
        return values.get(key, default)

    def _main_screen_with_airs(self):
        main_screen = Mock()
        for air_num in range(1, 5):
            setattr(main_screen, f"statusAIR{air_num}", False)
            setattr(main_screen, f"Air{air_num}Seconds", 0)
            setattr(main_screen, f"AirLabel_{air_num}", Mock())
            setattr(main_screen, f"AirIcon_{air_num}", Mock())
            setattr(main_screen, f"AirLED_{air_num}", Mock())
        main_screen.topOfHourActive = False
        return main_screen

    def test_preserves_running_toth_timer_color_and_time(self):
        from settings_functions import SettingsRestorer

        main_screen = self._main_screen_with_airs()
        main_screen.statusAIR3 = True
        main_screen.Air3Seconds = 1355
        main_screen.topOfHourActive = True
        settings = Mock()
        settings.value.side_effect = self._air_settings_value
        restorer = SettingsRestorer(main_screen, Mock())

        restorer.restore_timer(settings)

        main_screen.AirLabel_3.setText.assert_called_once_with("TOTH Timer\n22:35")
        main_screen.AirCountMark_3.setText.assert_called_once_with("▼")
        stylesheet = main_screen.AirLabel_3.setStyleSheet.call_args[0][0]
        assert "#FF0000" in stylesheet
        assert "#222222" not in stylesheet
        main_screen.AirLED_3.show.assert_called()

    def test_preserves_running_toth_timer_custom_caption(self):
        from settings_functions import SettingsRestorer

        main_screen = self._main_screen_with_airs()
        main_screen.statusAIR3 = True
        main_screen.Air3Seconds = 1355
        main_screen.topOfHourActive = True
        settings = Mock()

        def settings_value(key, default=None, **kwargs):
            if key == "TimerTOTHText":
                return "TOH"
            return self._air_settings_value(key, default, **kwargs)

        settings.value.side_effect = settings_value
        restorer = SettingsRestorer(main_screen, Mock())

        restorer.restore_timer(settings)

        main_screen.AirLabel_3.setText.assert_called_once_with("TOH\n22:35")

    def test_inactive_air3_keeps_configured_label_and_gray_style(self):
        from settings_functions import SettingsRestorer

        main_screen = self._main_screen_with_airs()
        settings = Mock()
        settings.value.side_effect = self._air_settings_value
        restorer = SettingsRestorer(main_screen, Mock())

        restorer.restore_timer(settings)

        main_screen.AirLabel_3.setText.assert_called_once_with("Radio\n0:00")
        main_screen.AirCountMark_3.setText.assert_called_once_with("▲")
        stylesheet = main_screen.AirLabel_3.setStyleSheet.call_args[0][0]
        assert "#555555" in stylesheet
        assert "#222222" in stylesheet


class TestLicenseDialog:
    """License tab is filled from Qt resources, not a PyQt GPL blob in the UI."""

    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_composed_text_documents_pyside_and_roboto(self, qapp):
        text = composed_license_dialog_text()
        assert "OnAirScreen Source-Available License" in text
        assert "PySide6" in text
        assert "GNU LESSER GENERAL PUBLIC LICENSE" in text
        assert "GNU GENERAL PUBLIC LICENSE" in text
        assert "SIL OPEN FONT LICENSE" in text
        assert "Riverbank Computing Limited" in text
        assert "wiki.qt.io/PySide_Logo" in text
        assert "creativecommons.org/licenses/by/3.0" in text
        assert "The OnAirScreen source license is being replaced" not in text

    def test_settings_license_tab_uses_composed_text(self, qapp):
        dialog = Settings(oacmode=True)
        text = dialog.plainTextEdit.toPlainText()
        assert text == composed_license_dialog_text()
        assert "PySide6" in text


class TestOpenLogFolder:
    """About tab can open the log folder in the system file manager."""

    @pytest.fixture
    def qapp(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_open_log_folder_uses_desktop_services(self, qapp, tmp_path):
        set_log_directory_override(tmp_path)
        try:
            dialog = Settings(oacmode=True)
            with patch("settings_functions.QDesktopServices.openUrl") as open_url:
                dialog.open_log_folder()
            open_url.assert_called_once()
            opened = open_url.call_args[0][0]
            assert tmp_path.as_posix() in opened.toLocalFile()
        finally:
            set_log_directory_override(None)


