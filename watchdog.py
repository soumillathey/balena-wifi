"""watchdog.py — Robust background watchdog and automatic hotspot fallback for balena."""
from __future__ import annotations

import logging
import threading
from typing import Optional

from balena_driver import is_network_connected
from connection import is_connecting
from constants import DEFAULT_WATCHDOG_INTERVAL
from hotspot import is_hotspot_active, start_emergency_hotspot, stop_emergency_hotspot

logger = logging.getLogger(__name__)

_watchdog_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_lock = threading.RLock()


def _loop(interval: float) -> None:
    consecutive_failures = 0
    failure_threshold = 2  # Require 2 consecutive failures to prevent flapping

    while not _stop_event.is_set():
        if is_connecting():
            _stop_event.wait(interval)
            continue

        online = is_network_connected()

        if online:
            consecutive_failures = 0
            if is_hotspot_active():
                logger.info("[Watchdog] Network connected. Stopping balena captive portal.")
                stop_emergency_hotspot()
        else:
            consecutive_failures += 1
            if consecutive_failures >= failure_threshold:
                if not is_hotspot_active() and not is_connecting():
                    logger.warning("[Watchdog] Wi-Fi lost. Launching balena captive portal...")
                    start_emergency_hotspot()

        _stop_event.wait(interval)


def start_watchdog(interval: float = DEFAULT_WATCHDOG_INTERVAL) -> None:
    """Start background watchdog thread."""
    global _watchdog_thread
    with _lock:
        if _watchdog_thread and _watchdog_thread.is_alive():
            return
        _stop_event.clear()
        _watchdog_thread = threading.Thread(
            target=_loop,
            args=(interval,),
            name="BalenaWiFiWatchdog",
            daemon=True,
        )
        _watchdog_thread.start()
        logger.info(f"[Watchdog] Started with check interval={interval}s.")


def stop_watchdog(timeout: float = 3.0) -> None:
    """Stop background watchdog thread."""
    global _watchdog_thread
    with _lock:
        _stop_event.set()
        if _watchdog_thread and _watchdog_thread.is_alive():
            _watchdog_thread.join(timeout=timeout)
            _watchdog_thread = None
        logger.info("[Watchdog] Stopped.")


__all__ = ["start_watchdog", "stop_watchdog"]
