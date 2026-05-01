"""
Lotus Desktop Application
========================
CustomTkinter-based control panel with first-time setup,
bot start/stop controls, and config management.

The bot runs as an INDEPENDENT background process (bot_service.py).
Closing this GUI does NOT stop the bot — it keeps running.
The GUI minimizes to system tray on close.
"""

import customtkinter as ctk
from PIL import Image
import json
import logging
import os
import sys
import subprocess
import threading
import time
import winreg

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE    = os.path.join(BASE_DIR, "logs", "lotus_app.log")
PID_FILE    = os.path.join(BASE_DIR, "lotus_bot.pid")

# Bot service script (runs independently)
BOT_SERVICE = os.path.join(BASE_DIR, "bot_service.py")

# ── File logger (failsafe — always active) ──
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("lotus")


# ── Startup Registry Helpers ──
STARTUP_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APP_NAME = "LotusControlPanel"


def _get_startup_command() -> str:
    """Return the command that starts the BOT SERVICE (not the GUI) on login.
    This ensures the bot starts fast and silently in background."""
    python_exe = sys.executable
    # Prefer pythonw.exe so no black console flashes on startup
    pythonw = python_exe.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        _log.warning("pythonw.exe not found at %s — falling back to python.exe", pythonw)
        pythonw = python_exe
    cmd = f'"{pythonw}" "{BOT_SERVICE}"'
    _log.debug("Startup command: %s", cmd)
    return cmd


def is_startup_enabled() -> bool:
    """Check whether Lotus is registered in the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0,
                             winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, STARTUP_APP_NAME)
        winreg.CloseKey(key)
        return val == _get_startup_command()
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_startup():
    """Add Lotus bot service to the Windows startup registry."""
    cmd = _get_startup_command()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0,
                         winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, STARTUP_APP_NAME, 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    _log.info("Startup registry set: %s", cmd)


def disable_startup():
    """Remove Lotus from the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0,
                             winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, STARTUP_APP_NAME)
        winreg.CloseKey(key)
        _log.info("Startup registry entry removed.")
    except FileNotFoundError:
        pass


# ── Theme ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Color Palette: Pure Black + Lotus Blue ──
BG_DARK        = "#080808"   # near-pure black background
BG_CARD        = "#111111"   # slightly lifted card surface
ACCENT         = "#3b82f6"   # lotus blue (matches logo)
ACCENT_HOVER   = "#60a5fa"   # lighter lotus blue on hover
GREEN          = "#3fb950"
RED            = "#f85149"
YELLOW         = "#e3a54a"
TEXT_PRIMARY   = "#ffffff"   # pure white
TEXT_SECONDARY = "#aaaaaa"   # soft grey
BORDER         = "#2a2a2a"   # very dark border

# ── Logo ──
LOGO_PATH = os.path.join(BASE_DIR, "assets", "lotus_logo.png")


def _load_logo(size: int = 90) -> ctk.CTkImage | None:
    """Load the lotus PNG as a CTkImage for HiDPI display."""
    try:
        if os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        pass
    return None


def load_config() -> dict | None:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_config(data: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Bot Process Management (PID-based) ──

def _get_bot_pid() -> int | None:
    """Read the bot's PID from the PID file."""
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _is_bot_alive() -> bool:
    """Check if the bot service process is actually running."""
    pid = _get_bot_pid()
    if pid is None:
        return False
    try:
        import psutil
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != "zombie"
    except Exception:
        return False


def _start_bot_service():
    """Launch bot_service.py as a fully detached background process."""
    python_exe = sys.executable
    pythonw = python_exe.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = python_exe

    # DETACHED_PROCESS + CREATE_NO_WINDOW + CREATE_NEW_PROCESS_GROUP
    # This makes the bot completely independent of this GUI process
    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    subprocess.Popen(
        [pythonw, BOT_SERVICE],
        cwd=BASE_DIR,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        start_new_session=True,
    )
    _log.info("Bot service launched as detached process")


def _stop_bot_service():
    """Stop the bot service by sending SIGTERM to its PID."""
    pid = _get_bot_pid()
    if pid is None:
        _log.info("No PID file — bot is not running")
        return

    try:
        import psutil
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        _log.info("Bot service (PID %d) stopped", pid)
    except Exception as e:
        _log.error("Failed to stop bot (PID %d): %s", pid, e)

    # Clean up PID file
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass


class LotusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        _log.info("=== Lotus app started ===")

        self.title("Lotus Control Panel")
        self.geometry("520x720")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config       = load_config()
        self._status_poll = None  # for after() polling

        # Try to set icon
        icon_path = os.path.join(BASE_DIR, "assets", "lotus_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        if self.config:
            self.show_control_panel()
        else:
            self.show_setup()

    # ──────────────────────────────────────────────
    # SETUP SCREEN
    # ──────────────────────────────────────────────
    def show_setup(self):
        self.clear_window()

        # Use a scrollable frame so content is never clipped
        outer = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        outer.pack(fill="both", expand=True)

        frame = ctk.CTkScrollableFrame(
            outer, fg_color=BG_DARK, corner_radius=0,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=TEXT_SECONDARY
        )
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        # Logo / Title
        _logo = _load_logo(80)
        if _logo:
            ctk.CTkLabel(frame, image=_logo, text="").pack(pady=(10, 2))
        else:
            ctk.CTkLabel(frame, text="🪷", font=("Segoe UI Emoji", 44)).pack(pady=(10, 2))
        ctk.CTkLabel(
            frame, text="Lotus", font=("Segoe UI", 32, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(0, 2))
        ctk.CTkLabel(
            frame, text="Windows Control Agent",
            font=("Segoe UI", 13), text_color=TEXT_SECONDARY
        ).pack(pady=(0, 16))

        # Separator
        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=6)

        ctk.CTkLabel(
            frame, text="First-Time Setup",
            font=("Segoe UI", 16, "bold"), text_color=ACCENT
        ).pack(pady=(8, 14))

        # Bot Token
        ctk.CTkLabel(
            frame, text="Telegram Bot Token", font=("Segoe UI", 13),
            text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x")
        self.token_entry = ctk.CTkEntry(
            frame, height=40, font=("Consolas", 13),
            placeholder_text="e.g. 123456:ABC-DEF...",
            fg_color=BG_CARD, border_color=BORDER, text_color=TEXT_PRIMARY
        )
        self.token_entry.pack(fill="x", pady=(4, 12))

        # Allowed User IDs
        ctk.CTkLabel(
            frame, text="Allowed Telegram User IDs (comma-separated)",
            font=("Segoe UI", 13), text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x")
        self.ids_entry = ctk.CTkEntry(
            frame, height=40, font=("Consolas", 13),
            placeholder_text="e.g. 123456789,987654321",
            fg_color=BG_CARD, border_color=BORDER, text_color=TEXT_PRIMARY
        )
        self.ids_entry.pack(fill="x", pady=(4, 12))

        # Your Name
        ctk.CTkLabel(
            frame, text="Your Name", font=("Segoe UI", 13),
            text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x")
        self.name_entry = ctk.CTkEntry(
            frame, height=40, font=("Segoe UI", 13),
            placeholder_text="e.g. Satyam",
            fg_color=BG_CARD, border_color=BORDER, text_color=TEXT_PRIMARY
        )
        self.name_entry.pack(fill="x", pady=(4, 16))

        # Error label
        self.setup_error = ctk.CTkLabel(
            frame, text="", font=("Segoe UI", 12), text_color=RED
        )
        self.setup_error.pack()

        # Save button — large and clearly visible
        ctk.CTkButton(
            frame, text="💾  Save & Continue", height=50,
            font=("Segoe UI", 16, "bold"), corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#0d1117", command=self.save_setup
        ).pack(fill="x", pady=(8, 20))

    def save_setup(self):
        token    = self.token_entry.get().strip()
        user_ids = self.ids_entry.get().strip()
        name     = self.name_entry.get().strip()

        if not token:
            self.setup_error.configure(text="⚠ Bot Token is required.")
            return
        if not name:
            self.setup_error.configure(text="⚠ Your Name is required.")
            return
        if ":" not in token:
            self.setup_error.configure(text="⚠ Invalid token format.")
            return

        self.config = {
            "bot_token":          token,
            "allowed_user_ids":   user_ids,
            "user_name":          name,
            "created_at":         time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_config(self.config)
        _log.info("Config saved for user: %s", name)
        self.show_control_panel()

    # ──────────────────────────────────────────────
    # CONTROL PANEL
    # ──────────────────────────────────────────────
    def show_control_panel(self):
        self.clear_window()
        name = self.config.get("user_name", "User")

        frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=40, pady=30)

        # Header
        _logo = _load_logo(90)
        if _logo:
            ctk.CTkLabel(frame, image=_logo, text="").pack(pady=(10, 2))
        else:
            ctk.CTkLabel(frame, text="🪷", font=("Segoe UI Emoji", 42)).pack(pady=(10, 2))
        ctk.CTkLabel(
            frame, text="Lotus", font=("Segoe UI", 32, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            frame, text=f"Hello {name} 👋",
            font=("Segoe UI", 16), text_color=TEXT_SECONDARY
        ).pack(pady=(0, 20))

        # Status card
        status_card = ctk.CTkFrame(
            frame, fg_color=BG_CARD, corner_radius=12, border_width=1,
            border_color=BORDER
        )
        status_card.pack(fill="x", pady=(0, 20), ipady=14)

        self.status_icon = ctk.CTkLabel(
            status_card, text="⏹", font=("Segoe UI Emoji", 22)
        )
        self.status_icon.pack(side="left", padx=(20, 8))

        status_text_frame = ctk.CTkFrame(status_card, fg_color="transparent")
        status_text_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            status_text_frame, text="Bot Status",
            font=("Segoe UI", 11), text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x")
        self.status_label = ctk.CTkLabel(
            status_text_frame, text="Checking...",
            font=("Segoe UI", 18, "bold"), text_color=YELLOW, anchor="w"
        )
        self.status_label.pack(fill="x")

        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶  Start Bot", height=48,
            font=("Segoe UI", 15, "bold"), corner_radius=10,
            fg_color=GREEN, hover_color="#2ea043",
            text_color="#0d1117", command=self.start_bot
        )
        self.start_btn.pack(fill="x", pady=(0, 10))

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹  Stop Bot", height=48,
            font=("Segoe UI", 15, "bold"), corner_radius=10,
            fg_color=RED, hover_color="#da3633",
            text_color="#ffffff", command=self.stop_bot, state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=(0, 10))

        # Separator
        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=10)

        # ── Startup toggle ──
        startup_card = ctk.CTkFrame(
            frame, fg_color=BG_CARD, corner_radius=10,
            border_width=1, border_color=BORDER
        )
        startup_card.pack(fill="x", pady=(0, 10), ipady=6)

        startup_left = ctk.CTkFrame(startup_card, fg_color="transparent")
        startup_left.pack(side="left", fill="x", expand=True, padx=(14, 0))

        ctk.CTkLabel(
            startup_left, text="🚀  Run on Windows Startup",
            font=("Segoe UI", 13, "bold"), text_color=TEXT_PRIMARY, anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            startup_left, text="Auto-launch bot silently when you log in",
            font=("Segoe UI", 11), text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x")

        self.startup_switch = ctk.CTkSwitch(
            startup_card, text="",
            width=52, onvalue=True, offvalue=False,
            progress_color=ACCENT, button_color=TEXT_PRIMARY,
            command=self.toggle_startup
        )
        self.startup_switch.pack(side="right", padx=14)

        # ── Always enable startup on launch ──
        if not is_startup_enabled():
            try:
                enable_startup()
            except Exception as exc:
                _log.error("Failed to set startup registry: %s", exc)
        self.startup_switch.select()
        self.startup_switch.configure(state="disabled")  # permanently ON

        # ── Minimize-to-tray info ──
        tray_card = ctk.CTkFrame(
            frame, fg_color=BG_CARD, corner_radius=10,
            border_width=1, border_color=BORDER
        )
        tray_card.pack(fill="x", pady=(0, 10), ipady=6)

        ctk.CTkLabel(
            tray_card, text="🔒  Closing this window hides to background",
            font=("Segoe UI", 12), text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x", padx=14)
        ctk.CTkLabel(
            tray_card, text="Bot keeps running even if you close this panel",
            font=("Segoe UI", 11), text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x", padx=14)

        # Separator
        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=10)

        # Utility buttons
        util_frame = ctk.CTkFrame(frame, fg_color="transparent")
        util_frame.pack(fill="x")

        ctk.CTkButton(
            util_frame, text="⚙ Change Settings", height=38,
            font=("Segoe UI", 13), corner_radius=8,
            fg_color=BG_CARD, hover_color=BORDER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_SECONDARY, command=self.change_settings
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        ctk.CTkButton(
            util_frame, text="🔄 Reset Setup", height=38,
            font=("Segoe UI", 13), corner_radius=8,
            fg_color=BG_CARD, hover_color=BORDER,
            border_width=1, border_color=BORDER,
            text_color=YELLOW, command=self.reset_setup
        ).pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Log area
        ctk.CTkLabel(
            frame, text="Console Output",
            font=("Segoe UI", 12), text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x", pady=(16, 4))

        self.log_box = ctk.CTkTextbox(
            frame, height=120, font=("Consolas", 11),
            fg_color=BG_CARD, text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER, corner_radius=8,
            state="disabled"
        )
        self.log_box.pack(fill="x")

        self.log("Lotus ready.")

        # ── Check bot status and auto-start if not running ──
        self._poll_bot_status()

    # ──────────────────────────────────────────────
    # BOT CONTROL (PID-based, independent process)
    # ──────────────────────────────────────────────
    def _poll_bot_status(self):
        """Periodically check if the bot service is alive and update UI."""
        alive = _is_bot_alive()
        self._update_ui_status(alive)

        if not alive and self.config:
            # Auto-start the bot if it's not running
            self.log("🤖 Bot not running — auto-starting...")
            self.start_bot()

        # Poll every 5 seconds
        self._status_poll = self.after(5000, self._poll_bot_status_silent)

    def _poll_bot_status_silent(self):
        """Silent status poll (no auto-start, just UI update)."""
        try:
            alive = _is_bot_alive()
            self._update_ui_status(alive)
        except Exception:
            pass
        self._status_poll = self.after(5000, self._poll_bot_status_silent)

    def _update_ui_status(self, running: bool):
        """Update the status label and button states based on bot state."""
        try:
            if running:
                pid = _get_bot_pid()
                self.status_label.configure(text=f"Running (PID {pid})", text_color=GREEN)
                self.status_icon.configure(text="✅")
                self.start_btn.configure(state="disabled")
                self.stop_btn.configure(state="normal")
            else:
                self.status_label.configure(text="Stopped", text_color=RED)
                self.status_icon.configure(text="⏹")
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
        except Exception:
            pass  # widgets may not exist during transitions

    def start_bot(self):
        if _is_bot_alive():
            self.log("Bot is already running.")
            return

        _log.info("Starting bot service...")
        self.log("Starting Lotus bot service...")

        try:
            _start_bot_service()
            self.log("✅ Bot service launched.")
            _log.info("Bot service launched successfully")

            # Give it a moment to write PID, then check
            self.after(2000, self._check_bot_started)
        except Exception as e:
            self.log(f"❌ Failed to start bot: {e}")
            _log.error("Failed to start bot: %s", e)

    def _check_bot_started(self):
        """Verify the bot actually started after launch."""
        if _is_bot_alive():
            pid = _get_bot_pid()
            self.log(f"✅ Bot confirmed running (PID {pid})")
            self._update_ui_status(True)
        else:
            self.log("⚠ Bot may still be starting up...")

    def stop_bot(self):
        if not _is_bot_alive():
            self.log("Bot is not running.")
            self._update_ui_status(False)
            return

        self.log("Stopping bot service...")
        _log.info("Stop requested by user")

        try:
            _stop_bot_service()
            self.log("⏹ Bot stopped.")
            _log.info("Bot stopped.")
        except Exception as e:
            self.log(f"❌ Stop error: {e}")
            _log.error("Stop error: %s", e)

        self._update_ui_status(False)

    def toggle_startup(self):
        """Startup is permanently enabled – re-select the switch if toggled."""
        self.startup_switch.select()
        self.log("ℹ Startup is permanently enabled for Lotus.")

    # ──────────────────────────────────────────────
    # UI HELPERS
    # ──────────────────────────────────────────────
    def log(self, msg: str):
        try:
            self.log_box.configure(state="normal")
            timestamp = time.strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{timestamp}] {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass  # log_box may not exist during setup screen

    def clear_window(self):
        # Cancel any pending status poll
        if hasattr(self, '_status_poll') and self._status_poll:
            self.after_cancel(self._status_poll)
            self._status_poll = None
        for widget in self.winfo_children():
            widget.destroy()

    def change_settings(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before changing settings.")
            return
        self.show_setup()
        # Pre-fill existing values
        if self.config:
            self.token_entry.insert(0, self.config.get("bot_token", ""))
            self.ids_entry.insert(0, self.config.get("allowed_user_ids", ""))
            self.name_entry.insert(0, self.config.get("user_name", ""))

    def reset_setup(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before resetting.")
            return
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.config = None
        self.show_setup()

    def on_close(self):
        """Hide the window instead of killing the bot.
        The bot runs independently and survives GUI close."""
        _log.info("GUI window closed — bot continues in background")
        self.withdraw()  # hide window

        # Show a brief notification that we're still running
        try:
            # Use a simple approach: after 100ms, fully destroy the GUI
            # The bot service keeps running independently
            self.after(500, self._really_close)
        except Exception:
            self.destroy()

    def _really_close(self):
        """Actually close the GUI. Bot keeps running."""
        _log.info("GUI destroyed — bot service remains active")
        self.destroy()


if __name__ == "__main__":
    _log.info("=== Startup triggered ===")

    # If bot is not running and config exists, start it immediately
    # (before the slow GUI loads)
    config = load_config()
    if config and config.get("bot_token") and not _is_bot_alive():
        _log.info("Pre-launching bot service before GUI...")
        try:
            _start_bot_service()
        except Exception as e:
            _log.error("Pre-launch failed: %s", e)

    app = LotusApp()
    app.mainloop()
    _log.info("=== App exited cleanly ===")
