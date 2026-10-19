"""hotspot.py — High-level hotspot and captive portal controller using balena wifi-connect."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from balena_driver import (
    balena_manager,
    fetch_scanned_networks,
    is_balena_available,
)
from constants import (
    DEFAULT_ACTIVITY_TIMEOUT,
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_PORTAL_DHCP_RANGE,
    DEFAULT_PORTAL_GATEWAY,
    DEFAULT_PORTAL_PORT,
    UI_DIR,
)

logger = logging.getLogger(__name__)


def start_emergency_hotspot(
    ssid: str = DEFAULT_HOTSPOT_SSID,
    password: str = DEFAULT_HOTSPOT_PASS,
    portal_port: int = DEFAULT_PORTAL_PORT,
    gateway: str = DEFAULT_PORTAL_GATEWAY,
    dhcp_range: str = DEFAULT_PORTAL_DHCP_RANGE,
    interface: Optional[str] = None,
    ui_dir: Optional[Path] = UI_DIR,
    activity_timeout: int = DEFAULT_ACTIVITY_TIMEOUT,
) -> bool:
    """Start balena wifi-connect captive portal access point."""
    logger.info(f"Initiating balena hotspot AP: SSID='{ssid}'")
    return balena_manager.start_portal(
        ssid=ssid,
        password=password,
        portal_port=portal_port,
        gateway=gateway,
        dhcp_range=dhcp_range,
        interface=interface,
        ui_dir=ui_dir,
        activity_timeout=activity_timeout,
    )


def stop_emergency_hotspot(timeout: float = 5.0) -> bool:
    """Stop the running balena wifi-connect captive portal."""
    logger.info("Stopping balena hotspot AP...")
    return balena_manager.stop_portal(timeout=timeout)


def is_hotspot_active() -> bool:
    """Check if balena wifi-connect AP is currently active."""
    return balena_manager.is_running()


def get_available_networks() -> list[dict[str, Any]]:
    """Return available Wi-Fi access points scanned by balena wifi-connect."""
    return fetch_scanned_networks()


__all__ = [
    "start_emergency_hotspot",
    "stop_emergency_hotspot",
    "is_hotspot_active",
    "get_available_networks",
    "is_balena_available",
]
