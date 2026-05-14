"""
Lotus Music Player (v3 — stable)
================================
Single-instance mpv player driven via JSON IPC over a Windows named pipe.

Design notes vs the v2 implementation:
- Pause/resume and volume now use real IPC commands instead of writing to
  stdin (which mpv silently drops without --input-terminal=yes).
- _kill_mpv only kills OUR mpv subprocess (by pid), not every mpv on the
  system. Your movie player is safe.
- Playlists live in <data_dir>/playlists.json. Single source of truth.
- All public methods return {"success": bool, "message": str} so the
  Telegram router can rely on a uniform contract.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
PLAYLIST_FILE = os.path.join(DATA_DIR, "playlists.json")

IS_WINDOWS = os.name == "nt"
IPC_PIPE = r"\\.\pipe\lotus-mpv"
IPC_SOCKET = "/tmp/lotus-mpv.sock"


class MusicPlayer:
    def __init__(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        self.player: dict[str, Any] = {
            "process": None,
            "current_song": None,
            "playlist": [],
            "index": 0,
            "paused": False,
            "volume": 80,
        }
        self.playlists: dict[str, list[str]] = {}
        self._load_playlists()
        self._monitor_thread: threading.Thread | None = None
        self._monitoring = False
        self._lock = threading.Lock()

    # ── Playlist persistence ────────────────────────────────────────────

    def _load_playlists(self) -> None:
        if os.path.exists(PLAYLIST_FILE):
            try:
                with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
                    self.playlists = json.load(f)
            except Exception as e:
                logger.warning("Could not load playlists: %s", e)
                self.playlists = {}

    def _save_playlists(self) -> None:
        try:
            with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(self.playlists, f, indent=2)
        except Exception as e:
            logger.error("Could not save playlists: %s", e)

    # ── Process lifecycle ───────────────────────────────────────────────

    def _ipc_path(self) -> str:
        return IPC_PIPE if IS_WINDOWS else IPC_SOCKET

    def _kill_mpv(self) -> None:
        """Terminate ONLY our managed mpv subprocess. Never use taskkill /IM."""
        proc = self.player.get("process")
        if not proc:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception as e:
            logger.debug("Error terminating mpv: %s", e)
        finally:
            self.player["process"] = None
            # Best-effort socket cleanup on POSIX
            if not IS_WINDOWS:
                try:
                    if os.path.exists(IPC_SOCKET):
                        os.remove(IPC_SOCKET)
                except OSError:
                    pass

    def _send_ipc(self, command: list[Any], timeout: float = 1.5) -> bool:
        """Send a JSON IPC command to mpv. Returns True on success.

        On Windows, named-pipe `open()` can block forever if mpv isn't
        listening, so we run it in a worker thread with a join timeout.
        """
        if not self.player.get("process"):
            return False
        payload = (json.dumps({"command": command}) + "\n").encode("utf-8")
        result = {"ok": False}

        def _do_send() -> None:
            try:
                if IS_WINDOWS:
                    with open(IPC_PIPE, "r+b", buffering=0) as f:
                        f.write(payload)
                else:
                    import socket
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    s.connect(IPC_SOCKET)
                    s.sendall(payload)
                    s.close()
                result["ok"] = True
            except Exception as e:
                logger.debug("IPC send failed for %s: %s", command, e)

        worker = threading.Thread(target=_do_send, daemon=True)
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            logger.debug("IPC send timed out for %s", command)
            return False
        return result["ok"]

    def _play_internal(self, song_query: str) -> tuple[bool, str]:
        mpv_path = shutil.which("mpv")
        if not mpv_path:
            return False, "❌ mpv is not installed or not in PATH."

        # Ensure stale process is gone
        self._kill_mpv()

        cmd = [
            mpv_path,
            "--no-video",
            "--really-quiet",
            "--idle=no",
            f"--volume={self.player['volume']}",
            f"--input-ipc-server={self._ipc_path()}",
            f"ytdl://ytsearch:{song_query}",
        ]

        kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }
        if IS_WINDOWS:
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        try:
            self.player["process"] = subprocess.Popen(cmd, **kwargs)
        except Exception as e:
            return False, f"❌ Failed to launch mpv: {e}"

        self.player["current_song"] = song_query
        self.player["paused"] = False

        if not self._monitoring:
            self._start_monitor()

        return True, f"🎵 Now playing: {song_query}"

    def _start_monitor(self) -> None:
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="lotus-mpv-monitor"
        )
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        while self._monitoring:
            time.sleep(2)
            with self._lock:
                proc = self.player.get("process")
                if not proc or proc.poll() is None:
                    continue
                # Track ended — advance playlist if any
                pl = self.player["playlist"]
                idx = self.player["index"]
                if pl and idx < len(pl) - 1:
                    self.player["index"] = idx + 1
                    next_song = pl[self.player["index"]]
                    logger.info("Auto-advancing to: %s", next_song)
                    self._play_internal(next_song)
                else:
                    self.player["process"] = None
                    self.player["current_song"] = None

    # ── Public API ──────────────────────────────────────────────────────

    def play_song(self, query: str) -> dict[str, Any]:
        with self._lock:
            self.player["playlist"] = []
            self.player["index"] = 0
            ok, msg = self._play_internal(query)
            return {"success": ok, "message": msg}

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._kill_mpv()
            self.player["playlist"] = []
            self.player["current_song"] = None
            return {"success": True, "message": "⏹ Music stopped."}

    def pause_resume(self) -> dict[str, Any]:
        if not self.player.get("process"):
            return {"success": False, "message": "⚠️ Nothing is playing."}
        new_state = not self.player["paused"]
        if self._send_ipc(["set_property", "pause", new_state]):
            self.player["paused"] = new_state
            return {"success": True, "message": "⏸ Paused." if new_state else "▶ Resumed."}
        return {"success": False, "message": "⚠️ Pause/resume failed."}

    def next_song(self) -> dict[str, Any]:
        with self._lock:
            pl = self.player["playlist"]
            if pl and self.player["index"] < len(pl) - 1:
                self.player["index"] += 1
                song = pl[self.player["index"]]
                ok, _ = self._play_internal(song)
                return {"success": ok, "message": f"⏭ Next: {song}"}
            return {"success": False, "message": "⚠️ End of playlist."}

    def set_volume(self, level: int | str) -> dict[str, Any]:
        try:
            vol = max(0, min(100, int(level)))
        except (TypeError, ValueError):
            return {"success": False, "message": "❌ Volume must be 0-100."}
        self.player["volume"] = vol
        if self.player.get("process"):
            self._send_ipc(["set_property", "volume", vol])
        return {"success": True, "message": f"🔊 Volume set to {vol}%."}

    def now_playing(self) -> dict[str, Any]:
        song = self.player.get("current_song")
        if not song:
            return {"success": False, "message": "⚠️ Nothing is playing."}
        state = "Paused" if self.player.get("paused") else "Playing"
        return {"success": True, "message": f"🎵 {state}: {song}"}

    # ── Playlist management ─────────────────────────────────────────────

    def create_playlist(self, name: str) -> dict[str, Any]:
        name = name.strip()
        if not name:
            return {"success": False, "message": "❌ Playlist name required."}
        if name in self.playlists:
            return {"success": False, "message": f"❌ Playlist '{name}' already exists."}
        self.playlists[name] = []
        self._save_playlists()
        return {"success": True, "message": f"✅ Created playlist: {name}"}

    def delete_playlist(self, name: str) -> dict[str, Any]:
        if name not in self.playlists:
            return {"success": False, "message": f"❌ Playlist '{name}' not found."}
        del self.playlists[name]
        self._save_playlists()
        return {"success": True, "message": f"🗑 Deleted playlist: {name}"}

    def add_to_playlist(self, name: str, song: str) -> dict[str, Any]:
        if name not in self.playlists:
            return {"success": False, "message": f"❌ Playlist '{name}' not found."}
        if song in self.playlists[name]:
            return {"success": False, "message": f"⚠️ '{song}' already in {name}."}
        self.playlists[name].append(song)
        self._save_playlists()
        return {"success": True, "message": f"✅ Added '{song}' to {name}."}

    def play_playlist(self, name: str) -> dict[str, Any]:
        if name not in self.playlists or not self.playlists[name]:
            return {"success": False, "message": f"❌ Playlist '{name}' not found or empty."}
        with self._lock:
            self.player["playlist"] = list(self.playlists[name])
            self.player["index"] = 0
            song = self.player["playlist"][0]
            ok, _ = self._play_internal(song)
            if ok:
                return {"success": True, "message": f"🎵 Playlist '{name}' → ▶ {song}"}
            return {"success": False, "message": "❌ Failed to start playlist."}

    def list_playlists(self) -> dict[str, Any]:
        if not self.playlists:
            return {"success": True, "message": "📋 No playlists yet."}
        lines = ["📋 *Playlists*"]
        for name, songs in self.playlists.items():
            lines.append(f"• `{name}` — {len(songs)} song(s)")
        return {"success": True, "message": "\n".join(lines)}


# Global singleton
player = MusicPlayer()
