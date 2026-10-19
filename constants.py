"""constants.py — Configuration constants for balena-based Wi-Fi setup."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Hotspot AP Configuration
DEFAULT_HOTSPOT_SSID = "hermes"
DEFAULT_HOTSPOT_PASS = "12345678"
DEFAULT_PORTAL_GATEWAY = "192.168.42.1"
DEFAULT_PORTAL_DHCP_RANGE = "192.168.42.2,192.168.42.254"

# Networking Ports
DEFAULT_PORTAL_PORT = 80          # Native captive portal HTTP port
DEFAULT_WEB_PORT = 8080           # Alternative management console port

# Timeouts & Intervals (seconds)
DEFAULT_WIFI_CONNECT_TIMEOUT = 60.0
DEFAULT_WATCHDOG_INTERVAL = 15.0
DEFAULT_ACTIVITY_TIMEOUT = 0      # 0 = do not exit on inactivity

# Paths & Balena Binary Names
BALENA_BINARY_NAMES = (
    "wifi-connect",
    str(BASE_DIR / "bin" / "wifi-connect"),
    "/usr/local/sbin/wifi-connect",
    "/usr/local/bin/wifi-connect",
)

UI_DIR = BASE_DIR / "ui"
TEMPLATES_DIR = BASE_DIR / "templates"
VAULT_DB_PATH = BASE_DIR / "wifi_vault.db"

# Release info for automated binary download
BALENA_REPO = "balena-os/wifi-connect"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{BALENA_REPO}/releases/latest"
