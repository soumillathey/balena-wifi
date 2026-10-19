"""auth.py — Superadmin authentication and session tokens."""
from __future__ import annotations

import os
import secrets
import threading
import time
from typing import Optional

SUPERADMIN_USER = os.getenv("SUPERADMIN_USER", "superadmin")
SUPERADMIN_PASS = os.getenv("SUPERADMIN_PASS", "Gluvok@241821")
SESSION_LIFETIME = 7200.0  # 2 hours
_sessions: dict[str, float] = {}
_lock = threading.Lock()


def create_token() -> str:
    """Generate a secure cryptographic session token."""
    token = secrets.token_hex(32)
    with _lock:
        _sessions[token] = time.time() + SESSION_LIFETIME
    return token


def validate_token(token: Optional[str]) -> bool:
    """Validate token and refresh expiration time if valid."""
    if not token:
        return False
    now = time.time()
    with _lock:
        exp = _sessions.get(token)
        if exp and exp > now:
            _sessions[token] = now + SESSION_LIFETIME
            return True
        _sessions.pop(token, None)
        return False


def verify_login(user: str, pwd: str) -> bool:
    """Verify credentials using timing-attack resistant comparison."""
    return secrets.compare_digest(user.strip(), SUPERADMIN_USER) and secrets.compare_digest(pwd, SUPERADMIN_PASS)


__all__ = ["create_token", "validate_token", "verify_login"]
