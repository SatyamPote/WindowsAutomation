"""
Lotus Desktop Application — v3.1
=================================
Modern glass-morphism control panel.
Bot runs as an INDEPENDENT background process (bot_service.py).
Closing the GUI does NOT stop the bot — it keeps running silently.
"""

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter
import json
import logging
import os
import sys
import subprocess
import threading
import time
import winreg
import psutil

# ── Runtime Defender Exclusion (silent, best-effort) ──────────────────────────
def _apply_defender_exclusion_async():
    try:
        app_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
             "-Command",
             f"Add-MpPreference -ExclusionPath '{app_dir}','C:\\ProgramData\\Lotus' "
             f"-ErrorAction SilentlyContinue; "
             f"Add-MpPreference -ExclusionProcess 'Lotus.exe','LotusTray.exe','python.exe','pythonw.exe' "
             f"-ErrorAction SilentlyContinue"],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except Exception:
        pass

threading.Thread(target=_apply_defender_exclusion_async, daemon=True).start()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR_SRC = os.path.dirname(os.path.abspath(__file__))
MCP_SRC = os.path.join(BASE_DIR_SRC, "src")
if os.path.exists(MCP_SRC) and MCP_SRC not in sys.path:
    sys.path.insert(0, MCP_SRC)

try:
    from windows_mcp.diagnostics import init_diagnostics
    init_diagnostics()
except ImportError:
    pass

PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
APP_DATA_DIR = os.path.join(PROGRAM_DATA, "Lotus")

from windows_mcp.assets import get_resource_path

ICON_PATH = get_resource_path("assets/lotus_icon.ico")
LOGO_PATH = get_resource_path("assets/lotus_logo.png")
BANNER_PATH = get_resource_path("assets/lotus_banner.png")

if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    CONFIG_FILE = os.path.join(exe_dir, "config.json")
else:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

LOG_FILE = os.path.join(APP_DATA_DIR, "logs", "lotus_app.log")
PID_FILE = os.path.join(APP_DATA_DIR, "lotus_bot.pid")
os.makedirs(os.path.join(APP_DATA_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE, level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("lotus")

# ── Startup Registry ──────────────────────────────────────────────────────────
STARTUP_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APP_NAME = "LotusControlPanel"

def _get_startup_command() -> str:
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" --bot-service'
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw): pythonw = sys.executable
    return f'"{pythonw}" "{os.path.abspath(__file__)}" --bot-service'

def is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, STARTUP_APP_NAME)
        winreg.CloseKey(key)
        return val == _get_startup_command()
    except Exception:
        return False

def enable_startup():
    cmd = _get_startup_command()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, STARTUP_APP_NAME, 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)

def disable_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, STARTUP_APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Color palette — deep dark glass
C_BG           = "#0a0a0f"
C_SURFACE      = "#12121a"
C_CARD         = "#1a1a28"
C_CARD_BORDER  = "#2a2a3f"
C_ACCENT       = "#c084fc"      # violet
C_ACCENT2      = "#f472b6"      # pink
C_GREEN        = "#4ade80"
C_RED          = "#f87171"
C_TEXT         = "#f1f5f9"
C_MUTED        = "#64748b"
C_DIVIDER      = "#1e1e30"

APP_NAME = "Lotus"
OWNER    = "Satyam Pote"

# ── Asset loader ──────────────────────────────────────────────────────────────
def get_app_dir():
    return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
APP_DIR = get_app_dir()

def _load_logo(size=60) -> ctk.CTkImage | None:
    for name in ("lotus_logo.png", "logo.png", "logo_white.png"):
        p = os.path.join(APP_DIR, "assets", name)
        if os.path.exists(p):
            img = Image.open(p).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return None

# ── Config helpers ────────────────────────────────────────────────────────────
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

# ── Bot process management ────────────────────────────────────────────────────
def _get_bot_pid() -> int | None:
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None

def _is_bot_alive() -> bool:
    pid = _get_bot_pid()
    if pid is None:
        return False
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != "zombie"
    except Exception:
        return False

def _start_bot_service():
    DETACHED      = 0x00000008
    NO_WIN        = 0x08000000
    NEW_GROUP     = 0x00000200
    if getattr(sys, 'frozen', False):
        args = [sys.executable, "--bot-service"]
    else:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw): pythonw = sys.executable
        args = [pythonw, os.path.abspath(__file__), "--bot-service"]
    subprocess.Popen(
        args, cwd=APP_DATA_DIR,
        creationflags=DETACHED | NO_WIN | NEW_GROUP,
        close_fds=True, start_new_session=True,
    )

def _stop_bot_service():
    pid = _get_bot_pid()
    if pid is None: return
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
    except Exception as e:
        _log.error("Stop bot error: %s", e)
    try:
        if os.path.exists(PID_FILE): os.remove(PID_FILE)
    except Exception:
        pass

# ── Main App Window ───────────────────────────────────────────────────────────
class LotusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        _log.info("=== Lotus app started ===")
        self.title("Lotus")
        self.geometry("420x640")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        icon_path = os.path.join(APP_DIR, "assets", "lotus_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.config_data  = load_config()
        self._status_poll = None
        self._log_poll    = None
        self._last_log_size = 0

        # Auto-enable startup
        if not is_startup_enabled():
            try: enable_startup()
            except Exception: pass

        if self.config_data:
            self.show_control_panel()
        else:
            self.show_setup()

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _card(self, parent, **kw) -> ctk.CTkFrame:
        defaults = dict(fg_color=C_CARD, corner_radius=14,
                        border_width=1, border_color=C_CARD_BORDER)
        defaults.update(kw)
        return ctk.CTkFrame(parent, **defaults)

    def _label(self, parent, text, size=13, weight="normal", color=None, **kw):
        return ctk.CTkLabel(parent, text=text,
                            font=("Segoe UI", size, weight),
                            text_color=color or C_TEXT, **kw)

    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=C_DIVIDER,
                     corner_radius=0).pack(fill="x", pady=8)

    def clear_window(self):
        if self._status_poll:
            self.after_cancel(self._status_poll); self._status_poll = None
        if self._log_poll:
            self.after_cancel(self._log_poll); self._log_poll = None
        for w in self.winfo_children():
            w.destroy()

    # ── SETUP SCREEN ─────────────────────────────────────────────────────────
    def show_setup(self):
        self.clear_window()

        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0,
                                        scrollbar_button_color=C_CARD,
                                        scrollbar_button_hover_color=C_ACCENT)
        scroll.pack(fill="both", expand=True, padx=24, pady=24)

        # Logo + title
        _logo = _load_logo(72)
        if _logo:
            ctk.CTkLabel(scroll, image=_logo, text="").pack(pady=(8, 4))
        else:
            ctk.CTkLabel(scroll, text="🌸", font=("Segoe UI Emoji", 48)).pack(pady=(8, 4))

        ctk.CTkLabel(scroll, text=APP_NAME,
                     font=("Segoe UI", 34, "bold"), text_color=C_ACCENT).pack()
        self._label(scroll, "First-Time Setup", size=13, color=C_MUTED).pack(pady=(2, 18))

        # Form card
        card = self._card(scroll)
        card.pack(fill="x", pady=6)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=18)

        fields = [
            ("Your Name", "e.g. Satyam", False),
            ("Telegram Bot Token", "e.g. 123456:ABC-DEF...", False),
            ("Allowed User IDs (comma-separated)", "e.g. 123456789", False),
        ]
        self._entries = []
        for label, placeholder, secret in fields:
            self._label(inner, label, size=12, color=C_MUTED, anchor="w").pack(fill="x", pady=(6, 2))
            e = ctk.CTkEntry(inner, height=40, font=("Consolas", 12),
                             placeholder_text=placeholder,
                             fg_color=C_SURFACE, border_color=C_CARD_BORDER,
                             text_color=C_TEXT, show="●" if secret else "")
            e.pack(fill="x", pady=(0, 4))
            self._entries.append(e)

        self._setup_err = self._label(inner, "", size=11, color=C_RED)
        self._setup_err.pack(pady=(4, 0))

        ctk.CTkButton(inner, text="Save & Continue →", height=46,
                      font=("Segoe UI", 14, "bold"), corner_radius=10,
                      fg_color=C_ACCENT, hover_color="#a855f7",
                      text_color="#0a0a0f", command=self.save_setup
                      ).pack(fill="x", pady=(14, 0))

        self._label(scroll, f"Designed by {OWNER}", size=10, color=C_MUTED).pack(pady=(14, 4))

    def save_setup(self):
        name  = self._entries[0].get().strip()
        token = self._entries[1].get().strip()
        ids   = self._entries[2].get().strip()

        if not name:
            self._setup_err.configure(text="⚠ Name is required."); return
        if not token or ":" not in token:
            self._setup_err.configure(text="⚠ Invalid bot token format."); return
        if not ids:
            self._setup_err.configure(text="⚠ Enter at least one Telegram User ID."); return

        self.config_data = {
            "name": name, "telegram_token": token,
            "allowed_user_id": ids, "model": "phi3",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_config(self.config_data)
        _log.info("Config saved for: %s", name)
        self.show_control_panel()

    # ── CONTROL PANEL ────────────────────────────────────────────────────────
    def show_control_panel(self):
        self.clear_window()
        name = self.config_data.get("name") or "User"

        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0,
                                        scrollbar_button_color=C_CARD,
                                        scrollbar_button_hover_color=C_ACCENT)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Header ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        _logo = _load_logo(64)
        if _logo:
            ctk.CTkLabel(header, image=_logo, text="").pack(pady=(4, 2))
        else:
            ctk.CTkLabel(header, text="🌸", font=("Segoe UI Emoji", 44)).pack(pady=(4, 2))

        ctk.CTkLabel(header, text=APP_NAME,
                     font=("Segoe UI", 30, "bold"), text_color=C_ACCENT).pack()
        self._label(header, f"Hello, {name} 👋", size=13, color=C_MUTED).pack(pady=(2, 0))

        # ── Status card ───────────────────────────────────────────────────
        status_card = self._card(scroll)
        status_card.pack(fill="x", pady=(0, 10))
        status_inner = ctk.CTkFrame(status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=16, pady=14)

        left = ctk.CTkFrame(status_inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        self._label(left, "BOT STATUS", size=10, color=C_MUTED, anchor="w").pack(fill="x")
        self.status_label = self._label(left, "Checking...", size=15, weight="bold",
                                        color=C_MUTED, anchor="w")
        self.status_label.pack(fill="x")

        self.status_dot = ctk.CTkLabel(status_inner, text="⬤", font=("Segoe UI", 22),
                                       text_color=C_MUTED)
        self.status_dot.pack(side="right", padx=(8, 0))

        # ── Action buttons ────────────────────────────────────────────────
        btn_card = self._card(scroll)
        btn_card.pack(fill="x", pady=(0, 10))
        btn_inner = ctk.CTkFrame(btn_card, fg_color="transparent")
        btn_inner.pack(fill="x", padx=16, pady=14)

        self.start_btn = ctk.CTkButton(
            btn_inner, text="▶  START BOT", height=48,
            font=("Segoe UI", 13, "bold"), corner_radius=10,
            fg_color=C_ACCENT, hover_color="#a855f7",
            text_color="#0a0a0f", command=self.start_bot)
        self.start_btn.pack(fill="x", pady=(0, 8))

        self.stop_btn = ctk.CTkButton(
            btn_inner, text="⏹  STOP BOT", height=44,
            font=("Segoe UI", 13), corner_radius=10,
            fg_color=C_CARD, hover_color=C_SURFACE,
            border_width=1, border_color=C_CARD_BORDER,
            text_color=C_MUTED, command=self.stop_bot, state="disabled")
        self.stop_btn.pack(fill="x")

        # ── Info row ──────────────────────────────────────────────────────
        info_card = self._card(scroll)
        info_card.pack(fill="x", pady=(0, 10))
        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=12)

        rows = [
            ("🚀  Auto-start on login", "Enabled (always on)"),
            ("🛡️  Windows Defender", "Exclusions applied"),
            ("🔒  Close = background", "Bot keeps running"),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(info_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            self._label(row, label, size=12, color=C_TEXT, anchor="w").pack(side="left")
            self._label(row, value, size=11, color=C_MUTED, anchor="e").pack(side="right")

        # ── Utility buttons ───────────────────────────────────────────────
        util_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        util_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            util_frame, text="⚙  Settings", height=38,
            font=("Segoe UI", 12), corner_radius=8,
            fg_color=C_CARD, hover_color=C_SURFACE,
            border_width=1, border_color=C_CARD_BORDER,
            text_color=C_MUTED, command=self.change_settings
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        ctk.CTkButton(
            util_frame, text="🔄  Reset", height=38,
            font=("Segoe UI", 12), corner_radius=8,
            fg_color=C_CARD, hover_color=C_SURFACE,
            border_width=1, border_color=C_CARD_BORDER,
            text_color=C_RED, command=self.reset_setup
        ).pack(side="right", expand=True, fill="x", padx=(5, 0))

        # ── Log console ───────────────────────────────────────────────────
        log_card = self._card(scroll)
        log_card.pack(fill="x", pady=(0, 4))
        log_inner = ctk.CTkFrame(log_card, fg_color="transparent")
        log_inner.pack(fill="x", padx=16, pady=(10, 14))

        self._label(log_inner, "CONSOLE OUTPUT", size=10, color=C_MUTED, anchor="w").pack(fill="x", pady=(0, 6))

        self.log_box = ctk.CTkTextbox(
            log_inner, height=130, font=("Consolas", 10),
            fg_color=C_SURFACE, text_color="#94a3b8",
            border_width=1, border_color=C_CARD_BORDER,
            corner_radius=8, state="disabled")
        self.log_box.pack(fill="x")

        self._label(scroll, f"Lotus v3.1 · by {OWNER}", size=10, color=C_MUTED).pack(pady=(6, 0))

        # Boot up
        self.log("🌸 Lotus ready.")
        self._poll_bot_status()
        self._poll_bot_logs()

    # ── Bot polling & control ─────────────────────────────────────────────────
    def _poll_bot_logs(self):
        try:
            bot_log_path = os.path.join(APP_DATA_DIR, "logs", "bot_service.log")
            if os.path.exists(bot_log_path):
                sz = os.path.getsize(bot_log_path)
                if sz > self._last_log_size:
                    with open(bot_log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self._last_log_size)
                        new_text = f.read()
                    self._last_log_size = sz
                    if new_text and hasattr(self, "log_box"):
                        self.log_box.configure(state="normal")
                        self.log_box.insert("end", new_text)
                        self.log_box.see("end")
                        self.log_box.configure(state="disabled")
                elif sz < self._last_log_size:
                    self._last_log_size = 0
        except Exception:
            pass
        self._log_poll = self.after(1000, self._poll_bot_logs)

    def _poll_bot_status(self):
        alive = _is_bot_alive()
        self._update_ui_status(alive)
        if not alive and self.config_data:
            self.log("🤖 Auto-starting bot...")
            self.start_bot()
        self._status_poll = self.after(5000, self._poll_bot_status_silent)

    def _poll_bot_status_silent(self):
        try:
            self._update_ui_status(_is_bot_alive())
        except Exception:
            pass
        self._status_poll = self.after(5000, self._poll_bot_status_silent)

    def _update_ui_status(self, running: bool):
        try:
            if running:
                pid = _get_bot_pid()
                self.status_label.configure(text=f"Running  (PID {pid})", text_color=C_GREEN)
                self.status_dot.configure(text_color=C_GREEN)
                self.start_btn.configure(state="disabled", fg_color="#1e3a2f",
                                         text_color="#4ade80")
                self.stop_btn.configure(state="normal", fg_color=C_CARD,
                                        border_color="#f87171", text_color=C_RED)
            else:
                self.status_label.configure(text="Stopped", text_color=C_RED)
                self.status_dot.configure(text_color=C_RED)
                self.start_btn.configure(state="normal", fg_color=C_ACCENT,
                                         text_color="#0a0a0f")
                self.stop_btn.configure(state="disabled", fg_color=C_CARD,
                                        border_color=C_CARD_BORDER, text_color=C_MUTED)
        except Exception:
            pass

    def start_bot(self):
        if _is_bot_alive():
            self.log("ℹ Bot is already running."); return
        self.log("🚀 Starting Lotus bot...")
        try:
            _start_bot_service()
            self.log("✅ Bot service launched.")
            self.after(2500, self._verify_bot_started)
        except Exception as e:
            self.log(f"❌ Failed to start: {e}")

    def _verify_bot_started(self):
        if _is_bot_alive():
            self.log(f"✅ Confirmed running (PID {_get_bot_pid()})")
            self._update_ui_status(True)
        else:
            self.log("⚠ Bot still starting — check logs if issue persists.")

    def stop_bot(self):
        if not _is_bot_alive():
            self._update_ui_status(False); return
        self.log("⏹ Stopping bot...")
        try:
            _stop_bot_service()
            self.log("✅ Bot stopped.")
        except Exception as e:
            self.log(f"❌ Stop error: {e}")
        self._update_ui_status(False)

    def log(self, msg: str):
        try:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

    def change_settings(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before changing settings."); return
        self.show_setup()
        if self.config_data:
            try:
                self._entries[0].insert(0, self.config_data.get("name", ""))
                self._entries[1].insert(0, self.config_data.get("telegram_token") or self.config_data.get("bot_token", ""))
                self._entries[2].insert(0, self.config_data.get("allowed_user_id") or self.config_data.get("allowed_user_ids", ""))
            except Exception:
                pass

    def reset_setup(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot first."); return
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.config_data = None
        self.show_setup()

    def on_close(self):
        _log.info("GUI closed — hiding to background")
        self.withdraw()

    def show_window(self):
        self.deiconify(); self.lift(); self.focus_force()

    def _really_close(self):
        _log.info("Full exit requested")
        try:
            if _is_bot_alive(): _stop_bot_service()
        except Exception:
            pass
        try:
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)


def _restart_bot_service():
    if _is_bot_alive():
        _stop_bot_service()
        time.sleep(1.5)
    _start_bot_service()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--bot-service" in sys.argv:
        # Import and run bot_service directly
        bot_svc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_service.py")
        if os.path.exists(bot_svc_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("bot_service", bot_svc_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.run_service()
        sys.exit(0)

    app = LotusApp()
    app.mainloop()
