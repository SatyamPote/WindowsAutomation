from platformdirs import user_data_dir, user_cache_dir
from pathlib import Path

APP_NAME = "mac-mcp"
DATA_DIR = Path(user_data_dir(APP_NAME))
CACHE_DIR = Path(user_cache_dir(APP_NAME))
