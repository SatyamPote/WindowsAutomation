"""Snapshot and Screenshot tools — desktop state capture."""

import logging

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from fastmcp import Context

from mac_mcp.tools._snapshot_helpers import (
    _as_bool,
    capture_desktop_state,
    build_snapshot_response,
)

logger = logging.getLogger(__name__)

state_tool = None
screenshot_tool = None


def register(mcp, *, get_desktop, get_analytics):
    global state_tool, screenshot_tool

    @mcp.tool(
        name="Snapshot",
        description=(
            "Take a screenshot and inspect the screen. Keywords: screenshot, screen capture, "
            "see screen, observe, look, inspect, UI elements, what's on screen. Captures desktop "
            "state including focused/opened windows and interactive elements (buttons, text fields, "
            "links, menus with coordinates). Set use_vision=True to include screenshot image. "
            "Set use_annotation=False for a clean screenshot without bounding box overlays. "
            "Set use_ui_tree=False for a faster screenshot-only snapshot. "
            "Always call this first to understand the current desktop state before taking actions."
        ),
        annotations=ToolAnnotations(
            title="Snapshot",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "State-Tool")
    def _state_tool(
        use_vision: bool | str = False,
        use_dom: bool | str = False,
        use_annotation: bool | str = True,
        use_ui_tree: bool | str = True,
        width_reference_line: int | None = None,
        height_reference_line: int | None = None,
        display: list[int] | None = None,
        ctx: Context = None,
    ):
        try:
            result = capture_desktop_state(
                get_desktop(),
                use_vision=_as_bool(use_vision),
                use_dom=_as_bool(use_dom),
                use_annotation=_as_bool(use_annotation),
                use_ui_tree=_as_bool(use_ui_tree),
                width_reference_line=width_reference_line,
                height_reference_line=height_reference_line,
                display=display,
                tool_name="Snapshot",
            )
        except Exception as e:
            logger.warning("Snapshot failed", exc_info=True)
            return [f"Error capturing desktop state: {e}. Please try again."]
        return build_snapshot_response(result, include_ui_details=True)

    @mcp.tool(
        name="Screenshot",
        description=(
            "Fast screenshot without UI tree extraction. Returns current screen image plus "
            "window summary. Use Snapshot when you need interactive element IDs and coordinates. "
            "Note: screenshot may be downscaled; multiply image coordinates by ratio of original "
            "size to displayed size to get actual screen coordinates for Click/Move actions."
        ),
        annotations=ToolAnnotations(
            title="Screenshot",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Screenshot-Tool")
    def _screenshot_tool(
        use_annotation: bool | str = False,
        width_reference_line: int | None = None,
        height_reference_line: int | None = None,
        display: list[int] | None = None,
        ctx: Context = None,
    ):
        try:
            result = capture_desktop_state(
                get_desktop(),
                use_vision=True,
                use_dom=False,
                use_annotation=_as_bool(use_annotation),
                use_ui_tree=False,
                width_reference_line=width_reference_line,
                height_reference_line=height_reference_line,
                display=display,
                tool_name="Screenshot",
            )
        except Exception as e:
            logger.warning("Screenshot failed", exc_info=True)
            return [f"Error capturing screenshot: {e}. Please try again."]
        return build_snapshot_response(
            result,
            include_ui_details=False,
            ui_detail_note=(
                "UI Tree: Skipped for fast screenshot. "
                "Call Snapshot when you need interactive element IDs."
            ),
        )

    state_tool = _state_tool
    screenshot_tool = _screenshot_tool
