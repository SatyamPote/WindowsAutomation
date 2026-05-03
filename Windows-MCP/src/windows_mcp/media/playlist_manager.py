import json
import os
import logging

logger = logging.getLogger(__name__)

class PlaylistManager:
    def __init__(self, data_root):
        self.data_dir = data_root
        os.makedirs(self.data_dir, exist_ok=True)
        self.playlists_file = os.path.join(self.data_dir, "playlists.json")
        self.playlists = self._load()

    def _load(self):
        if os.path.exists(self.playlists_file):
            try:
                with open(self.playlists_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load playlists: {e}")
        return {}

    def _save(self):
        try:
            with open(self.playlists_file, "w", encoding="utf-8") as f:
                json.dump(self.playlists, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save playlists: {e}")

    def create(self, name):
        if name in self.playlists:
            return False
        self.playlists[name] = []
        self._save()
        return True

    def delete(self, name):
        if name in self.playlists:
            del self.playlists[name]
            self._save()
            return True
        return False

    def add_song(self, name, song):
        if name in self.playlists:
            if song not in self.playlists[name]:
                self.playlists[name].append(song)
                self._save()
            return True
        return False

    def remove_song(self, name, song):
        if name in self.playlists:
            if song in self.playlists[name]:
                self.playlists[name].remove(song)
                self._save()
                return True
        return False

    def list_playlists(self):
        return list(self.playlists.keys())

    def get_playlist(self, name):
        return self.playlists.get(name, [])
