"""vault.py — SQLite storage for saved Wi-Fi networks in balena wifi setup."""
from __future__ import annotations

import sqlite3
from typing import Any

from constants import VAULT_DB_PATH

_SQL_INIT = (
    "CREATE TABLE IF NOT EXISTS wifi_networks ("
    "ssid TEXT PRIMARY KEY, password TEXT NOT NULL, "
    "last_connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(VAULT_DB_PATH), timeout=5.0)
    c.row_factory = sqlite3.Row
    with c:
        c.execute(_SQL_INIT)
    return c


def save_network(ssid: str, password: str) -> None:
    """Store or update Wi-Fi credentials in persistent vault."""
    sql = (
        "INSERT INTO wifi_networks (ssid, password, last_connected_at) "
        "VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(ssid) DO UPDATE SET password=excluded.password, "
        "last_connected_at=CURRENT_TIMESTAMP;"
    )
    with _conn() as c:
        c.execute(sql, (ssid, password))


def get_saved_networks() -> list[dict[str, Any]]:
    """Return all saved networks sorted by most recently used."""
    with _conn() as c:
        rows = c.execute(
            "SELECT ssid, last_connected_at FROM wifi_networks ORDER BY last_connected_at DESC"
        ).fetchall()
        return [{"ssid": r["ssid"], "last_connected_at": r["last_connected_at"]} for r in rows]


def get_network_password(ssid: str) -> str | None:
    """Retrieve saved password for a network by SSID."""
    with _conn() as c:
        row = c.execute("SELECT password FROM wifi_networks WHERE ssid = ?", (ssid,)).fetchone()
        return str(row["password"]) if row else None


def clear_saved_networks() -> None:
    """Purge all stored credentials from the vault."""
    with _conn() as c:
        c.execute("DELETE FROM wifi_networks;")


__all__ = [
    "save_network",
    "get_saved_networks",
    "get_network_password",
    "clear_saved_networks",
]
