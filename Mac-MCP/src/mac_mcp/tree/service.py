"""AX accessibility tree traversal — replaces Windows UIA TreeWalker."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

import mac_mcp.ax.core as ax_core
from mac_mcp.ax.controls import (
    get_element_label,
    is_interactive,
    is_scrollable,
    is_structural,
    is_visible,
)
from mac_mcp.ax.enums import AXAttr
from mac_mcp.tree.config import (
    MAX_TREE_DEPTH,
    TREE_TIMEOUT_PER_APP,
    SKIP_ROLES,
)
from mac_mcp.tree.views import (
    BoundingBox,
    TreeElementNode,
    ScrollElementNode,
    SemanticNode,
    TreeState,
    _prune_structural,
)

if TYPE_CHECKING:
    from mac_mcp.desktop.service import Desktop

logger = logging.getLogger(__name__)


class Tree:
    def __init__(self, desktop: "Desktop"):
        self._desktop = desktop
        self._element_index: dict[int, TreeElementNode] = {}
        self._label_counter = 0

    def on_focus_change(self, pid: int | None) -> None:
        logger.debug("Focus changed to PID %s", pid)

    def capture(self) -> TreeState:
        start = time.perf_counter()
        apps = ax_core.get_all_running_apps()

        interactive_nodes: list[TreeElementNode] = []
        scrollable_nodes: list[ScrollElementNode] = []
        semantic_root = SemanticNode(control_type="desktop", element_type="desktop")

        self._label_counter = 1

        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="ax-tree") as pool:
            futures = {
                pool.submit(self._capture_app, app_elem): app_elem
                for app_elem in apps
            }
            for future in as_completed(futures, timeout=10):
                try:
                    result = future.result(timeout=TREE_TIMEOUT_PER_APP)
                    if result is None:
                        continue
                    i_nodes, s_nodes, sem_nodes = result
                    interactive_nodes.extend(i_nodes)
                    scrollable_nodes.extend(s_nodes)
                    for n in sem_nodes:
                        semantic_root.add_child(n)
                except Exception:
                    logger.debug("Tree capture error for an app", exc_info=True)

        _prune_structural(semantic_root)

        self._element_index = {
            id(node): node for node in interactive_nodes
        }

        return TreeState(
            interactive_nodes=interactive_nodes,
            scrollable_nodes=scrollable_nodes,
            semantic_tree_root=semantic_root,
            capture_sec=time.perf_counter() - start,
        )

    def _capture_app(self, app_elem) -> tuple | None:
        try:
            app_name = ax_core.ax_get_attribute(app_elem, AXAttr.TITLE) or ""
            windows = ax_core.ax_get_windows(app_elem)
            if not windows:
                return None

            interactive: list[TreeElementNode] = []
            scrollable: list[ScrollElementNode] = []
            sem_nodes: list[SemanticNode] = []

            for window in windows:
                win_title = ax_core.ax_get_attribute(window, AXAttr.TITLE) or app_name
                win_node = SemanticNode(
                    control_type="AXWindow",
                    element_type="window",
                    name=win_title,
                    window_name=win_title,
                )
                self._traverse(window, interactive, scrollable, win_node, win_title, depth=0)
                if win_node.children:
                    sem_nodes.append(win_node)

            return interactive, scrollable, sem_nodes
        except Exception:
            logger.debug("Error capturing app", exc_info=True)
            return None

    def _traverse(
        self,
        element,
        interactive: list[TreeElementNode],
        scrollable: list[ScrollElementNode],
        parent_sem: SemanticNode,
        window_name: str,
        depth: int,
    ) -> None:
        if depth > MAX_TREE_DEPTH:
            return

        role = ax_core.ax_get_attribute(element, AXAttr.ROLE)
        if not role:
            return
        if role in SKIP_ROLES:
            return
        if not is_visible(element):
            return

        rect = ax_core.ax_get_rect(element)
        label = get_element_label(element)

        if rect is not None:
            bb = BoundingBox(
                left=rect.left,
                top=rect.top,
                right=rect.right,
                bottom=rect.bottom,
                width=rect.width,
                height=rect.height,
            )
            center = bb.get_center()

            if is_interactive(role):
                node = TreeElementNode(
                    bounding_box=bb,
                    center=center,
                    name=label,
                    control_type=role,
                    window_name=window_name,
                )
                interactive.append(node)
                sem_node = SemanticNode(
                    control_type=role,
                    element_type="interactive",
                    name=label,
                    window_name=window_name,
                    center=center,
                    bounding_box=bb,
                )
                parent_sem.add_child(sem_node)

            elif is_scrollable(role):
                s_node = ScrollElementNode(
                    name=label,
                    control_type=role,
                    window_name=window_name,
                    bounding_box=bb,
                    center=center,
                )
                scrollable.append(s_node)
                sem_node = SemanticNode(
                    control_type=role,
                    element_type="scrollable",
                    name=label,
                    window_name=window_name,
                    center=center,
                    bounding_box=bb,
                )
                parent_sem.add_child(sem_node)
                # Still traverse children of scrollable containers
                for child in ax_core.ax_get_children(element):
                    self._traverse(child, interactive, scrollable, sem_node, window_name, depth + 1)
                return

            elif is_structural(role) and label:
                sem_node = SemanticNode(
                    control_type=role,
                    element_type="structural",
                    name=label,
                    window_name=window_name,
                )
                parent_sem.add_child(sem_node)
                for child in ax_core.ax_get_children(element):
                    self._traverse(child, interactive, scrollable, sem_node, window_name, depth + 1)
                return

        for child in ax_core.ax_get_children(element):
            self._traverse(child, interactive, scrollable, parent_sem, window_name, depth + 1)

    def get_element_by_index(self, idx: int) -> TreeElementNode | None:
        """Get an interactive element by its position index (1-based) in the last capture."""
        return None  # Resolved via coordinate lookup in Phase 3

    def get_interactive_nodes(self) -> list[TreeElementNode]:
        return list(self._element_index.values())
