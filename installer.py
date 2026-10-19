"""installer.py — Automatic installation and binary management for balena wifi-connect."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

from constants import BASE_DIR

logger = logging.getLogger(__name__)

ARCH_MAP = {
    "aarch64": "aarch64-unknown-linux-gnu",
    "arm64": "aarch64-unknown-linux-gnu",
    "armv7l": "armv7-unknown-linux-gnueabihf",
    "armv7": "armv7-unknown-linux-gnueabihf",
    "x86_64": "x86_64-unknown-linux-gnu",
    "amd64": "x86_64-unknown-linux-gnu",
}


def get_target_triple() -> Optional[str]:
    """Return the rust target triple for the current machine architecture."""
    mach = platform.machine().lower()
    return ARCH_MAP.get(mach)


def install_wifi_connect(target_dir: Optional[Path] = None, version: str = "v4.11.1") -> Path:
    """Download and install the official balena wifi-connect binary for current architecture."""
    dest_dir = target_dir or (BASE_DIR / "bin")
    dest_dir.mkdir(parents=True, exist_ok=True)
    binary_dest = dest_dir / "wifi-connect"

    if binary_dest.is_file() and os.access(binary_dest, os.X_OK):
        logger.info(f"wifi-connect binary already present at {binary_dest}")
        return binary_dest

    triple = get_target_triple()
    if not triple:
        raise RuntimeError(
            f"Unsupported architecture '{platform.machine()}'. "
            "Please compile wifi-connect manually from https://github.com/balena-os/wifi-connect"
        )

    tar_filename = f"wifi-connect-{triple}.tar.gz"
    url = f"https://github.com/balena-os/wifi-connect/releases/download/{version}/{tar_filename}"
    logger.info(f"Downloading balena wifi-connect from {url}...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_tar = Path(tmp_dir) / tar_filename
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Balena-WiFi-Installer)"})
        with urllib.request.urlopen(req, timeout=30.0) as resp, open(tmp_tar, "wb") as out:
            shutil.copyfileobj(resp, out)

        with tarfile.open(tmp_tar, "r:gz") as tar:
            tar.extractall(path=tmp_dir)

        # Look for wifi-connect binary in extracted files
        extracted_bin = None
        for root, _, files in os.walk(tmp_dir):
            if "wifi-connect" in files:
                extracted_bin = Path(root) / "wifi-connect"
                break

        if not extracted_bin:
            raise RuntimeError(f"wifi-connect binary not found inside {tar_filename}")

        shutil.copy2(extracted_bin, binary_dest)
        binary_dest.chmod(0o755)

    logger.info(f"Successfully installed wifi-connect to {binary_dest}")
    return binary_dest
