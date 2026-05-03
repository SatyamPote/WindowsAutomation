"""
Lotus Control API
=================
Lightweight HTTP control server that runs inside bot_service.py as a daemon
thread. The Swift macOS app uses this to read status, stream logs, and manage
the service without touching Telegram.

All endpoints are on 127.0.0.1 only — no external exposure.

Endpoints
---------
GET  /api/status    service health, PID, uptime, telegram + ollama state
GET  /api/logs      last N log lines  (?lines=100)
GET  /api/config    current config.json (token is redacted)
POST /api/config    overwrite config fields; restart required to apply
POST /api/restart   save response → SIGTERM self → launchd/app restarts
POST /api/stop      SIGTERM self (caller must restart manually)
GET  /api/version   version string
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

_log = logging.getLogger(__name__)

# ── Module-level state (set by start()) ────────────────────────────────────────

_config_file: Path | None = None
_log_file: Path | None = None
_port_file: Path | None = None
_start_time: float = 0.0
_port: int = 40510
_server: HTTPServer | None = None

# Written by bot_service.py to expose runtime state to status endpoint
_service_state: dict[str, Any] = {
    "telegram_started": False,
    "model_name": "",
}

# ── Ollama reachability cache (avoids 1-sec timeout on every status poll) ──────

_ollama_cache: dict[str, Any] = {"reachable": False, "at": 0.0}
_OLLAMA_TTL = 30.0


def _ollama_reachable() -> bool:
    now = time.time()
    if now - _ollama_cache["at"] < _OLLAMA_TTL:
        return _ollama_cache["reachable"]
    # Refresh in background; return stale value immediately
    threading.Thread(target=_refresh_ollama, daemon=True).start()
    return _ollama_cache["reachable"]


def _refresh_ollama() -> None:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            _ollama_cache["reachable"] = r.status == 200
    except Exception:
        _ollama_cache["reachable"] = False
    _ollama_cache["at"] = time.time()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if _config_file and _config_file.exists():
        try:
            return json.loads(_config_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _redact_token(token: str) -> str:
    """Show enough of the token to identify it without exposing the secret."""
    if not token or len(token) < 14:
        return "***"
    return token[:8] + "****" + token[-6:]


def _tail_log(n: int = 100) -> list[str]:
    if not _log_file or not _log_file.exists():
        return []
    try:
        with open(_log_file, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-n:]]
    except Exception:
        return []


# ── Request handler ────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args) -> None:  # suppress access log spam
        pass

    # ── Response helpers ──

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "127.0.0.1")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                return json.loads(self.rfile.read(length))
        except Exception:
            pass
        return {}

    # ── CORS preflight ──

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── GET ──

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        match parsed.path:
            case "/api/status":
                cfg = _load_config()
                self._send_json({
                    "running": True,
                    "pid": os.getpid(),
                    "uptime_seconds": int(time.time() - _start_time),
                    "telegram_connected": _service_state.get("telegram_started", False),
                    "ollama_model": cfg.get("model_name") or _service_state.get("model_name", ""),
                    "ollama_reachable": _ollama_reachable(),
                    "service_version": "1.0.0",
                    "control_port": _port,
                })

            case "/api/logs":
                n = int(params.get("lines", ["100"])[0])
                n = max(1, min(n, 1000))
                self._send_json({"lines": _tail_log(n)})

            case "/api/config":
                cfg = _load_config()
                redacted = dict(cfg)
                if "telegram_token" in redacted:
                    redacted["telegram_token"] = _redact_token(redacted["telegram_token"])
                self._send_json(redacted)

            case "/api/version":
                self._send_json({"version": "1.0.0", "service": "com.lotus.botservice"})

            case _:
                self._send_json({"error": "not found"}, 404)

    # ── POST ──

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        match path:
            case "/api/config":
                body = self._read_body()
                if not body:
                    self._send_json({"error": "empty body"}, 400)
                    return
                cfg = _load_config()
                # Only overwrite keys that are present and non-empty in the request
                for k, v in body.items():
                    if v is not None and v != "":
                        cfg[k] = v
                if not cfg.get("created_at"):
                    cfg["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                try:
                    if _config_file:
                        _config_file.write_text(
                            json.dumps(cfg, indent=2), encoding="utf-8"
                        )
                    self._send_json({"ok": True})
                except Exception as e:
                    _log.error("Config write failed: %s", e)
                    self._send_json({"error": str(e)}, 500)

            case "/api/restart":
                # Send response first, then exit after a short delay.
                # launchd (KeepAlive=false) will NOT auto-restart; the Swift app
                # must call launchctl kickstart after receiving this response.
                self._send_json({"ok": True})
                _log.info("Restart requested via control API — sending SIGTERM")
                threading.Timer(0.25, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()

            case "/api/stop":
                self._send_json({"ok": True})
                _log.info("Stop requested via control API — sending SIGTERM")
                threading.Timer(0.25, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()

            case _:
                self._send_json({"error": "not found"}, 404)


# ── Public API ─────────────────────────────────────────────────────────────────

def start(
    config_file: Path,
    log_file: Path,
    port_file: Path,
    port: int = 40510,
) -> HTTPServer:
    """Start the control server in a background daemon thread.

    Tries ``port`` first; scans up to port+9 on EADDRINUSE.
    Writes the chosen port to ``port_file`` so the Swift app can discover it.
    Returns the HTTPServer instance (pass to ``stop()`` to shut down).
    """
    global _config_file, _log_file, _port_file, _port, _server, _start_time

    _config_file = config_file
    _log_file = log_file
    _port_file = port_file
    _start_time = time.time()

    # Find a free port
    import socket
    actual_port = port
    for candidate in range(port, port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", candidate))
            actual_port = candidate
            break
        except OSError:
            continue
    else:
        _log.warning("No free port found in %d–%d; using %d anyway", port, port + 9, port)
        actual_port = port

    _port = actual_port
    _server = HTTPServer(("127.0.0.1", actual_port), _Handler)

    # Write port file for Swift app discovery
    try:
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(str(actual_port), encoding="utf-8")
    except Exception as e:
        _log.warning("Could not write port file: %s", e)

    t = threading.Thread(
        target=_server.serve_forever,
        daemon=True,
        name="lotus-control-api",
    )
    t.start()
    _log.info("🌐 Control API listening on http://127.0.0.1:%d", actual_port)
    return _server


def stop() -> None:
    """Shut down the HTTP server and remove the port file."""
    global _server
    if _server:
        try:
            _server.shutdown()
        except Exception:
            pass
        _server = None
    if _port_file and _port_file.exists():
        try:
            _port_file.unlink()
        except Exception:
            pass
    _log.info("Control API stopped")


def set_telegram_started(started: bool, model: str = "") -> None:
    """Called by bot_service.py to update the Telegram connection state."""
    _service_state["telegram_started"] = started
    if model:
        _service_state["model_name"] = model
