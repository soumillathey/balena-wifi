#!/usr/bin/env bash
# install.sh — Setup script for balena wifi-connect on Linux / Raspberry Pi
set -e

echo "=== Balena WiFi Installer ==="

# Check Linux architecture
ARCH="$(uname -m)"
echo "Detected architecture: $ARCH"

case "$ARCH" in
    x86_64)
        TRIPLE="x86_64-unknown-linux-gnu"
        ;;
    aarch64|arm64)
        TRIPLE="aarch64-unknown-linux-gnu"
        ;;
    armv7l|armv7)
        TRIPLE="armv7-unknown-linux-gnueabihf"
        ;;
    *)
        echo "Warning: Unrecognized architecture $ARCH. You may need to compile wifi-connect manually."
        TRIPLE=""
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
mkdir -p "$BIN_DIR"

if [ -n "$TRIPLE" ]; then
    VERSION="v4.11.1"
    TAR_NAME="wifi-connect-$TRIPLE.tar.gz"
    DOWNLOAD_URL="https://github.com/balena-os/wifi-connect/releases/download/$VERSION/$TAR_NAME"

    echo "Downloading balena wifi-connect ($VERSION) from GitHub..."
    TMP_DIR="$(mktemp -d)"
    curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/$TAR_NAME"
    tar -xzf "$TMP_DIR/$TAR_NAME" -C "$TMP_DIR"
    
    # Locate extracted binary
    EXTRACTED="$(find "$TMP_DIR" -type f -name wifi-connect | head -n 1)"
    if [ -n "$EXTRACTED" ]; then
        cp "$EXTRACTED" "$BIN_DIR/wifi-connect"
        chmod +x "$BIN_DIR/wifi-connect"
        echo "Installed wifi-connect to $BIN_DIR/wifi-connect"
        
        # Optionally symlink to /usr/local/sbin if root
        if [ "$(id -u)" -eq 0 ]; then
            ln -sf "$BIN_DIR/wifi-connect" /usr/local/sbin/wifi-connect
            echo "Symlinked to /usr/local/sbin/wifi-connect"
        fi
    else
        echo "Failed to extract wifi-connect binary."
    fi
    rm -rf "$TMP_DIR"
fi

echo "=== Balena WiFi Setup Ready ==="
