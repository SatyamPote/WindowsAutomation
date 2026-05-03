"""
Lotus Media & Playlist System
==============================
Stable, dictionary-based player state.
Supports direct playback and playlist management.
"""

import os
import json
import subprocess
import shutil
import logging
import threading
import time

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
PLAYLIST_FILE = os.path.join(DATA_DIR, "playlists.json")

class MusicPlayer:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.player = {
            "process": None,
            "current_song": None,
            "playlist": [],
            "index": 0,
            "paused": False,
            "volume": 100
        }
        self._load_playlists()
        self._monitor_thread = None
        self._monitoring = False

    def _load_playlists(self):
        if os.path.exists(PLAYLIST_FILE):
            try:
                with open(PLAYLIST_FILE, "r") as f:
                    self.playlists = json.load(f)
            except:
                self.playlists = {}
        else:
            self.playlists = {}

    def _save_playlists(self):
        with open(PLAYLIST_FILE, "w") as f:
            json.dump(self.playlists, f, indent=2)

    def _kill_mpv(self):
        """Aggressive cleanup."""
        try:
            if self.player["process"]:
                self.player["process"].terminate()
                self.player["process"] = None
            os.system("taskkill /IM mpv.exe /F >nul 2>&1")
        except:
            pass

    def _play_internal(self, song_query):
        """Direct mpv launch."""
        mpv_path = shutil.which("mpv")
        if not mpv_path:
            return False, "❌ mpv not found."

        try:
            cmd = [
                mpv_path, 
                "--no-video", 
                f"--volume={self.player['volume']}",
                f"ytdl://ytsearch:{song_query}"
            ]
            self.player["process"] = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.player["current_song"] = song_query
            self.player["paused"] = False
            
            # Start monitoring if not already
            if not self._monitoring:
                self._start_monitor()
                
            return True, f"🎵 Now playing: {song_query}"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"

    def _start_monitor(self):
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        while self._monitoring:
            if self.player["process"] and self.player["process"].poll() is not None:
                # Process ended
                if self.player["playlist"] and self.player["index"] < len(self.player["playlist"]) - 1:
                    self.player["index"] += 1
                    next_song = self.player["playlist"][self.player["index"]]
                    logger.info(f"Auto-playing next: {next_song}")
                    self._play_internal(next_song)
                else:
                    self.player["process"] = None
                    self.player["current_song"] = None
            time.sleep(2)

    # ── PUBLIC COMMANDS ──

    def play_song(self, query):
        self._kill_mpv()
        self.player["playlist"] = []
        self.player["index"] = 0
        success, msg = self._play_internal(query)
        return {"success": success, "message": msg}

    def stop(self):
        self._kill_mpv()
        self.player["playlist"] = []
        self.player["current_song"] = None
        return {"success": True, "message": "⏹️ Music stopped"}

    def pause_resume(self):
        if self.player["process"]:
            try:
                self.player["process"].stdin.write(b"p")
                self.player["process"].stdin.flush()
                self.player["paused"] = not self.player["paused"]
                state = "Paused" if self.player["paused"] else "Resumed"
                return {"success": True, "message": f"⏯️ {state}"}
            except:
                pass
        return {"success": False, "message": "⚠️ No music playing."}

    def next_song(self):
        if self.player["playlist"] and self.player["index"] < len(self.player["playlist"]) - 1:
            self._kill_mpv()
            self.player["index"] += 1
            song = self.player["playlist"][self.player["index"]]
            success, _ = self._play_internal(song)
            return {"success": success, "message": f"▶ Next: {song}"}
        return {"success": False, "message": "⚠️ End of playlist."}

    def set_volume(self, level):
        try:
            vol = int(level)
            vol = max(0, min(100, vol))
            self.player["volume"] = vol
            if self.player["process"]:
                # mpv volume command via stdin (harder without IPC, easier to just send 0/9 keys multiple times or restart)
                # But we can restart with new volume for simplicity, or use 'set volume X' if mpv supports it via stdin
                try:
                    self.player["process"].stdin.write(f"set volume {vol}\n".encode())
                    self.player["process"].stdin.flush()
                except:
                    pass
            return {"success": True, "message": f"🔊 Volume set to {vol}%"}
        except:
            return {"success": False, "message": "❌ Invalid volume level."}

    # ── PLAYLIST MGMT ──

    def create_playlist(self, name):
        if name in self.playlists:
            return {"success": False, "message": f"❌ Playlist '{name}' already exists."}
        self.playlists[name] = []
        self._save_playlists()
        return {"success": True, "message": f"✅ Created playlist: {name}"}

    def delete_playlist(self, name):
        if name in self.playlists:
            del self.playlists[name]
            self._save_playlists()
            return {"success": True, "message": f"🗑️ Deleted playlist: {name}"}
        return {"success": False, "message": "❌ Playlist not found."}

    def add_to_playlist(self, name, song):
        if name not in self.playlists:
            return {"success": False, "message": f"❌ Playlist '{name}' not found."}
        self.playlists[name].append(song)
        self._save_playlists()
        return {"success": True, "message": f"✅ Added '{song}' to {name}"}

    def play_playlist(self, name):
        if name not in self.playlists or not self.playlists[name]:
            return {"success": False, "message": "❌ Playlist not found or empty."}
        
        self._kill_mpv()
        self.player["playlist"] = self.playlists[name]
        self.player["index"] = 0
        song = self.player["playlist"][0]
        success, _ = self._play_internal(song)
        if success:
            return {"success": True, "message": f"🎵 Playlist: {name}\n▶ Playing: {song}"}
        return {"success": False, "message": "❌ Failed to start playlist."}

# Global instance
player = MusicPlayer()
