"""MultiSelect and MultiEdit tools — batch element interaction."""

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="MultiSelect",
        description=(
            "Selects multiple items such as files, folders, or list items. "
            "If press_cmd=True (default), holds Cmd while clicking for multi-selection. "
            "Pass locs (list of [x, y] coordinates) or labels (list of UI element label ids). "
            "Provide either locs or labels."
        ),
        annotations=ToolAnnotations(
            title="MultiSelect",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Multi-Select-Tool")
    def multi_select_tool(
        locs: list[list[int]] | None = None,
        labels: list[int] | None = None,
        press_cmd: bool | str = True,
        ctx: Context = None,
    ) -> str:
        desktop = get_desktop()
        if locs is None and labels is None:
            raise ValueError("Either locs or labels must be provided.")
        locs = list(locs) if locs else []
        if labels is not None:
            if desktop.desktop_state is None:
                raise ValueError("Desktop state is empty. Please call Snapshot first.")
            try:
                resolved = desktop.get_coordinates_from_labels(labels)
                locs.extend([list(loc) for loc in resolved])
            except Exception as e:
                raise ValueError(f"Failed to resolve labels {labels}: {e}")

        press_cmd = press_cmd is True or (isinstance(press_cmd, str) and press_cmd.lower() == "true")
        desktop.multi_select(press_cmd, locs)
        elements_str = "\n".join([f"({loc[0]},{loc[1]})" for loc in locs])
        return f"Multi-selected elements at:\n{elements_str}"

    @mcp.tool(
        name="MultiEdit",
        description=(
            "Enters text into multiple input fields. "
            "Use locs=[[x, y, text], ...] for coordinate-based edits, "
            "or labels=[[label_id, text], ...] for label-based edits. "
            "Each field is clicked, cleared, and typed into sequentially. "
            "Provide either locs or labels."
        ),
        annotations=ToolAnnotations(
            title="MultiEdit",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Multi-Edit-Tool")
    def multi_edit_tool(
        locs: list[list] | None = None,
        labels: list[list] | None = None,
        ctx: Context = None,
    ) -> str:
        desktop = get_desktop()
        if locs is None and labels is None:
            raise ValueError("Either locs or labels must be provided.")
        locs = list(locs) if locs else []
        if labels is not None:
            if desktop.desktop_state is None:
                raise ValueError("Desktop state is empty. Please call Snapshot first.")
            processed = []
            for item in labels:
                if len(item) != 2:
                    raise ValueError(f"Each label item must be [label_id, text]. Invalid: {item}")
                try:
                    processed.append((int(item[0]), item[1]))
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid label id in item: {item}")
            try:
                label_ids = [p[0] for p in processed]
                resolved = desktop.get_coordinates_from_labels(label_ids)
                for (x, y), (_, text) in zip(resolved, processed):
                    locs.append([x, y, text])
            except Exception as e:
                raise ValueError(f"Failed to process labels: {e}")

        desktop.multi_edit(locs)
        elements_str = ", ".join([f"({e[0]},{e[1]}) → {e[2]!r}" for e in locs])
        return f"Multi-edited elements: {elements_str}"
