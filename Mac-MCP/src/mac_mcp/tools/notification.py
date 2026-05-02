"""Notification tool — macOS notifications and dialogs via osascript."""

from typing import Literal

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from mac_mcp.desktop.shell import AppleScriptExecutor
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Notification",
        description=(
            "Show a macOS notification or dialog. Keywords: notify, alert, message, popup, toast. "
            "Use mode='notification' for a banner notification (non-blocking, appears in Notification Center). "
            "Use mode='dialog' for a modal dialog that waits for user acknowledgment."
        ),
        annotations=ToolAnnotations(
            title="Notification",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Notification-Tool")
    def notification_tool(
        title: str,
        message: str,
        mode: Literal["notification", "dialog"] = "notification",
        ctx: Context = None,
    ) -> str:
        if mode == "dialog":
            script = f'display dialog "{_esc(message)}" with title "{_esc(title)}" buttons {{"OK"}}'
        else:
            script = f'display notification "{_esc(message)}" with title "{_esc(title)}"'
        _, code = AppleScriptExecutor.execute(script)
        if code != 0:
            return f"Notification failed (exit {code}). Check Automation permissions in System Settings."
        return f"Notification sent: {title} — {message}"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')
