# Phase 2 — AX Layer + UI Tree

**Goal:** The `Snapshot` tool works — full macOS Accessibility tree extraction with annotated
screenshot and UI element list. This is the core intelligence layer that all interaction tools
depend on.

**Prerequisite:** Phase 1 complete.

**Status:** Not started

---

## Background: AX vs UIA

Windows UIAutomation has a C++ in-process `TreeWalker`. macOS AX calls cross the process
boundary via Mach IPC — expect 2–5× slower traversal. Mitigate with:
- Depth limit (default 8)
- `ThreadPoolExecutor` per top-level window (same pattern as Windows-MCP)
- Aggressive caching of `AXUIElement` refs between snapshots

---

## Tasks

### 2.1 — AX Enums

**File:** `src/mac_mcp/ax/enums.py`

Define AX role, attribute, and action name constants.
These are string constants from the macOS AX API — no COM enums involved.

```python
# AX Roles (subset of kAXRole* constants)
class AXRole:
    APPLICATION         = "AXApplication"
    WINDOW              = "AXWindow"
    BUTTON              = "AXButton"
    TEXT_FIELD          = "AXTextField"
    TEXT_AREA           = "AXTextArea"
    STATIC_TEXT         = "AXStaticText"
    CHECK_BOX           = "AXCheckBox"
    RADIO_BUTTON        = "AXRadioButton"
    COMBO_BOX           = "AXComboBox"
    POP_UP_BUTTON       = "AXPopUpButton"
    MENU                = "AXMenu"
    MENU_ITEM           = "AXMenuItem"
    MENU_BAR            = "AXMenuBar"
    LIST                = "AXList"
    LIST_ITEM           = "AXCell"         # AXCell inside AXList/AXTable
    TABLE               = "AXTable"
    ROW                 = "AXRow"
    SCROLL_AREA         = "AXScrollArea"
    SCROLL_BAR          = "AXScrollBar"
    SLIDER              = "AXSlider"
    TAB_GROUP           = "AXTabGroup"
    TAB                 = "AXRadioButton"  # tabs are AXRadioButton inside AXTabGroup
    TOOL_BAR            = "AXToolbar"
    GROUP               = "AXGroup"
    SPLIT_GROUP         = "AXSplitGroup"
    IMAGE               = "AXImage"
    LINK                = "AXLink"
    UNKNOWN             = "AXUnknown"
    WEB_AREA            = "AXWebArea"
    GENERIC             = "AXGenericElement"

# AX Attributes
class AXAttr:
    ROLE                = "AXRole"
    SUBROLE             = "AXSubrole"
    TITLE               = "AXTitle"
    VALUE               = "AXValue"
    DESCRIPTION         = "AXDescription"
    HELP                = "AXHelp"
    PLACEHOLDER         = "AXPlaceholderValue"
    CHILDREN            = "AXChildren"
    PARENT              = "AXParent"
    WINDOWS             = "AXWindows"
    FOCUSED_WINDOW      = "AXFocusedWindow"
    FOCUSED_ELEMENT     = "AXFocusedUIElement"
    POSITION            = "AXPosition"
    SIZE                = "AXSize"
    FRAME               = "AXFrame"
    ENABLED             = "AXEnabled"
    FOCUSED             = "AXFocused"
    SELECTED            = "AXSelected"
    VISIBLE             = "AXVisible"
    HIDDEN              = "AXHidden"
    MINIMIZED           = "AXMinimized"
    MAIN                = "AXMain"
    DOCUMENT            = "AXDocument"
    URL                 = "AXURL"
    SELECTED_TEXT       = "AXSelectedText"
    NUMBER_OF_CHARS     = "AXNumberOfCharacters"
    ROWS                = "AXRows"
    COLUMNS             = "AXColumns"
    SELECTED_ROWS       = "AXSelectedRows"
    VERTICAL_SCROLL_BAR = "AXVerticalScrollBar"
    SCROLL_POSITION     = "AXScrollPosition"
    CONTENTS            = "AXContents"

# AX Actions
class AXAction:
    PRESS               = "AXPress"
    PICK                = "AXPick"
    CONFIRM             = "AXConfirm"
    CANCEL              = "AXCancel"
    SHOW_MENU           = "AXShowMenu"
    SHOW_MENU_BY_INDEX  = "AXShowMenuByIndex"
    DECREMENT           = "AXDecrement"
    INCREMENT           = "AXIncrement"
    RAISE               = "AXRaise"

# AX Notification names (used by AXObserver)
class AXNotification:
    FOCUSED_UI_ELEMENT_CHANGED  = "AXFocusedUIElementChanged"
    APPLICATION_ACTIVATED       = "AXApplicationActivated"
    APPLICATION_DEACTIVATED     = "AXApplicationDeactivated"
    WINDOW_CREATED              = "AXWindowCreated"
    WINDOW_MOVED                = "AXWindowMoved"
    WINDOW_RESIZED              = "AXWindowResized"
    VALUE_CHANGED               = "AXValueChanged"
    SELECTED_TEXT_CHANGED       = "AXSelectedTextChanged"
```

---

### 2.2 — AX Core

**File:** `src/mac_mcp/ax/core.py`

Thin wrapper over `ApplicationServices` + `AppKit`. All coordinate work uses macOS screen
coordinates (origin at bottom-left on macOS, convert to top-left for tool output).

```python
import ApplicationServices as AS
import AppKit
from dataclasses import dataclass
from mac_mcp.desktop.screenshot import Rect

# --- Rect helpers ---

def get_screen_size() -> tuple[int, int]:
    frame = AppKit.NSScreen.mainScreen().frame()
    return int(frame.size.width), int(frame.size.height)

def get_virtual_screen_rect() -> Rect:
    """Union of all monitor rects (top-left origin)."""
    screens = AppKit.NSScreen.screens()
    min_x = min(int(s.frame().origin.x) for s in screens)
    min_y = min(int(s.frame().origin.y) for s in screens)
    max_x = max(int(s.frame().origin.x + s.frame().size.width) for s in screens)
    max_y = max(int(s.frame().origin.y + s.frame().size.height) for s in screens)
    return Rect(left=min_x, top=min_y, right=max_x, bottom=max_y)

def get_monitors_rect() -> list[Rect]:
    return [
        Rect(
            left=int(s.frame().origin.x),
            top=int(s.frame().origin.y),
            right=int(s.frame().origin.x + s.frame().size.width),
            bottom=int(s.frame().origin.y + s.frame().size.height),
        )
        for s in AppKit.NSScreen.screens()
    ]

# --- App / window access ---

def get_frontmost_app():
    """Return AXUIElement for the frontmost application."""
    app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return AS.AXUIElementCreateApplication(app.processIdentifier())

def get_all_running_apps() -> list:
    """Return AXUIElement for each running app with windows."""
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    return [
        AS.AXUIElementCreateApplication(app.processIdentifier())
        for app in apps
        if app.activationPolicy() == AppKit.NSApplicationActivationPolicyRegular
    ]

# --- Attribute access ---

def ax_get_attribute(element, attribute: str):
    """Read an AX attribute value, return None on error."""
    err, value = AS.AXUIElementCopyAttributeValue(element, attribute, None)
    return value if err == AS.kAXErrorSuccess else None

def ax_get_children(element) -> list:
    children = ax_get_attribute(element, "AXChildren")
    return list(children) if children else []

def ax_get_windows(app_element) -> list:
    windows = ax_get_attribute(app_element, "AXWindows")
    return list(windows) if windows else []

def ax_get_position(element) -> tuple[int, int] | None:
    pos = ax_get_attribute(element, "AXPosition")
    if pos is None:
        return None
    pt = AS.AXValueGetValue(pos, AS.kAXValueCGPointType, None)
    return int(pt.x), int(pt.y) if pt else None

def ax_get_size(element) -> tuple[int, int] | None:
    sz = ax_get_attribute(element, "AXSize")
    if sz is None:
        return None
    size = AS.AXValueGetValue(sz, AS.kAXValueCGSizeType, None)
    return int(size.width), int(size.height) if size else None

def ax_get_rect(element) -> Rect | None:
    pos = ax_get_position(element)
    sz = ax_get_size(element)
    if pos is None or sz is None:
        return None
    x, y = pos
    w, h = sz
    screen_h = get_screen_size()[1]
    # Convert macOS bottom-left origin → top-left origin
    top = screen_h - y - h
    return Rect(left=x, top=top, right=x + w, bottom=top + h)

# --- Actions ---

def ax_perform_action(element, action: str) -> bool:
    err = AS.AXUIElementPerformAction(element, action)
    return err == AS.kAXErrorSuccess
```

---

### 2.3 — AX Controls

**File:** `src/mac_mcp/ax/controls.py`

Role-specific helpers — which roles are interactive, which are scrollable, label resolution.

```python
from mac_mcp.ax.enums import AXRole
from mac_mcp.ax.core import ax_get_attribute

INTERACTIVE_ROLES = {
    AXRole.BUTTON, AXRole.CHECK_BOX, AXRole.RADIO_BUTTON,
    AXRole.TEXT_FIELD, AXRole.TEXT_AREA, AXRole.COMBO_BOX,
    AXRole.POP_UP_BUTTON, AXRole.MENU_ITEM, AXRole.LIST_ITEM,
    AXRole.SLIDER, AXRole.TAB, AXRole.LINK,
}

SCROLLABLE_ROLES = {
    AXRole.SCROLL_AREA, AXRole.LIST, AXRole.TABLE,
    AXRole.TEXT_AREA,
}

def get_element_label(element) -> str:
    """Best human-readable label for an element."""
    for attr in ("AXTitle", "AXValue", "AXDescription", "AXPlaceholderValue", "AXHelp"):
        val = ax_get_attribute(element, attr)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ""

def is_interactive(role: str) -> bool:
    return role in INTERACTIVE_ROLES

def is_scrollable(role: str) -> bool:
    return role in SCROLLABLE_ROLES

def is_visible(element) -> bool:
    hidden = ax_get_attribute(element, "AXHidden")
    return not hidden
```

---

### 2.4 — AX Events

**File:** `src/mac_mcp/ax/events.py`

`AXObserver` wraps the macOS accessibility notification system. Equivalent to Windows
`UIAutomationFocusChangedEventHandler`.

```python
import ApplicationServices as AS
import AppKit
import threading
import logging

logger = logging.getLogger(__name__)

class FocusObserver:
    """Monitors system-wide focus changes via AXObserver."""

    def __init__(self, callback):
        self._callback = callback
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="ax-focus-observer")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        # Poll frontmost app PID and watch for focus change notifications
        # AXObserver requires a CFRunLoop — run it on this dedicated thread
        import CoreFoundation as CF
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        current_pid = None

        while self._running:
            app = workspace.frontmostApplication()
            pid = app.processIdentifier() if app else None
            if pid != current_pid:
                current_pid = pid
                try:
                    self._callback(pid)
                except Exception:
                    logger.exception("Error in focus callback")
            CF.CFRunLoopRunInMode(CF.kCFRunLoopDefaultMode, 0.25, False)
```

---

### 2.5 — Tree Config

**File:** `src/mac_mcp/tree/config.py`

Replaces Windows `tree/config.py` (UIA control types → AX roles).

```python
from mac_mcp.ax.enums import AXRole
from mac_mcp.ax.controls import INTERACTIVE_ROLES, SCROLLABLE_ROLES

MAX_TREE_DEPTH = 8
THREAD_MAX_RETRIES = 3

# Roles that should always be expanded (never treated as leaf)
ALWAYS_EXPAND_ROLES = {
    AXRole.APPLICATION, AXRole.WINDOW, AXRole.GROUP,
    AXRole.SPLIT_GROUP, AXRole.TOOL_BAR, AXRole.SCROLL_AREA,
    AXRole.TAB_GROUP, AXRole.LIST, AXRole.TABLE,
}

# Roles that are never worth including in the element tree
SKIP_ROLES = {
    AXRole.UNKNOWN, AXRole.GENERIC,
}
```

---

### 2.6 — Tree Views

**File:** `src/mac_mcp/tree/views.py`

Copy from Windows-MCP `tree/views.py` verbatim — data models are platform-agnostic.
`TreeElementNode`, `ScrollElementNode`, `TreeState`, `BoundingBox` stay unchanged.

---

### 2.7 — Tree Service

**File:** `src/mac_mcp/tree/service.py`

Replaces Windows `tree/service.py`. Uses `ThreadPoolExecutor` per window and recursive AX
traversal instead of UIA `TreeWalker`.

```python
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from mac_mcp.ax import core as ax
from mac_mcp.ax.controls import (
    get_element_label, is_interactive, is_scrollable, is_visible
)
from mac_mcp.ax.enums import AXRole, AXAttr
from mac_mcp.tree.config import MAX_TREE_DEPTH, THREAD_MAX_RETRIES, ALWAYS_EXPAND_ROLES, SKIP_ROLES
from mac_mcp.tree.views import TreeElementNode, ScrollElementNode, TreeState, BoundingBox

logger = logging.getLogger(__name__)

class Tree:
    def __init__(self, desktop):
        self._desktop = desktop
        self._element_index: dict[int, TreeElementNode] = {}
        self._state: TreeState | None = None

    def on_focus_change(self, pid: int | None) -> None:
        logger.debug("Focus changed to PID %s", pid)

    def capture(self) -> TreeState:
        apps = ax.get_all_running_apps()
        all_elements: list[TreeElementNode] = []
        all_scrollable: list[ScrollElementNode] = []
        label_counter = 1

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(self._capture_app, app_elem): app_elem
                for app_elem in apps
            }
            for future in as_completed(futures, timeout=10):
                try:
                    elements, scrollable = future.result(timeout=5)
                    # Assign sequential labels
                    for el in elements:
                        el.label = label_counter
                        label_counter += 1
                    all_elements.extend(elements)
                    all_scrollable.extend(scrollable)
                except TimeoutError:
                    logger.warning("Tree capture timed out for an app")
                except Exception:
                    logger.exception("Tree capture error")

        self._element_index = {el.label: el for el in all_elements}
        self._state = TreeState(elements=all_elements, scrollable=all_scrollable)
        return self._state

    def _capture_app(self, app_elem) -> tuple[list, list]:
        elements, scrollable = [], []
        for window in ax.ax_get_windows(app_elem):
            self._traverse(window, elements, scrollable, depth=0)
        return elements, scrollable

    def _traverse(self, element, elements, scrollable, depth: int) -> None:
        if depth > MAX_TREE_DEPTH:
            return

        role = ax.ax_get_attribute(element, AXAttr.ROLE) or ""
        if role in SKIP_ROLES:
            return
        if not is_visible(element):
            return

        rect = ax.ax_get_rect(element)
        if rect is None:
            return

        label = get_element_label(element)

        if is_interactive(role):
            elements.append(TreeElementNode(
                label=0,  # assigned later
                role=role,
                name=label,
                bounding_box=BoundingBox(
                    x=rect.left, y=rect.top,
                    width=rect.right - rect.left,
                    height=rect.bottom - rect.top,
                ),
            ))

        if is_scrollable(role):
            scrollable.append(ScrollElementNode(
                role=role,
                name=label,
                bounding_box=BoundingBox(
                    x=rect.left, y=rect.top,
                    width=rect.right - rect.left,
                    height=rect.bottom - rect.top,
                ),
            ))

        for child in ax.ax_get_children(element):
            self._traverse(child, elements, scrollable, depth + 1)

    def get_element_by_label(self, label: int) -> TreeElementNode | None:
        return self._element_index.get(label)
```

---

### 2.8 — Watchdog Service

**File:** `src/mac_mcp/watchdog/service.py`

Replaces Windows `watchdog/service.py`. Uses `FocusObserver` from `ax/events.py`.

```python
import logging
from mac_mcp.ax.events import FocusObserver

logger = logging.getLogger(__name__)

class WatchDog:
    def __init__(self):
        self._observer: FocusObserver | None = None
        self._focus_callback = None

    def set_focus_callback(self, callback) -> None:
        self._focus_callback = callback

    def start(self) -> None:
        self._observer = FocusObserver(callback=self._focus_callback or (lambda pid: None))
        self._observer.start()
        logger.debug("WatchDog started")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
        logger.debug("WatchDog stopped")
```

---

### 2.9 — Desktop Service: Snapshot Integration

**File:** `src/mac_mcp/desktop/service.py` — extend Phase 1 stub

Add `get_state()` which combines screenshot + tree capture. This is what `Snapshot` tool calls.

```python
from mac_mcp.tree.service import Tree
from mac_mcp.desktop.views import DesktopState, Window, Size
import mac_mcp.ax.core as ax

class Desktop:
    def __init__(self):
        self.desktop_state = None
        self.tree = Tree(self)     # add tree

    def get_screen_size(self) -> Size: ...          # unchanged from Phase 1

    def screenshot(self, scale=1.0): ...            # unchanged from Phase 1

    def get_state(self, use_annotation=True, use_vision=False, use_ui_tree=True,
                  as_bytes=False, scale=1.0, ...) -> DesktopState:
        image, backend = self.screenshot(scale=scale)
        tree_state = self.tree.capture() if use_ui_tree else None
        # annotate image with element labels if use_annotation
        # build DesktopState from image + tree_state
        ...

    def get_coordinates_from_label(self, label: int) -> tuple[int, int]:
        el = self.tree.get_element_by_label(label)
        if el is None:
            raise ValueError(f"No element with label {label}")
        bb = el.bounding_box
        return bb.x + bb.width // 2, bb.y + bb.height // 2
```

---

### 2.10 — Snapshot Tool

**Files:**
- `src/mac_mcp/tools/_snapshot_helpers.py` — port from Windows-MCP, update env var names
- `src/mac_mcp/tools/snapshot.py` — port from Windows-MCP, no structural changes

Update `_snapshot_helpers.py`:
- `WINDOWS_MCP_SCREENSHOT_SCALE` → `MAC_MCP_SCREENSHOT_SCALE`
- `WINDOWS_MCP_PROFILE_SNAPSHOT` → `MAC_MCP_PROFILE_SNAPSHOT`
- `WINDOWS_MCP_SCREENSHOT_BACKEND` → `MAC_MCP_SCREENSHOT_BACKEND`

Register snapshot in `tools/__init__.py`.

---

### 2.11 — Wire Watchdog into Lifespan

**File:** `src/mac_mcp/__main__.py` — update lifespan:

```python
from mac_mcp.watchdog.service import WatchDog

@asynccontextmanager
async def lifespan(app):
    global desktop, analytics, watchdog
    permissions.check_and_warn()
    ...
    desktop = Desktop()
    watchdog = WatchDog()
    watchdog.set_focus_callback(desktop.tree.on_focus_change)
    watchdog.start()
    try:
        yield
    finally:
        watchdog.stop()
        if analytics:
            await analytics.close()
```

---

## Completion Criteria

- [ ] `Snapshot` tool returns annotated screenshot with numbered element labels
- [ ] `Snapshot` tool returns UI tree listing interactive elements (buttons, text fields, etc.)
- [ ] Tree traversal completes within 5 seconds for a typical app (browser, Finder)
- [ ] WatchDog starts and stops cleanly with the server lifecycle
- [ ] AX attribute reads handle errors gracefully (no crash on protected apps)
- [ ] `ruff check .` passes
