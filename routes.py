"""routes.py — Flask blueprint for balena Wi-Fi setup web portal and REST API."""
from __future__ import annotations

from typing import Any

from auth import create_token, validate_token, verify_login
from balena_driver import is_network_connected
from connection import connect_to_wifi
from constants import TEMPLATES_DIR
from flask import Blueprint, jsonify, redirect, render_template, request
from hotspot import get_available_networks, is_hotspot_active
from vault import (
    clear_saved_networks,
    get_network_password,
    get_saved_networks,
    save_network,
)

routes_bp = Blueprint("wifi_routes", __name__, template_folder=str(TEMPLATES_DIR))


def _is_auth() -> bool:
    tok = request.headers.get("X-Auth-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    return validate_token(tok.strip() if tok else None)


@routes_bp.route("/")
@routes_bp.route("/wifi")
def index() -> str:
    return render_template("wifi.html")


# Captive portal detection helper endpoints for iOS / Android / Windows
@routes_bp.route("/hotspot-detect.html")
@routes_bp.route("/generate_204")
@routes_bp.route("/canonical.html")
@routes_bp.route("/ncsi.txt")
def captive_portal_redirect() -> Any:
    """Redirect OS captive portal probes directly to the Wi-Fi setup page."""
    if not is_network_connected():
        return redirect("/wifi", code=302)
    return "", 204


@routes_bp.route("/api/login", methods=["POST"])
def post_login() -> Any:
    data = request.get_json(silent=True) or {}
    if verify_login(str(data.get("userid", "")), str(data.get("password", ""))):
        return jsonify({"success": True, "token": create_token()})
    return jsonify({"success": False, "error": "Invalid user ID or password."}), 401


@routes_bp.route("/api/status")
def status() -> Any:
    return jsonify({
        "connected": is_network_connected(),
        "hotspot": is_hotspot_active(),
        "saved": get_saved_networks(),
    })


@routes_bp.route("/api/networks")
def networks() -> Any:
    """Get list of scanned Wi-Fi access points from balena."""
    return jsonify({"networks": get_available_networks()})


@routes_bp.route("/api/wifi", methods=["POST"])
def post_wifi() -> Any:
    if not _is_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ssid = str(data.get("ssid", "")).strip()
    if not ssid:
        return jsonify({"success": False, "message": "SSID cannot be empty"}), 400

    pwd = str(data.get("password", "")).strip() or get_network_password(ssid) or ""
    save_network(ssid, pwd)

    ok, msg = connect_to_wifi(ssid, pwd)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)


@routes_bp.route("/api/wifi/clear", methods=["POST"])
def post_clear() -> Any:
    if not _is_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    clear_saved_networks()
    return jsonify({"success": True, "message": "Saved networks cleared."})


__all__ = ["routes_bp"]
