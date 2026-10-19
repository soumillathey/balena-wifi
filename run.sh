#!/usr/bin/env bash
# run.sh — Run balena Wi-Fi setup
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v uv >/dev/null 2>&1; then
    exec uv run python wifi_setup.py "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 wifi_setup.py "$@"
else
    exec python wifi_setup.py "$@"
fi
