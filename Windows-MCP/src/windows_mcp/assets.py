import os
import sys
import logging

logger = logging.getLogger(__name__)

def get_resource_path(relative_path: str) -> str:
    """
    Robustly resolves paths for both development and PyInstaller production.
    
    Priority Search Order:
    1. PyInstaller Temp Extraction (_MEIPASS)
    2. Executable Directory (Side-loaded assets in Program Files)
    3. Project Root (Development mode)
    """
    # Fix path separators to be OS-agnostic for input
    relative_path = relative_path.replace("/", os.sep).replace("\\", os.sep)

    # 1. PyInstaller Temp Extraction Folder
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        path = os.path.join(meipass, relative_path)
        if os.path.exists(path):
            return path

    # 2. Executable Directory (Installed or Portable)
    exe_dir = os.path.dirname(sys.executable)
    path = os.path.join(exe_dir, relative_path)
    if os.path.exists(path):
        return path

    # 3. Source Code Fallback (assumes 3 levels up from src/windows_mcp/assets.py)
    # This reaches back to the repository root for assets/ and bin/
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base_dir, relative_path)
        if os.path.exists(path):
            return path
    except NameError: # __file__ not defined in some edge cases
        pass

    # 4. Final attempt: Current working directory
    path = os.path.abspath(relative_path)
    return path

def verify_asset_integrity() -> list[str]:
    """
    Validates that all critical UI and system assets are reachable.
    Returns a list of missing asset names.
    """
    critical_assets = [
        "assets/lotus_icon.ico",
        "assets/lotus_logo.png",
        "bin/mpv.exe",
        "bin/yt-dlp.exe"
    ]
    missing = []
    for asset in critical_assets:
        path = get_resource_path(asset)
        if not os.path.exists(path):
            missing.append(asset)
            logger.error(f"CRITICAL ASSET MISSING: {asset} (Resolved to: {path})")
        else:
            logger.debug(f"Asset Verified: {asset} -> {path}")
    
    return missing
