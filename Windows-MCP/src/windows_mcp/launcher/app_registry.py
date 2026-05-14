import json
import os
import difflib

CACHE_FILE = os.path.join(os.path.dirname(__file__), "launcher_cache.json")

# Dictionary of app groups
APP_DB = {
    "uwp": {
        "microsoft store": "ms-windows-store:",
        "settings": "ms-settings:",
        "bluetooth settings": "ms-settings:bluetooth",
        "wifi settings": "ms-settings:network-wifi",
        "display settings": "ms-settings:display",
        "camera": "microsoft.windows.camera:",
        "photos": "ms-photos:",
        "clock": "ms-clock:",
        "mail": "outlookmail:",
        "maps": "bingmaps:",
        "feedback hub": "feedback-hub:"
    },
    "classic": {
        "calculator": "calc.exe",
        "notepad": "notepad.exe",
        "paint": "mspaint.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "registry editor": "regedit.exe",
        "snipping tool": "snippingtool.exe",
        "explorer": "explorer.exe",
        "folder": "explorer.exe"
    },
    "browsers": {
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "firefox": "firefox.exe",
        "brave": "brave.exe",
        "opera": "opera.exe"
    },
    "office": {
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe"
    },
    "communication": {
        "whatsapp": "whatsapp:", # often registered as URI on Win11
        "telegram": "Telegram.exe",
        "discord": "Update.exe --processStart Discord.exe",
        "zoom": "Zoom.exe",
        "skype": "Skype.exe"
    },
    "developer": {
        "vs code": "Code.exe",
        "cursor": "Cursor.exe",
        "github desktop": "GitHubDesktop.exe",
        "docker": "Docker Desktop.exe",
        "postman": "Postman.exe"
    },
    "media": {
        "spotify": "spotify.exe",
        "vlc": "vlc.exe",
        "obs": "obs64.exe",
        "steam": "steam.exe"
    }
}

# Alias mapping
ALIASES = {
    "store": "microsoft store",
    "ms store": "microsoft store",
    "chrome browser": "chrome",
    "word": "word",
    "microsoft word": "word",
    "excel sheet": "excel",
    "paint app": "paint",
    "whatsapp desktop": "whatsapp",
    "cmd": "command prompt",
    "vscode": "vs code"
}

# Flatten all known apps for searching
FLAT_DB = {}
for category, apps in APP_DB.items():
    for name, cmd in apps.items():
        FLAT_DB[name] = {"category": category, "cmd": cmd}

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=4)
    except Exception:
        pass

def normalize_name(name: str) -> str:
    name = name.lower().strip()
    return ALIASES.get(name, name)

def get_app_info(app_name: str):
    """Find the best match for the app name using exact, alias, and fuzzy matching."""
    norm = normalize_name(app_name)
    
    # 1. Exact or Alias Match
    if norm in FLAT_DB:
        return FLAT_DB[norm]["cmd"], FLAT_DB[norm]["category"]
        
    # 2. Substring matching
    for key, data in FLAT_DB.items():
        if key in norm or norm in key:
            return data["cmd"], data["category"]
            
    # 3. Fuzzy matching
    matches = difflib.get_close_matches(norm, FLAT_DB.keys(), n=1, cutoff=0.6)
    if matches:
        matched_key = matches[0]
        return FLAT_DB[matched_key]["cmd"], FLAT_DB[matched_key]["category"]
        
    return None, None
