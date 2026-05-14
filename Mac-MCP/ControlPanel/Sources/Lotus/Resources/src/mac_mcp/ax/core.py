"""macOS Accessibility API wrapper — replaces uia/core.py."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import ApplicationServices as AS
    _AX_AVAILABLE = True
except ImportError:
    AS = None
    _AX_AVAILABLE = False

try:
    import AppKit
    _APPKIT_AVAILABLE = True
except ImportError:
    AppKit = None
    _APPKIT_AVAILABLE = False


@dataclass
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


# ---------------------------------------------------------------------------
# Screen geometry
# ---------------------------------------------------------------------------

def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary screen in logical points."""
    if _APPKIT_AVAILABLE:
        frame = AppKit.NSScreen.mainScreen().frame()
        return int(frame.size.width), int(frame.size.height)
    return 1920, 1080


def get_virtual_screen_rect() -> Rect:
    """Union rect of all monitors in logical points (top-left origin)."""
    if not _APPKIT_AVAILABLE:
        w, h = get_screen_size()
        return Rect(0, 0, w, h)
    screens = AppKit.NSScreen.screens()
    screen_h = get_screen_size()[1]
    rects = []
    for s in screens:
        f = s.frame()
        # NSScreen uses bottom-left origin; convert to top-left
        x = int(f.origin.x)
        y = int(screen_h - f.origin.y - f.size.height)
        rects.append(Rect(x, y, x + int(f.size.width), y + int(f.size.height)))
    return Rect(
        left=min(r.left for r in rects),
        top=min(r.top for r in rects),
        right=max(r.right for r in rects),
        bottom=max(r.bottom for r in rects),
    )


def get_monitors_rect() -> list[Rect]:
    if not _APPKIT_AVAILABLE:
        w, h = get_screen_size()
        return [Rect(0, 0, w, h)]
    screens = AppKit.NSScreen.screens()
    screen_h = get_screen_size()[1]
    result = []
    for s in screens:
        f = s.frame()
        x = int(f.origin.x)
        y = int(screen_h - f.origin.y - f.size.height)
        result.append(Rect(x, y, x + int(f.size.width), y + int(f.size.height)))
    return result


# ---------------------------------------------------------------------------
# Attribute access
# ---------------------------------------------------------------------------

def ax_get_attribute(element, attribute: str):
    """Read a single AX attribute. Returns None on any error."""
    if not _AX_AVAILABLE or element is None:
        return None
    try:
        err, value = AS.AXUIElementCopyAttributeValue(element, attribute, None)
        if err == AS.kAXErrorSuccess:
            return value
    except Exception:
        pass
    return None


def ax_get_children(element) -> list:
    children = ax_get_attribute(element, "AXChildren")
    if children is None:
        return []
    try:
        return list(children)
    except Exception:
        return []


def ax_get_windows(app_element) -> list:
    windows = ax_get_attribute(app_element, "AXWindows")
    if windows is None:
        return []
    try:
        return list(windows)
    except Exception:
        return []


def ax_get_position(element) -> tuple[int, int] | None:
    """Return (x, y) in top-left screen coordinates."""
    if not _AX_AVAILABLE:
        return None
    pos_val = ax_get_attribute(element, "AXPosition")
    if pos_val is None:
        return None
    try:
        ok, pt = AS.AXValueGetValue(pos_val, AS.kAXValueCGPointType, None)
        if ok:
            return int(pt.x), int(pt.y)
    except Exception:
        pass
    return None


def ax_get_size(element) -> tuple[int, int] | None:
    if not _AX_AVAILABLE:
        return None
    sz_val = ax_get_attribute(element, "AXSize")
    if sz_val is None:
        return None
    try:
        ok, sz = AS.AXValueGetValue(sz_val, AS.kAXValueCGSizeType, None)
        if ok:
            return int(sz.width), int(sz.height)
    except Exception:
        pass
    return None


def ax_get_rect(element) -> Rect | None:
    """Return bounding rect in top-left screen coordinates."""
    pos = ax_get_position(element)
    sz = ax_get_size(element)
    if pos is None or sz is None:
        return None
    x, y = pos
    w, h = sz
    if w <= 0 or h <= 0:
        return None
    return Rect(left=x, top=y, right=x + w, bottom=y + h)


# ---------------------------------------------------------------------------
# App / window access
# ---------------------------------------------------------------------------

def get_frontmost_app():
    """Return AXUIElement for the frontmost application."""
    if not _AX_AVAILABLE or not _APPKIT_AVAILABLE:
        return None
    try:
        app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        return AS.AXUIElementCreateApplication(app.processIdentifier())
    except Exception:
        return None


def get_all_running_apps() -> list:
    """Return AXUIElement for each regular (non-background) running app."""
    if not _AX_AVAILABLE or not _APPKIT_AVAILABLE:
        return []
    try:
        apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
        result = []
        for app in apps:
            try:
                if app.activationPolicy() == AppKit.NSApplicationActivationPolicyRegular:
                    result.append(AS.AXUIElementCreateApplication(app.processIdentifier()))
            except Exception:
                continue
        return result
    except Exception:
        return []


def get_frontmost_app_info() -> dict | None:
    """Return {name, pid} of the frontmost app."""
    if not _APPKIT_AVAILABLE:
        return None
    try:
        app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        return {
            "name": app.localizedName() or "",
            "pid": app.processIdentifier(),
        }
    except Exception:
        return None


def get_cursor_position() -> tuple[int, int] | None:
    """Return (x, y) cursor position in top-left screen coordinates."""
    try:
        import AppKit as _AppKit
        loc = _AppKit.NSEvent.mouseLocation()
        screen_h = get_screen_size()[1]
        return int(loc.x), int(screen_h - loc.y)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def ax_perform_action(element, action: str) -> bool:
    if not _AX_AVAILABLE or element is None:
        return False
    try:
        err = AS.AXUIElementPerformAction(element, action)
        return err == AS.kAXErrorSuccess
    except Exception:
        return False
