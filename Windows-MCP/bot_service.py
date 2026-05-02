"""
Lotus Bot Service — Background Process
=======================================
This script runs the Telegram bot as a standalone background process.
It is designed to:
  1. Start FAST (no GUI, no heavy imports)
  2. Run independently of the control panel
  3. Write a PID file so the GUI can track / stop it
  4. Auto-restart on crash with backoff

Usage:
  pythonw.exe bot_service.py          # silent background
  python.exe  bot_service.py          # with console (debug)
"""

import json
import logging
import os
import sys
import time
import signal

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
DATA_DIR = os.path.join(PROGRAM_DATA, "Lotus")

PID_FILE = os.path.join(DATA_DIR, "lotus_bot.pid")
LOG_FILE = os.path.join(DATA_DIR, "logs", "bot_service.log")
CONFIG_FILE = os.path.join(DATA_DIR, "config", "config.json")

BOT_SCRIPT = os.path.join(BASE_DIR, "src", "windows_mcp", "telegram_bot.py")
BOT_SRC_DIR = os.path.join(BASE_DIR, "src")

# ── Logging ──
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("bot_service")

# Also log to stderr if running with a console
if sys.stderr and hasattr(sys.stderr, "write"):
    try:
        _console = logging.StreamHandler(sys.stderr)
        _console.setLevel(logging.INFO)
        _console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        _log.addHandler(_console)
    except Exception:
        pass


def write_pid():
    """Write current PID to file so the control panel can find us."""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    _log.info("PID %d written to %s", os.getpid(), PID_FILE)


def remove_pid():
    """Clean up PID file on exit."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            _log.info("PID file removed")
    except Exception:
        pass


def load_config() -> dict | None:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            _log.error("Failed to load config.json: %s", e)
    else:
        _log.error("CONFIG_FILE does not exist at %s", CONFIG_FILE)
    return None


def is_already_running() -> bool:
    """Check if another bot_service instance is already running."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # Check if process is alive
        import psutil
        proc = psutil.Process(pid)
        # Verify it's actually our bot service, not a recycled PID
        cmdline = " ".join(proc.cmdline()).lower()
        if "bot_service" in cmdline or "telegram_bot" in cmdline:
            _log.info("Bot already running (PID %d)", pid)
            return True
    except Exception:
        # Process doesn't exist or can't be checked — stale PID file
        remove_pid()
    return False


def run_service():
    """Main entry point — run the bot directly in this process."""
    _log.info("=== Lotus Bot Service starting ===")

    if is_already_running():
        _log.info("Another instance is already running. Exiting.")
        sys.exit(0)

    config = load_config()
    if not config or not config.get("bot_token"):
        _log.error("No config.json or missing bot_token. Run the Lotus app first for setup.")
        sys.exit(1)

    # Write PID
    write_pid()

    # Set up clean exit
    def _cleanup(signum=None, frame=None):
        _log.info("Received signal %s — shutting down", signum)
        remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    # Add bot src to path so imports resolve
    if BOT_SRC_DIR not in sys.path:
        sys.path.insert(0, BOT_SRC_DIR)

    # Set env vars from config
    os.environ["TELEGRAM_BOT_TOKEN"] = config.get("bot_token", "")
    os.environ["TELEGRAM_ALLOWED_USER_IDS"] = config.get("allowed_user_ids", "")

    # Change to BASE_DIR so relative paths in bot code work
    os.chdir(BASE_DIR)

    # Auto-restart loop with backoff
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            _log.info("Starting bot (attempt %d/%d)...", attempt, max_retries)

            # Import and run the bot directly (in-process, no subprocess)
            from windows_mcp.telegram_bot import run_bot
            run_bot(token=config["bot_token"])

            # If run_bot returns normally, bot was stopped cleanly
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
                _log.info("Restarting in %d seconds...", retry_delay)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # exponential backoff, max 60s
            else:
                _log.error("Max retries reached. Giving up.")
    
    remove_pid()
    _log.info("=== Lotus Bot Service stopped ===")


if __name__ == "__main__":
    run_service()
