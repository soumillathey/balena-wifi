"""connector.py — High-level coordinator linking balena captive portal, web server, and watchdog."""
from __future__ import annotations

import logging
from typing import Optional

from connection import connect_to_wifi
from constants import (
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_PORTAL_GATEWAY,
    DEFAULT_PORTAL_PORT,
    DEFAULT_WEB_PORT,
)
from hotspot import is_balena_available, start_emergency_hotspot, stop_emergency_hotspot
from server import start_server, stop_server
from watchdog import start_watchdog, stop_watchdog

logger = logging.getLogger(__name__)


def setup_hotspot(
    port: int = DEFAULT_WEB_PORT,
    portal_port: int = DEFAULT_PORTAL_PORT,
    ssid: str = DEFAULT_HOTSPOT_SSID,
    password: str = DEFAULT_HOTSPOT_PASS,
    gateway: str = DEFAULT_PORTAL_GATEWAY,
    interface: Optional[str] = None,
) -> None:
    """Initialize balena wifi-connect captive portal, management web server, and background watchdog."""
    print(f"\n[Balena WiFi] Initializing setup services (SSID='{ssid}')...")

    # 1. Start balena wifi-connect captive portal
    start_emergency_hotspot(
        ssid=ssid,
        password=password,
        portal_port=portal_port,
        gateway=gateway,
        interface=interface,
    )

    # 2. Start management console if on different port
    if port != portal_port:
        start_server(port=port)

    # 3. Start background watchdog
    start_watchdog()

    engine_tag = "balena-io/wifi-connect" if is_balena_available() else "balena simulation mode"
    print(f"[Balena WiFi] Engine: {engine_tag}")
    print(f"[Balena WiFi] Hotspot active: SSID='{ssid}' | Password='{password}'")
    print(f"[Balena WiFi] Captive portal: http://{gateway}:{portal_port}")
    if port != portal_port:
        print(f"[Balena WiFi] Web console:    http://{gateway}:{port}/wifi")
    print("[Balena WiFi] Ready. Press Ctrl+C to terminate services.\n")


def shutdown_services() -> None:
    """Gracefully terminate all balena Wi-Fi background services."""
    print("\n[Balena WiFi] Terminating Wi-Fi services...")
    stop_server()
    stop_watchdog()
    stop_emergency_hotspot()
    print("[Balena WiFi] All services stopped.")


__all__ = ["connect_to_wifi", "setup_hotspot", "shutdown_services"]
