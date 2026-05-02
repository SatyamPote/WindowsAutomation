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
BASE_DIR_SRC = os.path.dirname(os.path.abspath(__file__))
MCP_SRC = os.path.join(BASE_DIR_SRC, "src")
if os.path.exists(MCP_SRC) and MCP_SRC not in sys.path:
    sys.path.insert(0, MCP_SRC)

PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
APP_DATA_DIR = os.path.join(PROGRAM_DATA, "Lotus")

# Config is now in the app directory for easier manual access
if getattr(sys, 'frozen', False):
    CONFIG_FILE = os.path.join(os.path.dirname(sys.executable), "config.json")
else:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

LOG_FILE = os.path.join(APP_DATA_DIR, "logs", "lotus_app.log")
PID_FILE = os.path.join(APP_DATA_DIR, "lotus_bot.pid")
os.makedirs(os.path.join(APP_DATA_DIR, "logs"), exist_ok=True)

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
    if getattr(sys, 'frozen', False):
        cmd = f'"{sys.executable}" --bot-service'
    else:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw): pythonw = sys.executable
        cmd = f'"{pythonw}" "{os.path.abspath(__file__)}" --bot-service'
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


# ── Theme & Brand ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#888888"
BORDER = "#333333"
OWNER = "Satyam Pote"
APP_NAME = "Lotus"

# ── Color Palette: Ghost (White on Image) ──
BG_DARK        = None        # transparent background
BG_CARD        = "transparent" 
ACCENT         = "#ffffff"   # white text/accentstead of pink
ACCENT_HOVER   = "#e0e0e0"   # light grey
GREEN          = "#ffffff"   # white buttons for a noir look
RED            = "#333333"   # dark grey for stop
YELLOW         = "#ffffff"
TEXT_PRIMARY   = "#ffffff"   # pure white
TEXT_SECONDARY = "#888888"   # medium grey
BORDER         = "#222222"   # dark border

# ── UI Assets Dir ──
def get_app_dir():
    return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
APP_DIR = get_app_dir()

# ── Logo ──
LOGO_PATH = os.path.join(APP_DIR, "assets", "lotus_logo.png")


def _load_logo(size: int = 60) -> ctk.CTkImage | None:
    """Load the UI logo PNG."""
    try:
        # User wants PINK logo back
        logo_path = os.path.join(APP_DIR, "assets", "lotus_logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(APP_DIR, "assets", "logo_white.png")
            
        if os.path.exists(logo_path):
            img = Image.open(logo_path).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        else:
            _log.error("Logo file NOT FOUND at: %s", logo_path)
    except Exception as e:
        _log.error("Failed to load logo: %s", e)
    return None

def _load_banner() -> ctk.CTkImage | None:
    """Load the UI banner PNG."""
    try:
        banner_path = os.path.join(APP_DIR, "assets", "banner.png")
        if os.path.exists(banner_path):
            img = Image.open(banner_path).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(520, 150))
    except Exception:
        pass
    return None

def _load_background() -> ctk.CTkImage | None:
    """Load the full window background image."""
    try:
        bg_path = os.path.join(APP_DIR, "assets", "bg_pond.png")
        if os.path.exists(bg_path):
            img = Image.open(bg_path).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(400, 600))
        else:
            _log.error("Background image NOT FOUND at: %s", bg_path)
    except Exception as e:
        _log.error("Failed to load background image: %s", e)
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
    """Launch bot service as a fully detached background process."""
    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    if getattr(sys, 'frozen', False):
        args = [sys.executable, "--bot-service"]
    else:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw): pythonw = sys.executable
        args = [pythonw, os.path.abspath(__file__), "--bot-service"]

    subprocess.Popen(
        args,
        cwd=APP_DATA_DIR,
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

        self.title("Lotus")
        self.geometry("400x600")
        self.resizable(False, False)
        self.configure(fg_color="#1a1a1a") # Fallback color

        # Background Image - Make it the container for everything else
        _bg = _load_background()
        if _bg:
            self.bg_label = ctk.CTkLabel(self, image=_bg, text="")
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.bg_label.lower() 
        else:
            self.bg_label = self
            _log.warning("No background image loaded, using fallback.")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config       = load_config()
        self._status_poll = None  # for after() polling
        self._log_poll    = None
        self._last_log_size = 0

        # Try to set icon
        icon_path = os.path.join(APP_DIR, "assets", "lotus_icon.ico")
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
        outer = ctk.CTkFrame(self.bg_label, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)

        _banner = _load_banner()
        if _banner:
            ctk.CTkLabel(outer, image=_banner, text="").pack(fill="x")

        frame = ctk.CTkScrollableFrame(
            outer, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=TEXT_SECONDARY
        )
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        # Logo / Title
        _logo = _load_logo(80)
        if _logo:
            ctk.CTkLabel(frame, image=_logo, text="").pack(pady=(10, 2))
        else:
            ctk.CTkLabel(frame, text="🌸", font=("Segoe UI Emoji", 44)).pack(pady=(10, 2))
        ctk.CTkLabel(
            frame, text=APP_NAME, font=("Segoe UI", 32, "bold"),
            text_color="#ffffff"
        ).pack(pady=(0, 2))
        ctk.CTkLabel(
            frame, text="Windows Control Agent",
            font=("Segoe UI", 13), text_color="#aaaaaa"
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
            "name":               name,
            "telegram_token":     token,
            "allowed_user_id":    user_ids,
            "model":              "phi3", # Default to phi3 if not set
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
        name = self.config.get("name") or self.config.get("user_name", "User")

        frame = ctk.CTkScrollableFrame(
            self.bg_label, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=TEXT_SECONDARY
        )
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        # Header
        _logo = _load_logo(70)
        if _logo:
            ctk.CTkLabel(frame, image=_logo, text="").pack(pady=(10, 2))
        else:
            ctk.CTkLabel(frame, text="🌸", font=("Segoe UI Emoji", 42)).pack(pady=(10, 2))
        ctk.CTkLabel(
            frame, text=APP_NAME, font=("Segoe UI", 32, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            frame, text=f"Hello {name} 👋",
            font=("Segoe UI", 16), text_color=TEXT_SECONDARY
        ).pack(pady=(0, 20))

        # Status area (no card)
        status_card = ctk.CTkFrame(
            frame, fg_color="transparent", corner_radius=0
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
            font=("Segoe UI", 14), text_color=YELLOW, anchor="w"
        )
        self.status_label.pack(fill="x")

        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶ START BOT", height=48,
            font=("Segoe UI", 13), corner_radius=0,
            fg_color="transparent", border_width=1, border_color=ACCENT,
            hover_color="#1a1a1a", text_color=ACCENT, command=self.start_bot
        )
        self.start_btn.pack(fill="x", pady=(0, 12))

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹ STOP BOT", height=48,
            font=("Segoe UI", 13), corner_radius=0,
            fg_color="transparent", border_width=1, border_color=BORDER,
            hover_color="#1a1a1a", text_color=TEXT_SECONDARY, command=self.stop_bot, state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=(0, 10))

        # Separator
        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=10)

        # ── Startup toggle (no card) ──
        startup_card = ctk.CTkFrame(
            frame, fg_color="transparent", corner_radius=0
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

        # ── Minimize-to-tray info (no card) ──
        tray_card = ctk.CTkFrame(
            frame, fg_color="transparent", corner_radius=0
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
            fg_color="transparent", text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER, corner_radius=0,
            state="disabled"
        )
        self.log_box.pack(fill="x")

        # Owner tag
        ctk.CTkLabel(
            frame, text=f"Designed by {OWNER}",
            font=("Segoe UI", 10), text_color="#444444"
        ).pack(pady=(10, 0))

        self.log("Lotus ready.")

        # ── Check bot status and auto-start if not running ──
        self._poll_bot_status()
        self._poll_bot_logs()

    # ──────────────────────────────────────────────
    # BOT CONTROL (PID-based, independent process)
    # ──────────────────────────────────────────────
    def _poll_bot_logs(self):
        """Continuously stream bot_service.log into the UI log box."""
        try:
            bot_log_path = os.path.join(APP_DATA_DIR, "logs", "bot_service.log")
            if os.path.exists(bot_log_path):
                current_size = os.path.getsize(bot_log_path)
                if current_size > self._last_log_size:
                    with open(bot_log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self._last_log_size)
                        new_text = f.read()
                    self._last_log_size = current_size
                    if new_text and hasattr(self, 'log_box'):
                        self.log_box.configure(state="normal")
                        self.log_box.insert("end", new_text)
                        self.log_box.see("end")
                        self.log_box.configure(state="disabled")
                elif current_size < self._last_log_size:
                    self._last_log_size = 0
        except Exception:
            pass
        self._log_poll = self.after(1000, self._poll_bot_logs)

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
                self.status_label.configure(text=f"Running (PID {pid})", text_color="#ffffff")
                self.status_icon.configure(text="✅", text_color="#ffffff")
                self.start_btn.configure(state="disabled")
                self.stop_btn.configure(state="normal")
            else:
                self.status_label.configure(text="Stopped", text_color="#888888")
                self.status_icon.configure(text="⏹", text_color="#888888")
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
        if hasattr(self, '_log_poll') and self._log_poll:
            self.after_cancel(self._log_poll)
            self._log_poll = None
        
        # Destroy everything EXCEPT the background label itself
        for widget in self.winfo_children():
            if hasattr(self, 'bg_label') and widget == self.bg_label:
                # But clear the children of the background label!
                for child in self.bg_label.winfo_children():
                    child.destroy()
                continue
            widget.destroy()

    def change_settings(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before changing settings.")
            return
        self.show_setup()
        # Pre-fill existing values
        if self.config:
            self.token_entry.insert(0, self.config.get("telegram_token") or self.config.get("bot_token", ""))
            self.ids_entry.insert(0, self.config.get("allowed_user_id") or self.config.get("allowed_user_ids", ""))
            self.name_entry.insert(0, self.config.get("name") or self.config.get("user_name", ""))

    def reset_setup(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before resetting.")
            return
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.config = None
        self.show_setup()

    def on_close(self):
        """Hide the window to system tray instead of killing the app."""
        _log.info("GUI window closed — hiding to system tray")
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _really_close(self):
        """Stop bot, destroy tray, then exit cleanly."""
        _log.info("GUI destroyed — exiting app")
        try:
            if _is_bot_alive():
                _stop_bot_service()
        except Exception:
            pass
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)

def _restart_bot_service():
    """Stop then re-launch the bot service."""
    if _is_bot_alive():
        _stop_bot_service()
        time.sleep(1.5)
    _start_bot_service()


def check_for_update() -> tuple[bool, str]:
    """Check GitHub releases for a newer version. Returns (available, version)."""
    try:
        import requests, json
        url = "https://api.github.com/repos/SatyamPote/Lotus/releases/latest"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            latest = data.get("tag_name", "")
            current = "v2.0"   # bump this each build
            if latest and latest != current:
                return True, latest
    except Exception:
        pass
    return False, ""


def setup_tray(app):
    import pystray
    from pystray import MenuItem as item

    def on_open(icon, item_):
        app.after(0, app.show_window)

    def on_start(icon, item_):
        app.after(0, app.start_bot)

    def on_stop(icon, item_):
        app.after(0, app.stop_bot)

    def on_restart(icon, item_):
        app.after(0, lambda: threading.Thread(target=_restart_bot_service, daemon=True).start())

    def on_exit(icon, item_):
        app.after(0, app._really_close)

    try:
        _ico_path = os.path.join(APP_DIR, "assets", "lotus_icon.ico")
        image = Image.open(_ico_path)
    except Exception:
        image = Image.new('RGB', (64, 64), color=(255, 102, 178))

    menu = pystray.Menu(
        item('Open Control Panel', on_open, default=True),
        pystray.Menu.SEPARATOR,
        item('Start Bot',    on_start),
        item('Stop Bot',     on_stop),
        item('Restart Bot',  on_restart),
        pystray.Menu.SEPARATOR,
        item('Exit Lotus',   on_exit),
    )

    app.tray_icon = pystray.Icon("Lotus", image, "Lotus — Running", menu)
    threading.Thread(target=app.tray_icon.run, daemon=True).start()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot-service", action="store_true", help="Run background bot service")
    parser.add_argument("--player-tui", action="store_true", help="Run music player TUI")
    args, unknown = parser.parse_known_args()

    if args.player_tui:
        # Import and run the music player TUI
        # We use parse_known_args so we can pass the rest to the TUI main
        from windows_mcp.media import player_tui
        # Manually set sys.argv for the TUI's argparse
        sys.argv = [sys.argv[0]] + unknown
        player_tui.main()
        sys.exit(0)

    if args.bot_service:
        # Import and run the bot service loop directly
        import bot_service
        bot_service.run_service()
        sys.exit(0)

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
    setup_tray(app)
    app.mainloop()
    _log.info("=== App exited cleanly ===")
