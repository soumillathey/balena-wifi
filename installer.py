"""installer.py — Automatic installation and binary management for balena wifi-connect."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from constants import BASE_DIR

logger = logging.getLogger(__name__)

ARCH_MAP = {
    "aarch64": "linux-aarch64",
    "arm64": "linux-aarch64",
    "armv7l": "linux-armv7hf",
    "armv7": "linux-armv7hf",
    "armv8l": "linux-armv7hf",
    "armhf": "linux-armv7hf",
    "x86_64": "linux-amd64",
    "amd64": "linux-amd64",
    "i386": "linux-i386",
    "i686": "linux-i386",
}


def get_target_arch() -> Optional[str]:
    """Return the release architecture tag for the current machine."""
    mach = platform.machine().lower()
    return ARCH_MAP.get(mach)


get_target_triple = get_target_arch


def install_wifi_connect(target_dir: Optional[Path] = None, version: str = "v4.11.1") -> Path:
    """Download and install the official balena wifi-connect binary for current architecture."""
    dest_dir = target_dir or (BASE_DIR / "bin")
    dest_dir.mkdir(parents=True, exist_ok=True)
    binary_dest = dest_dir / "wifi-connect"

    if binary_dest.is_file() and os.access(binary_dest, os.X_OK):
        logger.info(f"wifi-connect binary already present at {binary_dest}")
        return binary_dest

    target = get_target_arch()
    if not target:
        raise RuntimeError(
            f"Unsupported architecture '{platform.machine()}'. "
            "Please compile wifi-connect manually from https://github.com/balena-os/wifi-connect"
        )

    zip_filename = f"wifi-connect-{version}-{target}.zip"
    url = f"https://github.com/balena-os/wifi-connect/releases/download/{version}/{zip_filename}"
    logger.info(f"Downloading balena wifi-connect from {url}...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_zip = Path(tmp_dir) / zip_filename
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Balena-WiFi-Installer)"})
        with urllib.request.urlopen(req, timeout=45.0) as resp, open(tmp_zip, "wb") as out:
            shutil.copyfileobj(resp, out)

        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(path=tmp_dir)

        # Look for wifi-connect binary in extracted files
        extracted_bin = None
        for root, _, files in os.walk(tmp_dir):
            if "wifi-connect" in files:
                extracted_bin = Path(root) / "wifi-connect"
                break

        if not extracted_bin:
            raise RuntimeError(f"wifi-connect binary not found inside {zip_filename}")

        shutil.copy2(extracted_bin, binary_dest)
        binary_dest.chmod(0o755)

        # Extract bundled UI assets if present and not already customized
        extracted_ui = Path(tmp_dir) / "ui"
        local_ui = BASE_DIR / "ui"
        if extracted_ui.is_dir() and not (local_ui / "index.html").exists():
            shutil.copytree(extracted_ui, local_ui, dirs_exist_ok=True)

    logger.info(f"Successfully installed wifi-connect to {binary_dest}")
    return binary_dest
