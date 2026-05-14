import logging
import os


def enable_debug() -> None:
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("mac_mcp").setLevel(logging.DEBUG)


def is_debug() -> bool:
    return os.getenv("MAC_MCP_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
