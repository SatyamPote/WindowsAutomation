import os

from mac_mcp.ax.enums import AXRole

MAX_TREE_DEPTH = int(os.getenv("MAC_MCP_TREE_DEPTH", "8"))
THREAD_MAX_RETRIES = 3
TREE_TIMEOUT_PER_APP = 5.0  # seconds

ALWAYS_EXPAND_ROLES = {
    AXRole.APPLICATION,
    AXRole.WINDOW,
    AXRole.GROUP,
    AXRole.SPLIT_GROUP,
    AXRole.TOOL_BAR,
    AXRole.SCROLL_AREA,
    AXRole.TAB_GROUP,
    AXRole.LIST,
    AXRole.TABLE,
    AXRole.OUTLINE,
    AXRole.WEB_AREA,
    AXRole.MENU_BAR,
    AXRole.ROW,
}

SKIP_ROLES = {
    AXRole.UNKNOWN,
    AXRole.GENERIC,
    AXRole.SCROLL_BAR,
    AXRole.SPLITTER,
    AXRole.COLUMN,
    AXRole.PROGRESS,
    AXRole.IMAGE,
    AXRole.STATIC_TEXT,
}
