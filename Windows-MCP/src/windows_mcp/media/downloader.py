"""
Lotus Download Manager
======================
Handles all download operations:
  - General URL downloads (files, PDFs, etc.)
  - YouTube video/audio downloads via yt-dlp
  - Image search + bulk download

All downloads show progress in a visible terminal window.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import logging
import time
import urllib.request
import urllib.parse
import json
from windows_mcp.paths import get_lotus_bin_dir

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DL_TUI_SCRIPT = os.path.join(_THIS_DIR, "download_tui.py")


def _get_storage_dir(subdir: str = "downloads") -> str:
    """Get storage directory, creating if needed."""
    PROGRAM_DATA = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    base = os.path.join(PROGRAM_DATA, "Lotus", "storage", subdir)
    os.makedirs(base, exist_ok=True)
    return base


def _find_ytdlp() -> str | None:
    """Find yt-dlp binary."""
    path = shutil.which("yt-dlp")
    if path:
        return path
    bin_dir = get_lotus_bin_dir()
    local = bin_dir / "yt-dlp.exe"
    if local.exists():
        return str(local)
    return None


def _find_python() -> str:
    """Find python.exe (not pythonw.exe or Lotus.exe GUI)."""
    # Prefer system python because PyInstaller's sys.executable (Lotus.exe) 
    # is a GUI app and cannot spawn a visible console!
    system_python = shutil.which("python") or shutil.which("python3")
    if getattr(sys, 'frozen', False):
        return system_python or "python"
        
    python_exe = sys.executable
    if "pythonw" in python_exe.lower():
        python_exe = python_exe.lower().replace("pythonw.exe", "python.exe")
        if not os.path.exists(python_exe):
            python_exe = system_python or "python"
    return python_exe


class DownloadManager:
    """Manages all download operations for Lotus."""

    def __init__(self):
        self.process = None
        self._control_file = os.path.join(_THIS_DIR, ".dl_control")
        self._status_file = os.path.join(_THIS_DIR, ".dl_status")

    # ------------------------------------------------------------------
    # YouTube Downloads
    # ------------------------------------------------------------------
    def download_youtube(self, url: str, quality: str = "720", audio_only: bool = False):
        """
        Download a YouTube video/audio.
        quality: '360', '720', '1080'
        audio_only: if True, extract audio as mp3
        """
        ytdlp = _find_ytdlp()
        if not ytdlp:
            return False, "❌ yt-dlp not found. Place `yt-dlp.exe` in the `bin/` folder or add to PATH."

        if audio_only:
            save_dir = _get_storage_dir("audio")
        else:
            save_dir = _get_storage_dir("videos")
        python_exe = _find_python()

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 1 # SW_NORMAL
            
            self.process = subprocess.Popen(
                [
                    python_exe, _DL_TUI_SCRIPT,
                    "--mode", "youtube",
                    "--url", url,
                    "--quality", quality,
                    "--audio-only", str(audio_only),
                    "--ytdlp", ytdlp,
                    "--output", save_dir,
                    "--control", self._control_file,
                    "--status", self._status_file,
                ],
                cwd=_THIS_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=si,
            )
            mode_str = "🎵 Audio" if audio_only else f"🎬 Video ({quality}p)"
            return True, (
                f"📥 **Downloading YouTube**\n"
                f"🔗 `{url}`\n"
                f"📊 Quality: {mode_str}\n"
                f"📂 Saving to: `storage/downloads/`\n\n"
                f"🖥️ A download window has opened on your desktop."
            )
        except Exception as e:
            logger.error("Failed to launch download TUI: %s", e)
            return False, f"❌ Failed to start download: {e}"

    # ------------------------------------------------------------------
    # General URL Downloads
    # ------------------------------------------------------------------
    def download_url(self, url: str):
        """Download any file from a URL."""
        save_dir = _get_storage_dir("files")
        python_exe = _find_python()

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 1 # SW_NORMAL
            
            self.process = subprocess.Popen(
                [
                    python_exe, _DL_TUI_SCRIPT,
                    "--mode", "url",
                    "--url", url,
                    "--output", save_dir,
                    "--control", self._control_file,
                    "--status", self._status_file,
                ],
                cwd=_THIS_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=si,
            )
            return True, (
                f"📥 **Downloading File**\n"
                f"🔗 `{url}`\n"
                f"📂 Saving to: `storage/downloads/`\n\n"
                f"🖥️ A download window has opened on your desktop."
            )
        except Exception as e:
            return False, f"❌ Failed to start download: {e}"

    # ------------------------------------------------------------------
    # Image Downloads
    # ------------------------------------------------------------------
    def download_images(self, topic: str, count: int = 5):
        """Download images for a topic using web scraping."""
        save_dir = _get_storage_dir("images")
        python_exe = _find_python()

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 1 # SW_NORMAL
            
            self.process = subprocess.Popen(
                [
                    python_exe, _DL_TUI_SCRIPT,
                    "--mode", "images",
                    "--query", topic,
                    "--count", str(count),
                    "--output", save_dir,
                    "--control", self._control_file,
                    "--status", self._status_file,
                ],
                cwd=_THIS_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=si,
            )
            return True, (
                f"🖼️ **Downloading Images**\n"
                f"🔍 Topic: `{topic}`\n"
                f"📊 Count: {count} images\n"
                f"📂 Saving to: `storage/images/`\n\n"
                f"🖥️ A download window has opened on your desktop."
            )
        except Exception as e:
            return False, f"❌ Failed to start image download: {e}"

    def cancel(self):
        """Cancel any running download."""
        if self.process and self.process.poll() is None:
            try:
                import psutil
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
                parent.kill()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
            return True, "⏹ Download cancelled."
        return False, "⚠️ No active download."


# Singleton
download_manager = DownloadManager()
