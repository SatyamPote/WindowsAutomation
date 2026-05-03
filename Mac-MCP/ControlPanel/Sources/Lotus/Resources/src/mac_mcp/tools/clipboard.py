"""Clipboard tool — macOS pbcopy/pbpaste clipboard operations."""

import subprocess
from typing import Literal

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Clipboard",
        description=(
            'Copy/paste clipboard operations. Keywords: copy, paste, clipboard, text transfer. '
            'Use mode="get" to read current clipboard content, mode="set" to write text to clipboard.'
        ),
        annotations=ToolAnnotations(
            title="Clipboard",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Clipboard-Tool")
    def clipboard_tool(
        mode: Literal["get", "set"],
        text: str | None = None,
        ctx: Context = None,
    ) -> str:
        try:
            if mode == "get":
                result = subprocess.run(
                    ["pbpaste"], capture_output=True, timeout=5
                )
                if result.returncode != 0:
                    return "Error: pbpaste failed — clipboard may be empty or inaccessible."
                content = result.stdout.decode("utf-8", errors="replace")
                return f"Clipboard content:\n{content}" if content else "Clipboard is empty."
            elif mode == "set":
                if text is None:
                    return "Error: text parameter required for set mode."
                subprocess.run(
                    ["pbcopy"], input=text.encode("utf-8"), capture_output=True, timeout=5, check=True
                )
                preview = text[:100] + ("..." if len(text) > 100 else "")
                return f"Clipboard set to: {preview}"
            else:
                return 'Error: mode must be "get" or "set".'
        except subprocess.TimeoutExpired:
            return "Error: clipboard operation timed out."
        except Exception as e:
            return f"Error managing clipboard: {e}"
