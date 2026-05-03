"""Launch, switch, and resize macOS applications."""

import logging
import subprocess
import time

import mac_mcp.ax.core as ax_core
from mac_mcp.launcher.detection import find_app

logger = logging.getLogger(__name__)


def launch(name: str) -> str:
    match = find_app(name)
    if match is None:
        return f"App not found: {name!r}. Try a different name."
    _, path = match
    result = subprocess.run(
        ["open", "-a", str(path)],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        return f"Failed to launch {path.stem}: {result.stderr.strip()}"
    time.sleep(1.5)
    return f"Launched {path.stem}"


def switch(name: str) -> str:
    try:
        import AppKit
    except ImportError:
        return "AppKit not available"

    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    name_lower = name.lower()
    for app in apps:
        app_name = (app.localizedName() or "").lower()
        if name_lower in app_name or app_name in name_lower:
            app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            time.sleep(0.3)
            return f"Switched to {app.localizedName()}"
    return f"No running app found matching: {name!r}"


def resize(name: str | None, loc: list[int] | None, size: list[int] | None) -> str:
    try:
        import AppKit
        import ApplicationServices as AS
        import Quartz
    except ImportError:
        return "Required frameworks not available"

    # Find target app element
    if name:
        apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
        name_lower = name.lower()
        target_pid = None
        for app in apps:
            if name_lower in (app.localizedName() or "").lower():
                target_pid = app.processIdentifier()
                break
        if target_pid is None:
            return f"No running app found matching: {name!r}"
        app_elem = AS.AXUIElementCreateApplication(target_pid)
    else:
        app_elem = ax_core.get_frontmost_app()

    if app_elem is None:
        return "No target app found"

    windows = ax_core.ax_get_windows(app_elem)
    if not windows:
        return "No windows found for target app"

    win = windows[0]
    msgs = []

    if loc and len(loc) == 2:
        try:
            pt = Quartz.CGPointMake(float(loc[0]), float(loc[1]))
            val = AS.AXValueCreate(AS.kAXValueCGPointType, pt)
            AS.AXUIElementSetAttributeValue(win, "AXPosition", val)
            msgs.append(f"moved to ({loc[0]},{loc[1]})")
        except Exception as e:
            msgs.append(f"position failed: {e}")

    if size and len(size) == 2:
        try:
            sz = Quartz.CGSizeMake(float(size[0]), float(size[1]))
            val = AS.AXValueCreate(AS.kAXValueCGSizeType, sz)
            AS.AXUIElementSetAttributeValue(win, "AXSize", val)
            msgs.append(f"resized to {size[0]}×{size[1]}")
        except Exception as e:
            msgs.append(f"size failed: {e}")

    return f"Window {', '.join(msgs)}" if msgs else "Nothing to do"
