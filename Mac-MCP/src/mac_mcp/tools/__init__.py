"""tools subpackage — registers all MCP tool definitions on a FastMCP instance."""

from mac_mcp.tools import (
    app,
    clipboard,
    defaults,
    filesystem,
    input,
    multi,
    notification,
    process,
    scrape,
    shell,
    snapshot,
)

_MODULES = [
    shell,
    snapshot,
    input,
    app,
    filesystem,
    clipboard,
    process,
    scrape,
    notification,
    defaults,
    multi,
]


def register_all(mcp, *, get_desktop, get_analytics):
    for mod in _MODULES:
        mod.register(mcp, get_desktop=get_desktop, get_analytics=get_analytics)
