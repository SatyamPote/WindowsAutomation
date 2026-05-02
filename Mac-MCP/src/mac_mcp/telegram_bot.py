"""Lotus Telegram bot — macOS desktop control via Telegram."""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import os
import re
import subprocess
import time
import uuid
from functools import wraps
from pathlib import Path

import psutil
from dotenv import load_dotenv
from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path.home() / "Library" / "Application Support" / "Lotus"
LOG_DIR = BASE_DIR / "logs"
STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "config"

STORAGE_FILES = STORAGE_DIR / "files"
STORAGE_IMAGES = STORAGE_DIR / "images"
STORAGE_AUDIO = STORAGE_DIR / "audio"
STORAGE_TEMP = STORAGE_DIR / "temp"

for _d in [LOG_DIR, STORAGE_DIR, DATA_DIR, STORAGE_FILES, STORAGE_IMAGES, STORAGE_AUDIO, STORAGE_TEMP]:
    _d.mkdir(parents=True, exist_ok=True)
    (_d / ".keep").touch()

USER_FILE = DATA_DIR / "users.json"
MEMORY_FILE = DATA_DIR / "memory.json"
STATS_FILE = DATA_DIR / "stats.json"
CONFIG_FILE = DATA_DIR / "config.json"

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning("Failed to save %s: %s", path, e)


def load_users() -> dict:
    return _load_json(USER_FILE, {})


def save_user(uid: str, data: dict) -> None:
    users = load_users()
    users[str(uid)] = data
    _save_json(USER_FILE, users)


def load_memory() -> dict:
    return _load_json(MEMORY_FILE, {})


def save_memory(mem: dict) -> None:
    _save_json(MEMORY_FILE, mem)


def load_stats() -> dict:
    return _load_json(STATS_FILE, {"commands": 0, "apps_opened": 0, "command_counts": {}, "date": time.strftime("%Y-%m-%d")})


def save_stats(stats: dict) -> None:
    _save_json(STATS_FILE, stats)


def load_config() -> dict:
    return _load_json(CONFIG_FILE, {})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

CONFIRM_TIMEOUT = 10
DANGEROUS_COMMANDS = {"shutdown", "restart"}
RECENT_COMMANDS: dict[int, bool] = {}
COMMAND_COUNTER = 0
clipboard_history: list[str] = []


def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        allowed = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        if not allowed:
            await update.effective_message.reply_text(
                f"🔒 Not authorized. Set TELEGRAM_ALLOWED_USER_IDS.\nYour ID: `{user.id}`",
                parse_mode="Markdown",
            )
            return
        allowed_ids = [x.strip() for x in allowed.replace(",", " ").split()]
        if str(user.id) not in allowed_ids:
            await update.effective_message.reply_text("🔒 Access denied.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def _take_screenshot() -> Image.Image:
    from mac_mcp.desktop import screenshot as screenshot_mod
    img, _backend = screenshot_mod.capture(capture_rect=None)
    max_w, max_h = 1920, 1080
    if img.width > max_w or img.height > max_h:
        ratio = min(max_w / img.width, max_h / img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    return img


# ---------------------------------------------------------------------------
# Ollama AI fallback
# ---------------------------------------------------------------------------

CHAT_RESPONSES = {
    r"\bhello\b|\bhi\b|\bhey\b": "Hey! How can I help you control your Mac?",
    r"\bthank(s| you)\b": "You're welcome!",
    r"\btime\b": "__TIME__",
    r"\bdate\b": "__DATE__",
    r"\bhow are you\b": "Running fine! Ready to automate your Mac.",
}


def _chat_reply(text: str) -> str | None:
    t = text.strip().lower()
    for pattern, response in CHAT_RESPONSES.items():
        if re.search(pattern, t):
            if response == "__TIME__":
                return f"Current time: {time.strftime('%I:%M %p')}"
            if response == "__DATE__":
                return f"Today is {time.strftime('%B %d, %Y')}"
            return response
    return _ollama_chat(text)


def _ollama_chat(text: str) -> str | None:
    try:
        import requests as _req
        cfg = load_config()
        model = cfg.get("model_name", os.getenv("OLLAMA_MODEL", "phi3"))
        r = _req.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": f"You are Lotus, a helpful macOS AI assistant. Keep responses brief and friendly. User says: {text}",
                "stream": False,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("response")
    except Exception as e:
        logger.debug("Ollama fallback failed: %s", e)
    return "I'm a macOS automation bot. Type /help to see what I can do!"


# ---------------------------------------------------------------------------
# System commands (macOS)
# ---------------------------------------------------------------------------

async def execute_system_cmd(action: str) -> dict:
    scripts = {
        "shutdown": 'tell application "Finder" to shut down',
        "restart":  'tell application "Finder" to restart',
        "sleep":    'tell application "System Events" to sleep',
        "lock":     'tell application "System Events" to keystroke "q" using {command down, control down}',
    }
    script = scripts.get(action)
    if not script:
        return {"success": False, "message": f"Unknown action: {action}"}
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode == 0:
        return {"success": True, "message": f"✅ {action.title()} executed."}
    return {"success": False, "message": f"Failed: {result.stderr.strip()}"}


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _open_path(path: str) -> None:
    subprocess.run(["open", path], check=False)


def find_file(query: str) -> list[str]:
    search_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.cwd(),
    ]
    matches: list[str] = []
    query = query.lower().strip()
    has_ext = "." in query and len(query.split(".")[-1]) >= 2

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        for root, _, files in os.walk(base_dir):
            for f in files:
                f_lower = f.lower()
                if f_lower == query:
                    matches.append(os.path.join(root, f))
                    continue
                if has_ext:
                    if query in f_lower:
                        matches.append(os.path.join(root, f))
                else:
                    name_no_ext = os.path.splitext(f_lower)[0]
                    if query == name_no_ext or query in name_no_ext:
                        matches.append(os.path.join(root, f))

    seen: set[str] = set()
    unique = []
    for m in sorted(set(matches), key=len):
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_activity(user_msg: str, bot_resp: str) -> None:
    try:
        log_path = LOG_DIR / "activity_log.txt"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] USER: {user_msg[:100]}\n")
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]  BOT: {bot_resp[:100]}\n")
    except Exception:
        pass


def track_command(cmd: str) -> None:
    stats = load_stats()
    today = time.strftime("%Y-%m-%d")
    if stats.get("date") != today:
        stats = {"commands": 0, "apps_opened": 0, "command_counts": {}, "date": today}
    stats["commands"] = stats.get("commands", 0) + 1
    counts = stats.setdefault("command_counts", {})
    key = cmd.split()[0].lower() if cmd else "unknown"
    counts[key] = counts.get(key, 0) + 1
    save_stats(stats)


def cleanup_storage() -> None:
    try:
        cutoff = time.time() - 3 * 3600
        for d in [STORAGE_TEMP]:
            for f in d.iterdir():
                if f.is_file() and f.stat().st_mtime < cutoff and f.name != ".keep":
                    f.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background threads
# ---------------------------------------------------------------------------

_bot_app = None  # set in run_bot


def battery_alert_check_loop() -> None:
    alerted = False
    while True:
        try:
            batt = psutil.sensors_battery()
            if batt and not batt.power_plugged:
                if batt.percent <= 15 and not alerted:
                    if _bot_app:
                        allowed = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
                        uid = [x.strip() for x in allowed.replace(",", " ").split() if x.strip()]
                        if uid:
                            asyncio.run_coroutine_threadsafe(
                                _bot_app.bot.send_message(
                                    chat_id=uid[0],
                                    text=f"🔋 Battery low: {batt.percent:.0f}% — please charge!",
                                ),
                                _bot_app.updater.get_event_loop() if hasattr(_bot_app, "updater") else asyncio.get_event_loop(),
                            )
                    alerted = True
                elif batt.percent > 20:
                    alerted = False
        except Exception:
            pass
        time.sleep(120)


def clipboard_tracker_loop() -> None:
    last = ""
    while True:
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, timeout=3)
            if result.returncode == 0:
                current = result.stdout.decode("utf-8", errors="replace").strip()
                if current and current != last:
                    last = current
                    if len(clipboard_history) >= 10:
                        clipboard_history.pop(0)
                    clipboard_history.append(current)
        except Exception:
            pass
        time.sleep(2)


# ---------------------------------------------------------------------------
# Main command parser
# ---------------------------------------------------------------------------

async def parse_and_execute(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    t = text.strip()
    t_lower = t.lower()
    first = t_lower.split()[0] if t_lower.split() else ""

    # ── Navigation ──
    cwd = context.user_data.get("cwd", str(Path.home() / "Desktop"))
    context.user_data["cwd"] = cwd

    if t_lower in ("ls", "list"):
        try:
            items = os.listdir(cwd)
            if not items:
                return {"success": True, "message": f"📁 Empty: `{cwd}`"}
            dirs = [f"📁 `{i}`" for i in items if os.path.isdir(os.path.join(cwd, i))]
            files = [f"📄 `{i}`" for i in items if not os.path.isdir(os.path.join(cwd, i))]
            return {"success": True, "message": f"📍 `{cwd}`\n\n" + "\n".join((dirs + files)[:30])}
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    if t_lower.startswith("cd "):
        target = t[3:].strip()
        new_path = os.path.dirname(cwd) if target == ".." else os.path.join(cwd, target)
        if not os.path.exists(new_path):
            for item in os.listdir(cwd):
                if target.lower() in item.lower() and os.path.isdir(os.path.join(cwd, item)):
                    new_path = os.path.join(cwd, item)
                    break
        if os.path.isdir(new_path):
            context.user_data["cwd"] = os.path.abspath(new_path)
            return {"success": True, "message": f"📂 `{context.user_data['cwd']}`"}
        return {"success": False, "message": f"Folder '{target}' not found."}

    # ── System commands ──
    if t_lower in ("shutdown", "restart", "sleep", "lock"):
        if t_lower in DANGEROUS_COMMANDS:
            context.user_data["pending_confirm"] = {"action": t_lower, "time": time.time()}
            return {"success": True, "message": f"⚠️ Confirm *{t_lower}*? Reply `yes` within 10s or `no` to cancel."}
        return await execute_system_cmd(t_lower)

    # ── Screenshot ──
    if t_lower in ("screenshot", "take screenshot", "screen"):
        return {"success": True, "message": "__SCREENSHOT__"}

    # ── Shell commands ──
    if first in ("run", "exec", "bash", "$"):
        cmd = t[len(first):].strip()
        if not cmd:
            return {"success": False, "message": "Run what? e.g. `run ls -la`"}
        try:
            result = subprocess.run(
                ["bash", "-c", cmd], capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip() or "(no output)"
            return {"success": True, "message": f"```\n{output[:3000]}\n```"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Command timed out (30s)."}
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    # ── App control ──
    if first in ("open", "launch", "start"):
        app_name = t[len(first):].strip()
        if not app_name:
            return {"success": False, "message": f"Open what? e.g. `{first} Safari`"}
        # Is it a URL or domain?
        if re.match(r"^https?://", app_name) or re.match(r"^[a-z0-9\-]+\.(com|net|org|io|gov|ai|me)$", app_name):
            url = app_name if app_name.startswith("http") else f"https://{app_name}"
            subprocess.run(["open", url], check=False)
            return {"success": True, "message": f"🌐 Opened {url}"}
        from mac_mcp.launcher import app_launcher
        result = app_launcher.launch(app_name)
        return {"success": True, "message": f"🚀 {result}"}

    if first == "switch":
        app_name = t[len(first):].strip()
        from mac_mcp.launcher import app_launcher
        result = app_launcher.switch(app_name)
        return {"success": True, "message": f"🔄 {result}"}

    if first == "close":
        target = t[5:].strip()
        if not target:
            return {"success": False, "message": "Close what? e.g. `close Safari`"}
        killed = 0
        for p in psutil.process_iter(["name"]):
            try:
                if target.lower() in (p.info["name"] or "").lower():
                    p.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"success": bool(killed), "message": f"Closed {killed} process(es) matching '{target}'."}

    # ── Process list ──
    if t_lower in ("ps", "processes", "tasklist"):
        rows = []
        for p in sorted(psutil.process_iter(["pid", "name", "memory_info"]), key=lambda x: (x.info.get("memory_info") or psutil.pmem(0, 0)).rss, reverse=True)[:15]:
            try:
                mem_mb = (p.info["memory_info"].rss if p.info["memory_info"] else 0) / (1024 * 1024)
                rows.append(f"`{p.info['pid']:>6}` {p.info['name'][:25]:<25} {mem_mb:.1f}MB")
            except Exception:
                pass
        return {"success": True, "message": "📊 *Top Processes:*\n" + "\n".join(rows)}

    if first in ("kill", "killpid"):
        target = t[len(first):].strip()
        if not target:
            return {"success": False, "message": "Kill what? e.g. `kill Safari` or `killpid 1234`"}
        if first == "killpid" and target.isdigit():
            try:
                p = psutil.Process(int(target))
                name = p.name()
                p.terminate()
                return {"success": True, "message": f"Killed {name} (PID {target})."}
            except Exception as e:
                return {"success": False, "message": f"Error: {e}"}
        killed = 0
        for p in psutil.process_iter(["name"]):
            try:
                if target.lower() in (p.info["name"] or "").lower():
                    p.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"success": bool(killed), "message": f"Killed {killed} process(es) matching '{target}'."}

    # ── Clipboard ──
    if t_lower == "clipboard":
        if not clipboard_history:
            return {"success": True, "message": "📋 Clipboard history is empty."}
        lines = ["📋 *Recent Clipboard Items:*\n"]
        for i, item in enumerate(reversed(clipboard_history), 1):
            disp = item if len(item) < 100 else item[:97] + "..."
            lines.append(f"{i}. `{disp}`")
        return {"success": True, "message": "\n".join(lines)}

    if t_lower == "clear clipboard":
        clipboard_history.clear()
        return {"success": True, "message": "✅ Clipboard history cleared."}

    if first == "copy":
        payload = t[4:].strip()
        if not payload:
            return {"success": False, "message": "Copy what? e.g. `copy hello world`"}
        subprocess.run(["pbcopy"], input=payload.encode(), check=False)
        return {"success": True, "message": f"📋 Copied: `{payload[:100]}`"}

    if first == "paste":
        result = subprocess.run(["pbpaste"], capture_output=True)
        content = result.stdout.decode("utf-8", errors="replace")
        return {"success": True, "message": f"📋 Clipboard:\n`{content[:500]}`" if content else "📋 Clipboard is empty."}

    # ── File operations ──
    file_extensions = (".pdf", ".txt", ".docx", ".xlsx", ".png", ".jpg", ".mp3", ".mp4", ".py", ".md")
    if first in ("find",) or any(ext in t_lower for ext in file_extensions):
        query = t[len(first):].strip() if first == "find" else t
        matches = find_file(query)
        if matches:
            context.user_data["last_files"] = matches
            if len(matches) == 1:
                _open_path(matches[0])
                return {"success": True, "message": f"📂 Opened `{os.path.basename(matches[0])}`"}
            file_map = context.user_data.setdefault("file_map", {})
            buttons = []
            for i, p in enumerate(matches[:10]):
                fid = str(uuid.uuid4())[:8]
                file_map[fid] = p
                buttons.append([InlineKeyboardButton(f"{i+1}. {os.path.basename(p)}", callback_data=f"f:open:{fid}")])
            context.user_data["file_map"] = file_map
            await update.message.reply_text(f"🔍 Matches for '{query}':", reply_markup=InlineKeyboardMarkup(buttons))
            return {"success": True, "message": "Select a file."}
        if first == "find":
            return {"success": False, "message": f"No files found for '{query}'."}

    if first == "reveal":
        path = t[len("reveal"):].strip()
        if path and os.path.exists(path):
            subprocess.run(["open", "-R", path], check=False)
            return {"success": True, "message": f"📂 Revealed in Finder: `{path}`"}
        return {"success": False, "message": "Path not found."}

    if first == "send" and " to " not in t_lower:
        query = t[4:].strip()
        if not query:
            return {"success": False, "message": "Send what? e.g. `send report.pdf`"}
        matches = find_file(query)
        if matches:
            context.user_data["last_files"] = matches
            if len(matches) == 1:
                return {"success": True, "message": f"__SEND_FILE__:{matches[0]}"}
            file_map = context.user_data.setdefault("file_map", {})
            buttons = []
            for i, p in enumerate(matches[:10]):
                fid = str(uuid.uuid4())[:8]
                file_map[fid] = p
                buttons.append([InlineKeyboardButton(f"{i+1}. {os.path.basename(p)}", callback_data=f"f:send:{fid}")])
            context.user_data["file_map"] = file_map
            await update.message.reply_text("📤 Which file?", reply_markup=InlineKeyboardMarkup(buttons))
            return {"success": True, "message": "Select a file."}
        return {"success": False, "message": f"File '{query}' not found."}

    if first == "delete":
        query = t[6:].strip()
        if not query:
            return {"success": False, "message": "Delete what? e.g. `delete report.pdf`"}
        matches = find_file(query)
        if not matches:
            return {"success": False, "message": f"File '{query}' not found."}
        context.user_data["last_files"] = matches
        if len(matches) == 1:
            context.user_data["pending_delete"] = matches[0]
            return {"success": True, "message": f"⚠️ Confirm delete `{os.path.basename(matches[0])}`? Reply `yes`."}
        file_map = context.user_data.setdefault("file_map", {})
        buttons = []
        for i, p in enumerate(matches[:10]):
            fid = str(uuid.uuid4())[:8]
            file_map[fid] = p
            buttons.append([InlineKeyboardButton(f"{i+1}. {os.path.basename(p)}", callback_data=f"f:delete:{fid}")])
        context.user_data["file_map"] = file_map
        await update.message.reply_text("🗑️ Which file to delete?", reply_markup=InlineKeyboardMarkup(buttons))
        return {"success": True, "message": "Select a file."}

    # ── Keyboard shortcut ──
    if first == "shortcut":
        shortcut = t[len("shortcut"):].strip()
        if not shortcut:
            return {"success": False, "message": "Which shortcut? e.g. `shortcut cmd+c`"}
        from mac_mcp.desktop.service import Desktop
        _desktop = Desktop()
        _desktop.shortcut(shortcut)
        return {"success": True, "message": f"⌨️ Pressed {shortcut}"}

    # ── Web search ──
    if first == "search":
        q = t[6:].strip()
        if not q:
            return {"success": False, "message": "Search what? e.g. `search AI tools`"}
        import urllib.parse
        encoded = urllib.parse.quote(q)
        await asyncio.to_thread(subprocess.run, ["open", f"https://www.google.com/search?q={encoded}"], check=False)
        return {"success": True, "message": f"🌐 Searching '{q}' on Google"}

    # ── Download (yt-dlp) ──
    if first == "download":
        rest = t[8:].strip()
        if not rest:
            return {"success": False, "message": "Download what?\n• `download <url>`\n• `download youtube <url>`"}
        orig_url = re.search(r"(https?://[^\s]+)", text)
        url = orig_url.group(1) if orig_url else rest
        if "youtube.com" in url or "youtu.be" in url:
            context.user_data["pending_download"] = {"url": url}
            buttons = [
                [InlineKeyboardButton("360p", callback_data="dl:360"),
                 InlineKeyboardButton("720p", callback_data="dl:720"),
                 InlineKeyboardButton("1080p", callback_data="dl:1080")],
                [InlineKeyboardButton("🎵 Audio only (MP3)", callback_data="dl:audio")],
            ]
            await update.message.reply_text(
                f"🎬 *YouTube Download*\n`{url}`\n\nSelect quality:",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown",
            )
            return {"success": True, "message": ""}
        try:
            out_path = str(STORAGE_FILES / os.path.basename(url.split("?")[0]))
            result = await asyncio.to_thread(
                subprocess.run,
                ["curl", "-L", "-o", out_path, url],
                capture_output=True, text=True, timeout=60,
            )
            return {"success": result.returncode == 0, "message": "✅ Downloaded." if result.returncode == 0 else f"❌ Failed: {result.stderr[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Download error: {e}"}

    # ── Dashboard ──
    if t_lower == "dashboard":
        stats = load_stats()
        counts = stats.get("command_counts", {})
        top_cmd = max(counts, key=counts.get) if counts else "—"
        batt = psutil.sensors_battery()
        batt_str = f"{batt.percent:.0f}% {'🔌' if batt.power_plugged else '🔋'}" if batt else "N/A"
        total_sz = sum(f.stat().st_size for f in STORAGE_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
        msg = (
            f"📊 *Lotus Dashboard*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📅 {stats.get('date', 'today')}\n"
            f"⚡ Commands: {stats.get('commands', 0)}\n"
            f"🏆 Top: `{top_cmd}`\n"
            f"📦 Storage: {total_sz:.1f} MB\n"
            f"🧠 CPU: {psutil.cpu_percent()}%  RAM: {psutil.virtual_memory().percent}%\n"
            f"🔋 Battery: {batt_str}"
        )
        return {"success": True, "message": msg}

    # ── System info ──
    if t_lower in ("status", "sysinfo", "info"):
        batt = psutil.sensors_battery()
        batt_str = f"{batt.percent:.0f}% {'🔌' if batt.power_plugged else '🔋'}" if batt else "N/A"
        return {
            "success": True,
            "message": (
                f"🖥️ *System Status*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🧠 CPU: {psutil.cpu_percent()}%\n"
                f"📟 RAM: {psutil.virtual_memory().percent}% used\n"
                f"💾 Disk: {psutil.disk_usage('/').percent}% used\n"
                f"🔋 Battery: {batt_str}\n"
                f"⏱️ Uptime: {_uptime()}"
            ),
        }

    # ── Logs ──
    if t_lower == "show logs":
        log_path = LOG_DIR / "activity_log.txt"
        if not log_path.exists():
            return {"success": True, "message": "📂 No logs found."}
        lines = log_path.read_text(encoding="utf-8").splitlines()
        recent = "\n".join(lines[-20:])
        return {"success": True, "message": f"📜 *Recent Logs:*\n```\n{recent}\n```"}

    if t_lower == "clear logs":
        (LOG_DIR / "activity_log.txt").write_text("")
        return {"success": True, "message": "✅ Logs cleared."}

    if t_lower == "storage status":
        total_sz = sum(f.stat().st_size for f in STORAGE_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
        file_count = sum(1 for f in STORAGE_DIR.rglob("*") if f.is_file())
        return {"success": True, "message": f"📦 Storage: {total_sz:.1f} MB · {file_count} files\n`{STORAGE_DIR}`"}

    # ── Command memory ──
    set_match = re.match(r"^set\s+(\w+)\s*=\s*(.+)$", t_lower)
    if set_match:
        name, actions = set_match.group(1), set_match.group(2)
        mem = load_memory()
        mem[name] = actions
        save_memory(mem)
        return {"success": True, "message": f"✅ Saved `{name}` → `{actions}`\nType `{name}` to run."}

    if t_lower in ("memory list", "my commands"):
        mem = load_memory()
        if not mem:
            return {"success": True, "message": "📝 No saved commands.\nUse: `set study = open safari + open vscode`"}
        lines = ["📝 *Saved Commands:*\n"] + [f"• `{k}` → `{v}`" for k, v in mem.items()]
        return {"success": True, "message": "\n".join(lines)}

    if first in ("forget", "unset"):
        name = t[len(first):].strip().lower()
        mem = load_memory()
        if name in mem:
            del mem[name]
            save_memory(mem)
            return {"success": True, "message": f"🗑️ Removed `{name}`."}
        return {"success": False, "message": f"No command `{name}` found."}

    mem = load_memory()
    if t_lower in mem:
        actions = re.split(r"\s*(?:\+|and|then)\s*", mem[t_lower])
        results = []
        for action in actions[:5]:
            action = action.strip()
            if action:
                res = await parse_and_execute(action, update, context)
                results.append(f"• {res.get('message', '?')}")
        return {"success": True, "message": f"🔄 Running `{t_lower}`:\n" + "\n".join(results)}

    # ── Result memory (open 1, send 2) ──
    if first in ("open", "send") and len(t.split()) == 2 and t.split()[1].isdigit():
        idx = int(t.split()[1]) - 1
        last_files = context.user_data.get("last_files", [])
        if 0 <= idx < len(last_files):
            path = last_files[idx]
            if first == "open":
                _open_path(path)
                return {"success": True, "message": f"Opened `{os.path.basename(path)}`"}
            return {"success": True, "message": f"__SEND_FILE__:{path}"}
        return {"success": False, "message": f"No file at index {idx + 1}."}

    # ── Ollama / conversational fallback ──
    chat_resp = _chat_reply(text)
    if chat_resp:
        return {"success": True, "message": chat_resp}

    return {"success": False, "message": "❓ I didn't understand that. Type /help to see available commands."}


def _uptime() -> str:
    secs = int(time.time() - psutil.boot_time())
    h, m = divmod(secs // 60, 60)
    d, h = divmod(h, 24)
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"


# ---------------------------------------------------------------------------
# Telegram command handlers
# ---------------------------------------------------------------------------

@require_auth
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name
    buttons = [
        [InlineKeyboardButton("🖥️ System", callback_data="system"),
         InlineKeyboardButton("📁 Files", callback_data="files")],
        [InlineKeyboardButton("🚀 Apps", callback_data="apps"),
         InlineKeyboardButton("📷 Screenshot", callback_data="screenshot")],
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("❓ Help", callback_data="help")],
    ]
    await update.message.reply_text(
        f"🌸 *Welcome to Lotus, {name}!*\nYour macOS AI Control Agent.\n\nType naturally or use buttons below.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


@require_auth
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🌸 *Lotus — macOS Control*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Apps:* `open Safari` · `launch VSCode` · `switch Terminal` · `close Chrome`\n"
        "*Shell:* `run ls -la` · `bash echo hello`\n"
        "*Files:* `find report.pdf` · `send notes.txt` · `delete old.log`\n"
        "*Screen:* `screenshot`\n"
        "*System:* `status` · `lock` · `sleep` · `shutdown` · `restart`\n"
        "*Procs:* `ps` · `kill Safari` · `killpid 1234`\n"
        "*Clipboard:* `clipboard` · `copy hello` · `paste`\n"
        "*Web:* `search AI news` · `open github.com`\n"
        "*Download:* `download <url>` · `download youtube <url>`\n"
        "*Shortcuts:* `shortcut cmd+c`\n"
        "*Memory:* `set work = open vscode` · `my commands`\n"
        "*Logs:* `show logs` · `clear logs`\n"
        "*Dashboard:* `dashboard`"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


@require_auth
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    res = await parse_and_execute("status", update, context)
    await update.message.reply_text(res["message"], parse_mode="Markdown")


@require_auth
async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screenshot(update)


@require_auth
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "clear" in update.message.text.lower():
        (LOG_DIR / "activity_log.txt").write_text("")
        await update.message.reply_text("✅ Logs cleared.")
        return
    log_path = LOG_DIR / "activity_log.txt"
    if not log_path.exists():
        await update.message.reply_text("📂 No logs found.")
        return
    lines = log_path.read_text(encoding="utf-8").splitlines()
    await update.message.reply_text(
        f"📜 *Recent Logs:*\n```\n{''.join(lines[-20:])}\n```",
        parse_mode="Markdown",
    )


@require_auth
async def cmd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    # File actions
    if data.startswith("f:"):
        parts = data.split(":", 2)
        action, fid = parts[1], parts[2]
        path = context.user_data.get("file_map", {}).get(fid)
        if not path or not os.path.exists(path):
            await query.edit_message_text("❌ File not found.")
            return
        fname = os.path.basename(path)
        if action == "send":
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > 50:
                await query.edit_message_text(f"❌ File too large ({size_mb:.1f} MB). Telegram limit is 50 MB.")
                return
            with open(path, "rb") as f:
                await query.message.reply_document(document=f, caption=f"📄 {fname}")
            await query.edit_message_text(f"✅ Sent: {fname}")
        elif action == "open":
            _open_path(path)
            await query.edit_message_text(f"✅ Opened: {fname}")
        elif action == "delete":
            try:
                os.remove(path)
                await query.edit_message_text(f"✅ Deleted: `{fname}`")
            except Exception as e:
                await query.edit_message_text(f"❌ Delete failed: {e}")
        return

    # YouTube download quality
    if data.startswith("dl:"):
        quality = data.split(":")[1]
        pending = context.user_data.pop("pending_download", None)
        if not pending:
            await query.edit_message_text("⚠️ No pending download.")
            return
        url = pending.get("url", "")
        await query.edit_message_text("⏳ Downloading…")
        try:
            out_dir = str(STORAGE_FILES)
            if quality == "audio":
                cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", f"{out_dir}/%(title)s.%(ext)s", url]
            else:
                cmd = ["yt-dlp", f"-f bestvideo[height<={quality}]+bestaudio/best[height<={quality}]", "-o", f"{out_dir}/%(title)s.%(ext)s", url]
            result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                await query.edit_message_text(f"✅ Downloaded to `{out_dir}`")
            else:
                await query.edit_message_text(f"❌ Download failed:\n```{result.stderr[:300]}```", parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return

    # Screenshot callback
    if data == "screenshot":
        await query.edit_message_text("📷 Taking screenshot…")
        await _send_screenshot_to_chat(query.message.chat_id, query.get_bot())
        return

    CATEGORY_TEXT = {
        "help":       "Type /help for all commands.",
        "status":     f"🖥️ CPU: {psutil.cpu_percent()}%  RAM: {psutil.virtual_memory().percent}%",
        "system":     "⚙️ *System*\n`lock` · `sleep` · `shutdown` · `restart` · `status`",
        "files":      "📁 *Files*\n`ls` · `cd <dir>` · `find <name>` · `send <name>` · `delete <name>`",
        "apps":       "🚀 *Apps*\n`open <name>` · `switch <name>` · `close <name>`",
    }
    await query.edit_message_text(CATEGORY_TEXT.get(data, "Unknown option."), parse_mode="Markdown")


async def _send_screenshot(update: Update) -> None:
    import io
    try:
        await update.message.reply_text("📷 Taking screenshot…")
        img = _take_screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(photo=buf, caption="🖥️ Screenshot")
    except Exception as e:
        await update.message.reply_text(f"❌ Screenshot failed: {e}")


async def _send_screenshot_to_chat(chat_id: int, bot) -> None:
    import io
    try:
        img = _take_screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await bot.send_photo(chat_id=chat_id, photo=buf, caption="🖥️ Screenshot")
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ Screenshot failed: {e}")


@require_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global COMMAND_COUNTER
    text = update.message.text
    if not text:
        return

    user_id = str(update.effective_user.id)
    msg_id = update.message.message_id
    if msg_id in RECENT_COMMANDS:
        return
    RECENT_COMMANDS[msg_id] = True

    # Greeting logic
    users = load_users()
    now = time.time()
    greeting = ""
    if user_id not in users:
        users[user_id] = {"name": update.effective_user.first_name, "last_seen": now}
        save_user(user_id, users[user_id])
        greeting = f"👋 Hello {users[user_id]['name']}!\n\n"
    else:
        last_seen = users[user_id].get("last_seen", 0)
        if now - last_seen > 12 * 3600:
            greeting = f"🏠 Welcome back, {users[user_id]['name']}!\n\n"
        users[user_id]["last_seen"] = now
        save_user(user_id, users[user_id])

    COMMAND_COUNTER += 1
    track_command(text)
    if COMMAND_COUNTER >= 10:
        cleanup_storage()
        gc.collect()
        COMMAND_COUNTER = 0

    # Confirmation handler
    answer = text.strip().lower()
    if answer in ("yes", "no"):
        pending_confirm = context.user_data.get("pending_confirm")
        if pending_confirm:
            context.user_data.pop("pending_confirm")
            if answer == "no":
                await update.message.reply_text("❌ Cancelled.")
                return
            if time.time() - pending_confirm.get("time", 0) > CONFIRM_TIMEOUT:
                await update.message.reply_text("⏰ Confirmation timed out.")
                return
            res = await execute_system_cmd(pending_confirm["action"])
            await update.message.reply_text(greeting + res["message"], parse_mode="Markdown")
            return

        pending_delete = context.user_data.pop("pending_delete", None)
        if pending_delete:
            if answer == "yes":
                try:
                    os.remove(pending_delete)
                    await update.message.reply_text(f"✅ Deleted `{os.path.basename(pending_delete)}`.", parse_mode="Markdown")
                except Exception as e:
                    await update.message.reply_text(f"❌ Delete failed: {e}")
            else:
                await update.message.reply_text("❌ Cancelled.")
            return

    result = await parse_and_execute(text, update, context)
    msg = result.get("message", "")
    if not msg:
        return

    if msg == "__SCREENSHOT__":
        await _send_screenshot(update)
        return

    if msg.startswith("__SEND_FILE__:"):
        path = msg[len("__SEND_FILE__:"):]
        if not os.path.exists(path):
            await update.message.reply_text("❌ File not found.")
            return
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 50:
            await update.message.reply_text(f"❌ File too large ({size_mb:.1f} MB). Telegram limit is 50 MB.")
            return
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, caption=f"📄 {os.path.basename(path)}")
        log_activity(text, f"Sent file: {path}")
        return

    full_msg = greeting + msg
    log_activity(text, msg[:100])
    # Telegram max message length is 4096
    if len(full_msg) > 4000:
        for chunk in [full_msg[i:i+4000] for i in range(0, len(full_msg), 4000)]:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        try:
            await update.message.reply_text(full_msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(full_msg)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning("Telegram error: %s", context.error, exc_info=context.error)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_bot(token: str | None = None) -> None:
    global _bot_app

    # Load .env
    env_candidates = [
        Path(__file__).parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(str(env_path))
            break
    else:
        load_dotenv()

    if not token:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        # Try config.json
        cfg = load_config()
        token = cfg.get("telegram_bot_token")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set. Add it to .env or config.json.")

    # Load allowed IDs from config if not in env
    if not os.getenv("TELEGRAM_ALLOWED_USER_IDS"):
        cfg = load_config()
        allowed = cfg.get("allowed_user_id") or cfg.get("allowed_user_ids", "")
        if allowed:
            os.environ["TELEGRAM_ALLOWED_USER_IDS"] = str(allowed)

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(read_timeout=300, write_timeout=300, connect_timeout=300)
    app = ApplicationBuilder().token(token).request(request).build()
    _bot_app = app

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CallbackQueryHandler(cmd_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    import threading
    threading.Thread(target=battery_alert_check_loop, daemon=True).start()
    threading.Thread(target=clipboard_tracker_loop, daemon=True).start()

    logger.info("🌸 Lotus Telegram bot starting…")
    app.run_polling()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        level=logging.INFO,
    )
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n⏹ Bot stopped.")
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
