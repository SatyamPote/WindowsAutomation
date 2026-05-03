import os
import logging
from datetime import datetime
from windows_mcp.paths import get_lotus_log_dir

logger = logging.getLogger(__name__)

class ActivityLogger:
    def __init__(self):
        self.log_dir = get_lotus_log_dir()
        self.log_file = os.path.join(self.log_dir, "activity_log.txt")
        
    def log(self, command, status="SUCCESS", details=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] COMMAND: {command} | STATUS: {status} | DETAILS: {details}\n"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Failed to write to activity log: {e}")

    def get_logs(self, limit=20):
        if not os.path.exists(self.log_file):
            return "No logs found."
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-limit:])
        except Exception as e:
            return f"Error reading logs: {e}"

    def clear_logs(self):
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            return "Logs cleared successfully."
        except Exception as e:
            return f"Failed to clear logs: {e}"

# Singleton
activity_logger = ActivityLogger()
