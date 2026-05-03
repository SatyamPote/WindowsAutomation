import io
import json
import logging
import os
import platform
import time
import re
import uuid
import asyncio
import subprocess
import psutil
import difflib
from functools import wraps
from dotenv import load_dotenv
from PIL import Image

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from windows_mcp.launcher.detection import load_app_cache, find_executable
from windows_mcp.launcher.app_launcher import launch_app
from windows_mcp.uia.whatsapp import send_message
from windows_mcp.contacts.contact_manager import get_contact, load_contacts, add_contact, remove_contact, format_contacts
from windows_mcp.desktop.powershell import PowerShellExecutor
from windows_mcp.media.music_player import player as music_player
from windows_mcp.media.downloader import download_manager
from windows_mcp.media.playlist_manager import PlaylistManager
from windows_mcp.media.voice_system import VoiceSystem
from windows_mcp.research.research_engine import ResearchEngine
from windows_mcp.filesystem.storage_manager import storage_manager
from windows_mcp.tools.activity_logger import activity_logger
from windows_mcp.paths import (
    get_lotus_storage_dir, 
    get_lotus_data_dir, 
    get_lotus_log_dir
)

VERSION = "2.1.0-PROD"
REPO_URL = "https://github.com/SatyamPote/Lotus"
logger = logging.getLogger(__name__)

# Directory Setup
STORAGE_DIR = get_lotus_storage_dir()
DATA_DIR = get_lotus_data_dir()
LOG_DIR = get_lotus_log_dir()

STORAGE_FILES = STORAGE_DIR / "files"
STORAGE_VIDEOS = STORAGE_DIR / "videos"
STORAGE_IMAGES = STORAGE_DIR / "images"
STORAGE_AUDIO = STORAGE_DIR / "audio"
STORAGE_RESEARCH = STORAGE_DIR / "research"
STORAGE_TEMP = STORAGE_DIR / "temp"

for d in [STORAGE_FILES, STORAGE_VIDEOS, STORAGE_IMAGES, STORAGE_AUDIO, STORAGE_RESEARCH, STORAGE_TEMP]:
    d.mkdir(parents=True, exist_ok=True)

# Managers
playlist_manager = PlaylistManager(DATA_DIR)
voice_config_path = DATA_DIR / "voice_config.json"
voice_system = VoiceSystem(str(STORAGE_AUDIO), str(voice_config_path))
research_engine = ResearchEngine(str(STORAGE_DIR))

# Persistence
USER_FILE = os.path.join(DATA_DIR, "users.json")
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f: return json.load(f)
    return {}

def save_user(uid, data):
    users = load_users()
    users[str(uid)] = data
    with open(USER_FILE, 'w') as f: json.dump(users, f, indent=4)

# Cache for deduplication & processing
RECENT_COMMANDS = {}
APP_CACHE = load_app_cache()
COMMAND_COUNTER = 0

# App mapping for quick detection
APP_MAPPING = {
    "calculator": "calc.exe", "calc": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "vs code": "Code.exe", "code": "Code.exe",
    "whatsapp": "WhatsApp", "watsapp": "WhatsApp",
    "chrome": "chrome.exe", "google chrome": "chrome.exe",
    "edge": "msedge.exe", "microsoft edge": "msedge.exe",
    "word": "winword.exe", "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "vlc": "vlc.exe",
    "spotify": "spotify.exe",
    "settings": "start ms-settings:",
    "terminal": "wt.exe", "powershell": "powershell.exe", "cmd": "cmd.exe"
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user: return
        allowed = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        if not allowed:
            await update.effective_message.reply_text(f"🔒 Unauthorized. `TELEGRAM_ALLOWED_USER_IDS` is not set.\nYour Telegram User ID is: `{user.id}`", parse_mode="MarkdownV2")
            return
        try:
            allowed_ids = [int(x.strip()) for x in allowed.split(",") if x.strip()]
            if user.id not in allowed_ids:
                await update.effective_message.reply_text(
                    f"🔒 *Access Denied*\nYour ID (`{user.id}`) is not in the allowed list.\n\n"
                    f"Admin/Owner: Satyam Pote\nGitHub: https://github.com/SatyamPote\n\n"
                    f"Add your ID to `.env` or `config.json` to enable access.",
                    parse_mode="Markdown"
                )
                logger.warning("Unauthorized access attempt from ID: %s", user.id)
                return
        except ValueError:
            await update.effective_message.reply_text("❌ Configuration Error: `TELEGRAM_ALLOWED_USER_IDS` is invalid.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _take_screenshot() -> Image.Image:
    import pyautogui
    img = pyautogui.screenshot()
    path = os.path.join(STORAGE_DIR, f"ss_{int(time.time())}.png")
    img.save(path)
    return img, path



# Common typo → correct spelling table
TYPO_MAP = {
    'watsapp': 'whatsapp', 'whatsup': 'whatsapp', 'waatsapp': 'whatsapp',
    'calculater': 'calculator', 'calculatr': 'calculator',
    'notpad': 'notepad', 'noetpad': 'notepad',
    'chorme': 'chrome', 'crhome': 'chrome', 'goggle': 'google',
    'spootify': 'spotify', 'spotfy': 'spotify',
    'downlod': 'download', 'downlaod': 'download',
    'screnshot': 'screenshot', 'screenshoot': 'screenshot',
    'serach': 'search', 'seach': 'search',
    'youtub': 'youtube', 'yotube': 'youtube',
    'colse': 'close', 'clos': 'close',
    'opn': 'open', 'ope ': 'open ',
    'plya': 'play', 'palY': 'play',
    'voume': 'volume', 'volme': 'volume',
    'pasue': 'pause', 'paus': 'pause',
    'shutdwon': 'shutdown', 'shtudown': 'shutdown',
    'restrat': 'restart', 'restat': 'restart',
}

def clean_input(text: str) -> str:
    """Clean input: remove fillers and handle typos."""
    t = text.strip().lower()
    # Remove fillers requested by user
    t = re.sub(r'\b(on|about|research)\b', '', t)
    # Remove asterisks, slashes
    t = re.sub(r'^[^a-z0-9]+', '', t)
    # Apply typo corrections
    for wrong, right in TYPO_MAP.items():
        t = t.replace(wrong, right)
    return t.strip()

def log_error(cmd: str, err: Exception):
    """Log errors with stack trace to logs/errors.log."""
    import traceback
    os.makedirs(LOG_DIR, exist_ok=True)
    err_path = LOG_DIR / "errors.log"
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    with open(err_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} COMMAND: {cmd}\n")
        f.write(f"ERROR: {str(err)}\n")
        f.write(traceback.format_exc())
        f.write("-" * 50 + "\n")

def clear_temp_cache(context: ContextTypes.DEFAULT_TYPE):
    """Clear memory and temporary mappings."""
    import gc
    context.user_data["file_map"] = {}
    context.user_data["last_files"] = []
    RECENT_COMMANDS.clear()
    cleanup_storage()
    gc.collect()
    logger.info("🧹 Cache cleared (Memory Optimized)")

def log_activity(user_msg: str, bot_resp: str):
    """Log user interactions to file."""
    log_path = os.path.join(LOG_DIR, "activity_log.txt")
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    log_entry = f"{timestamp}\nUser: {user_msg}\nBot: {bot_resp}\n" + "-"*30 + "\n"
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# Storage limits (2GB)
STORAGE_LIMIT = 2 * 1024 * 1024 * 1024   # 2 GB
STORAGE_TARGET = 1.5 * 1024 * 1024 * 1024  # 1.5 GB cleanup target

def cleanup_storage():
    """Keep storage folder under 2GB. If over, delete oldest files until 1.5GB."""
    # Always delete temp files
    for root, _, fnames in os.walk(STORAGE_TEMP):
        for fn in fnames:
            if fn != ".keep":
                try: os.remove(os.path.join(root, fn))
                except: pass

    all_files = []
    for root, _, fnames in os.walk(STORAGE_DIR):
        for fn in fnames:
            if fn == ".keep" or fn.endswith(".json") or fn.endswith(".txt"): continue
            fp = os.path.join(root, fn)
            if os.path.isfile(fp):
                all_files.append(fp)
    
    total_size = sum(os.path.getsize(f) for f in all_files)
    
    if total_size > STORAGE_LIMIT:
        all_files.sort(key=os.path.getctime)
        for f in all_files:
            try:
                sz = os.path.getsize(f)
                os.remove(f)
                total_size -= sz
                if total_size < STORAGE_TARGET:
                    break
            except Exception:
                pass
        logger.info("🗑️ Storage cleaned (reduced to %.1f MB)", total_size / (1024*1024))

# Dangerous commands that require confirmation
DANGEROUS_COMMANDS = {"shutdown", "restart", "close all apps"}
CONFIRM_TIMEOUT = 10  # seconds

# ── Command Memory System ──
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

def load_memory() -> dict:
    """Load saved custom commands."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_memory(mem: dict):
    """Save custom commands."""
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(mem, f, indent=2)

# ── Dashboard Stats ──
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

def load_stats() -> dict:
    """Load daily stats."""
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            if stats.get("date") == today:
                return stats
        except Exception:
            pass
    return {"date": today, "commands": 0, "command_counts": {}, "apps_opened": 0}

def save_stats(stats: dict):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

def track_command(cmd_text: str):
    """Track a command for dashboard stats."""
    stats = load_stats()
    stats["commands"] = stats.get("commands", 0) + 1
    first = cmd_text.split()[0] if cmd_text else "unknown"
    counts = stats.get("command_counts", {})
    counts[first] = counts.get(first, 0) + 1
    stats["command_counts"] = counts
    if first in ["openapp", "startapp", "launchapp"]:
        stats["apps_opened"] = stats.get("apps_opened", 0) + 1
    save_stats(stats)

# ── Battery Alert System ──
_battery_alert_sent = False

def battery_alert_check_loop():
    import time
    import asyncio
    global _battery_alert_sent
    while True:
        try:
            batt = psutil.sensors_battery()
            if not batt:
                time.sleep(60)
                continue
            
            if batt.percent < 20 and not batt.power_plugged and not _battery_alert_sent:
                _battery_alert_sent = True
                users = load_users()
                if users:
                    # Use tiny-tts (or existing TTS) to generate audio
                    import pyttsx3
                    import threading
                    alert_dir = os.path.join(STORAGE_DIR, "alerts")
                    os.makedirs(alert_dir, exist_ok=True)
                    alert_file = os.path.join(alert_dir, "battery.mp3")
                    
                    def gen_tts():
                        engine = pyttsx3.init()
                        engine.save_to_file(f"Warning. Battery level is at {batt.percent} percent. Please plug in your charger.", alert_file)
                        engine.runAndWait()
                    
                    t = threading.Thread(target=gen_tts)
                    t.start()
                    t.join(timeout=10)
                    
                    # Need to notify via requests since we're outside PTB async context
                    token = _load_config_token() or os.getenv("TELEGRAM_BOT_TOKEN")
                    if token:
                        import requests
                        for user_id in users.keys():
                            try:
                                if os.path.exists(alert_file):
                                    with open(alert_file, 'rb') as f:
                                        requests.post(
                                            f"https://api.telegram.org/bot{token}/sendVoice",
                                            data={"chat_id": user_id, "caption": f"⚠️ *Battery Low Alert Sent*\nLevel: {batt.percent}%", "parse_mode": "Markdown"},
                                            files={"voice": f}
                                        )
                                else:
                                    requests.post(
                                        f"https://api.telegram.org/bot{token}/sendMessage",
                                        json={"chat_id": user_id, "text": f"⚠️ *Battery Low Alert Sent*\nLevel: {batt.percent}%", "parse_mode": "Markdown"}
                                    )
                            except Exception:
                                pass
                        
            elif batt.percent > 40 or batt.power_plugged:
                _battery_alert_sent = False
        except Exception as e:
            logger.error(f"Battery check error: {e}")
        time.sleep(60)

# ── Clipboard History System ──
clipboard_history = []

def _is_password_like(text: str) -> bool:
    """Filter out texts that look like passwords."""
    if not text or len(text) < 6 or len(text) > 32: return False
    # If it has spaces, probably a sentence, not a password
    if ' ' in text.strip(): return False
    has_upper = any(c.isupper() for c in text)
    has_lower = any(c.islower() for c in text)
    has_digit = any(c.isdigit() for c in text)
    has_special = any(not c.isalnum() for c in text)
    return has_upper and has_lower and has_digit and has_special

def clipboard_tracker_loop():
    import pyperclip
    import time
    global clipboard_history
    last_text = ""
    while True:
        try:
            current_text = pyperclip.paste()
            if current_text and current_text != last_text:
                last_text = current_text
                current_text = current_text.strip()
                if current_text and not _is_password_like(current_text):
                    if current_text in clipboard_history:
                        clipboard_history.remove(current_text)
                    clipboard_history.insert(0, current_text)
                    if len(clipboard_history) > 5:
                        clipboard_history.pop()
        except Exception:
            pass
        time.sleep(2)

# ── Global Task Queue ──
TASK_QUEUE = asyncio.Queue()
_queue_running = False

async def process_task_queue(context: ContextTypes.DEFAULT_TYPE):
    global _queue_running
    if _queue_running: return
    _queue_running = True
    while not TASK_QUEUE.empty():
        task = await TASK_QUEUE.get()
        text, update = task["text"], task["update"]
        try:
            res = await parse_and_execute(text, update, context)
            msg = res.get("message", "Done")
            icon = "✅" if res.get("success") else "❌"
            if res.get("success") and "Play" in msg:
                icon = "🎵"
            elif res.get("success") and "Opened" in msg:
                icon = "📁"
            await update.message.reply_text(f"{icon} `{text}`\n{msg}", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: `{text}`\n{e}")
        TASK_QUEUE.task_done()
    _queue_running = False

def close_all_apps():
    """Safely close all user applications."""
    system_procs = ["lotus.exe", "python.exe", "pythonw.exe", "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "explorer.exe", "svchost.exe", "winlogon.exe"]
    closed_count = 0
    for p in psutil.process_iter(['name']):
        try:
            name = p.info['name'].lower()
            if name not in system_procs and not any(s in name for s in ["telegram", "mcp"]):
                p.terminate()
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return f"✅ Closed {closed_count} applications safely."

async def execute_system_cmd(action: str) -> dict:
    cmds = {
        "shutdown": "shutdown /s /t 0",
        "restart": "shutdown /r /t 0",
        "lock": "rundll32.exe user32.dll,LockWorkStation",
        "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
    }
    if action in cmds:
        subprocess.Popen(cmds[action], shell=True)
        return {"success": True, "message": f"System {action} initiated."}
    return {"success": False, "message": "Unknown system command."}

# ---------------------------------------------------------------------------
# Conversational Chat Engine
# ---------------------------------------------------------------------------

CHAT_RESPONSES = {
    # greetings
    r'\b(hi|hello|hey|sup|yo)\b': "Hey! 👋 I'm Lotus — your Windows AI assistant, built by *Satyam Pote*. What do you need?",
    r'\b(how are you|how r u|how are u)\b': "I'm running perfectly! 🚀 Ready to control your PC. What's the command?",
    r'\b(what can you do|what do you do|capabilities|features)\b': "I can control your entire Windows PC! Open apps, play music, manage files, take screenshots, send WhatsApp messages, run PowerShell, and much more. Type /help for full list.",
    r'\b(who are you|what are you|your name)\b': "I'm *Lotus* 🌸 — an AI-powered Windows control agent created by *Satyam Pote*. I execute your commands on your PC via Telegram, fast and reliably.",
    r'\b(who made you|who created you|who built you|who is your (creator|developer|maker|author|owner))\b': "I was created by *Satyam Pote* 🧑‍💻\n\n🔗 GitHub: [SatyamPote](https://github.com/SatyamPote)\n📧 Email: satyampote9999@gmail.com\n\nLotus is an open-source AI Windows control agent. 🌸",
    r'\b(thanks|thank you|thx|ty)\b': "You're welcome! 😊 Anything else?",
    r'\b(good|great|awesome|nice|cool|perfect|excellent)\b': "Glad it worked! 🎉 What's next?",
    r'\b(help me|i need help|assist me)\b': "Sure! Here's what I can do — type /help for the full command list.",
    r'\b(ok|okay|alright|got it|sure)\b': "Got it! Let me know if you need anything.",
    r'\b(bye|goodbye|see you|later|cya)\b': "See you! 👋 I'll be here whenever you need PC control.",
    r'\b(what time is it|current time|time now)\b': f"Current time: {time.strftime('%I:%M %p')}",
    r'\b(what.*date|today.*date|current date)\b': f"Today is {time.strftime('%B %d, %Y')}",
    r'\b(are you working|are you online|you there|you alive)\b': "Yes! ✅ Online and ready. What do you need?",
}

def _chat_reply(text: str) -> str | None:
    """Returns a conversational reply if text looks like chat, else None."""
    t = text.strip().lower()
    for pattern, response in CHAT_RESPONSES.items():
        if re.search(pattern, t):
            # Replace time/date placeholders dynamically
            if 'time' in pattern:
                return f"Current time: {time.strftime('%I:%M %p')}"
            if 'date' in pattern:
                return f"Today is {time.strftime('%B %d, %Y')}"
            return response
    # ── FINAL FALLBACK: Local Ollama AI ──
    return _ollama_chat(text)

def _ollama_chat(text: str) -> str | None:
    """Fallback to local Ollama AI for real conversation."""
    try:
        import requests
        import sys as _sys
        model_name = "phi3"  # Default
        # Search for config.json in multiple locations
        config_candidates = []
        if getattr(_sys, 'frozen', False):
            config_candidates.append(os.path.join(os.path.dirname(_sys.executable), "config.json"))
        config_candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.json"))
        PROGRAM_DATA_DIR = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        config_candidates.append(os.path.join(PROGRAM_DATA_DIR, "Lotus", "config", "config.json"))
        for cp in config_candidates:
            cp = os.path.normpath(cp)
            if os.path.exists(cp):
                try:
                    with open(cp, 'r') as f:
                        cfg = json.load(f)
                    model_name = cfg.get("model") or cfg.get("model_name", "phi3")
                    break
                except Exception:
                    pass
        
        # Call Ollama API with Lotus identity
        system_prompt = (
            "You are Lotus, a helpful Windows AI assistant created by Satyam Pote. "
            "You control the user's Windows PC via Telegram. "
            "Keep responses brief, friendly, and helpful. "
            "If asked who made you or who your creator is, always say Satyam Pote. "
            "Never claim to be made by OpenAI, Microsoft, Google, or any other company. "
            "You are an independent open-source project."
        )
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": f"{system_prompt}\n\nUser says: {text}",
                "stream": False
            },
            timeout=5
        )
        if response.status_code == 200:
            reply = response.json().get("response", "").strip()
            if reply:
                return f"🤖 *AI ({model_name}):*\n{reply}"
    except Exception as e:
        logger.debug(f"Ollama chat fallback failed: {e}")
    
    return "I'm Lotus 🌸, your Windows AI agent by Satyam Pote. I can execute commands but need Ollama running for AI chat. Try /help to see what I can do!"

def find_file(query: str) -> list[str]:
    """
    Improved fuzzy search for files in common user folders.
    Rules:
    - Lowercase matching
    - Ignore extension if missing in query
    - Match partial names
    - Recursive search in Downloads, Desktop, Documents, and CWD
    """
    search_dirs = [
        os.path.join(os.path.expanduser("~"), "Downloads"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.getcwd()
    ]
    
    matches = []
    query = query.lower().strip()
    has_ext = "." in query and len(query.split(".")[-1]) >= 2
    
    for base_dir in search_dirs:
        if not os.path.exists(base_dir): continue
        for root, _, files in os.walk(base_dir):
            for f in files:
                f_lower = f.lower()
                # 1. Exact match
                if f_lower == query:
                    matches.append(os.path.abspath(os.path.join(root, f)))
                    continue
                
                # 2. Fuzzy match
                if has_ext:
                    # If query has ext, match exactly or containing
                    if query in f_lower:
                        matches.append(os.path.abspath(os.path.join(root, f)))
                else:
                    # If query no ext, match f name without ext
                    name_no_ext = os.path.splitext(f_lower)[0]
                    if query == name_no_ext or query in name_no_ext:
                        matches.append(os.path.abspath(os.path.join(root, f)))
                        
    # Deduplicate and sort by path length (shallowest first)
    unique_matches = list(set(matches))
    unique_matches.sort(key=len)
    return unique_matches

# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _execute_play_search(platform: str, intent: str, query: str, encoded: str, url: str):
    import pyautogui
    import pygetwindow as gw
    import webbrowser
    if platform == "spotify": _play_spotify(intent, query, encoded, url)
    elif platform == "youtube": _play_youtube(intent, query, encoded, url)
    else: webbrowser.open(url)

def _focus_window(title_keywords: list) -> bool:
    import pygetwindow as gw
    for keyword in title_keywords:
        try:
            windows = gw.getWindowsWithTitle(keyword)
            if windows:
                win = windows[0]
                if win.isMinimized: win.restore(); time.sleep(0.5)
                win.activate(); time.sleep(0.5); return True
        except Exception: continue
    return False

def _play_spotify(intent: str, query: str, encoded: str, url: str):
    import pyautogui
    import webbrowser
    spotify_running = any('spotify' in (p.info.get('name') or '').lower() for p in psutil.process_iter(['name']) if not isinstance(p, Exception))
    if not spotify_running:
        try: os.startfile("spotify:"); time.sleep(5); spotify_running = True
        except Exception: pass
    if not spotify_running: webbrowser.open(url); return
    focused = _focus_window(["Spotify", "Spotify Free", "Spotify Premium"])
    if not focused: webbrowser.open(url); return
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'l'); time.sleep(0.4); pyautogui.hotkey('ctrl', 'a'); time.sleep(0.1)
    try:
        q_safe = query.replace('"', '\\"')
        subprocess.run(['powershell', '-command', f'Set-Clipboard -Value "{q_safe}"'], capture_output=True, timeout=3)
        pyautogui.hotkey('ctrl', 'v')
    except Exception: pyautogui.typewrite(query[:50], interval=0.03)
    time.sleep(0.4); pyautogui.press('enter')
    if intent != "play": return
    time.sleep(2.5)
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("Spotify")
        if not wins: return
        win = wins[0]; wx, wy, ww, wh = win.left, win.top, win.width, win.height
        card_cx, card_cy = wx + int(ww * 0.16), wy + int(wh * 0.37)
        pyautogui.moveTo(card_cx, card_cy, duration=0.4); time.sleep(0.5)
        try:
            import PIL.ImageGrab
            scan_x1, scan_y1, scan_x2, scan_y2 = wx + int(ww * 0.03), wy + int(wh * 0.20), wx + int(ww * 0.32), wy + int(wh * 0.54)
            screen = PIL.ImageGrab.grab(bbox=(scan_x1, scan_y1, scan_x2, scan_y2))
            pixels = screen.load(); pw, ph = screen.size; found_x, found_y = None, None
            for px in range(pw):
                for py in range(ph):
                    r, g, b = pixels[px, py][:3]
                    if r <= 80 and 150 <= g <= 220 and 50 <= b <= 130: found_x, found_y = scan_x1 + px, scan_y1 + py; break
                if found_x: break
            if found_x: pyautogui.click(found_x, found_y); return
        except Exception: pass
        pyautogui.doubleClick(card_cx, card_cy); time.sleep(0.5)
    except Exception: webbrowser.open(url)

def _play_youtube(intent: str, query: str, encoded: str, url: str):
    import webbrowser; webbrowser.open(url)
    if intent == "play":
        time.sleep(5)
        focused = _focus_window(["YouTube", "Google Chrome", "Microsoft Edge", "Firefox", "Brave", "Opera"])
        if focused:
            import pyautogui; time.sleep(0.5); pyautogui.press('tab', presses=10, interval=0.05); pyautogui.press('enter')

async def parse_and_execute(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """STRICT PRIORITY ROUTER: System > File > Music > Research > AI Fallback."""
    raw_text = text
    t = clean_input(text)
    first_word = t.split()[0] if t else ""
    
    # ── 1. SYSTEM COMMANDS ──
    sys_cmds = ["shutdown", "restart", "lock", "sleep", "storage status", "clear storage", "show logs", "clear logs", "dashboard"]
    if t in sys_cmds:
        if t == "storage status":
            status = storage_manager.get_status()
            return {"success": True, "message": f"📦 *Storage Status*\nSize: {status['size_mb']:.2f} MB / {status['limit_mb']} MB"}
        if t == "clear storage": return {"success": True, "message": storage_manager.clear_storage()}
        if t == "show logs": return {"success": True, "message": f"📜 *Logs:*\n`{activity_logger.get_logs(10)}`"}
        if t == "clear logs": return {"success": True, "message": activity_logger.clear_logs()}
        if t == "dashboard":
            stats = load_stats()
            return {"success": True, "message": f"📊 *Lotus Dashboard*\nCommands: {stats.get('commands', 0)}\nApps: {stats.get('apps_opened', 0)}"}
        return await execute_system_cmd(t)

    # ── 2. FILE COMMANDS (open/send) ──
    if first_word in ["open", "send", "find"]:
        query = t.replace(first_word, "").strip()
        if query:
            # Search in storage, research, downloads
            search_dirs = [STORAGE_DIR, STORAGE_RESEARCH, os.path.join(os.path.expanduser("~"), "Downloads")]
            found_path = None
            for d in search_dirs:
                if not os.path.exists(d): continue
                for root, _, files in os.walk(d):
                    for f in files:
                        if query in f.lower():
                            found_path = os.path.join(root, f)
                            break
                    if found_path: break
                if found_path: break
            
            if found_path:
                if first_word == "open":
                    os.startfile(found_path)
                    return {"success": True, "message": f"📂 Opened: `{os.path.basename(found_path)}`"}
                elif first_word == "send":
                    return {"success": True, "message": f"__SEND_FILE__:{found_path}"}
                else:
                    return {"success": True, "message": f"📍 Found: `{found_path}`"}
            
            # General fallback search
            if first_word == "find":
                matches = find_file(query)
                if matches:
                    context.user_data["last_files"] = matches[:5]
                    resp = "🔍 *Found matches:*\n" + "\n".join([f"{i+1}. `{os.path.basename(m)}`" for i, m in enumerate(matches[:5])])
                    return {"success": True, "message": resp}

    # ── 3. MUSIC & PLAYLIST COMMANDS ──
    # Regex for complex playlist commands
    create_pl = re.match(r'^create playlist\s+(.+)$', t)
    delete_pl = re.match(r'^delete playlist\s+(.+)$', t)
    add_pl = re.match(r'^add to playlist\s+(\w+)\s+(.+)$', t)
    play_pl = re.match(r'^play playlist\s+(.+)$', t)
    vol_cmd = re.match(r'^volume\s+(\d+)$', t)

    if first_word == "play" and not play_pl:
        query = t[4:].strip()
        if not query: return {"success": False, "message": "❓ Play what?"}
        return music_player.play_song(query)

    if t == "stop": return music_player.stop()
    if t in ["pause", "resume"]: return music_player.pause_resume()
    if t == "next": return music_player.next_song()
    
    if vol_cmd: return music_player.set_volume(vol_cmd.group(1))
    if create_pl: return music_player.create_playlist(create_pl.group(1).strip())
    if delete_pl: return music_player.delete_playlist(delete_pl.group(1).strip())
    if add_pl: return music_player.add_to_playlist(add_pl.group(1), add_pl.group(2))
    if play_pl: return music_player.play_playlist(play_pl.group(1).strip())

    # ── 4. RESEARCH / DOWNLOAD ──
    if first_word == "research":
        topic = t.replace("research", "").strip()
        if topic: return {"success": True, "message": f"__RESEARCH__:{topic}"}
    
    if first_word == "download":
        query = t[9:].strip()
        if "youtube.com" in query or "youtu.be" in query:
            return {"success": True, "message": f"📥 Download queued: {query}"}

    # ── 5. VOICE COMMANDS ──
    if t == "voice on": return {"success": True, "message": voice_system.toggle_voice(True)}
    if t == "voice off": return {"success": True, "message": voice_system.toggle_voice(False)}
    if t == "stop voice":
        voice_system.stop_voice()
        return {"success": True, "message": "🔇 Local voice stopped."}
    
    if first_word == "say":
        words = t[4:].strip()
        if words:
            voice_system.speak(words)
            return {"success": True, "message": f"🗣️ Speaking: {words}"}
        return {"success": False, "message": "❓ Say what?"}

    if t == "voice auto on":
        voice_system.auto_voice = True
        return {"success": True, "message": "🎙️ Auto-voice feedback: ON"}
    if t == "voice auto off":
        voice_system.auto_voice = False
        return {"success": True, "message": "🎙️ Auto-voice feedback: OFF"}

    if t.startswith("voice style"):
        style = t.replace("voice style", "").strip()
        if style in ["female", "male"]:
            voice_system.config["style"] = style
            voice_system.save_config()
            return {"success": True, "message": f"🎭 Voice style set to: {style}"}
        return {"success": False, "message": "❓ Style must be 'female' or 'male'."}

    # ── 6. AI FALLBACK ──
    chat_resp = _chat_reply(raw_text)
    if chat_resp:
        return {"success": True, "message": chat_resp}

    return {"success": False, "message": "❓ Command unrecognized. Try `/help`."}

# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------



@require_auth
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name
    help_text = (
        f"🌸 *Welcome to Lotus, {name}!* 👋\n"
        "Your Personal Windows AI Control System.\n\n"
        "Explore my capabilities using the buttons below or type naturally (e.g., 'play some music')."
    )
    buttons = [
        [InlineKeyboardButton("📁 Files", callback_data="files"),
         InlineKeyboardButton("🎵 Media", callback_data="media")],
        [InlineKeyboardButton("🖥️ System", callback_data="system"),
         InlineKeyboardButton("📥 Downloads", callback_data="downloads")],
        [InlineKeyboardButton("💬 WhatsApp", callback_data="whatsapp"),
         InlineKeyboardButton("📷 Tools", callback_data="tools")],
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

@require_auth
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🌸 *Lotus AI — Full Guide*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ *Basic Controls*\n"
        "• `/start` — Quick dashboard\n"
        "• `/help` — Show this guide\n"
        "• `/version` — Check for updates\n"
        "• `/status` — View PC health\n\n"
        "🎵 *Media & Playlists*\n"
        "• `play <song>` — Play music\n"
        "• `pause` / `resume` / `stop` / `next`\n"
        "• `volume <0-100>`\n"
        "• `create playlist <name>`\n"
        "• `delete playlist <name>`\n"
        "• `play playlist <name>`\n"
        "• `add to playlist <name> <song>`\n\n"
        "🗣️ *Voice Feedback*\n"
        "• `voice on` / `voice off` — Toggle voice\n"
        "• `stop voice` — Kill local audio\n"
        "• `voice style female` — Sweet female tone\n"
        "• `voice auto on/off` — Auto replies\n"
        "• `say <text>` — Talk via PC speakers\n\n"
        "🖥️ *System & Tools*\n"
        "• `record screen <seconds>` — Captures MP4\n"
        "• `take screenshot` — Full desktop view\n"
        "• `lock pc` / `sleep pc` / `shutdown`\n"
        "• `open <app>` (e.g., Chrome, VS Code)\n"
        "• `close <app>` — Terminate process\n\n"
        "📁 *File Management*\n"
        "• `find <name>` — Search PC files\n"
        "• `send <name>` — Get file on Telegram\n"
        "• `compress <name>` — ZIP file/folder\n"
        "• `delete <name>` — Remove from PC\n\n"
        "💬 *Automation*\n"
        "• `research <topic>` — Advanced search\n"
        "• `send msg to <contact> <text>` — WhatsApp\n"
        "• `set <name> = <cmds>` — Create macros\n\n"
        "👤 *Developer:* Satyam Pote\n"
        "Type any command naturally. Lotus will understand!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

@require_auth
async def cmd_add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/add <name> : <number>"""
    msg = update.message.text[5:].strip()
    if ":" not in msg:
        await update.message.reply_text("❌ Usage: `/add Name : +1234567890`", parse_mode="Markdown")
        return
    name, phone = msg.split(":", 1)
    res = add_contact(name.strip(), phone.strip())
    await update.message.reply_text(f"✅ {res}")

@require_auth
async def cmd_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_contacts(), parse_mode="Markdown")

@require_auth
async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👤 *Owner Information*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Name:* Satyam Pote\n"
        "*Email:* satyampote9999@gmail.com\n"
        "*GitHub:* [SatyamPote](https://github.com/SatyamPote)\n"
        "*Project:* Lotus Control Agent\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *About:*\n"
        "I build AI tools, automation systems, and custom Windows agents.\n\n"
        "📩 Contact for custom tools, automation, or collaboration.\n"
        "Open to freelance and open-source projects."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

@require_auth
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_path = os.path.join(LOG_DIR, "activity_log.txt")
    if "clear" in update.message.text.lower():
        with open(log_path, 'w') as f: f.write("")
        await update.message.reply_text("✅ Logs cleared.")
        return
    if not os.path.exists(log_path):
        await update.message.reply_text("📂 No logs found.")
        return
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        recent = "".join(lines[-20:])
    await update.message.reply_text(f"📜 *Recent Logs:*\n\n`{recent}`", parse_mode="Markdown")

@require_auth
async def cmd_storage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    all_files = []
    for root, _, fnames in os.walk(STORAGE_DIR):
        for fn in fnames:
            fp = os.path.join(root, fn)
            if os.path.isfile(fp): all_files.append(fp)
    total_size = sum(os.path.getsize(f) for f in all_files) / (1024*1024)
    await update.message.reply_text(
        f"📦 *Storage Status*\n━━━━━━━━━\n📂 *Path:* `{STORAGE_DIR}`\n"
        f"📊 *Size:* {total_size:.2f} MB / 2048 MB (2 GB)\n"
        f"📁 *Files:* {len(all_files)}",
        parse_mode="Markdown"
    )

@require_auth
async def cmd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data.startswith("f:"):
        _, action, fid = query.data.split(":")
        path = context.user_data.get("file_map", {}).get(fid)
        if not path or not os.path.exists(path):
            await query.edit_message_text("❌ File no longer available or not found.")
            return
        fname = os.path.basename(path)
        if action == "send":
            # Check file size (Telegram bot limit is 50MB)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > 50:
                await query.edit_message_text(f"❌ File too large ({size_mb:.1f}MB). Telegram bots are limited to 50MB.")
                return
            
            with open(path, 'rb') as f:
                # Use a long read_timeout for large files
                await query.message.reply_document(
                    document=f, 
                    caption=f"📄 {fname}",
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=300,
                    pool_timeout=300
                )
            await query.edit_message_text(f"✅ Sent: {fname}")
        elif action == "open":
            os.startfile(path); await query.edit_message_text(f"✅ Opened: {fname}")
        elif action == "find":
            await query.edit_message_text(f"📍 Location: `{path}`", parse_mode="Markdown")
        elif action == "delete":
            try:
                os.remove(path)
                await query.edit_message_text(f"✅ Deleted: `{fname}`")
            except Exception as e:
                await query.edit_message_text(f"❌ Failed to delete: {e}")
        return

    # Download quality selection callback
    if query.data.startswith("dl:"):
        quality = query.data.split(":")[1]
        pending = context.user_data.get("pending_download")
        if not pending:
            await query.edit_message_text("⚠️ No pending download.")
            return
        url = pending.get("url", "")
        context.user_data.pop("pending_download", None)
        if quality == "audio":
            success, msg = download_manager.download_youtube(url, audio_only=True)
        else:
            success, msg = download_manager.download_youtube(url, quality=quality)
        await query.edit_message_text(msg, parse_mode="Markdown")
        return

    CATEGORY_TEXT = {
        "help": "💡 Type `/help` for a full list of commands or use the buttons below.",
        "status": f"📊 *System Status*\n━━━━━━━━━\n🧠 *CPU:* {psutil.cpu_percent()}%\n📟 *RAM:* {psutil.virtual_memory().percent}%",
        "media": "🎵 *Media Control*\n• `play <name>`\n• `pause` / `resume`\n• `next` / `stop`\n• `volume up/down`",
        "files": "📁 *File Navigation*\n• `ls` — List directory\n• `cd <folder>` — Move\n• `open <file>` — View\n• `send <file>` — Upload",
        "system": "⚙️ *System Control*\n• `lock` / `sleep`\n• `shutdown` / `restart`\n• `open settings` / `cmd` / `taskmgr`",
        "tools": "📷 *Desktop Tools*\n• `take screenshot`\n• `open terminal`\n• `close <app>`",
        "whatsapp": "💬 *WhatsApp*\n• `send <text> to <contact>`\n• `send screenshot to <contact>`",
        "downloads": "📥 *Downloads*\n• `download youtube <url>`\n• `download images <topic>`\n• `download <url>`\n• `download cancel`",
    }
    await query.edit_message_text(CATEGORY_TEXT.get(query.data, "Unknown option."), parse_mode="Markdown")

@require_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text: return
    
    # Standard Frame
    FRAME_TOP = "━━━━━━━━━━━━━━━━━━━━\n📖 *Lotus Response*\n━━━━━━━━━━━━━━━━━━━━\n"
    FRAME_BTM = "\n━━━━━━━━━━━━━━━━━━━━"

    processing_msg = await update.message.reply_text("⏳ Processing...")
    try:
        async with asyncio.timeout(180.0):
            res = await parse_and_execute(text, update, context)
            msg = res.get("message", "Done")
            success = res.get("success", False)

            # Special Signal Handling
            if msg.startswith("__RESEARCH__:"):
                topic = msg.split(":", 1)[1]
                await processing_msg.edit_text(f"🔍 Researching *{topic}*...")
                result = await asyncio.to_thread(research_engine.perform_research, topic)
                if result["success"]:
                    for img in result["images"][:3]:
                        try:
                            with open(img, 'rb') as f: await update.message.reply_photo(f)
                        except: pass
                    with open(result["pdf"], 'rb') as f:
                        await update.message.reply_document(f, caption=f"📄 Report: {topic}")
                    await processing_msg.edit_text(f"{FRAME_TOP}✅ Research Complete: {topic}{FRAME_BTM}", parse_mode="Markdown")
                else:
                    await processing_msg.edit_text(f"{FRAME_TOP}❌ Research Failed: {topic}{FRAME_BTM}", parse_mode="Markdown")
                return

            if msg.startswith("__SEND_FILE__:"):
                path = msg.split(":", 1)[1]
                with open(path, 'rb') as f:
                    await update.message.reply_document(f, caption=f"📄 {os.path.basename(path)}")
                await processing_msg.delete()
                return

            # Final response
            icon = "✅" if success else "❌"
            if "play" in msg.lower(): icon = "🎵"
            
            await processing_msg.edit_text(f"{FRAME_TOP}{icon} {msg}{FRAME_BTM}", parse_mode="Markdown")
            
            # Voice Feedback (if enabled)
            if voice_system.auto_voice and success:
                # Clean markdown for TTS
                tts_text = msg.replace("*", "").replace("_", "").replace("`", "")
                voice_system.speak(tts_text)
            
    except Exception as e:
        log_error(text, e)
        await processing_msg.edit_text(f"{FRAME_TOP}❌ Critical Error occurred. Check logs.{FRAME_BTM}", parse_mode="Markdown")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        error_msg = f"❌ Telegram Error: {context.error}"
        if "Timed out" in str(context.error):
            error_msg = "⚠️ Upload timed out. The file might be too large or the connection slow."
        await update.effective_message.reply_text(error_msg)

def _load_config_token() -> str | None:
    """Load bot token from config.json if it exists."""
    import sys as _sys
    # Check app directory first (where installer puts it), then ProgramData
    candidates = []
    if getattr(_sys, 'frozen', False):
        candidates.append(os.path.join(os.path.dirname(_sys.executable), "config.json"))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.json"))
    PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    candidates.append(os.path.join(PROGRAM_DATA, "Lotus", "config", "config.json"))
    for config_path in candidates:
        config_path = os.path.normpath(config_path)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                return cfg.get("telegram_token") or cfg.get("bot_token")
            except Exception:
                pass
    return None

def run_bot(token: str = None) -> None:
    # Find .env relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    env_path = os.path.join(project_root, ".env")
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv() # Fallback to CWD

    # Priority: param > config.json > env var
    if not token:
        token = _load_config_token()
    if not token:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set. Run Lotus app or set env var.")
    
    # Also load allowed user IDs from config if present
    import sys as _sys
    config_candidates = []
    if getattr(_sys, 'frozen', False):
        config_candidates.append(os.path.join(os.path.dirname(_sys.executable), "config.json"))
    config_candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.json"))
    PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    config_candidates.append(os.path.join(PROGRAM_DATA, "Lotus", "config", "config.json"))
    for cp in config_candidates:
        cp = os.path.normpath(cp)
        if os.path.exists(cp):
            try:
                with open(cp, 'r') as f:
                    cfg = json.load(f)
                allowed = cfg.get("allowed_user_id") or cfg.get("allowed_user_ids", "")
                if allowed and not os.getenv("TELEGRAM_ALLOWED_USER_IDS"):
                    os.environ["TELEGRAM_ALLOWED_USER_IDS"] = str(allowed)
                break
            except Exception:
                pass

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(read_timeout=300, write_timeout=300, connect_timeout=300)
    
    async def post_init(application):
        from telegram import BotCommand
        bot_cmds = [
            BotCommand("start", "Show dashboard"),
            BotCommand("help", "Show all commands"),
            BotCommand("version", "Check for updates"),
            BotCommand("playlist", "List music playlists"),
            BotCommand("voice", "Voice Control: on/off/stop"),
            BotCommand("status", "View PC hardware status"),
            BotCommand("contacts", "List WhatsApp contacts"),
            BotCommand("storage", "Check storage usage"),
            BotCommand("admin", "Creator details")
        ]
        try:
            await application.bot.set_my_commands(bot_cmds)
            logger.info("✅ Telegram bot commands menu updated.")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")

    app = ApplicationBuilder().token(token).request(request).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("version", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("playlist", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("add", cmd_add_contact))
    app.add_handler(CommandHandler("contacts", cmd_contacts))
    app.add_handler(CommandHandler("owner", cmd_owner))
    app.add_handler(CommandHandler("admin", cmd_owner))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("storage", cmd_storage))
    app.add_handler(CommandHandler("status", lambda u, c: u.message.reply_text(f"📊 CPU: {psutil.cpu_percent()}% · RAM: {psutil.virtual_memory().percent}%")))
    app.add_handler(CallbackQueryHandler(cmd_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_error_handler(error_handler)
    
    # Start background job for battery alerts (using thread to avoid PTB JobQueue issues)
    import threading
    threading.Thread(target=battery_alert_check_loop, daemon=True).start()
    
    # Start clipboard tracker loop
    threading.Thread(target=clipboard_tracker_loop, daemon=True).start()
    
    logger.info("🚀 Lotus starting (with 300s timeouts)...")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    # Silence noisy comtypes debug logs
    logging.getLogger("comtypes").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n⏹ Bot stopped by user.")
    except Exception as e:
        import traceback
        print("\n❌ ERROR:", e)
        traceback.print_exc()
        input("\nPress Enter to exit...")
