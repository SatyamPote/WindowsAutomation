"""
Lotus Music Player — Controller
==================================
Opens a visible terminal window with a TUI music player.
Uses mpv + yt-dlp to search YouTube and stream audio.

Communication between Telegram bot and the TUI window
is done via control/status files.
"""

import os
import shutil
import subprocess
import logging
import sys
import time
from windows_mcp.paths import get_lotus_bin_dir

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TUI_SCRIPT = os.path.join(_THIS_DIR, "player_tui.py")


class MusicPlayer:
    def __init__(self):
        self.process = None       # the TUI python process (CREATE_NEW_CONSOLE)
        self._query = ""
        self._control_file = os.path.join(_THIS_DIR, ".player_control")
        self._status_file = os.path.join(_THIS_DIR, ".player_status")
        # Ensure state is always a dict to prevent 'tuple' attribute errors
        self.state = {
            "process": None,
            "queue": [],
            "index": 0
        }

    # ------------------------------------------------------------------
    # Dependency check
    # ------------------------------------------------------------------
    def check_dependencies(self):
        self.mpv_path = shutil.which("mpv")
        self.ytdlp_path = shutil.which("yt-dlp")

        bin_dir = get_lotus_bin_dir()

        if not self.mpv_path:
            candidates = [
                os.path.join(bin_dir, "mpv.exe"),
                os.path.join(bin_dir, "mpv", "mpv.exe")
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    self.mpv_path = cand
                    break

        if not self.ytdlp_path:
            local_ytdlp = os.path.join(bin_dir, "yt-dlp.exe")
            if os.path.exists(local_ytdlp):
                self.ytdlp_path = local_ytdlp

        return self.mpv_path is not None and self.ytdlp_path is not None

    # ------------------------------------------------------------------
    # Control helpers
    # ------------------------------------------------------------------
    def _send_control(self, command: str):
        try:
            with open(self._control_file, "w", encoding="utf-8") as f:
                f.write(command)
        except Exception as e:
            logger.error("Failed to write control command: %s", e)

    def _is_tui_running(self) -> bool:
        if self.process is not None and self.process.poll() is None:
            return True
        return False

    def _cleanup_files(self):
        for f in [self._control_file, self._status_file]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

    def _kill_tui(self):
        """Force-kill the TUI process and any orphaned TUI windows."""
        import psutil
        
        # 0. Kill ALL mpv instances (Aggressive cleanup)
        try:
            os.system("taskkill /IM mpv.exe /F >nul 2>&1")
        except: pass

        # 1. Kill the known process handle if it exists
        if self.process is not None:
            pid = self.process.pid
            try:
                parent = psutil.Process(pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
                parent.kill()
                parent.wait(timeout=2)
            except Exception:
                pass
        
        # 2. Aggressive Fallback: Scan all processes for 'player_tui.py'
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any('player_tui.py' in part for part in cmdline):
                    logger.info("Killing orphaned TUI process: %d", proc.info['pid'])
                    try:
                        for child in proc.children(recursive=True):
                            child.kill()
                    except Exception:
                        pass
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        self.process = None
        self.state["process"] = None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def play_song(self, query: str):
        if not self.check_dependencies():
            return {"success": False, "message": "❌ mpv or yt-dlp missing in bin/ folder."}

        # Stop any existing playback
        self.stop()
        self._query = query

        # Clear old files
        self._cleanup_files()

        python_exe = sys.executable
        if "pythonw" in python_exe.lower():
            python_exe = python_exe.lower().replace("pythonw.exe", "python.exe")
            if not os.path.exists(python_exe):
                python_exe = shutil.which("python") or shutil.which("python3") or "python"

        try:
            system_python = shutil.which("python") or shutil.which("python3") or "python"
            
            if getattr(sys, 'frozen', False):
                cmd = [system_python, _TUI_SCRIPT]
            else:
                cmd = [python_exe, _TUI_SCRIPT]

            cmd.extend([
                "--query", query,
                "--mpv", self.mpv_path,
                "--ytdlp", self.ytdlp_path,
                "--control", self._control_file,
                "--status", self._status_file,
            ])

            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 1 # SW_NORMAL
            
            self.process = subprocess.Popen(
                cmd,
                cwd=_THIS_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=si,
            )
            self.state["process"] = self.process
            logger.info("Launched TUI player (PID %d) for: %s", self.process.pid, query)

            return {"success": True, "message": f"🎵 **Playing:** {query}\nDesktop player window opened."}

        except Exception as e:
            logger.error("Failed to launch TUI player: %s", e)
            return {"success": False, "message": f"❌ Failed to open music player: {e}"}

    def pause(self):
        if self._is_tui_running():
            self._send_control("pause")
            return {"success": True, "message": "⏸ Music paused."}
        return {"success": False, "message": "⚠️ No music playing."}

    def resume(self):
        if self._is_tui_running():
            self._send_control("resume")
            return {"success": True, "message": "▶️ Resumed."}
        return {"success": False, "message": "⚠️ No music playing."}

    def stop(self):
        if self._is_tui_running():
            self._send_control("quit")
            try:
                self.process.wait(timeout=2)
            except Exception:
                pass

        self._kill_tui()
        self.process = None
        self.state["process"] = None
        self._query = ""
        self._cleanup_files()
        return {"success": True, "message": "⏹ Music stopped. Player closed."}

    def volume_up(self):
        if self._is_tui_running():
            self._send_control("volume_up")
            return {"success": True, "message": "🔊 Volume up."}
        return {"success": False, "message": "⚠️ No music playing."}

    def volume_down(self):
        if self._is_tui_running():
            self._send_control("volume_down")
            return {"success": True, "message": "🔉 Volume down."}
        return {"success": False, "message": "⚠️ No music playing."}

    def next_song(self):
        if self._is_tui_running():
            self._send_control("next")
            return {"success": True, "message": "⏭ Skipped to next track."}
        return {"success": False, "message": "⚠️ No music playing."}

    def previous_song(self):
        if self._is_tui_running():
            self._send_control("prev")
            return {"success": True, "message": "⏮ Skipped to previous track."}
        return {"success": False, "message": "⚠️ No music playing."}


player = MusicPlayer()
