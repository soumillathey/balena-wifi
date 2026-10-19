#!/usr/bin/env bash
# install.sh — Setup script for balena wifi-connect on Linux / Raspberry Pi
set -e

echo "=== Balena WiFi Installer ==="

ARCH="$(uname -m)"
echo "Detected architecture: $ARCH"

case "$ARCH" in
    x86_64|amd64)
        TARGET="linux-amd64"
        ;;
    aarch64|arm64)
        TARGET="linux-aarch64"
        ;;
    armv7l|armv7|armv8l|armhf)
        TARGET="linux-armv7hf"
        ;;
    i386|i686)
        TARGET="linux-i386"
        ;;
    *)
        echo "Warning: Unrecognized architecture $ARCH."
        TARGET=""
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
mkdir -p "$BIN_DIR"

if [ -n "$TARGET" ]; then
    VERSION="v4.11.1"
    ZIP_NAME="wifi-connect-$VERSION-$TARGET.zip"
    DOWNLOAD_URL="https://github.com/balena-os/wifi-connect/releases/download/$VERSION/$ZIP_NAME"

    echo "Downloading balena wifi-connect ($VERSION) from GitHub..."
    TMP_DIR="$(mktemp -d)"
    curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/$ZIP_NAME"

    if command -v unzip >/dev/null 2>&1; then
        unzip -q "$TMP_DIR/$ZIP_NAME" -d "$TMP_DIR"
    else
        python3 -c "import zipfile; zipfile.ZipFile('$TMP_DIR/$ZIP_NAME').extractall('$TMP_DIR')"
    fi
    
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

# Ensure Wi-Fi is unblocked
if command -v rfkill >/dev/null 2>&1; then
    rfkill unblock wifi 2>/dev/null || true
fi

echo "=== Balena WiFi Setup Ready ==="
