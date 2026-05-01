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

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TUI_SCRIPT = os.path.join(_THIS_DIR, "player_tui.py")


class MusicPlayer:
    def __init__(self):
        self.process = None       # the TUI python process (CREATE_NEW_CONSOLE)
        self._query = ""
        self._control_file = os.path.join(_THIS_DIR, ".player_control")
        self._status_file = os.path.join(_THIS_DIR, ".player_status")

    # ------------------------------------------------------------------
    # Dependency check
    # ------------------------------------------------------------------
    def check_dependencies(self):
        self.mpv_path = shutil.which("mpv")
        self.ytdlp_path = shutil.which("yt-dlp")

        project_root = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))
        bin_dir = os.path.join(project_root, "bin")

        if not self.mpv_path:
            local_mpv = os.path.join(bin_dir, "mpv.exe")
            if os.path.exists(local_mpv):
                self.mpv_path = local_mpv

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
        # This handles cases where the bot restarted and lost the process handle.
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any('player_tui.py' in part for part in cmdline):
                    logger.info("Killing orphaned TUI process: %d", proc.info['pid'])
                    # Kill children (mpv) first
                    try:
                        for child in proc.children(recursive=True):
                            child.kill()
                    except Exception:
                        pass
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        self.process = None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def play_song(self, query: str):
        if not self.check_dependencies():
            return False, (
                "❌ mpv or yt-dlp not installed.\n"
                "Place `mpv.exe` and `yt-dlp.exe` in the `bin/` folder or add them to PATH."
            )

        # Stop any existing playback
        self.stop()
        self._query = query

        # Clear old files
        self._cleanup_files()

        # Find python.exe (not pythonw.exe — we need a console)
        python_exe = sys.executable
        if "pythonw" in python_exe.lower():
            python_exe = python_exe.lower().replace("pythonw.exe", "python.exe")
            if not os.path.exists(python_exe):
                python_exe = shutil.which("python") or shutil.which("python3") or "python"

        try:
            # CREATE_NEW_CONSOLE opens a VISIBLE new window AND lets us
            # keep the process handle so we can kill it later with stop.
            self.process = subprocess.Popen(
                [
                    python_exe, _TUI_SCRIPT,
                    "--query", query,
                    "--mpv", self.mpv_path,
                    "--ytdlp", self.ytdlp_path,
                    "--control", self._control_file,
                    "--status", self._status_file,
                ],
                cwd=_THIS_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            logger.info("Launched TUI player (PID %d) for: %s", self.process.pid, query)

            return True, (
                f"🎵 **Now Playing:** {query}\n"
                f"🖥️ A music player window has opened on your desktop.\n\n"
                f"**Controls:**\n"
                f"• `pause` — Pause playback\n"
                f"• `resume` — Resume playback\n"
                f"• `stop` — Stop and close player\n"
                f"• `volume up/down` — Adjust volume\n"
                f"• `next` — Skip track"
            )

        except Exception as e:
            logger.error("Failed to launch TUI player: %s", e)
            return False, f"❌ Failed to open music player: {e}"

    def pause(self):
        if self._is_tui_running():
            self._send_control("pause")
            return True, "⏸ Music paused."
        return False, "⚠️ No music is currently playing."

    def resume(self):
        if self._is_tui_running():
            self._send_control("resume")
            return True, "▶️ Resumed."
        return False, "⚠️ No music is currently playing."

    def stop(self):
        if self._is_tui_running():
            # First try graceful quit via control file
            self._send_control("quit")
            # Give TUI 2 seconds to shut down gracefully
            try:
                self.process.wait(timeout=2)
            except Exception:
                pass

        # Final cleanup: kill any orphaned TUI windows and clean files
        self._kill_tui()
        self.process = None
        self._query = ""
        self._cleanup_files()
        return True, "⏹ Music stopped. Player window closed."

    def volume_up(self):
        if self._is_tui_running():
            self._send_control("volume_up")
            return True, "🔊 Volume increased."
        return False, "⚠️ No music is currently playing."

    def volume_down(self):
        if self._is_tui_running():
            self._send_control("volume_down")
            return True, "🔉 Volume decreased."
        return False, "⚠️ No music is currently playing."

    def next_song(self):
        if self._is_tui_running():
            self._send_control("next")
            return True, "⏭ Skipped to next track."
        return False, "⚠️ No music is currently playing."


player = MusicPlayer()
