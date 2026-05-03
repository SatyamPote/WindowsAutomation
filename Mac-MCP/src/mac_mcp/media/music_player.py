"""
Lotus Music Player (macOS)
===========================
Plays music by searching YouTube via yt-dlp, streamed through mpv.
mpv runs headlessly in the background; control is via its JSON IPC socket.

Requirements (both installable via Homebrew):
  brew install mpv yt-dlp
"""

import json
import logging
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_MPV_SOCK = "/tmp/lotus_mpv.sock"
_HOMEBREW_BINS = ["/opt/homebrew/bin", "/usr/local/bin"]


def _find_bin(name: str) -> str | None:
    path = shutil.which(name)
    if path:
        return path
    for d in _HOMEBREW_BINS:
        candidate = os.path.join(d, name)
        if os.path.exists(candidate):
            return candidate
    return None


class MusicPlayer:
    """Controls a background mpv process via Unix IPC socket."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._query = ""
        self._volume = 70

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _send_ipc(self, command: list) -> bool:
        """Send a JSON command to the running mpv instance."""
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(_MPV_SOCK)
            s.sendall(json.dumps({"command": command}).encode() + b"\n")
            s.close()
            return True
        except Exception as e:
            logger.debug("mpv IPC error: %s", e)
            return False

    def _kill(self) -> None:
        if self._process is not None:
            try:
                self._process.kill()
                self._process.wait(timeout=2)
            except Exception:
                pass
        self._process = None
        try:
            Path(_MPV_SOCK).unlink(missing_ok=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play_song(self, query: str) -> tuple[bool, str]:
        mpv = _find_bin("mpv")
        ytdlp = _find_bin("yt-dlp")

        if not mpv:
            return False, (
                "❌ mpv not found.\n"
                "Install with: `brew install mpv`\n"
                "Then also install yt-dlp: `brew install yt-dlp`"
            )
        if not ytdlp:
            return False, "❌ yt-dlp not found. Install with: `brew install yt-dlp`"

        # Stop any existing playback
        self.stop()
        self._query = query

        # Enrich PATH so mpv can find yt-dlp
        env = os.environ.copy()
        env["PATH"] = ":".join(_HOMEBREW_BINS) + ":" + env.get("PATH", "")

        try:
            self._process = subprocess.Popen(
                [
                    mpv,
                    "--no-video",
                    "--really-quiet",
                    f"--input-ipc-server={_MPV_SOCK}",
                    f"--volume={self._volume}",
                    f"ytdl://ytsearch1:{query}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )

            # Wait up to 2 s for the IPC socket to appear
            for _ in range(20):
                if Path(_MPV_SOCK).exists():
                    break
                time.sleep(0.1)

            return True, (
                f"🎵 *Now Playing:* {query}\n\n"
                f"**Controls:**\n"
                f"• `pause` — Pause\n"
                f"• `resume` — Resume\n"
                f"• `stop music` — Stop & exit\n"
                f"• `volume up` / `volume down` — Adjust volume\n"
                f"• `next` — Skip track"
            )
        except Exception as e:
            logger.error("Failed to launch mpv: %s", e)
            return False, f"❌ Failed to start player: {e}"

    def pause(self) -> tuple[bool, str]:
        if not self._is_running():
            return False, "⚠️ No music is playing."
        ok = self._send_ipc(["set_property", "pause", True])
        return (True, "⏸ Music paused.") if ok else (False, "❌ Could not pause.")

    def resume(self) -> tuple[bool, str]:
        if not self._is_running():
            return False, "⚠️ No music is playing."
        ok = self._send_ipc(["set_property", "pause", False])
        return (True, "▶️ Resumed.") if ok else (False, "❌ Could not resume.")

    def stop(self) -> tuple[bool, str]:
        if self._is_running():
            self._send_ipc(["quit"])
            try:
                self._process.wait(timeout=2)
            except Exception:
                pass
        self._kill()
        self._query = ""
        return True, "⏹ Music stopped."

    def volume_up(self) -> tuple[bool, str]:
        if not self._is_running():
            return False, "⚠️ No music is playing."
        self._volume = min(100, self._volume + 10)
        self._send_ipc(["set_property", "volume", self._volume])
        return True, f"🔊 Volume: {self._volume}%"

    def volume_down(self) -> tuple[bool, str]:
        if not self._is_running():
            return False, "⚠️ No music is playing."
        self._volume = max(0, self._volume - 10)
        self._send_ipc(["set_property", "volume", self._volume])
        return True, f"🔉 Volume: {self._volume}%"

    def next_song(self) -> tuple[bool, str]:
        if not self._is_running():
            return False, "⚠️ No music is playing."
        ok = self._send_ipc(["playlist-next", "force"])
        return (True, "⏭ Skipped to next track.") if ok else (False, "❌ Could not skip.")

    def now_playing(self) -> tuple[bool, str]:
        if not self._is_running():
            return False, "⚠️ No music is playing."
        return True, f"🎵 Now playing: *{self._query}* · Vol {self._volume}%"


music_player = MusicPlayer()
