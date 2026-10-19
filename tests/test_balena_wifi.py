"""test_balena_wifi.py — Comprehensive unit tests for balena wifi setup."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

TESTS_DIR = Path(__file__).resolve().parent
MODULE_DIR = TESTS_DIR.parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import auth
import balena_driver
import connection
import connector
import constants
import hotspot
import installer
import routes
import server
import vault
import watchdog
import wifi_setup


# --- 1. Constants & Installer Tests ---
def test_constants():
    assert constants.DEFAULT_HOTSPOT_SSID == "hermes"
    assert constants.DEFAULT_HOTSPOT_PASS == "12345678"
    assert constants.DEFAULT_PORTAL_GATEWAY == "192.168.42.1"
    assert constants.DEFAULT_PORTAL_PORT == 80
    assert constants.DEFAULT_WEB_PORT == 8080


def test_target_triple_detection():
    with patch("platform.machine", return_value="aarch64"):
        assert installer.get_target_triple() == "aarch64-unknown-linux-gnu"
    with patch("platform.machine", return_value="x86_64"):
        assert installer.get_target_triple() == "x86_64-unknown-linux-gnu"
    with patch("platform.machine", return_value="armv7l"):
        assert installer.get_target_triple() == "armv7-unknown-linux-gnueabihf"
    with patch("platform.machine", return_value="unknown_cpu"):
        assert installer.get_target_triple() is None


# --- 2. Vault Tests ---
def test_vault_crud(tmp_path):
    test_db = tmp_path / "test_vault.db"
    with patch.object(vault, "VAULT_DB_PATH", test_db):
        vault.clear_saved_networks()
        assert vault.get_saved_networks() == []
        assert vault.get_network_password("TestSSID") is None

        vault.save_network("TestSSID", "secret123")
        saved = vault.get_saved_networks()
        assert len(saved) == 1
        assert saved[0]["ssid"] == "TestSSID"
        assert vault.get_network_password("TestSSID") == "secret123"

        # Update password
        vault.save_network("TestSSID", "newsecret")
        assert vault.get_network_password("TestSSID") == "newsecret"

        vault.clear_saved_networks()
        assert vault.get_saved_networks() == []


# --- 3. Authentication Tests ---
def test_auth_verification():
    assert auth.verify_login("superadmin", "Gluvok@241821") is True
    assert auth.verify_login("superadmin", "wrongpassword") is False
    assert auth.verify_login("hacker", "Gluvok@241821") is False


def test_session_token_lifecycle():
    token = auth.create_token()
    assert isinstance(token, str) and len(token) == 64
    assert auth.validate_token(token) is True
    assert auth.validate_token("invalid_token_123") is False
    assert auth.validate_token(None) is False


# --- 4. Balena Process Manager & Driver Tests ---
def test_balena_simulation_mode():
    mgr = balena_driver.BalenaProcessManager()
    with patch.object(balena_driver, "is_balena_available", return_value=False):
        ok = mgr.start_portal(ssid="hermes", password="pass")
        assert ok is True
        assert mgr.is_running() is True
        stop_ok = mgr.stop_portal()
        assert stop_ok is True
        assert mgr.is_running() is False


def test_fetch_scanned_networks():
    with patch.object(balena_driver, "is_balena_available", return_value=False):
        networks = balena_driver.fetch_scanned_networks()
        assert isinstance(networks, list)
        assert len(networks) > 0
        assert any(n["ssid"] == "Office_WiFi_5G" for n in networks)


# --- 5. Connection Tests ---
def test_connect_to_wifi_empty_ssid():
    ok, msg = connection.connect_to_wifi("", "password")
    assert ok is False
    assert "SSID cannot be empty" in msg


def test_connect_to_wifi_success():
    with patch.object(connection, "submit_credentials_to_balena", return_value=(True, "Success")), \
         patch.object(connection, "is_network_connected", return_value=True):
        ok, msg = connection.connect_to_wifi("FacilityWiFi", "Pass1234")
        assert ok is True
        assert "FacilityWiFi" in msg


def test_connect_to_wifi_failure_fallback():
    with patch.object(connection, "submit_credentials_to_balena", return_value=(False, "Invalid credentials")), \
         patch.object(connection, "is_hotspot_active", return_value=False), \
         patch.object(connection, "start_emergency_hotspot") as mock_start_hotspot:
        ok, msg = connection.connect_to_wifi("BadWiFi", "WrongPass")
        assert ok is False
        mock_start_hotspot.assert_called_once()


# --- 6. Watchdog Tests ---
def test_watchdog_lifecycle():
    watchdog.stop_watchdog()
    with patch.object(watchdog, "is_network_connected", return_value=True), \
         patch.object(watchdog, "is_hotspot_active", return_value=True), \
         patch.object(watchdog, "stop_emergency_hotspot") as mock_stop_hot:
        watchdog.start_watchdog(interval=0.1)
        time.sleep(0.25)
        watchdog.stop_watchdog()
        mock_stop_hot.assert_called()


# --- 7. Connector Tests ---
@patch.object(connector, "start_watchdog")
@patch.object(connector, "start_server")
@patch.object(connector, "start_emergency_hotspot")
def test_setup_hotspot(mock_hot, mock_srv, mock_dog):
    connector.setup_hotspot(port=9090, portal_port=80, ssid="test-ap", password="secretpassword")
    mock_hot.assert_called_once_with(
        ssid="test-ap",
        password="secretpassword",
        portal_port=80,
        gateway="192.168.42.1",
        interface=None,
    )
    mock_srv.assert_called_once_with(port=9090)
    mock_dog.assert_called_once()


@patch.object(connector, "stop_emergency_hotspot")
@patch.object(connector, "stop_watchdog")
@patch.object(connector, "stop_server")
def test_shutdown_services(mock_srv, mock_dog, mock_hot):
    connector.shutdown_services()
    mock_srv.assert_called_once()
    mock_dog.assert_called_once()
    mock_hot.assert_called_once()


# --- 8. Routes & API Tests ---
@pytest.fixture
def client():
    app = server.create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_and_captive_routes(client):
    res = client.get("/")
    assert res.status_code == 200
    res_wifi = client.get("/wifi")
    assert res_wifi.status_code == 200

    with patch("routes.is_network_connected", return_value=False):
        res_portal = client.get("/generate_204")
        assert res_portal.status_code == 302
        assert "/wifi" in res_portal.headers["Location"]


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "connected" in data
    assert "hotspot" in data
    assert "saved" in data


def test_api_networks(client):
    res = client.get("/api/networks")
    assert res.status_code == 200
    data = res.get_json()
    assert "networks" in data


def test_api_login_and_auth_flow(client):
    # Invalid login
    res_fail = client.post("/api/login", json={"userid": "superadmin", "password": "wrong"})
    assert res_fail.status_code == 401

    # Valid login
    res_ok = client.post("/api/login", json={"userid": "superadmin", "password": "Gluvok@241821"})
    assert res_ok.status_code == 200
    token = res_ok.get_json()["token"]

    # Post Wi-Fi without auth
    res_no_auth = client.post("/api/wifi", json={"ssid": "Test", "password": "pass"})
    assert res_no_auth.status_code == 401

    # Post Wi-Fi with valid auth token
    with patch("routes.connect_to_wifi", return_value=(True, "Connected successfully")):
        res_auth = client.post(
            "/api/wifi",
            headers={"X-Auth-Token": token},
            json={"ssid": "Plant_Network", "password": "test"},
        )
        assert res_auth.status_code == 200
        assert res_auth.get_json()["success"] is True


# --- 9. CLI Tests ---
@patch.object(wifi_setup, "connect_to_wifi", return_value=(True, "Connected"))
@patch("sys.argv", ["wifi_setup.py", "--connect", "--ssid", "PhoneHotspot", "--password", "phonepass"])
def test_cli_connect(mock_connect):
    wifi_setup.main()
    mock_connect.assert_called_once_with("PhoneHotspot", "phonepass")


@patch("sys.exit")
@patch.object(wifi_setup, "shutdown_services")
def test_cli_shutdown(mock_shutdown_services, mock_exit):
    wifi_setup.shutdown()
    mock_shutdown_services.assert_called_once()
    mock_exit.assert_called_once_with(0)
