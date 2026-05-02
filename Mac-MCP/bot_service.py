"""
Lotus Bot Service — macOS Background Process
=============================================
Runs the Telegram bot as a standalone background process.
  1. Starts fast (no GUI)
  2. Runs independently of the control panel
  3. Writes a PID file so the GUI can track / stop it
  4. Auto-restarts on crash with exponential backoff

Usage:
  python bot_service.py          # foreground (debug)
  python bot_service.py &        # background (shell)
  # Or launched automatically by app.py
"""

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "src"

APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "Lotus"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
(APP_DATA_DIR / "logs").mkdir(exist_ok=True)

CONFIG_FILE = BASE_DIR / "config.json"
PID_FILE = APP_DATA_DIR / "lotus_bot.pid"
LOG_FILE = APP_DATA_DIR / "logs" / "bot_service.log"

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("bot_service")

# Console handler when running interactively
if sys.stderr and hasattr(sys.stderr, "write"):
    try:
        _ch = logging.StreamHandler(sys.stderr)
        _ch.setLevel(logging.INFO)
        _ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        _log.addHandler(_ch)
    except Exception:
        pass


# ── Helpers ────────────────────────────────────────────────────────────────

def write_pid() -> None:
    PID_FILE.write_text(str(os.getpid()))
    _log.info("PID %d written to %s", os.getpid(), PID_FILE)


def remove_pid() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
        _log.info("PID file removed")
    except Exception:
        pass


def load_config() -> dict | None:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            _log.error("Failed to load config.json: %s", e)
    else:
        _log.error("config.json not found at %s — run app.py first", CONFIG_FILE)
    return None


def is_already_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        import psutil
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()).lower()
        if "bot_service" in cmdline or "telegram_bot" in cmdline or "mac_mcp" in cmdline:
            _log.info("Bot already running (PID %d)", pid)
            return True
    except Exception:
        remove_pid()
    return False


# ── Main ───────────────────────────────────────────────────────────────────

def run_service() -> None:
    _log.info("=== Lotus Bot Service starting (macOS) ===")

    if is_already_running():
        _log.info("Another instance already running — exiting.")
        sys.exit(0)

    config = load_config()
    token = (config or {}).get("telegram_token") or (config or {}).get("bot_token", "")
    if not token:
        _log.error("No token in config.json — run app.py first.")
        sys.exit(1)

    write_pid()

    def _cleanup(signum=None, frame=None):
        _log.info("Signal %s received — shutting down", signum)
        remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    # Set env vars from config so telegram_bot picks them up
    os.environ["TELEGRAM_BOT_TOKEN"] = token
    allowed = str((config or {}).get("allowed_user_id") or (config or {}).get("allowed_user_ids", ""))
    if allowed:
        os.environ["TELEGRAM_ALLOWED_USER_IDS"] = allowed
    model = (config or {}).get("model_name") or (config or {}).get("model", "phi3")
    os.environ.setdefault("OLLAMA_MODEL", model)

    os.chdir(str(BASE_DIR))

    max_retries = 5
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            _log.info("Starting bot (attempt %d/%d)…", attempt, max_retries)
            from mac_mcp.telegram_bot import run_bot
            run_bot(token=token)
            _log.info("Bot stopped normally.")
            break
        except SystemExit:
            _log.info("Bot exited via SystemExit.")
            break
        except KeyboardInterrupt:
            _log.info("KeyboardInterrupt — stopping.")
            break
        except Exception as e:
            _log.exception("Bot crashed (attempt %d/%d): %s", attempt, max_retries, e)
            if attempt < max_retries:
                _log.info("Restarting in %ds…", retry_delay)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
            else:
                _log.error("Max retries reached — giving up.")

    remove_pid()
    _log.info("=== Lotus Bot Service stopped ===")


if __name__ == "__main__":
    run_service()
