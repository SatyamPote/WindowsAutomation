import os
import shutil
import logging
from windows_mcp.paths import get_lotus_storage_dir

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self, limit_gb=2):
        self.storage_root = get_lotus_storage_dir()
        self.limit_bytes = limit_gb * 1024 * 1024 * 1024
        
    def get_status(self):
        total_size = 0
        file_count = 0
        for root, dirs, files in os.walk(self.storage_root):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
                file_count += 1
        
        size_mb = total_size / (1024 * 1024)
        limit_mb = self.limit_bytes / (1024 * 1024)
        percent = (total_size / self.limit_bytes) * 100 if self.limit_bytes > 0 else 0
        
        return {
            "size_mb": size_mb,
            "limit_mb": limit_mb,
            "percent": percent,
            "file_count": file_count,
            "path": str(self.storage_root)
        }

    def clear_storage(self):
        try:
            for item in os.listdir(self.storage_root):
                item_path = os.path.join(self.storage_root, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            # Recreate subdirs
            for d in ["videos", "audio", "images", "files", "research"]:
                os.makedirs(os.path.join(self.storage_root, d), exist_ok=True)
            return "Storage cleared successfully."
        except Exception as e:
            return f"Failed to clear storage: {e}"

    def auto_cleanup(self):
        status = self.get_status()
        if status["percent"] > 90:
            logger.warning("Storage nearly full, triggering auto-cleanup of oldest files...")
            # Simple cleanup: delete oldest files across all subdirs
            all_files = []
            for root, _, files in os.walk(self.storage_root):
                for f in files:
                    fp = os.path.join(root, f)
                    all_files.append((fp, os.path.getmtime(fp)))
            
            # Sort by time
            all_files.sort(key=lambda x: x[1])
            
            # Delete oldest 20%
            to_delete = all_files[:max(1, len(all_files)//5)]
            for fp, _ in to_delete:
                try:
                    os.remove(fp)
                except:
                    pass

# Singleton
storage_manager = StorageManager()
