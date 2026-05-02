"""
Lotus — macOS Control Panel
============================
CustomTkinter GUI for configuring and running the Lotus Telegram bot.
The bot runs as an independent background process (bot_service.py).
Closing this window hides the app to the macOS menu bar — the bot keeps running.

Features:
  • First-time setup wizard (token, user IDs, name, Ollama model)
  • Ollama model auto-detection from local server
  • Start / stop / status of the background bot service
  • Start-on-login via launchd
  • Live log viewer
  • macOS menu bar icon for quick access
"""

import json
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

import customtkinter as ctk
import psutil
from PIL import Image

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SRC_DIR  = BASE_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "Lotus"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
(APP_DATA_DIR / "logs").mkdir(exist_ok=True)

CONFIG_FILE   = BASE_DIR / "config.json"
PID_FILE      = APP_DATA_DIR / "lotus_bot.pid"
LOG_FILE      = APP_DATA_DIR / "logs" / "lotus_app.log"
BOT_LOG_FILE  = APP_DATA_DIR / "logs" / "bot_service.log"
LAUNCHD_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.lotus.botservice.plist"

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("lotus_app")

# ── Theme ──────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT         = "#ffffff"
ACCENT_HOVER   = "#e0e0e0"
TEXT_PRIMARY   = "#ffffff"
TEXT_SECONDARY = "#888888"
BORDER         = "#333333"
GREEN          = "#4caf50"
RED            = "#f44336"
APP_NAME       = "Lotus"


# ── Asset helpers ──────────────────────────────────────────────────────────

def _assets() -> Path:
    return BASE_DIR / "assets"


def _load_logo(size: int = 60) -> ctk.CTkImage | None:
    for name in ("lotus_logo.png", "logo_white.png", "logo.png"):
        p = _assets() / name
        if p.exists():
            try:
                img = Image.open(p).convert("RGBA")
                return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            except Exception:
                pass
    return None


def _load_banner() -> ctk.CTkImage | None:
    p = _assets() / "banner.png"
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(520, 150))
        except Exception:
            pass
    return None


def _load_background() -> ctk.CTkImage | None:
    p = _assets() / "bg_pond.png"
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(400, 600))
        except Exception:
            pass
    return None


# ── Config ─────────────────────────────────────────────────────────────────

def load_config() -> dict | None:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def save_config(data: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Ollama helpers ─────────────────────────────────────────────────────────

def fetch_ollama_models() -> list[str]:
    """Return models available on the local Ollama server, or [] on failure."""
    try:
        import requests as _req
        r = _req.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def ollama_is_running() -> bool:
    try:
        import requests as _req
        return _req.get("http://localhost:11434/api/tags", timeout=2).status_code == 200
    except Exception:
        return False


# ── macOS Login Item helpers ────────────────────────────────────────────────

def _bot_service_cmd() -> list[str]:
    return [sys.executable, str(BASE_DIR / "bot_service.py")]


def is_startup_enabled() -> bool:
    return LAUNCHD_PLIST.exists()


def enable_startup() -> None:
    cmd = _bot_service_cmd()
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lotus.botservice</string>
    <key>ProgramArguments</key>
    <array>
        {''.join(f'<string>{c}</string>' for c in cmd)}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{BOT_LOG_FILE}</string>
    <key>StandardErrorPath</key>
    <string>{BOT_LOG_FILE}</string>
</dict>
</plist>"""
    LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHD_PLIST.write_text(plist)
    subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST)], check=False)
    _log.info("launchd agent installed: %s", LAUNCHD_PLIST)


def disable_startup() -> None:
    if LAUNCHD_PLIST.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], check=False)
        LAUNCHD_PLIST.unlink(missing_ok=True)
        _log.info("launchd agent removed")


# ── Bot process management ──────────────────────────────────────────────────

def _get_bot_pid() -> int | None:
    try:
        if PID_FILE.exists():
            return int(PID_FILE.read_text().strip())
    except Exception:
        pass
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


def _start_bot_service() -> None:
    cmd = _bot_service_cmd()
    proc = subprocess.Popen(
        cmd,
        start_new_session=True,
        stdout=open(BOT_LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        cwd=str(BASE_DIR),
    )
    _log.info("Bot service launched (PID %d)", proc.pid)


def _stop_bot_service() -> None:
    pid = _get_bot_pid()
    if pid is None:
        return
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        _log.info("Bot service (PID %d) stopped", pid)
    except Exception as e:
        _log.error("Failed to stop bot (PID %d): %s", pid, e)
    PID_FILE.unlink(missing_ok=True)


# ── macOS Menu Bar Icon ─────────────────────────────────────────────────────

_menubar_thread: threading.Thread | None = None


def _start_menubar_icon(app_ref: "LotusApp") -> None:
    """Install a macOS menu bar status item using PyObjC."""
    try:
        import AppKit

        class _MenuBarDelegate(AppKit.NSObject):
            def show_(self, sender):
                app_ref.after(0, app_ref.show_window)

            def toggleBot_(self, sender):
                if _is_bot_alive():
                    app_ref.after(0, app_ref.stop_bot)
                else:
                    app_ref.after(0, app_ref.start_bot)

            def quit_(self, sender):
                app_ref.after(0, app_ref.quit_app)

        status_bar = AppKit.NSStatusBar.systemStatusBar()
        status_item = status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        status_item.setTitle_("🌸")
        status_item.setHighlightMode_(True)

        menu = AppKit.NSMenu.alloc().init()
        delegate = _MenuBarDelegate.alloc().init()

        show_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show Lotus", "show:", ""
        )
        show_item.setTarget_(delegate)

        toggle_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Toggle Bot", "toggleBot:", ""
        )
        toggle_item.setTarget_(delegate)

        sep = AppKit.NSMenuItem.separatorItem()

        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quit:", ""
        )
        quit_item.setTarget_(delegate)

        menu.addItem_(show_item)
        menu.addItem_(toggle_item)
        menu.addItem_(sep)
        menu.addItem_(quit_item)

        status_item.setMenu_(menu)

        # Keep strong references so they aren't GC'd
        app_ref._menubar_status_item = status_item
        app_ref._menubar_delegate = delegate

    except Exception as e:
        _log.debug("Menu bar icon unavailable: %s", e)


# ── Model picker widget ─────────────────────────────────────────────────────

class OllamaModelPicker(ctk.CTkFrame):
    """Entry + refresh button that auto-populates a dropdown from Ollama."""

    def __init__(self, master, default_model: str = "phi3", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._models: list[str] = []
        self._var = ctk.StringVar(value=default_model)

        self._dropdown = ctk.CTkOptionMenu(
            self,
            variable=self._var,
            values=[default_model],
            fg_color="#1a1a1a",
            button_color=BORDER,
            button_hover_color="#444444",
            dropdown_fg_color="#1a1a1a",
            text_color=TEXT_PRIMARY,
            font=("Menlo", 12),
        )
        self._dropdown.pack(side="left", fill="x", expand=True)

        self._refresh_btn = ctk.CTkButton(
            self, text="⟳", width=36, height=40,
            fg_color="transparent", hover_color=BORDER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_SECONDARY, font=("SF Pro Text", 16),
            command=self._refresh,
        )
        self._refresh_btn.pack(side="left", padx=(6, 0))

        self._ollama_label = ctk.CTkLabel(
            self, text="", font=("SF Pro Text", 11), text_color=TEXT_SECONDARY
        )
        self._ollama_label.pack(side="left", padx=(8, 0))

        self._refresh(silent=True)

    def _refresh(self, silent: bool = False) -> None:
        self._ollama_label.configure(text="…")
        threading.Thread(target=self._fetch, args=(silent,), daemon=True).start()

    def _fetch(self, silent: bool) -> None:
        models = fetch_ollama_models()
        self.after(0, lambda: self._apply(models, silent))

    def _apply(self, models: list[str], silent: bool) -> None:
        if models:
            self._models = models
            current = self._var.get()
            self._dropdown.configure(values=models)
            if current not in models:
                self._var.set(models[0])
            self._ollama_label.configure(text=f"✅ {len(models)} model{'s' if len(models) != 1 else ''}")
        else:
            self._ollama_label.configure(
                text="⚠ Ollama not found" if not silent else "⚠ Ollama offline"
            )

    def get(self) -> str:
        return self._var.get()

    def set(self, value: str) -> None:
        self._var.set(value)


# ── Main App ───────────────────────────────────────────────────────────────

class LotusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        _log.info("=== Lotus app started ===")

        self.title("Lotus")
        self.geometry("420x660")
        self.resizable(False, False)
        self.configure(fg_color="#1a1a1a")

        _bg = _load_background()
        if _bg:
            self.bg_label = ctk.CTkLabel(self, image=_bg, text="")
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.bg_label.lower()
        else:
            self.bg_label = self

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config_data = load_config()
        self._status_poll: str | None = None
        self._log_poll: str | None = None
        self._last_log_size = 0

        # Start menu bar icon in background thread
        threading.Thread(target=_start_menubar_icon, args=(self,), daemon=True).start()

        if self.config_data:
            self.show_control_panel()
        else:
            self.show_setup()

    # ── Setup screen ────────────────────────────────────────────────────────

    def show_setup(self):
        self.clear_window()

        outer = ctk.CTkFrame(self.bg_label, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)

        _banner = _load_banner()
        if _banner:
            ctk.CTkLabel(outer, image=_banner, text="").pack(fill="x")

        frame = ctk.CTkScrollableFrame(
            outer, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=TEXT_SECONDARY,
        )
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        _logo = _load_logo(80)
        if _logo:
            ctk.CTkLabel(frame, image=_logo, text="").pack(pady=(10, 2))
        else:
            ctk.CTkLabel(frame, text="🌸", font=("SF Pro Display", 44)).pack(pady=(10, 2))

        ctk.CTkLabel(frame, text=APP_NAME,
                     font=("SF Pro Display", 32, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(0, 2))
        ctk.CTkLabel(frame, text="macOS Remote Control Agent",
                     font=("SF Pro Text", 13),
                     text_color="#aaaaaa").pack(pady=(0, 16))

        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=6)
        ctk.CTkLabel(frame, text="Setup",
                     font=("SF Pro Display", 16, "bold"),
                     text_color=ACCENT).pack(pady=(8, 14))

        # ── Bot Token ──
        self._label(frame, "Telegram Bot Token")
        self.token_entry = ctk.CTkEntry(
            frame, height=40, font=("Menlo", 12),
            placeholder_text="123456:ABC-DEF…",
            fg_color="transparent", border_color=BORDER, text_color=TEXT_PRIMARY,
        )
        self.token_entry.pack(fill="x", pady=(4, 12))

        # ── Allowed User IDs ──
        self._label(frame, "Allowed Telegram User IDs  (comma-separated)")
        self.ids_entry = ctk.CTkEntry(
            frame, height=40, font=("Menlo", 12),
            placeholder_text="123456789, 987654321",
            fg_color="transparent", border_color=BORDER, text_color=TEXT_PRIMARY,
        )
        self.ids_entry.pack(fill="x", pady=(4, 12))

        # ── Your Name ──
        self._label(frame, "Your Name")
        self.name_entry = ctk.CTkEntry(
            frame, height=40, font=("SF Pro Text", 13),
            placeholder_text="e.g. Jayash",
            fg_color="transparent", border_color=BORDER, text_color=TEXT_PRIMARY,
        )
        self.name_entry.pack(fill="x", pady=(4, 12))

        # ── Ollama Model ──
        self._label(frame, "Ollama Model  (AI chat fallback — must be pulled locally)")
        self.model_picker = OllamaModelPicker(frame, default_model="phi3")
        self.model_picker.pack(fill="x", pady=(4, 4))

        ctk.CTkLabel(
            frame,
            text="Install Ollama: brew install ollama  →  ollama pull phi3",
            font=("SF Pro Text", 10), text_color="#555555",
        ).pack(fill="x", pady=(0, 12))

        self.setup_error = ctk.CTkLabel(
            frame, text="", font=("SF Pro Text", 12), text_color=RED
        )
        self.setup_error.pack()

        ctk.CTkButton(
            frame, text="💾  Save & Launch Bot", height=50,
            font=("SF Pro Display", 16, "bold"), corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#0d1117", command=self.save_setup,
        ).pack(fill="x", pady=(8, 20))

    def _label(self, parent, text: str) -> None:
        ctk.CTkLabel(
            parent, text=text,
            font=("SF Pro Text", 13), text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x")

    def save_setup(self):
        token    = self.token_entry.get().strip()
        user_ids = self.ids_entry.get().strip()
        name     = self.name_entry.get().strip()
        model    = self.model_picker.get().strip() or "phi3"

        if not token:
            self.setup_error.configure(text="⚠ Bot Token is required.")
            return
        if not name:
            self.setup_error.configure(text="⚠ Your Name is required.")
            return
        if ":" not in token:
            self.setup_error.configure(text="⚠ Invalid token format (expected 123456:ABC…).")
            return

        self.config_data = {
            "name":            name,
            "telegram_token":  token,
            "allowed_user_id": user_ids,
            "model_name":      model,
            "created_at":      time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_config(self.config_data)
        _log.info("Config saved for: %s (model=%s)", name, model)
        self.show_control_panel()

    # ── Control panel ────────────────────────────────────────────────────────

    def show_control_panel(self):
        self.clear_window()
        name  = (self.config_data or {}).get("name", "there")
        model = (self.config_data or {}).get("model_name", "—")

        frame = ctk.CTkScrollableFrame(
            self.bg_label, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=TEXT_SECONDARY,
        )
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        # Header
        _logo = _load_logo(70)
        if _logo:
            ctk.CTkLabel(frame, image=_logo, text="").pack(pady=(10, 2))
        else:
            ctk.CTkLabel(frame, text="🌸", font=("SF Pro Display", 42)).pack(pady=(10, 2))

        ctk.CTkLabel(frame, text=APP_NAME,
                     font=("SF Pro Display", 32, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(0, 2))
        ctk.CTkLabel(frame, text=f"Hello {name} 👋",
                     font=("SF Pro Text", 15),
                     text_color=TEXT_SECONDARY).pack(pady=(0, 4))

        # Ollama model badge
        ollama_color = GREEN if ollama_is_running() else "#555555"
        self.ollama_badge = ctk.CTkLabel(
            frame,
            text=f"🤖  {model}",
            font=("Menlo", 11),
            text_color=ollama_color,
        )
        self.ollama_badge.pack(pady=(0, 16))

        # Status row
        status_row = ctk.CTkFrame(frame, fg_color="#111111", corner_radius=8)
        status_row.pack(fill="x", pady=(0, 16), ipady=10)

        self.status_icon = ctk.CTkLabel(
            status_row, text="⏹", font=("SF Pro Display", 22)
        )
        self.status_icon.pack(side="left", padx=(16, 8))

        txt_col = ctk.CTkFrame(status_row, fg_color="transparent")
        txt_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(txt_col, text="Bot Status",
                     font=("SF Pro Text", 11),
                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        self.status_label = ctk.CTkLabel(
            txt_col, text="Checking…",
            font=("SF Pro Text", 14),
            text_color=ACCENT, anchor="w",
        )
        self.status_label.pack(fill="x")

        # Buttons
        self.start_btn = ctk.CTkButton(
            frame, text="▶  START BOT", height=48,
            font=("SF Pro Text", 13), corner_radius=0,
            fg_color="transparent", border_width=1, border_color=ACCENT,
            hover_color="#1a1a1a", text_color=ACCENT,
            command=self.start_bot,
        )
        self.start_btn.pack(fill="x", pady=(0, 10))

        self.stop_btn = ctk.CTkButton(
            frame, text="⏹  STOP BOT", height=48,
            font=("SF Pro Text", 13), corner_radius=0,
            fg_color="transparent", border_width=1, border_color=BORDER,
            hover_color="#1a1a1a", text_color=TEXT_SECONDARY,
            command=self.stop_bot, state="disabled",
        )
        self.stop_btn.pack(fill="x", pady=(0, 10))

        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=10)

        # Login item toggle
        li_row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        li_row.pack(fill="x", pady=(0, 10), ipady=6)

        li_left = ctk.CTkFrame(li_row, fg_color="transparent")
        li_left.pack(side="left", fill="x", expand=True, padx=(12, 0))
        ctk.CTkLabel(li_left, text="🚀  Start on Login",
                     font=("SF Pro Text", 13, "bold"),
                     text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(li_left, text="Auto-launch bot silently at login",
                     font=("SF Pro Text", 11),
                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")

        self.startup_switch = ctk.CTkSwitch(
            li_row, text="", width=52, onvalue=True, offvalue=False,
            progress_color=ACCENT, button_color=TEXT_PRIMARY,
            command=self.toggle_startup,
        )
        self.startup_switch.pack(side="right", padx=12)
        if is_startup_enabled():
            self.startup_switch.select()

        ctk.CTkLabel(
            frame, text="🔒  Closing this window keeps the bot running",
            font=("SF Pro Text", 12), text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=10)

        # Utility buttons
        util = ctk.CTkFrame(frame, fg_color="transparent")
        util.pack(fill="x")

        ctk.CTkButton(
            util, text="⚙  Settings", height=38,
            font=("SF Pro Text", 13), corner_radius=8,
            fg_color="transparent", hover_color=BORDER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_SECONDARY,
            command=self.change_settings,
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        ctk.CTkButton(
            util, text="🔄  Reset", height=38,
            font=("SF Pro Text", 13), corner_radius=8,
            fg_color="transparent", hover_color=BORDER,
            border_width=1, border_color=BORDER,
            text_color=RED,
            command=self.reset_setup,
        ).pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Log viewer
        ctk.CTkLabel(
            frame, text="Console Output",
            font=("SF Pro Text", 12), text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x", pady=(16, 4))

        self.log_box = ctk.CTkTextbox(
            frame, height=120, font=("Menlo", 11),
            fg_color="#0d0d0d", text_color="#66bb6a",
            border_width=1, border_color=BORDER, corner_radius=0,
            state="disabled",
        )
        self.log_box.pack(fill="x")

        ctk.CTkLabel(
            frame, text="macOS Remote Control Agent",
            font=("SF Pro Text", 10), text_color="#333333",
        ).pack(pady=(10, 0))

        self.log("Lotus ready.")
        self._poll_bot_status()
        self._poll_bot_logs()

    # ── Bot control ──────────────────────────────────────────────────────────

    def _poll_bot_logs(self):
        try:
            if BOT_LOG_FILE.exists():
                size = BOT_LOG_FILE.stat().st_size
                if size > self._last_log_size:
                    with open(BOT_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self._last_log_size)
                        new_text = f.read()
                    self._last_log_size = size
                    if new_text and hasattr(self, "log_box"):
                        self.log_box.configure(state="normal")
                        self.log_box.insert("end", new_text)
                        self.log_box.see("end")
                        self.log_box.configure(state="disabled")
                elif size < self._last_log_size:
                    self._last_log_size = 0
        except Exception:
            pass
        self._log_poll = self.after(1000, self._poll_bot_logs)

    def _poll_bot_status(self):
        alive = _is_bot_alive()
        self._update_ui_status(alive)
        if not alive and self.config_data:
            self.log("🤖 Bot not running — auto-starting…")
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
                self.status_label.configure(
                    text=f"Running  (PID {pid})", text_color=GREEN
                )
                self.status_icon.configure(text="🟢")
                self.start_btn.configure(state="disabled")
                self.stop_btn.configure(state="normal")
            else:
                self.status_label.configure(text="Stopped", text_color=TEXT_SECONDARY)
                self.status_icon.configure(text="⏹")
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
        except Exception:
            pass

    def start_bot(self):
        if _is_bot_alive():
            self.log("Bot is already running.")
            return
        self.log("Starting Lotus bot service…")
        try:
            _start_bot_service()
            self.log("✅ Bot service launched.")
            self.after(2500, self._check_bot_started)
        except Exception as e:
            self.log(f"❌ Failed to start: {e}")

    def _check_bot_started(self):
        if _is_bot_alive():
            self.log(f"✅ Bot running (PID {_get_bot_pid()})")
            self._update_ui_status(True)
        else:
            self.log("⚠ Bot may still be starting…")

    def stop_bot(self):
        if not _is_bot_alive():
            self.log("Bot is not running.")
            self._update_ui_status(False)
            return
        self.log("Stopping bot service…")
        threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_stop(self):
        _stop_bot_service()
        self.after(0, lambda: self.log("⏹ Bot stopped."))
        self.after(0, lambda: self._update_ui_status(False))

    # ── Login item ────────────────────────────────────────────────────────

    def toggle_startup(self):
        if self.startup_switch.get():
            try:
                enable_startup()
                self.log("🚀 Start-on-login enabled.")
            except Exception as e:
                self.log(f"❌ Failed to enable startup: {e}")
                self.startup_switch.deselect()
        else:
            try:
                disable_startup()
                self.log("Start-on-login disabled.")
            except Exception as e:
                self.log(f"❌ Failed to disable startup: {e}")
                self.startup_switch.select()

    # ── UI helpers ────────────────────────────────────────────────────────

    def log(self, msg: str):
        try:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

    def clear_window(self):
        if hasattr(self, "_status_poll") and self._status_poll:
            self.after_cancel(self._status_poll)
            self._status_poll = None
        if hasattr(self, "_log_poll") and self._log_poll:
            self.after_cancel(self._log_poll)
            self._log_poll = None
        for widget in self.winfo_children():
            if hasattr(self, "bg_label") and widget == self.bg_label:
                for child in self.bg_label.winfo_children():
                    child.destroy()
                continue
            widget.destroy()

    def change_settings(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before changing settings.")
            return
        self.show_setup()
        if self.config_data:
            self.token_entry.insert(0, self.config_data.get("telegram_token", ""))
            self.ids_entry.insert(0, self.config_data.get("allowed_user_id", ""))
            self.name_entry.insert(0, self.config_data.get("name", ""))
            self.model_picker.set(self.config_data.get("model_name", "phi3"))

    def reset_setup(self):
        if _is_bot_alive():
            self.log("⚠ Stop the bot before resetting.")
            return
        CONFIG_FILE.unlink(missing_ok=True)
        self.config_data = None
        self.show_setup()

    def on_close(self):
        _log.info("Window closed — hiding to background")
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        _log.info("Quit requested")
        if _is_bot_alive():
            _stop_bot_service()
        self.destroy()
        sys.exit(0)


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bot-service", action="store_true",
        help="Run background bot service only (no GUI)"
    )
    args, _ = parser.parse_known_args()

    if args.bot_service:
        sys.path.insert(0, str(SRC_DIR))
        from bot_service import run_service
        run_service()
        sys.exit(0)

    # Pre-launch bot before GUI loads for faster perceived startup
    _cfg = load_config()
    if _cfg and _cfg.get("telegram_token") and not _is_bot_alive():
        try:
            _start_bot_service()
        except Exception as e:
            _log.error("Pre-launch failed: %s", e)

    app = LotusApp()
    app.mainloop()
    _log.info("=== App exited cleanly ===")
