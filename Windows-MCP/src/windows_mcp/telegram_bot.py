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

logger = logging.getLogger(__name__)

# Directory Setup
BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, "logs")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DATA_DIR = os.path.join(BASE_DIR, "data")

STORAGE_FILES = os.path.join(STORAGE_DIR, "files")
STORAGE_VIDEOS = os.path.join(STORAGE_DIR, "videos")
STORAGE_IMAGES = os.path.join(STORAGE_DIR, "images")
STORAGE_AUDIO = os.path.join(STORAGE_DIR, "audio")
STORAGE_TEMP = os.path.join(STORAGE_DIR, "temp")

for d in [LOG_DIR, STORAGE_DIR, DATA_DIR, STORAGE_FILES, STORAGE_VIDEOS, STORAGE_IMAGES, STORAGE_AUDIO, STORAGE_TEMP]:
    os.makedirs(d, exist_ok=True)
    # create .keep file
    open(os.path.join(d, ".keep"), "w").close()

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



def clean_input(text: str) -> str:
    # Fix merged words and spaces
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    t = text.strip().lower()
    
    # Aggressive normalization
    fillers = [
        r'\bapplication\b', r'\baplication\b', r'\bsoftware\b', 
        r'\bcan you\b', r'\bplease\b', r'\bsong\b'
    ]
    for f in fillers:
        t = re.sub(f, '', t)
    
    # Fix common typos
    t = t.replace('watsapp', 'whatsapp')
    return t.strip()

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
    system_procs = ["python.exe", "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "explorer.exe", "svchost.exe", "winlogon.exe"]
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
    r'\b(hi|hello|hey|sup|yo)\b': "Hey! 👋 I'm Lotus — your Windows AI. What do you need?",
    r'\b(how are you|how r u|how are u)\b': "I'm running perfectly! 🚀 Ready to control your PC. What's the command?",
    r'\b(what can you do|what do you do|capabilities|features)\b': "I can control your entire Windows PC! Open apps, play music, manage files, take screenshots, send WhatsApp messages, and much more. Type /help for full list.",
    r'\b(who are you|what are you|your name)\b': "I'm *Lotus* 🖥️ — an AI that controls your Windows PC via Telegram. Built to execute your commands fast and reliably.",
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
    # Detect questions
    if t.endswith('?') or t.startswith(('what', 'how', 'why', 'when', 'where', 'who', 'can you', 'do you')):
        return "I'm a Windows automation bot. I can execute commands but can't answer general questions. Try /help to see what I can do!"
    return None

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
    """Strictly classified parser: Music > Apps > Msg > Files > Web."""
    t = clean_input(text)
    t_clean = t.replace("please", "").strip()
    first_word = t.split()[0] if t else ""
    
    # ── PRIORITY 0: Shell-like Navigation ──
    cwd = context.user_data.get("cwd", os.path.join(os.path.expanduser("~"), "Desktop"))
    context.user_data["cwd"] = cwd
    
    if t in ["ls", "list"]:
        logger.info(f"Intent: NAVIGATION (ls)")
        try:
            items = os.listdir(cwd)
            if not items: return {"success": True, "message": f"📁 Folder is empty: `{cwd}`"}
            folder_list = [f"📁 `{item}`" for item in items if os.path.isdir(os.path.join(cwd, item))]
            file_list = [f"📄 `{item}`" for item in items if not os.path.isdir(os.path.join(cwd, item))]
            resp = f"📍 *Current Path:* `{cwd}`\n\n" + "\n".join(folder_list[:20] + file_list[:20])
            return {"success": True, "message": resp}
        except Exception as e: return {"success": False, "message": f"Error: {e}"}

    if t.startswith("cd "):
        logger.info(f"Intent: NAVIGATION (cd)")
        target = t[3:].strip()
        new_path = os.path.dirname(cwd) if target == ".." else os.path.join(cwd, target)
        if not os.path.exists(new_path):
            for item in os.listdir(cwd):
                if target.lower() in item.lower() and os.path.isdir(os.path.join(cwd, item)):
                    new_path = os.path.join(cwd, item); break
        if os.path.isdir(new_path):
            context.user_data["cwd"] = os.path.abspath(new_path)
            return {"success": True, "message": f"📂 Moved to: `{context.user_data['cwd']}`"}
        return {"success": False, "message": f"Folder '{target}' not found."}

    # ── PRIORITY 1: Music Control ──
    if first_word in ["play", "pause", "resume", "stop", "volume", "next"]:
        logger.info(f"Intent: MUSIC ({first_word})")
        if first_word == "play":
            query = t[4:].strip()
            if not query: return {"success": False, "message": "Play what? (e.g. `play happy nation`)"}
            success, msg = music_player.play_song(query)
            return {"success": success, "message": msg}
        
        music_cmds = {
            "pause": music_player.pause, 
            "resume": music_player.resume, 
            "next": music_player.next_song, 
            "stop": music_player.stop,
            "volume up": music_player.volume_up,
            "volume down": music_player.volume_down
        }
        cmd_key = t if t in music_cmds else first_word
        if cmd_key in music_cmds:
            success, msg = music_cmds[cmd_key]()
            return {"success": success, "message": msg}

    # ── PRIORITY 1b: Download Manager ──
    if first_word == "download":
        rest = t[8:].strip()
        logger.info(f"Intent: DOWNLOAD ({rest[:30]})")

        # YouTube download — extract the actual URL from the text
        if rest.startswith("youtube ") or 'youtube.com' in rest or 'youtu.be' in rest or 'youtub ' in rest:
            # Extract URL from the ORIGINAL text to preserve case-sensitive Video IDs!
            orig_url_match = re.search(r'(https?://[^\s]+)', text)
            if orig_url_match:
                url = orig_url_match.group(1)
            else:
                # If no URL found, treat rest as search query minus "youtube "
                query_str = rest.replace("youtube ", "").replace("youtub ", "").strip()
                # Use ytsearch1: to tell yt-dlp to search and download the first result
                url = f"ytsearch1:{query_str}"
            
            # Store pending download for quality selection
            context.user_data["pending_download"] = {"type": "youtube", "url": url}
            buttons = [
                [InlineKeyboardButton("360p", callback_data="dl:360"),
                 InlineKeyboardButton("720p", callback_data="dl:720"),
                 InlineKeyboardButton("1080p", callback_data="dl:1080")],
                [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="dl:audio")],
            ]
            await update.message.reply_text(
                f"🎬 *YouTube Download*\n\n🔗 `{url}`\n\nSelect quality:",
                reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown"
            )
            return {"success": True, "message": "Select download quality above."}

        # Image download
        if rest.startswith("images "):
            topic = rest[7:].strip()
            if not topic:
                return {"success": False, "message": "Download images of what? (e.g. `download images cars`)"}
            success, msg = download_manager.download_images(topic)
            return {"success": success, "message": msg}

        # General URL download
        if rest.startswith("http") or "://" in text:
            orig_url_match = re.search(r'(https?://[^\s]+)', text)
            url = orig_url_match.group(1) if orig_url_match else rest
            success, msg = download_manager.download_url(url)
            return {"success": success, "message": msg}

        # Cancel
        if rest == "cancel":
            success, msg = download_manager.cancel()
            return {"success": success, "message": msg}

        return {"success": False, "message": "\n".join([
            "📥 **Download Commands:**",
            "• `download youtube <url>` — YouTube video/audio",
            "• `download images <topic>` — Bulk image download",
            "• `download <url>` — Direct file download",
            "• `download cancel` — Cancel active download",
        ])}

    # ── PRIORITY 1c: TTS / Speak ──
    if first_word == "speak":
        speak_text = t[5:].strip()
        if not speak_text:
            return {"success": False, "message": "Speak what? (e.g. `speak hello world`)"}
        logger.info("Intent: TTS")
        try:
            tts_dir = os.path.join(STORAGE_DIR, "tts")
            os.makedirs(tts_dir, exist_ok=True)
            tts_path = os.path.join(tts_dir, f"tts_{int(time.time())}.mp3")
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(speak_text, tts_path)
            engine.runAndWait()
            return {"success": True, "message": f"__SEND_FILE__:{tts_path}"}
        except ImportError:
            return {"success": False, "message": "⚠️ pyttsx3 not installed. Run: `pip install pyttsx3`"}
        except Exception as e:
            return {"success": False, "message": f"❌ TTS failed: {e}"}

    # ── PRIORITY 2: App Control (openapp / closeapp / close) ──
    if first_word in ["openapp", "startapp", "launchapp", "close"]:
        logger.info(f"Intent: APP_CONTROL ({first_word})")
        target = t[len(first_word):].strip()
        
        if first_word == "close":
            if target == "all apps":
                context.user_data["pending_confirm"] = {"action": "close all apps", "time": time.time()}
                return {"success": True, "message": "⚠️ Are you sure you want to **close all apps**?\nReply `yes` within 10 seconds to confirm, or `no` to cancel."}
            # Fuzzy match process name
            target_proc = APP_MAPPING.get(target, target)
            if not target_proc.endswith(".exe") and "." not in target_proc: target_proc += ".exe"
            closed = False
            for p in psutil.process_iter(['name']):
                if p.info['name'] and target_proc.lower() in p.info['name'].lower():
                    p.terminate(); closed = True
            return {"success": closed, "message": f"{target.title()} closed" if closed else f"Could not find {target}"}

        # Handle openapp (Known Apps/Settings)
        if target in ["settings"]: subprocess.Popen("start ms-settings:", shell=True); return {"success": True, "message": "Opened Settings"}
        mapped_app = APP_MAPPING.get(target, target)
        if mapped_app.startswith("start "):
            subprocess.Popen(mapped_app, shell=True); return {"success": True, "message": f"Opened {target}"}
        
        # Launch app (Only if it's a known app or has .exe)
        if target in APP_MAPPING or target.endswith(".exe"):
            res = launch_app(mapped_app)
            if res.get("success"): return res
        
        # Fallback: try to find and launch
        res = launch_app(mapped_app)
        return res

    # ── PRIORITY 3: Messaging (WhatsApp) ──
    if first_word == "send" and " to " in t:
        logger.info(f"Intent: MESSAGING")
        send_match = re.search(r'^send\s+(.+?)\s+to\s+(.+?)$', t)
        if send_match:
            payload, name = send_match.group(1).strip(), send_match.group(2).strip()
            contact = get_contact(name)
            if contact: return send_message(contact['phone'], payload, is_file=os.path.isfile(payload))

    # ── PRIORITY 4: File Operations (open / find) ──
    file_extensions = ('.pdf', '.txt', '.docx', '.xlsx', '.png', '.jpg', '.mp3', '.mp4')
    if any(ext in t for ext in file_extensions) or first_word in ["find", "open"]:
        logger.info(f"Intent: FILE_OPS")
        query = t[len(first_word):].strip() if first_word in ["find", "open"] else t
        matches = find_file(query)
        if matches:
            context.user_data["last_files"] = matches
            if len(matches) > 1:
                file_map = context.user_data.get("file_map", {})
                buttons = [[InlineKeyboardButton(f"{i+1}. {os.path.basename(p)}", callback_data=f"f:open:{str(uuid.uuid4())[:8]}")] for i, p in enumerate(matches[:10])]
                for i, p in enumerate(matches[:10]): file_map[buttons[i][0].callback_data.split(":")[-1]] = p
                context.user_data["file_map"] = file_map
                await update.message.reply_text(f"🔍 Matches for '{query}':", reply_markup=InlineKeyboardMarkup(buttons))
                return {"success": True, "message": "Select a file."}
            os.startfile(matches[0]); return {"success": True, "message": f"Opened {os.path.basename(matches[0])}"}
        if first_word == "open":
            return {"success": False, "message": f"File '{query}' not found."}

    # ── PRIORITY 5: Website Detection (Domains) ──
    if first_word in ["openapp", "startapp", "launchapp"]:
        target = t[len(first_word):].strip()
        if re.match(r'^[a-z0-9\-]+\.(com|net|org|io|gov|edu|in|me|ai)$', target):
            logger.info(f"Intent: WEBSITE")
            import webbrowser; webbrowser.open(f"https://{target}"); return {"success": True, "message": f"Opened {target}"}

    # ── PRIORITY 5b: System (with confirmation for dangerous commands) ──
    if t in ["shutdown", "restart", "lock", "sleep"]:
        logger.info(f"Intent: SYSTEM")
        if t in DANGEROUS_COMMANDS:
            context.user_data["pending_confirm"] = {"action": t, "time": time.time()}
            return {"success": True, "message": f"\u26a0\ufe0f Are you sure you want to **{t}**?\nReply `yes` within 10 seconds to confirm, or `no` to cancel."}
        return await execute_system_cmd(t)

    # ── PRIORITY 5c: Screenshot commands ──
    if t in ["take screenshot", "screenshot"]:
        return {"success": True, "message": "__SCREENSHOT__"}
    if t in ["send screenshot"]:
        return {"success": True, "message": "__SEND_SCREENSHOT__"}

    # ── PRIORITY 5d: System utilities ──
    if t in ["show logs"]:
        log_path = os.path.join(LOG_DIR, "activity_log.txt")
        if not os.path.exists(log_path): return {"success": True, "message": "📂 No logs found."}
        with open(log_path, 'r', encoding='utf-8') as f: lines = f.readlines()
        recent = "".join(lines[-20:])
        return {"success": True, "message": f"📜 *Recent Logs:*\n\n`{recent}`"}
    if t in ["clear logs"]:
        log_path = os.path.join(LOG_DIR, "activity_log.txt")
        with open(log_path, 'w') as f: f.write("")
        return {"success": True, "message": "✅ Logs cleared."}
    if t in ["storage status"]:
        all_files = []
        for root, _, fnames in os.walk(STORAGE_DIR):
            for fn in fnames:
                fp = os.path.join(root, fn)
                if os.path.isfile(fp): all_files.append(fp)
        total_size = sum(os.path.getsize(f) for f in all_files) / (1024*1024)
        return {"success": True, "message": f"\ud83d\udce6 *Storage:* {total_size:.2f} MB / 2048 MB (2 GB)\n\ud83d\udcc2 `{STORAGE_DIR}`"}

    # ── PRIORITY 6: Delete file ──
    if first_word == "delete":
        query = t[6:].strip()
        if not query: return {"success": False, "message": "Delete what? (e.g. `delete report`)"}
        matches = find_file(query)
        if not matches: return {"success": False, "message": f"File '{query}' not found."}
        context.user_data["last_files"] = matches
        context.user_data["pending_delete"] = matches[0] if len(matches) == 1 else None
        if len(matches) == 1:
            return {"success": True, "message": f"⚠️ Confirm delete `{os.path.basename(matches[0])}`?\nReply `yes` to confirm."}
        file_map = context.user_data.get("file_map", {})
        buttons = [[InlineKeyboardButton(f"{i+1}. {os.path.basename(p)}", callback_data=f"f:delete:{str(uuid.uuid4())[:8]}")] for i, p in enumerate(matches[:10])]
        for i, p in enumerate(matches[:10]): file_map[buttons[i][0].callback_data.split(":")[-1]] = p
        context.user_data["file_map"] = file_map
        await update.message.reply_text(f"🗑️ Which file to delete?", reply_markup=InlineKeyboardMarkup(buttons))
        return {"success": True, "message": "Select a file to delete."}

    # ── PRIORITY 6b: Send file via Telegram ──
    if first_word == "send" and " to " not in t:
        query = t[4:].strip()
        if not query: return {"success": False, "message": "Send what? (e.g. `send report`)"}
        matches = find_file(query)
        if matches:
            context.user_data["last_files"] = matches
            if len(matches) == 1:
                return {"success": True, "message": f"__SEND_FILE__:{matches[0]}"}
            file_map = context.user_data.get("file_map", {})
            buttons = [[InlineKeyboardButton(f"{i+1}. {os.path.basename(p)}", callback_data=f"f:send:{str(uuid.uuid4())[:8]}")] for i, p in enumerate(matches[:10])]
            for i, p in enumerate(matches[:10]): file_map[buttons[i][0].callback_data.split(":")[-1]] = p
            context.user_data["file_map"] = file_map
            await update.message.reply_text(f"📤 Which file to send?", reply_markup=InlineKeyboardMarkup(buttons))
            return {"success": True, "message": "Select a file to send."}
        return {"success": False, "message": f"File '{query}' not found."}

    # ── PRIORITY 7: Web Search (ONLY "search <query>") ──
    if first_word == "search":
        q = t[6:].strip()
        if not q: return {"success": False, "message": "Search what? (e.g. `search AI tools`)"}
        logger.info(f"Intent: WEB_SEARCH")
        import urllib.parse; encoded = urllib.parse.quote(q)
        import webbrowser; await asyncio.to_thread(webbrowser.open, f"https://www.google.com/search?q={encoded}")
        resp = f"🌐 Searching '{q}' on Google"
        log_activity(text, resp)
        return {"success": True, "message": resp}

    # ── PRIORITY 8: Result Memory (open 1, send 2) ──
    if t.split()[0] in ["open", "send"] and len(t.split()) == 2 and t.split()[1].isdigit():
        idx = int(t.split()[1]) - 1
        last_files = context.user_data.get("last_files", [])
        if 0 <= idx < len(last_files):
            path = last_files[idx]
            if first_word == "open":
                os.startfile(path); return {"success": True, "message": f"Opened {os.path.basename(path)}"}
            else:
                return {"success": True, "message": f"__SEND_FILE__:{path}"}
        return {"success": False, "message": f"No file at index {idx+1}. Use `find` first."}

    # ── PRIORITY 9: Dashboard ──
    if t == "dashboard":
        stats = load_stats()
        cmd_count = stats.get("commands", 0)
        apps_opened = stats.get("apps_opened", 0)
        counts = stats.get("command_counts", {})
        top_cmd = max(counts, key=counts.get) if counts else "—"
        top_count = counts.get(top_cmd, 0) if counts else 0
        # Storage
        total_sz = 0
        for root, _, fnames in os.walk(STORAGE_DIR):
            for fn in fnames:
                fp = os.path.join(root, fn)
                if os.path.isfile(fp):
                    total_sz += os.path.getsize(fp)
        sz_mb = total_sz / (1024 * 1024)
        # Battery
        batt = psutil.sensors_battery()
        batt_str = f"{batt.percent}% {'🔌' if batt.power_plugged else '🔋'}" if batt else "N/A"
        msg = (
            f"📊 *Lotus Dashboard*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Date: {stats.get('date', 'today')}\n"
            f"⚡ Commands: {cmd_count}\n"
            f"🏆 Top: `{top_cmd}` ({top_count}x)\n"
            f"🖥️ Apps Opened: {apps_opened}\n"
            f"📦 Storage: {sz_mb:.1f} MB / 2048 MB\n"
            f"🔋 Battery: {batt_str}"
        )
        return {"success": True, "message": msg}

    # ── PRIORITY 10: Command Memory ──
    # set <name> = <commands>
    set_match = re.match(r'^set\s+(\w+)\s*=\s*(.+)$', t)
    if set_match:
        name = set_match.group(1).lower()
        actions = set_match.group(2).strip()
        mem = load_memory()
        mem[name] = actions
        save_memory(mem)
        return {"success": True, "message": f"✅ Saved: `{name}` → `{actions}`\n\nType `{name}` to run it."}

    if t == "memory list" or t == "my commands":
        mem = load_memory()
        if not mem:
            return {"success": True, "message": "📝 No saved commands.\n\nUse: `set study = open chrome + open vscode`"}
        lines = [f"📝 *Saved Commands:*\n"]
        for k, v in mem.items():
            lines.append(f"• `{k}` → `{v}`")
        return {"success": True, "message": "\n".join(lines)}

    if t.startswith("forget ") or t.startswith("unset "):
        name = t.split(maxsplit=1)[1].strip().lower()
        mem = load_memory()
        if name in mem:
            del mem[name]
            save_memory(mem)
            return {"success": True, "message": f"🗑️ Removed: `{name}`"}
        return {"success": False, "message": f"No command `{name}` found."}

    # Memory recall — check if input matches a saved command name
    mem = load_memory()
    if t in mem:
        logger.info(f"Intent: MEMORY_RECALL ({t})")
        # Execute saved commands (split by + or and)
        actions = re.split(r'\s*(?:\+|and|then)\s*', mem[t])
        results = []
        for action in actions[:5]:
            action = action.strip()
            if action:
                res = await parse_and_execute(action, update, context)
                results.append(f"• {res.get('message', '?')}")
        return {"success": True, "message": f"🔄 Running `{t}`:\n" + "\n".join(results)}

    # ── PRIORITY 11: Clipboard System ──
    if t == "clipboard":
        if not clipboard_history:
            return {"success": True, "message": "📋 Clipboard is empty."}
        lines = ["📋 *Last Copied Items:*\n"]
        for i, item in enumerate(clipboard_history):
            # truncate long items
            disp = item if len(item) < 100 else item[:97] + "..."
            lines.append(f"{i+1}. `{disp}`")
        return {"success": True, "message": "\n".join(lines)}

    if t == "clear clipboard":
        clipboard_history.clear()
        return {"success": True, "message": "✅ Clipboard history cleared."}

    if t.startswith("copy "):
        payload = t[5:].strip()
        if not payload:
            return {"success": False, "message": "Copy what? (e.g. `copy hello`)"}
        import pyperclip
        pyperclip.copy(payload)
        return {"success": True, "message": f"📋 Copied to PC clipboard:\n`{payload}`"}

    # ── PRIORITY 12: Conversational Chat ──
    chat_resp = _chat_reply(text)
    if chat_resp:
        return {"success": True, "message": chat_resp}

    # ── FINAL: Error — DO NOT open browser ──
    logger.info(f"Intent: UNRECOGNIZED — '{t}'")
    return {"success": False, "message": "❓ I didn't understand that.\nUse /help to see available commands."}

# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------



@require_auth
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    users = load_users()
    name = update.effective_user.first_name

    if user_id not in users:
        users[user_id] = {"name": name, "last_seen": time.time()}
        save_user(user_id, users[user_id])
        text = (
            f"Hello {name} 👋\n"
            f"Welcome to *Lotus* — your Windows Control Agent.\n\n"
            f"🎵 `play kesariya`\n"
            f"📥 `download youtube <url>`\n"
            f"🖥️ `openapp chrome`\n"
            f"📁 `find report.pdf`\n"
            f"🔊 `speak hello world`\n"
            f"📸 `take screenshot`\n"
            f"🔗 `open chrome and play music`\n\n"
            f"Type /help for the full command guide."
        )
    else:
        name = users[user_id].get("name", name)
        h = int(time.strftime("%H"))
        period = "Morning" if h < 12 else "Afternoon" if h < 18 else "Evening"
        text = (
            f"Good {period}, {name}! 👋\n"
            f"Welcome back to *Lotus*.\n\n"
            f"• `play arijit singh`\n"
            f"• `openapp spotify`\n"
            f"• `download images cars`\n"
            f"• `dashboard` (daily stats)\n"
            f"• `take screenshot`\n\n"
            f"Type /help for all commands."
        )

    keyboard = [
        [InlineKeyboardButton("🎵 Music", callback_data="media"),
         InlineKeyboardButton("📥 Downloads", callback_data="downloads"),
         InlineKeyboardButton("🖥️ Apps", callback_data="tools")],
        [InlineKeyboardButton("📁 Files", callback_data="files"),
         InlineKeyboardButton("📸 Screenshot", callback_data="tools"),
         InlineKeyboardButton("⚙️ System", callback_data="system")],
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("📋 Full Help", callback_data="help")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

@require_auth
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 *Lotus — Command Guide*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎵 *MUSIC*\n"
        "• `play <song>` — _e.g._ `play kesariya`\n"
        "• `pause` · `resume` · `stop` · `next`\n"
        "• `volume up` · `volume down`\n\n"
        "📥 *DOWNLOADS*\n"
        "• `download youtube <url>`\n"
        "  _Asks: 360p / 720p / 1080p / MP3_\n"
        "• `download images <topic>`\n"
        "  _e.g._ `download images cars`\n"
        "• `download <url>` — any file\n"
        "• `download cancel`\n\n"
        "🔊 *VOICE*\n"
        "• `speak <text>` — _e.g._ `speak hello`\n\n"
        "🖥️ *APPS*\n"
        "• `openapp <name>` — _e.g._ `openapp chrome`\n"
        "• `close <name>` · `close all apps`\n\n"
        "📁 *FILES*\n"
        "• `ls` · `cd <folder>` · `cd ..`\n"
        "• `find <file>` — _e.g._ `find report`\n"
        "• `open <file>` · `send <file>`\n"
        "• `delete <file>` (⚠️ confirmation)\n\n"
        "⚡ *SYSTEM & TOOLS*\n"
        "• `take screenshot` · `send screenshot`\n"
        "• `lock` · `sleep`\n"
        "• `shutdown` · `restart` (⚠️ confirmation)\n"
        "• `search <query>`\n"
        "• `dashboard` — Daily stats & battery\n"
        "• `storage status` · `show logs`\n"
        "• `clipboard` — Show last 5 copied items\n"
        "• `clear clipboard` · `copy <text>`\n\n"
        "🧠 *COMMAND MEMORY*\n"
        "• `set <name> = <actions>`\n"
        "  _e.g._ `set study = open chrome and play lofi`\n"
        "• `memory list` — Show saved commands\n"
        "• `forget <name>` — Delete saved command\n\n"
        "🔗 *MULTI-COMMAND & QUEUE*\n"
        "• `open chrome and play music`\n"
        "• `take screenshot then send screenshot`\n"
        "  _Multiple commands are auto-queued._\n\n"
        "⌨️ *SLASH COMMANDS*\n"
        "• /start · /help · /owner · /admin\n"
        "• /logs · /storage · /status\n\n"
        "🔋 _Auto voice-alerts sent when battery <20%_\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "_All commands are case-insensitive._\n"
        "_⚠️ Dangerous commands require yes/no (10s)._"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

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
    global COMMAND_COUNTER
    text = update.message.text
    if not text: return
    user_id = str(update.effective_user.id)
    msg_id = update.message.message_id
    if msg_id in RECENT_COMMANDS: return
    RECENT_COMMANDS[msg_id] = True
    
    # User Store & Greeting logic
    users = load_users()
    now = time.time()
    greeting = ""
    
    if user_id not in users:
        users[user_id] = {"name": update.effective_user.first_name, "last_seen": now}
        save_user(user_id, users[user_id])
        greeting = f"👋 Hello {users[user_id]['name']}, welcome! How can I help you today?\n\n"
    else:
        last_seen = users[user_id].get("last_seen", 0)
        time_diff = now - last_seen
        if time_diff > 12 * 3600:
            greeting = f"🏠 Welcome back {users[user_id]['name']}, how can I help you today?\n\n"
        elif time.strftime("%d", time.localtime(last_seen)) != time.strftime("%d", time.localtime(now)):
            h = int(time.strftime("%H"))
            period = "Morning" if h < 12 else "Afternoon" if h < 18 else "Evening"
            greeting = f"🌅 Good {period} {users[user_id]['name']}!\n\n"
        users[user_id]["last_seen"] = now
        save_user(user_id, users[user_id])

    global COMMAND_COUNTER
    COMMAND_COUNTER += 1
    track_command(text)
    
    if COMMAND_COUNTER >= 3:
        clear_temp_cache(context)
        cleanup_storage()
        import gc
        gc.collect()
        COMMAND_COUNTER = 0

    # Confirmation handler (yes/no for dangerous commands + delete)
    answer = text.strip().lower()
    if answer in ["yes", "no"]:
        # Dangerous command confirmation (shutdown/restart/close all)
        pending_confirm = context.user_data.get("pending_confirm")
        if pending_confirm:
            context.user_data.pop("pending_confirm")
            if answer == "no":
                await update.message.reply_text("❌ Cancelled.")
                return
            elapsed = time.time() - pending_confirm.get("time", 0)
            if elapsed > CONFIRM_TIMEOUT:
                await update.message.reply_text("⏰ Confirmation timed out. Please send the command again.")
                return
            action = pending_confirm["action"]
            if action == "close all apps":
                await update.message.reply_text(close_all_apps())
            else:
                res = await execute_system_cmd(action)
                await update.message.reply_text(f"✅ {res.get('message', 'Done')}")
            return

        # Delete confirmation
        if answer == "yes" and context.user_data.get("pending_delete"):
            path = context.user_data.pop("pending_delete")
            try:
                os.remove(path)
                await update.message.reply_text(f"✅ Deleted: `{os.path.basename(path)}`", parse_mode="Markdown")
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to delete: {e}")
            return

    processing_msg = await update.message.reply_text("⏳ Processing...")
    try:
        async with asyncio.timeout(120.0):
            # Multi-command support: split on " and " or " then "
            sub_commands = re.split(r'\s+and\s+|\s+then\s+', text, flags=re.IGNORECASE)
            sub_commands = [s.strip() for s in sub_commands if s.strip()]

            if len(sub_commands) > 1:
                # Add to task queue sequentially
                for sub_cmd in sub_commands[:5]:
                    await TASK_QUEUE.put({"text": sub_cmd, "update": update})
                await processing_msg.edit_text(f"{greeting}⏳ Added {len(sub_commands[:5])} commands to queue.")
                asyncio.create_task(process_task_queue(context))
                log_activity(text, f"Multi-command queued: {len(sub_commands)} commands")
                return

            res = await parse_and_execute(text, update, context)
            msg = res.get("message", "Done")
            icon = "✅" if res.get("success") else "❌"
            if res.get("success"):
                if "Playing" in msg or "Opened" in msg or "Download" in msg:
                    icon = "🎵" if "Play" in msg else ("📥" if "Download" in msg else "📁")
            
            # For direct commands, update the processing message
            if res.get("success") and not msg.startswith("__"):
                await processing_msg.edit_text(f"{greeting}{icon} {msg}")
            elif not res.get("success"):
                await processing_msg.edit_text(f"{icon} {msg}")

            # Handle special signals
            if msg == "__SCREENSHOT__":
                img, path = _take_screenshot()
                with open(path, 'rb') as f:
                    await update.message.reply_photo(photo=f, caption="🖥️ Screenshot captured.")
                await processing_msg.delete()
                log_activity(text, "Captured screenshot")
                return

            if msg == "__SEND_SCREENSHOT__":
                ss_files = sorted(
                    [os.path.join(STORAGE_DIR, f) for f in os.listdir(STORAGE_DIR) if f.startswith("ss_")],
                    key=os.path.getmtime, reverse=True
                )
                if not ss_files:
                    img, path = _take_screenshot()
                else:
                    path = ss_files[0]
                with open(path, 'rb') as f:
                    await update.message.reply_document(document=f, caption="📸 Screenshot")
                await processing_msg.delete()
                log_activity(text, "Sent screenshot")
                return

            if msg.startswith("__SEND_FILE__:"):
                fpath = msg.split(":", 1)[1]
                fname = os.path.basename(fpath)
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                if size_mb > 50:
                    await processing_msg.edit_text(f"❌ File too large ({size_mb:.1f}MB). Telegram limit is 50MB.")
                    return
                with open(fpath, 'rb') as f:
                    await update.message.reply_document(
                        document=f, caption=f"📄 {fname}",
                        read_timeout=300, write_timeout=300, connect_timeout=300, pool_timeout=300
                    )
                await processing_msg.edit_text(f"✅ Sent: {fname}")
                log_activity(text, f"Sent file: {fname}")
                return

            icon = "✅" if res.get("success") else "❌"
            if res.get("success"):
                if "Playing" in msg or "play" in msg.lower(): icon = "🎵"
                elif "Opened" in msg or "open" in msg.lower(): icon = "✅"
                elif "Download" in msg: icon = "📥"
                elif "Sent" in msg: icon = "📁"
            resp_text = f"{icon} {msg}"
            final_resp = f"{greeting}{resp_text}"
            try:
                await processing_msg.edit_text(final_resp, parse_mode="Markdown" if (greeting or res.get("success")) else None)
            except Exception as e:
                if "Message is not modified" not in str(e):
                    raise e
            log_activity(text, resp_text)
            
            COMMAND_COUNTER += 1
            if COMMAND_COUNTER % 3 == 0:
                cleanup_storage()
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Error: {e}", exc_info=True)
            await processing_msg.edit_text(f"❌ Error: {str(e)}")

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Try multiple levels up to find the root config.json
    possible_paths = [
        os.path.join(os.getcwd(), "config.json"),
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "config.json")), # Root
        os.path.abspath(os.path.join(script_dir, "..", "..", "config.json")),       # Windows-MCP root
    ]
    for config_path in possible_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                return cfg.get("bot_token")
            except Exception:
                continue
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(os.getcwd(), "config.json"),
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "config.json")),
        os.path.abspath(os.path.join(script_dir, "..", "..", "config.json")),
    ]
    for config_path in possible_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                allowed = cfg.get("allowed_user_ids", "")
                if allowed and not os.getenv("TELEGRAM_ALLOWED_USER_IDS"):
                    os.environ["TELEGRAM_ALLOWED_USER_IDS"] = allowed
                break # Found it
            except Exception:
                continue

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(read_timeout=300, write_timeout=300, connect_timeout=300)
    
    app = ApplicationBuilder().token(token).request(request).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
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
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n⏹ Bot stopped by user.")
    except Exception as e:
        import traceback
        print("\n❌ ERROR:", e)
        traceback.print_exc()
        input("\nPress Enter to exit...")
