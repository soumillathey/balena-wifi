"""server.py — Web server runner for balena Wi-Fi setup console."""
from __future__ import annotations

import logging
import threading
from typing import Optional

from flask import Flask
from routes import routes_bp
from werkzeug.serving import BaseWSGIServer, make_server

logging.getLogger("werkzeug").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(routes_bp)
    return app


_srv: Optional[BaseWSGIServer] = None
_lock = threading.Lock()


def start_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start standalone web portal server in a background thread."""
    global _srv
    with _lock:
        if _srv is not None:
            return
        app = create_app()
        try:
            _srv = make_server(host, port, app)
        except OSError as e:
            logger.warning(f"Could not bind web server to {host}:{port}: {e}")
            return

        threading.Thread(target=_srv.serve_forever, name="BalenaWebServer", daemon=True).start()
        logger.info(f"Web server started at http://{host}:{port}/wifi")


def stop_server() -> None:
    """Gracefully shutdown web portal server."""
    global _srv
    with _lock:
        if _srv is not None:
            _srv.shutdown()
            _srv = None
            logger.info("Web server stopped.")


__all__ = ["create_app", "start_server", "stop_server"]
