"""
Lotus System Tray Launcher
==========================
Runs in the Windows notification area. Right-click menu:
    🌸 Open Lotus       → opens the control panel (Lotus.exe --gui)
    ▶  Start Bot        → spawns bot_service.py if not already running
    ⏹  Stop Bot         → stops the running bot via PID file
    🌐 Open Telegram    → opens t.me link
    ℹ  Check for Updates → calls updater.check_for_updates
    ✖  Exit             → stops bot and exits tray

The tray uses pystray + Pillow. It is the recommended entry point for
silent / startup launches — `Lotus.exe --tray` (or no args) starts here.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
import webbrowser

# pystray + PIL are runtime deps; soft-fail if missing during dev imports
try:
    import pystray
    from PIL import Image
except Exception as e:  # pragma: no cover
    print(f"[lotus_tray] Missing dependency: {e}. Install pystray + pillow.")
    raise

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
DATA_DIR = os.path.join(PROGRAM_DATA, "Lotus")
PID_FILE = os.path.join(DATA_DIR, "lotus_bot.pid")

ICON_PATH = os.path.join(BASE_DIR, "assets", "lotus_icon.ico")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "lotus_logo.png")
BOT_SERVICE = os.path.join(BASE_DIR, "bot_service.py")
LOTUS_EXE = os.path.join(BASE_DIR, "Lotus.exe")


# ── Helpers ───────────────────────────────────────────────────────────────

def _load_icon() -> Image.Image:
    for path in (ICON_PATH, LOGO_PATH):
        if os.path.isfile(path):
            try:
                return Image.open(path)
            except Exception as e:
                logger.debug("Could not open %s: %s", path, e)
    # Fallback: 64x64 magenta lotus dot
    img = Image.new("RGB", (64, 64), color=(236, 64, 122))
    return img


def _read_pid() -> int | None:
    if not os.path.isfile(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _verify_lotus_pid(pid: int) -> bool:
    """Confirm pid actually belongs to a Lotus bot/tray process — not a
    recycled PID owned by something unrelated."""
    try:
        import psutil
        if not psutil.pid_exists(pid):
            return False
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()).lower()
        name = (proc.name() or "").lower()
    except Exception:
        return False
    markers = ("bot_service", "telegram_bot", "lotus.exe", "lotustray.exe")
    return any(m in cmdline for m in markers) or any(m in name for m in markers)


def _is_bot_running() -> bool:
    pid = _read_pid()
    if not pid:
        return False
    if _verify_lotus_pid(pid):
        return True
    # Stale PID file — clean it up so the next start works
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    return False


def _spawn_bot_service() -> bool:
    """Start bot_service.py headlessly. Returns True on launch."""
    if _is_bot_running():
        return True

    # Prefer pythonw.exe (no console). Fall back to python.exe / Lotus.exe.
    if getattr(sys, "frozen", False) and os.path.isfile(LOTUS_EXE):
        cmd = [LOTUS_EXE, "--bot-service"]
    else:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        runner = pythonw if os.path.isfile(pythonw) else sys.executable
        cmd = [runner, BOT_SERVICE]

    creation = 0
    if os.name == "nt":
        creation = 0x08000000  # CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creation,
        )
    except Exception as e:
        logger.error("Failed to spawn bot service: %s", e)
        return False

    # Give it a moment to write its PID
    for _ in range(20):
        time.sleep(0.25)
        if _is_bot_running():
            return True
    return False


def _stop_bot_service() -> bool:
    pid = _read_pid()
    if not pid:
        return True
    if not _verify_lotus_pid(pid):
        # Stale or hijacked PID — refuse to terminate and just clean up
        logger.info("Refusing to terminate pid %s — not a Lotus process", pid)
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return True
    try:
        import psutil
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return True
    except Exception as e:
        logger.warning("Could not stop bot (pid %s): %s", pid, e)
        return False


def _open_control_panel() -> None:
    if getattr(sys, "frozen", False) and os.path.isfile(LOTUS_EXE):
        try:
            subprocess.Popen([LOTUS_EXE, "--gui"], cwd=BASE_DIR)
            return
        except Exception as e:
            logger.warning("Could not launch Lotus.exe --gui: %s", e)
    # Dev fallback: try `python app.py`
    app_py = os.path.join(BASE_DIR, "app.py")
    if os.path.isfile(app_py):
        try:
            subprocess.Popen([sys.executable, app_py], cwd=BASE_DIR)
        except Exception as e:
            logger.warning("Could not launch app.py: %s", e)


def _open_telegram(_icon=None, _item=None) -> None:
    webbrowser.open("https://t.me")


def _check_updates(_icon=None, _item=None) -> None:
    try:
        # In frozen onefile builds, PyInstaller extracts bundled data to
        # sys._MEIPASS. In dev, fall back to the on-disk src/ tree.
        meipass = getattr(sys, "_MEIPASS", None)
        for candidate in (
            os.path.join(meipass, "src") if meipass else None,
            os.path.join(BASE_DIR, "src"),
        ):
            if candidate and os.path.isdir(candidate) and candidate not in sys.path:
                sys.path.insert(0, candidate)

        from windows_mcp.updater import check_for_updates  # type: ignore
        result = check_for_updates()
        msg = result.get("message", "")
        if result.get("is_outdated"):
            webbrowser.open(result.get("url", ""))
        # Show via Windows toast if possible, else print
        try:
            from win10toast import ToastNotifier  # type: ignore
            ToastNotifier().show_toast("Lotus", msg, duration=5, threaded=True)
        except Exception:
            print(msg)
    except Exception as e:
        logger.error("Update check failed: %s", e)


# ── Tray actions ──────────────────────────────────────────────────────────

def _on_open(icon, _item):
    threading.Thread(target=_open_control_panel, daemon=True).start()


def _on_start(icon, _item):
    threading.Thread(target=_spawn_bot_service, daemon=True).start()


def _on_stop(icon, _item):
    threading.Thread(target=_stop_bot_service, daemon=True).start()


def _on_exit(icon, _item):
    _stop_bot_service()
    icon.stop()


def _bot_status_text(_item) -> str:
    return "● Bot: Running" if _is_bot_running() else "○ Bot: Stopped"


def build_menu() -> "pystray.Menu":
    return pystray.Menu(
        pystray.MenuItem(_bot_status_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Lotus", _on_open, default=True),
        pystray.MenuItem("Start Bot", _on_start, enabled=lambda _: not _is_bot_running()),
        pystray.MenuItem("Stop Bot", _on_stop, enabled=lambda _: _is_bot_running()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Telegram", _open_telegram),
        pystray.MenuItem("Check for Updates", _check_updates),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", _on_exit),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    icon = pystray.Icon(
        "Lotus",
        icon=_load_icon(),
        title="Lotus — AI Control Agent",
        menu=build_menu(),
    )

    # Auto-start the bot service when the tray launches
    threading.Thread(target=_spawn_bot_service, daemon=True).start()

    icon.run()


if __name__ == "__main__":
    main()
