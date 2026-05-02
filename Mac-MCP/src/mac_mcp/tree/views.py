from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_ACTION_MAP: dict[str, str] = {
    "axtextfield":   "fill",
    "axtextarea":    "fill",
    "axsearchfield": "fill",
    "axcheckbox":    "toggle",
    "axradiobutton": "select",
    "axcombobox":    "select",
    "axpopupbutton": "select",
    "axslider":      "slide",
    "axdisclosuretriangle": "toggle",
    "axscrollarea":  "scroll",
    "axlist":        "scroll",
    "axtable":       "scroll",
    "axoutline":     "scroll",
}


def _action_for(role: str) -> str:
    return _ACTION_MAP.get(role.lower(), "click")


@dataclass
class BoundingBox:
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int

    def get_center(self) -> "Center":
        return Center(x=self.left + self.width // 2, y=self.top + self.height // 2)

    def xyxy_to_string(self) -> str:
        return f"({self.left},{self.top},{self.right},{self.bottom})"


@dataclass
class Center:
    x: int
    y: int

    def to_string(self) -> str:
        return f"({self.x},{self.y})"


@dataclass
class TreeElementNode:
    bounding_box: BoundingBox
    center: Center
    name: str = ""
    control_type: str = ""
    window_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrollElementNode:
    name: str
    control_type: str
    window_name: str
    bounding_box: BoundingBox
    center: Center
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Semantic tree
# ---------------------------------------------------------------------------

@dataclass
class SemanticNode:
    control_type: str
    element_type: str          # desktop | window | structural | interactive | scrollable
    name: str = ""
    window_name: str = ""
    center: Center | None = None
    bounding_box: BoundingBox | None = None
    children: list["SemanticNode"] = field(default_factory=list)

    def add_child(self, child: "SemanticNode") -> None:
        self.children.append(child)


def _format_semantic_node(node: SemanticNode) -> str:
    role = node.control_type.lower()
    name = node.name
    if node.element_type == "window":
        return f'window "{name}"'
    if node.element_type == "structural":
        return f'{role} "{name}"'
    if node.element_type in ("interactive", "scrollable"):
        coords = node.center.to_string() if node.center else "(?)"
        action = _action_for(node.control_type)
        return f'{coords} {role} "{name}"  [action: {action}]'
    return f'{role} "{name}"'


def _render_semantic_node(
    node: SemanticNode, lines: list[str], prefix: str, is_last: bool
) -> None:
    if node.element_type == "desktop":
        lines.append("desktop")
    else:
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{_format_semantic_node(node)}")

    if not node.children:
        return
    ext = "    " if is_last else "│   "
    new_prefix = prefix + ext
    for i, child in enumerate(node.children):
        _render_semantic_node(child, lines, new_prefix, i == len(node.children) - 1)


def _prune_structural(node: SemanticNode) -> bool:
    node.children = [c for c in node.children if _prune_structural(c)]
    if node.element_type == "structural" and not node.children:
        return False
    return True


def _render_flat_tree(nodes: list, *, scrollable: bool = False) -> str:
    windows: dict[str, list] = {}
    for node in nodes:
        windows.setdefault(node.window_name, []).append(node)

    lines = []
    for window_name, window_nodes in windows.items():
        lines.append(f'window "{window_name}"')
        for i, node in enumerate(window_nodes):
            connector = "└──" if i == len(window_nodes) - 1 else "├──"
            coords = node.center.to_string()
            role = node.control_type.lower()
            name = node.name
            action = _action_for(node.control_type)
            lines.append(f'{connector} {coords} {role} "{name}"  [action: {action}]')
        lines.append("")
    return "\n".join(lines).rstrip()


@dataclass
class TreeState:
    interactive_nodes: list[TreeElementNode] = field(default_factory=list)
    scrollable_nodes: list[ScrollElementNode] = field(default_factory=list)
    semantic_tree_root: SemanticNode | None = None
    capture_sec: float = 0.0

    def interactive_elements_to_string(self) -> str:
        if not self.interactive_nodes:
            return "No interactive elements"
        return _render_flat_tree(self.interactive_nodes)

    def scrollable_elements_to_string(self) -> str:
        if not self.scrollable_nodes:
            return "No scrollable elements"
        return _render_flat_tree(self.scrollable_nodes, scrollable=True)

    def semantic_tree_to_string(self) -> str:
        if not self.semantic_tree_root:
            return "No elements"
        lines: list[str] = []
        _render_semantic_node(self.semantic_tree_root, lines, "", is_last=True)
        return "\n".join(lines)
