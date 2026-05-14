"""Snapshot / Screenshot shared helpers."""

import io
import logging
import os
import time
from textwrap import dedent

from fastmcp.utilities.types import Image

from mac_mcp.desktop.service import Desktop, Size
from mac_mcp.desktop.utils import remove_private_use_chars

logger = logging.getLogger(__name__)

MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = 1920, 1080


def _screenshot_scale() -> float:
    value = os.getenv("MAC_MCP_SCREENSHOT_SCALE", "1.0")
    try:
        scale = float(value)
    except ValueError:
        scale = 1.0
    return max(0.1, min(1.0, scale))


def _snapshot_profile_enabled() -> bool:
    return os.getenv("MAC_MCP_PROFILE_SNAPSHOT", "").strip().lower() in {"1", "true", "yes", "on"}


def _as_bool(value: bool | str) -> bool:
    return value is True or (isinstance(value, str) and value.lower() == "true")


def capture_desktop_state(
    desktop: Desktop,
    *,
    use_vision: bool,
    use_dom: bool,
    use_annotation: bool,
    use_ui_tree: bool,
    width_reference_line: int | None,
    height_reference_line: int | None,
    display: list[int] | None,
    tool_name: str,
) -> dict:
    profile_enabled = _snapshot_profile_enabled()
    t0 = time.perf_counter()

    if use_dom and not use_ui_tree:
        raise ValueError("use_dom=True requires use_ui_tree=True")

    display_indices = Desktop.parse_display_selection(display)

    grid_lines = None
    if width_reference_line and height_reference_line:
        grid_lines = (int(width_reference_line), int(height_reference_line))

    desktop_state = desktop.get_state(
        use_vision=use_vision,
        use_dom=use_dom,
        use_annotation=use_annotation,
        use_ui_tree=use_ui_tree,
        as_bytes=False,
        scale=_screenshot_scale(),
        grid_lines=grid_lines,
        display_indices=display_indices,
        max_image_size=Size(width=MAX_IMAGE_WIDTH, height=MAX_IMAGE_HEIGHT),
    )

    semantic_tree = ""
    interactive_elements = ""
    scrollable_elements = ""

    if desktop_state.tree_state:
        semantic_tree = desktop_state.tree_state.semantic_tree_to_string()
        interactive_elements = desktop_state.tree_state.interactive_elements_to_string()
        scrollable_elements = desktop_state.tree_state.scrollable_elements_to_string()

    windows = desktop_state.windows_to_string()
    active_window = desktop_state.active_window_to_string()
    active_desktop = desktop_state.active_desktop_to_string()
    all_desktops = desktop_state.desktops_to_string()

    screenshot_bytes = None
    if use_vision and desktop_state.screenshot is not None:
        buf = io.BytesIO()
        desktop_state.screenshot.save(buf, format="PNG")
        screenshot_bytes = buf.getvalue()

    if profile_enabled:
        logger.info(
            "%s: %.1fms use_vision=%s use_ui_tree=%s",
            tool_name,
            (time.perf_counter() - t0) * 1000,
            use_vision,
            use_ui_tree,
        )

    return {
        "desktop_state": desktop_state,
        "interactive_elements": interactive_elements,
        "scrollable_elements": scrollable_elements,
        "semantic_tree": semantic_tree,
        "windows": windows,
        "active_window": active_window,
        "active_desktop": active_desktop,
        "all_desktops": all_desktops,
        "screenshot_bytes": screenshot_bytes,
    }


def build_snapshot_response(
    capture_result: dict,
    *,
    include_ui_details: bool,
    ui_detail_note: str | None = None,
) -> list:
    desktop_state = capture_result["desktop_state"]
    interactive_elements = remove_private_use_chars(capture_result["interactive_elements"])
    scrollable_elements = remove_private_use_chars(capture_result["scrollable_elements"])
    semantic_tree = remove_private_use_chars(capture_result["semantic_tree"])
    windows = capture_result["windows"]
    active_window = capture_result["active_window"]
    active_desktop = capture_result["active_desktop"]
    all_desktops = capture_result["all_desktops"]
    screenshot_bytes = capture_result["screenshot_bytes"]

    metadata_text = f"Cursor Position: {desktop_state.cursor_position}\n"
    if desktop_state.screenshot_original_size:
        orig = desktop_state.screenshot_original_size
        metadata_text += (
            f"Screenshot Original Size: {orig.to_string()}"
            " (screenshot may be downscaled; multiply image coordinates by"
            " ratio of original size to displayed size for actual screen coordinates)\n"
        )
    if desktop_state.screenshot_backend:
        metadata_text += f"Screenshot Backend: {desktop_state.screenshot_backend}\n"
    if ui_detail_note:
        metadata_text += f"{ui_detail_note}\n"

    response_text = dedent(f"""
    {metadata_text}
    Active Desktop:
    {active_desktop}

    All Desktops:
    {all_desktops}

    Focused Window:
    {active_window}

    Opened Windows:
    {windows}
    """)

    if include_ui_details:
        response_text += dedent(f"""
    Interactive Elements:
    {interactive_elements or "None"}

    Scrollable Elements:
    {scrollable_elements or "None"}

    UI Tree:
    {semantic_tree or "No elements found."}""")

    response: list = [response_text]
    if screenshot_bytes:
        response.append(Image(data=screenshot_bytes, format="png"))
    return response
