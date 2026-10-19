"""wifi_setup.py — Standalone CLI entry point for balena Wi-Fi setup."""
from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from connector import connect_to_wifi, setup_hotspot, shutdown_services
from constants import (
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_PORTAL_GATEWAY,
    DEFAULT_PORTAL_PORT,
    DEFAULT_WEB_PORT,
)
from installer import install_wifi_connect


def shutdown(signum: int = 0, frame: object = None) -> None:
    shutdown_services()
    sys.exit(0)


def main() -> None:
    p = argparse.ArgumentParser(description="Balena Wi-Fi Setup: Robust Hotspot & Captive Portal Manager")
    p.add_argument("--connect", action="store_true", help="Connect to an existing Wi-Fi / phone hotspot")
    p.add_argument("--ssid", default=DEFAULT_HOTSPOT_SSID, help="Hotspot or target network SSID")
    p.add_argument("--password", default=DEFAULT_HOTSPOT_PASS, help="Hotspot or target network password")
    p.add_argument("--port", type=int, default=DEFAULT_WEB_PORT, help="Web management console port")
    p.add_argument("--portal-port", type=int, default=DEFAULT_PORTAL_PORT, help="Balena captive portal port")
    p.add_argument("--gateway", default=DEFAULT_PORTAL_GATEWAY, help="Portal gateway IP address")
    p.add_argument("--interface", default="", help="Network interface (default: auto-detected wlan0)")
    p.add_argument("--install", action="store_true", help="Download and install official balena wifi-connect binary")
    args = p.parse_args()

    if args.install:
        print("[Balena WiFi] Checking and downloading official wifi-connect binary...")
        try:
            installed_path = install_wifi_connect()
            print(f"[Balena WiFi] Installation complete: {installed_path}")
        except Exception as e:
            print(f"[Balena WiFi] Installation error: {e}")
            sys.exit(1)
        return

    if args.connect:
        target_ssid = args.ssid if args.ssid != DEFAULT_HOTSPOT_SSID else input("Target Wi-Fi SSID: ").strip()
        target_pwd = args.password if args.password != DEFAULT_HOTSPOT_PASS else input("Target Wi-Fi Password: ").strip()
        ok, msg = connect_to_wifi(target_ssid, target_pwd)
        print(f"[{'SUCCESS' if ok else 'FAILED'}] {msg}")
        return

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, shutdown)

    # On Linux, if wifi-connect is missing, auto-install it
    from balena_driver import is_balena_available
    import platform
    if not is_balena_available() and platform.system() == "Linux":
        print("[Balena WiFi] wifi-connect binary not found on this Linux system.")
        print("[Balena WiFi] Automatically downloading official balena-io/wifi-connect binary...")
        try:
            installed_path = install_wifi_connect()
            print(f"[Balena WiFi] Installed: {installed_path}")
        except Exception as e:
            print(f"[Balena WiFi] Auto-download warning: {e}")

    setup_hotspot(
        port=args.port,
        portal_port=args.portal_port,
        ssid=args.ssid,
        password=args.password,
        gateway=args.gateway,
        interface=args.interface or None,
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
