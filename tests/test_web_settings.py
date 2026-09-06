#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the web settings API."""

import json
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import sys

if not QApplication.instance():
    QApplication(sys.argv)

from network import OASHTTPRequestHandler
from web_settings import (
    UNCHANGED_SENTINEL,
    apply_web_config,
    authenticate_web_settings_pin,
    export_config_dict,
    field_is_enabled,
    get_web_config,
    hash_web_settings_pin,
    iter_schema_fields,
    list_web_presets,
    load_web_preset,
    save_web_preset,
    schema_as_json,
    session_store,
    SettingsApiError,
    verify_web_settings_pin,
    web_settings_pin_required,
)


@pytest.fixture
def ini_settings(tmp_path):
    settings = QSettings(str(tmp_path / "OnAirScreen.ini"), QSettings.Format.IniFormat)
    yield settings
    settings.sync()


@pytest.fixture
def handler():
    request_handler = OASHTTPRequestHandler.__new__(OASHTTPRequestHandler)
    request_handler.path = ""
    request_handler.wfile = Mock()
    request_handler.rfile = BytesIO(b"")
    request_handler.headers = {}
    request_handler.send_response = Mock()
    request_handler.send_header = Mock()
    request_handler.send_error = Mock()
    request_handler.end_headers = Mock()
    request_handler.address_string = Mock(return_value="127.0.0.1")
    request_handler.main_screen = None
    request_handler.settings_bridge = None
    request_handler.command_signal = None
    return request_handler


class TestPinHashing:
    def test_hash_and_verify_roundtrip(self):
        stored = hash_web_settings_pin("studio-pin")
        assert stored.startswith("pbkdf2_sha256$")
        assert "studio-pin" not in stored
        assert verify_web_settings_pin("studio-pin", stored) is True
        assert verify_web_settings_pin("wrong", stored) is False

    def test_empty_pin_is_unprotected(self, ini_settings):
        assert web_settings_pin_required(ini_settings) is False
        token = authenticate_web_settings_pin("", ini_settings)
        assert session_store.valid(token) is True


class TestConfigRoundtrip:
    def test_apply_and_get_returns_plaintext_secrets_and_keeps_mqtt(self, ini_settings):
        apply_web_config(
            {
                "General": {"stationname": "Web Station", "updatekey": "secret-key-value"},
                "MQTT": {"enablemqtt": True, "mqttpassword": "broker-secret"},
            },
            settings=ini_settings,
        )
        snapshot = get_web_config(ini_settings)
        assert snapshot["General"]["stationname"] == "Web Station"
        assert snapshot["General"]["updatekey"] == "secret-key-value"
        assert snapshot["MQTT"]["enablemqtt"] is True
        assert snapshot["MQTT"]["mqttpassword"] == "broker-secret"
        exported = export_config_dict(include_mqtt=True, settings=ini_settings)
        assert exported["MQTT"]["mqttpassword"] == "broker-secret"
        without_mqtt = export_config_dict(include_mqtt=False, settings=ini_settings)
        assert "MQTT" not in without_mqtt

    def test_plaintext_secrets_are_returned_for_show_hide(self, ini_settings):
        apply_web_config(
            {
                "WeatherWidget": {"owmAPIKey": "owm-secret-key", "owmWidgetEnabled": True},
                "MQTT": {"enablemqtt": True, "mqttpassword": "broker-secret"},
            },
            settings=ini_settings,
        )
        snapshot = get_web_config(ini_settings)
        assert snapshot["WeatherWidget"]["owmAPIKey"] == "owm-secret-key"
        assert snapshot["MQTT"]["mqttpassword"] == "broker-secret"
        assert snapshot["Network"]["websettingspin"] == ""

    def test_apply_skips_virtual_aoip_widgets(self, ini_settings):
        apply_web_config(
            {
                "Audio": {
                    "livewire_source": "should-not-write",
                    "aes67_stream": "also-virtual",
                    "livewire_channel": 42,
                    "aes67_id": "abc",
                    "aes67_addr": "239.69.1.1",
                    "aes67_port": 5004,
                    "aes67_name": "Studio Mix",
                    "aes67_codec": "L24",
                    "aes67_rate": 48000,
                    "aes67_channels": 2,
                    "aes67_manual": True,
                }
            },
            settings=ini_settings,
        )
        snapshot = get_web_config(ini_settings)
        assert "livewire_source" not in snapshot["Audio"]
        assert "aes67_stream" not in snapshot["Audio"]
        assert snapshot["Audio"]["livewire_channel"] == 42
        assert snapshot["Audio"]["aes67_id"] == "abc"
        assert snapshot["Audio"]["aes67_addr"] == "239.69.1.1"
        assert snapshot["Audio"]["aes67_manual"] is True

    def test_unchanged_sentinel_keeps_secret(self, ini_settings):
        apply_web_config({"MQTT": {"mqttpassword": "keep-me"}}, settings=ini_settings)
        apply_web_config(
            {"MQTT": {"mqttpassword": UNCHANGED_SENTINEL}, "General": {"slogan": "New slogan"}},
            settings=ini_settings,
        )
        exported = export_config_dict(include_mqtt=True, settings=ini_settings)
        assert exported["MQTT"]["mqttpassword"] == "keep-me"
        assert get_web_config(ini_settings)["General"]["slogan"] == "New slogan"

    def test_unknown_key_is_rejected(self, ini_settings):
        with pytest.raises(SettingsApiError, match="Unknown setting"):
            apply_web_config({"General": {"not_a_real_key": "x"}}, settings=ini_settings)

    def test_invalid_instance_name_is_rejected(self, ini_settings):
        with pytest.raises(SettingsApiError, match="Instance name"):
            apply_web_config({"General": {"instancename": "Studio 1"}}, settings=ini_settings)

    def test_pin_is_hashed_and_can_be_cleared(self, ini_settings):
        apply_web_config({"Network": {"websettingspin": "1234"}}, settings=ini_settings)
        stored = get_web_config(ini_settings)["Network"]["websettingspin"]
        assert stored == UNCHANGED_SENTINEL
        assert web_settings_pin_required(ini_settings) is True
        apply_web_config({"Network": {"websettingspin": "-"}}, settings=ini_settings)
        assert web_settings_pin_required(ini_settings) is False

    def test_apply_syncs_dialog_and_emits_finished(self, ini_settings):
        main_screen = Mock()
        apply_web_config(
            {"General": {"slogan": "Applied"}},
            main_screen=main_screen,
            settings=ini_settings,
        )
        main_screen.settings.restoreSettingsFromConfig.assert_called_once()
        main_screen.settings.sigConfigFinished.emit.assert_called_once()


class TestPresets:
    def test_save_omits_mqtt_and_load_fills_form(self, ini_settings, tmp_path, monkeypatch):
        monkeypatch.setattr("web_settings.presets_directory", lambda settings=None: tmp_path)
        apply_web_config(
            {
                "General": {"stationname": "Preset Station"},
                "MQTT": {"mqttpassword": "not-in-preset"},
            },
            settings=ini_settings,
        )
        saved = save_web_preset("Studio Look", settings=ini_settings)
        assert saved["filename"] == "Studio_Look"
        listed = list_web_presets(ini_settings)
        assert listed[0]["filename"] == "Studio_Look"
        with open(tmp_path / "Studio_Look.json", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert "MQTT" not in payload["config"]
        apply_web_config({"General": {"stationname": "Changed"}}, settings=ini_settings)
        loaded = load_web_preset("Studio_Look", settings=ini_settings)
        assert loaded["General"]["stationname"] == "Preset Station"


class TestSchema:
    def test_schema_has_desktop_tabs_and_loglevel(self):
        schema = schema_as_json()
        tab_ids = [tab["id"] for tab in schema["tabs"]]
        assert tab_ids == [
            "general", "network", "advanced", "timers", "fonts", "timesource", "audio", "gpio",
        ]
        general_keys = {(field["group"], field["key"]) for field in schema["tabs"][0]["fields"]}
        assert ("General", "loglevel") in general_keys
        assert ("General", "always_start_fullscreen") in general_keys
        network_keys = {(field["group"], field["key"]) for field in schema["tabs"][1]["fields"]}
        assert ("Network", "websettingspin") in network_keys
        assert ("MQTT", "mqttpassword") in network_keys


def _schema_field(group: str, key: str):
    for item in iter_schema_fields():
        if item.group == group and item.key == key:
            return item
    raise AssertionError(f"schema field {group}/{key} not found")


def _json_field(schema: dict, group: str, key: str) -> dict:
    for tab in schema["tabs"]:
        for item in tab["fields"]:
            if item["group"] == group and item["key"] == key:
                return item
    raise AssertionError(f"JSON field {group}/{key} not found")


class TestEnablement:
    def test_schema_json_emits_enabled_when_rules(self):
        schema = schema_as_json()
        livewire = _json_field(schema, "Audio", "livewire_channel")
        assert livewire["enabledWhen"] == [
            {"group": "Audio", "key": "enabled", "eq": True},
            {"group": "Audio", "key": "source", "eq": "livewire"},
        ]
        ntp = _json_field(schema, "NTP", "ntpcheckserver")
        assert ntp["enabledWhenAny"] == [
            {"group": "NTP", "key": "ntpcheck", "eq": True},
            {"group": "TimeSource", "key": "source", "eq": "ntp"},
        ]
        assert "enabledWhen" not in _json_field(schema, "Audio", "enabled")
        livewire_source = _json_field(schema, "Audio", "livewire_source")
        assert livewire_source["widget"] == "livewire_source"
        assert livewire_source["virtual"] is True
        aes67_stream = _json_field(schema, "Audio", "aes67_stream")
        assert aes67_stream["widget"] == "aes67_stream"
        assert aes67_stream["virtual"] is True
        assert _json_field(schema, "Audio", "aes67_id")["hidden"] is True
        assert _json_field(schema, "Audio", "aes67_addr")["hidden"] is True
        assert _json_field(schema, "Audio", "livewire_channel")["hidden"] is False

    def test_livewire_vs_aes67(self):
        livewire = {"Audio": {"enabled": True, "source": "livewire"}}
        aes67 = {"Audio": {"enabled": True, "source": "aes67"}}
        meters_off = {"Audio": {"enabled": False, "source": "livewire"}}
        channel = _schema_field("Audio", "livewire_channel")
        aes_addr = _schema_field("Audio", "aes67_addr")
        aoip = _schema_field("Audio", "livewire_iface")
        device = _schema_field("Audio", "input_device")
        assert field_is_enabled(channel, livewire) is True
        assert field_is_enabled(channel, aes67) is False
        assert field_is_enabled(channel, meters_off) is False
        assert field_is_enabled(aes_addr, aes67) is True
        assert field_is_enabled(aes_addr, livewire) is False
        assert field_is_enabled(aoip, livewire) is True
        assert field_is_enabled(aoip, aes67) is True
        assert field_is_enabled(device, livewire) is False
        assert field_is_enabled(device, {"Audio": {"enabled": True, "source": "device"}}) is True
        source_combo = _schema_field("Audio", "livewire_source")
        aes_combo = _schema_field("Audio", "aes67_stream")
        assert field_is_enabled(source_combo, livewire) is True
        assert field_is_enabled(source_combo, aes67) is False
        assert field_is_enabled(aes_combo, aes67) is True
        assert field_is_enabled(aes_combo, livewire) is False

    def test_mqtt_fields_follow_enablemqtt(self):
        server = _schema_field("MQTT", "mqttserver")
        assert field_is_enabled(server, {"MQTT": {"enablemqtt": True}}) is True
        assert field_is_enabled(server, {"MQTT": {"enablemqtt": False}}) is False

    def test_ptp_and_ltc_serial_vs_audio(self):
        ptp = _schema_field("TimeSource", "ptp_iface")
        ltc_port = _schema_field("TimeSource", "ltc_port")
        ltc_device = _schema_field("TimeSource", "ltc_audio_device")
        assert field_is_enabled(ptp, {"TimeSource": {"source": "ptp"}}) is True
        assert field_is_enabled(ptp, {"TimeSource": {"source": "ltc"}}) is False
        serial = {"TimeSource": {"source": "ltc", "ltc_input": "serial"}}
        audio = {"TimeSource": {"source": "ltc", "ltc_input": "audio"}}
        assert field_is_enabled(ltc_port, serial) is True
        assert field_is_enabled(ltc_port, audio) is False
        assert field_is_enabled(ltc_device, audio) is True
        assert field_is_enabled(ltc_device, serial) is False

    def test_ntp_server_or_rules(self):
        server = _schema_field("NTP", "ntpcheckserver")
        assert field_is_enabled(server, {"NTP": {"ntpcheck": True}, "TimeSource": {"source": "local"}}) is True
        assert field_is_enabled(server, {"NTP": {"ntpcheck": False}, "TimeSource": {"source": "ntp"}}) is True
        assert field_is_enabled(server, {"NTP": {"ntpcheck": False}, "TimeSource": {"source": "ptp"}}) is False

    def test_tooloud_led_only_for_led_action(self):
        led = _schema_field("Audio", "tooloud_led")
        text = _schema_field("Audio", "tooloudtext")
        warning = {"Audio": {"tooloud": True, "tooloud_action": "warning"}}
        trigger = {"Audio": {"tooloud": True, "tooloud_action": "led"}}
        off = {"Audio": {"tooloud": False, "tooloud_action": "led"}}
        assert field_is_enabled(led, trigger) is True
        assert field_is_enabled(led, warning) is False
        assert field_is_enabled(led, off) is False
        assert field_is_enabled(text, warning) is True
        assert field_is_enabled(text, trigger) is False

    def test_gpio_fields_follow_enabled_and_custom_action(self):
        pin = _schema_field("GPIO", "gpi1_pin")
        command = _schema_field("GPIO", "gpi1_command")
        on = {"GPIO": {"enabled": True, "gpi1_action": "LED1"}}
        custom = {"GPIO": {"enabled": True, "gpi1_action": "CUSTOM"}}
        off = {"GPIO": {"enabled": False, "gpi1_action": "CUSTOM"}}
        assert field_is_enabled(pin, on) is True
        assert field_is_enabled(pin, off) is False
        assert field_is_enabled(command, custom) is True
        assert field_is_enabled(command, on) is False
        assert field_is_enabled(command, off) is False


class TestHttpRoutes:
    def test_auth_status_is_public(self, handler):
        handler.path = "/api/settings/auth"
        with patch("network.web_settings_pin_required", return_value=False):
            handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.write.call_args[0][0].decode("utf-8"))
        assert body["required"] is False

    def test_settings_get_requires_token_when_pin_set(self, handler):
        handler.path = "/api/settings"
        handler.headers = {}
        with patch("network.web_settings_pin_required", return_value=True):
            with patch("network.session_store.valid", return_value=False):
                handler.do_GET()
        written = handler.wfile.write.call_args[0][0].decode("utf-8")
        assert handler.send_response.call_args[0][0] == 401
        assert "unauthorized" in written

    def test_settings_get_returns_config_without_pin(self, handler):
        handler.path = "/api/settings"
        handler.headers = {}
        with patch("network.web_settings_pin_required", return_value=False):
            with patch.object(handler, "_call_settings_api", return_value={"config": {"General": {}}}):
                handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.write.call_args[0][0].decode("utf-8"))
        assert "config" in body

    def test_settings_put_applies_config(self, handler):
        payload = {"config": {"General": {"slogan": "From Web"}}}
        raw = json.dumps(payload).encode("utf-8")
        handler.rfile = BytesIO(raw)
        handler.headers = {"Content-Length": str(len(raw))}
        handler.path = "/api/settings"
        with patch("network.web_settings_pin_required", return_value=False):
            with patch.object(handler, "_call_settings_api", return_value={"status": "ok"}) as mocked:
                handler.do_PUT()
                mocked.assert_called_once_with("put", payload)
        handler.send_response.assert_called_with(200)

    def test_unlock_with_wrong_pin(self, handler):
        raw = json.dumps({"pin": "nope"}).encode("utf-8")
        handler.rfile = BytesIO(raw)
        handler.headers = {"Content-Length": str(len(raw))}
        handler.path = "/api/settings/auth"
        with patch("network.authenticate_web_settings_pin", side_effect=SettingsApiError("Invalid PIN", 401)):
            handler.do_POST()
        assert handler.send_response.call_args[0][0] == 401

    def test_aoip_list_route(self, handler):
        handler.path = "/api/settings/aoip?source=livewire&iface=&channel=1"
        with patch("network.web_settings_pin_required", return_value=False):
            with patch.object(
                handler,
                "_call_settings_api",
                return_value={"source": "livewire", "running": False, "streams": []},
            ) as mocked:
                handler.do_GET()
                mocked.assert_called_once()
                assert mocked.call_args[0][0] == "aoip_list"
        handler.send_response.assert_called_with(200)

    def test_aoip_sdp_and_stop_routes(self, handler):
        payload = {"sdp": "v=0", "iface": ""}
        raw = json.dumps(payload).encode("utf-8")
        handler.rfile = BytesIO(raw)
        handler.headers = {"Content-Length": str(len(raw))}
        handler.path = "/api/settings/aoip/sdp"
        with patch("network.web_settings_pin_required", return_value=False):
            with patch.object(handler, "_call_settings_api", return_value={"streams": []}) as mocked:
                handler.do_POST()
                mocked.assert_called_once_with("aoip_sdp", payload)
        handler.send_response.assert_called_with(200)

        handler.path = "/api/settings/aoip/stop"
        handler.rfile = BytesIO(b"")
        handler.headers = {"Content-Length": "0"}
        with patch("network.web_settings_pin_required", return_value=False):
            with patch.object(handler, "_call_settings_api", return_value={"status": "ok"}) as mocked:
                handler.do_POST()
                mocked.assert_called_once_with("aoip_stop")
