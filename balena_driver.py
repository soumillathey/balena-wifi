"""balena_driver.py — Low-level process runner and API client for balena wifi-connect."""
from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from constants import (
    BALENA_BINARY_NAMES,
    DEFAULT_ACTIVITY_TIMEOUT,
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_PORTAL_DHCP_RANGE,
    DEFAULT_PORTAL_GATEWAY,
    DEFAULT_PORTAL_PORT,
    UI_DIR,
)

logger = logging.getLogger(__name__)

# Simulation state for non-Linux / development environments
_SIMULATION_STATE = {
    "is_connected": False,
    "current_ssid": "",
    "portal_running": False,
}


def find_wifi_connect_bin() -> Optional[str]:
    """Find balena wifi-connect binary path."""
    for candidate in BALENA_BINARY_NAMES:
        if candidate.startswith("/"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def is_balena_available() -> bool:
    """Check if balena wifi-connect is installed and runnable."""
    return find_wifi_connect_bin() is not None


def is_root() -> bool:
    """Check if running as root."""
    return getattr(os, "geteuid", lambda: 0)() == 0


def get_wifi_interface() -> str:
    """Detect first available wireless network interface or default to wlan0."""
    # Check /sys/class/net on Linux
    sys_net = Path("/sys/class/net")
    if sys_net.is_dir():
        for dev in sys_net.iterdir():
            if (dev / "wireless").is_dir() or dev.name.startswith("wl"):
                return dev.name
    return "wlan0"


def is_network_connected(host: str = "1.1.1.1", port: int = 53, timeout: float = 2.0) -> bool:
    """Robust internet/Wi-Fi connectivity check via socket connect to reliable DNS server."""
    if not is_balena_available() and not Path("/sys/class/net").exists():
        return _SIMULATION_STATE["is_connected"]

    for target in ((host, port), ("8.8.8.8", 53)):
        try:
            with socket.create_connection(target, timeout=timeout):
                return True
        except (OSError, socket.timeout):
            continue
    return False


class BalenaProcessManager:
    """Manages the lifecycle of the balena wifi-connect captive portal process."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen[str]] = None
        self._lock = threading.RLock()
        self._log_thread: Optional[threading.Thread] = None
        self._portal_port: int = DEFAULT_PORTAL_PORT
        self._gateway: str = DEFAULT_PORTAL_GATEWAY

    @property
    def portal_port(self) -> int:
        return self._portal_port

    @property
    def gateway(self) -> str:
        return self._gateway

    def is_running(self) -> bool:
        with self._lock:
            if not is_balena_available():
                return _SIMULATION_STATE["portal_running"]
            if self._process is None:
                return False
            ret = self._process.poll()
            return ret is None

    def start_portal(
        self,
        ssid: str = DEFAULT_HOTSPOT_SSID,
        password: str = DEFAULT_HOTSPOT_PASS,
        portal_port: int = DEFAULT_PORTAL_PORT,
        gateway: str = DEFAULT_PORTAL_GATEWAY,
        dhcp_range: str = DEFAULT_PORTAL_DHCP_RANGE,
        interface: Optional[str] = None,
        ui_dir: Optional[Path] = None,
        activity_timeout: int = DEFAULT_ACTIVITY_TIMEOUT,
    ) -> bool:
        with self._lock:
            if self.is_running():
                logger.info("balena wifi-connect is already running.")
                return True

            self._portal_port = portal_port
            self._gateway = gateway

            bin_path = find_wifi_connect_bin()
            if not bin_path:
                logger.warning("[Simulation] wifi-connect binary not found. Running in simulation mode.")
                _SIMULATION_STATE["portal_running"] = True
                return True

            iface = interface or get_wifi_interface()
            custom_ui = str(ui_dir or UI_DIR)

            cmd: list[str] = []
            if not is_root() and shutil.which("sudo"):
                cmd.extend(["sudo", "-n"])

            cmd.extend([
                bin_path,
                "--portal-ssid", ssid,
                "--portal-gateway", gateway,
                "--portal-dhcp-range", dhcp_range,
                "--portal-listening-port", str(portal_port),
                "--portal-interface", iface,
                "--activity-timeout", str(activity_timeout),
            ])

            if password:
                cmd.extend(["--portal-passphrase", password])

            if os.path.isdir(custom_ui):
                cmd.extend(["--ui-directory", custom_ui])

            logger.info(f"Starting balena wifi-connect: {' '.join(cmd)}")
            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except Exception as e:
                logger.error(f"Failed to start wifi-connect process: {e}")
                return False

            # Pipe logs in background thread
            def _stream_logs(proc: subprocess.Popen[str]) -> None:
                if not proc.stdout:
                    return
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        logger.info(f"[wifi-connect] {line.strip()}")
                proc.stdout.close()

            self._log_thread = threading.Thread(
                target=_stream_logs,
                args=(self._process,),
                name="WifiConnectLogs",
                daemon=True,
            )
            self._log_thread.start()

            # Wait briefly to ensure it did not instantly crash (e.g. port bind error)
            time.sleep(1.0)
            if self._process.poll() is not None:
                logger.error(f"wifi-connect exited immediately with code {self._process.returncode}")
                return False

            return True

    def stop_portal(self, timeout: float = 5.0) -> bool:
        with self._lock:
            if not is_balena_available():
                _SIMULATION_STATE["portal_running"] = False
                return True

            if self._process is None:
                return True

            if self._process.poll() is not None:
                self._process = None
                return True

            logger.info("Stopping balena wifi-connect process...")
            try:
                self._process.terminate()
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning("wifi-connect did not terminate gracefully; sending kill signal.")
                self._process.kill()
                self._process.wait(timeout=2.0)
            except Exception as e:
                logger.error(f"Error stopping wifi-connect: {e}")
            finally:
                self._process = None

            return True


# Global singleton manager
balena_manager = BalenaProcessManager()


def fetch_scanned_networks(portal_host: str = "127.0.0.1", port: Optional[int] = None) -> list[dict[str, Any]]:
    """Query balena wifi-connect REST API for scanned Wi-Fi access points."""
    target_port = port or balena_manager.portal_port
    if not is_balena_available():
        # Provide rich realistic mock networks in simulation mode
        return [
            {"ssid": "Office_WiFi_5G", "signal": -42, "security": "WPA2-PSK"},
            {"ssid": "Guest_Network", "signal": -58, "security": "Open"},
            {"ssid": "Warehouse_AP_North", "signal": -72, "security": "WPA2-PSK"},
            {"ssid": "MobileHotspot", "signal": -35, "security": "WPA2-PSK"},
        ]

    for endpoint in (f"http://{portal_host}:{target_port}/networks", f"http://{portal_host}:{target_port}/ssids"):
        try:
            req = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
        except Exception:
            continue
    return []


def submit_credentials_to_balena(
    ssid: str,
    password: str,
    portal_host: str = "127.0.0.1",
    port: Optional[int] = None,
    timeout: float = 45.0,
) -> tuple[bool, str]:
    """Submit Wi-Fi credentials to balena wifi-connect REST API (POST /connect)."""
    target_port = port or balena_manager.portal_port
    if not is_balena_available():
        # Simulate connection sequence
        time.sleep(1.0)
        _SIMULATION_STATE["is_connected"] = True
        _SIMULATION_STATE["current_ssid"] = ssid
        _SIMULATION_STATE["portal_running"] = False
        return True, f"Connected to '{ssid}' (simulated balena mode)."

    url = f"http://{portal_host}:{target_port}/connect"
    payload = json.dumps({"ssid": ssid, "passphrase": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            if status_code in (200, 201, 202):
                return True, f"Credentials submitted successfully to balena wifi-connect for '{ssid}'."
            return False, f"Unexpected response from wifi-connect: HTTP {status_code}"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        return False, f"Failed connecting to '{ssid}': HTTP {e.code} — {err_msg}"
    except Exception as e:
        # If wifi-connect switches interfaces immediately, HTTP request may disconnect as connection succeeds
        return True, f"Credentials sent to balena wifi-connect for '{ssid}' (connection initiated)."
