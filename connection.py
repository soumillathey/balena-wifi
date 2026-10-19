"""connection.py — Wi-Fi client connection and credential management via balena."""
from __future__ import annotations

import logging
import threading
import time

from balena_driver import (
    is_network_connected,
    submit_credentials_to_balena,
)
from constants import DEFAULT_WIFI_CONNECT_TIMEOUT
from hotspot import is_hotspot_active, start_emergency_hotspot

logger = logging.getLogger(__name__)

_connection_in_progress = threading.Event()


def is_connecting() -> bool:
    """Check if an active Wi-Fi connection handshake is currently executing."""
    return _connection_in_progress.is_set()


def connect_to_wifi(
    ssid: str,
    password: str,
    timeout: float = DEFAULT_WIFI_CONNECT_TIMEOUT,
) -> tuple[bool, str]:
    """Connect to a Wi-Fi access point via balena wifi-connect with automatic AP fallback."""
    if not ssid or not ssid.strip():
        return False, "SSID cannot be empty."

    ssid = ssid.strip()
    _connection_in_progress.set()
    logger.info(f"Initiating Wi-Fi connection to '{ssid}' via balena...")

    try:
        # Submit credentials to balena-io/wifi-connect engine
        ok, msg = submit_credentials_to_balena(ssid, password, timeout=timeout)
        if not ok:
            logger.warning(f"Balena rejected credentials for '{ssid}': {msg}")
            if not is_hotspot_active():
                logger.info("Re-activating emergency hotspot AP after failed attempt...")
                start_emergency_hotspot()
            return False, msg

        # Give NetworkManager and DHCP lease up to 10 seconds to stabilize
        start_wait = time.time()
        verified = False
        while time.time() - start_wait < 10.0:
            if is_network_connected():
                verified = True
                break
            time.sleep(1.0)

        if verified:
            logger.info(f"Verified active connection to '{ssid}'.")
            return True, f"Successfully connected to Wi-Fi: '{ssid}'."

        # If not verified online yet, check if simulation or still connecting
        if not is_hotspot_active():
            # Connection may take slightly longer in some networks
            return True, f"Credentials accepted for '{ssid}'. Connecting in background."

        # If hotspot is still active and network check failed, fallback
        logger.warning(f"Connection verification timed out for '{ssid}'. Restoring AP.")
        start_emergency_hotspot()
        return False, f"Connection to '{ssid}' failed or timed out. Hotspot portal restored."

    except Exception as e:
        logger.exception(f"Unexpected error while connecting to '{ssid}': {e}")
        if not is_hotspot_active():
            start_emergency_hotspot()
        return False, f"Connection error: {e}"
    finally:
        _connection_in_progress.clear()


__all__ = ["connect_to_wifi", "is_connecting"]
