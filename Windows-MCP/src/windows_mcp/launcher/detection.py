import os
import json
import glob
import logging
import difflib

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.getcwd(), "data", "apps_cache.json")

SEARCH_PATHS = [
    os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    os.environ.get("ProgramFiles", r"C:\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    os.path.expandvars(r"%LOCALAPPDATA%")
]

def build_app_index():
    apps = {}
    
    # Ensure data dir exists
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    
    logger.info("Scanning for installed applications...")
    
    # Scan Start Menu Shortcuts first (they have nice names)
    for path in SEARCH_PATHS[:2]:
        if not os.path.exists(path): continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(".lnk"):
                    name = file[:-4].lower().strip()
                    full_path = os.path.join(root, file)
                    apps[name] = full_path

    # Scan Program Files for executables (limit depth to avoid infinite scan)
    for path in SEARCH_PATHS[2:]:
        if not os.path.exists(path): continue
        try:
            for item in os.listdir(path):
                full_item = os.path.join(path, item)
                if os.path.isdir(full_item):
                    try:
                        for sub_item in os.listdir(full_item):
                            if sub_item.lower().endswith(".exe"):
                                name = sub_item[:-4].lower().strip()
                                # Only add if we don't have a nice shortcut name for it
                                if name not in apps:
                                    apps[name] = os.path.join(full_item, sub_item)
                    except (PermissionError, FileNotFoundError):
                        pass
        except (PermissionError, FileNotFoundError):
            pass

    with open(CACHE_FILE, "w") as f:
        json.dump(apps, f, indent=4)
        
    return apps

def load_app_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return build_app_index()

def find_executable(app_name: str, hint_cmd: str = None) -> str:
    """Finds the best matching app using fuzzy search."""
    cache = load_app_cache()
    norm = app_name.lower().strip()
    
    if norm in cache:
        return cache[norm]
        
    # Substring match
    for name, path in cache.items():
        if norm in name or name in norm:
            return path
            
    # Fuzzy match
    matches = difflib.get_close_matches(norm, cache.keys(), n=1, cutoff=0.5)
    if matches:
        return cache[matches[0]]
        
    # Return original hint if no cache match
    return hint_cmd if hint_cmd else None
