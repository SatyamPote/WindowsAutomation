# Phase 3 — Input + Window Control

**Goal:** All input tools work (`Click`, `Type`, `Scroll`, `Move`, `Shortcut`, `Wait`) and the
`App` tool works (launch, resize, switch). The agent can fully interact with the desktop.

**Prerequisite:** Phase 2 complete — `Snapshot` must work so elements have labels and coordinates.

**Status:** Not started

---

## Tasks

### 3.1 — Key Alias Table

**File:** `src/mac_mcp/desktop/service.py`

Windows-MCP has `_KEY_ALIASES` mapping user-facing names to UIA `SendKeys` format.
On Mac, `pynput` uses its own key names. Replace the alias table entirely.

```python
from pynput.keyboard import Key

_KEY_ALIASES: dict[str, Key | str] = {
    # Modifier keys
    "ctrl":        Key.ctrl,
    "control":     Key.ctrl,
    "shift":       Key.shift,
    "alt":         Key.alt,
    "option":      Key.alt,
    "cmd":         Key.cmd,
    "command":     Key.cmd,
    "windows":     Key.cmd,    # common alias from Windows users
    "meta":        Key.cmd,
    # Navigation
    "enter":       Key.enter,
    "return":      Key.enter,
    "tab":         Key.tab,
    "space":       Key.space,
    "backspace":   Key.backspace,
    "delete":      Key.delete,
    "escape":      Key.esc,
    "esc":         Key.esc,
    "up":          Key.up,
    "down":        Key.down,
    "left":        Key.left,
    "right":       Key.right,
    "home":        Key.home,
    "end":         Key.end,
    "pageup":      Key.page_up,
    "pagedown":    Key.page_down,
    # Function keys
    "f1":  Key.f1,  "f2":  Key.f2,  "f3":  Key.f3,  "f4":  Key.f4,
    "f5":  Key.f5,  "f6":  Key.f6,  "f7":  Key.f7,  "f8":  Key.f8,
    "f9":  Key.f9,  "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    # Lock keys
    "capslock":    Key.caps_lock,
    "scrolllock":  Key.scroll_lock,
    "numlock":     Key.num_lock,
    # Media
    "volumeup":    Key.media_volume_up,
    "volumedown":  Key.media_volume_down,
    "mute":        Key.media_volume_mute,
    "playpause":   Key.media_play_pause,
    "nexttrack":   Key.media_next,
    "prevtrack":   Key.media_previous,
}
```

---

### 3.2 — Keyboard Input

**File:** `src/mac_mcp/desktop/service.py` — `type_text()` and `send_shortcut()` methods

```python
from pynput.keyboard import Controller as KeyboardController, Key
import time

_keyboard = KeyboardController()

class Desktop:
    ...

    def type_text(
        self,
        text: str,
        loc: list[int] | None = None,
        clear: bool = False,
        press_enter: bool = False,
        caret_position: str = "idle",
    ) -> None:
        if loc:
            self.click(loc=loc)
            time.sleep(0.1)

        if clear:
            # Select all + delete
            with _keyboard.pressed(Key.cmd):
                _keyboard.press('a')
                _keyboard.release('a')
            time.sleep(0.05)
            _keyboard.press(Key.backspace)
            _keyboard.release(Key.backspace)
            time.sleep(0.05)

        if caret_position == "start":
            _keyboard.press(Key.home)
            _keyboard.release(Key.home)
        elif caret_position == "end":
            _keyboard.press(Key.end)
            _keyboard.release(Key.end)

        _keyboard.type(text)

        if press_enter:
            _keyboard.press(Key.enter)
            _keyboard.release(Key.enter)

    def send_shortcut(self, keys: list[str]) -> None:
        """Press a key combination, e.g. ['cmd', 'c'] for Cmd+C."""
        resolved = []
        for k in keys:
            alias = _KEY_ALIASES.get(k.lower())
            if alias is not None:
                resolved.append(alias)
            elif len(k) == 1:
                resolved.append(k)
            else:
                raise ValueError(f"Unknown key: {k!r}")

        # Press all keys, then release in reverse
        for key in resolved:
            _keyboard.press(key)
            time.sleep(0.02)
        time.sleep(0.05)
        for key in reversed(resolved):
            _keyboard.release(key)
```

---

### 3.3 — Mouse Input

**File:** `src/mac_mcp/desktop/service.py` — `click()`, `move()`, `scroll()` methods

```python
from pynput.mouse import Controller as MouseController, Button
import time

_mouse = MouseController()

class Desktop:
    ...

    def click(
        self,
        loc: list[int],
        button: str = "left",
        clicks: int = 1,
    ) -> None:
        x, y = loc[0], loc[1]
        _mouse.position = (x, y)
        time.sleep(0.05)

        if clicks == 0:
            return  # hover only

        btn = {
            "left":   Button.left,
            "right":  Button.right,
            "middle": Button.middle,
        }.get(button, Button.left)

        for _ in range(clicks):
            _mouse.press(btn)
            time.sleep(0.02)
            _mouse.release(btn)
            if clicks > 1:
                time.sleep(0.1)

    def move(self, loc: list[int]) -> None:
        _mouse.position = (loc[0], loc[1])

    def scroll(self, loc: list[int], direction: str, amount: int = 3) -> None:
        _mouse.position = (loc[0], loc[1])
        time.sleep(0.05)
        dx, dy = 0, 0
        match direction:
            case "up":    dy =  amount
            case "down":  dy = -amount
            case "left":  dx = -amount
            case "right": dx =  amount
        _mouse.scroll(dx, dy)
```

---

### 3.4 — App Launcher

**Files:**
- `src/mac_mcp/launcher/app_registry.py`
- `src/mac_mcp/launcher/detection.py`
- `src/mac_mcp/launcher/app_launcher.py`

#### `app_registry.py` — Spotlight-based app discovery

```python
import subprocess
import json
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def get_all_apps() -> dict[str, Path]:
    """Return {app_name_lower: .app bundle path} for all installed apps."""
    result = subprocess.run(
        ["mdfind", "kMDItemKind == 'Application'"],
        capture_output=True, text=True, timeout=10,
    )
    apps = {}
    for line in result.stdout.splitlines():
        p = Path(line.strip())
        if p.suffix == ".app" and p.exists():
            name = p.stem.lower()
            apps[name] = p
    return apps
```

#### `detection.py` — fuzzy name resolution

```python
from thefuzz import process as fuzzy
from mac_mcp.launcher.app_registry import get_all_apps

def find_app_path(name: str) -> tuple[str, object] | None:
    """Fuzzy-match an app name and return (matched_name, path)."""
    apps = get_all_apps()
    match, score = fuzzy.extractOne(name.lower(), list(apps.keys()))
    if score < 60:
        return None
    return match, apps[match]
```

#### `app_launcher.py` — launch / resize / switch

```python
import AppKit
import subprocess
import time
from mac_mcp.launcher.detection import find_app_path
import mac_mcp.ax.core as ax_core
from mac_mcp.ax.enums import AXAttr, AXAction

class AppLauncher:
    @staticmethod
    def launch(name: str) -> str:
        match = find_app_path(name)
        if match is None:
            return f"App not found: {name!r}"
        _, path = match
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        url = AppKit.NSURL.fileURLWithPath_(str(path))
        config = AppKit.NSWorkspaceOpenConfiguration.configuration()
        workspace.openApplicationAtURL_configuration_completionHandler_(url, config, None)
        time.sleep(1.5)
        return f"Launched {path.stem}"

    @staticmethod
    def switch(name: str) -> str:
        apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
        for app in apps:
            if name.lower() in (app.localizedName() or "").lower():
                app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
                return f"Switched to {app.localizedName()}"
        return f"No running app found matching: {name!r}"

    @staticmethod
    def resize(name: str | None, loc: list[int] | None, size: list[int] | None) -> str:
        # Get target window AXElement
        if name:
            apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
            for app in apps:
                if name.lower() in (app.localizedName() or "").lower():
                    app_elem = ax_core.get_frontmost_app()  # or by PID
                    windows = ax_core.ax_get_windows(app_elem)
                    if windows:
                        win = windows[0]
                        if loc:
                            import ApplicationServices as AS
                            import CoreGraphics as CG
                            pt = CG.CGPointMake(loc[0], loc[1])
                            val = AS.AXValueCreate(AS.kAXValueCGPointType, pt)
                            AS.AXUIElementSetAttributeValue(win, AXAttr.POSITION, val)
                        if size:
                            sz = CG.CGSizeMake(size[0], size[1])
                            val = AS.AXValueCreate(AS.kAXValueCGSizeType, sz)
                            AS.AXUIElementSetAttributeValue(win, AXAttr.SIZE, val)
                        return f"Resized {app.localizedName()} window"
        return "Window not found"
```

---

### 3.5 — Desktop Service: App Method

**File:** `src/mac_mcp/desktop/service.py` — add `app()` method

```python
from mac_mcp.launcher.app_launcher import AppLauncher

class Desktop:
    ...

    def app(
        self,
        mode: str = "launch",
        name: str | None = None,
        window_loc: list[int] | None = None,
        window_size: list[int] | None = None,
    ) -> str:
        match mode:
            case "launch":
                return AppLauncher.launch(name or "")
            case "switch":
                return AppLauncher.switch(name or "")
            case "resize":
                return AppLauncher.resize(name, window_loc, window_size)
            case _:
                return f"Unknown mode: {mode}"
```

---

### 3.6 — Port Input Tools

**File:** `src/mac_mcp/tools/input.py`

Port from Windows-MCP `tools/input.py`. No structural changes — just update imports
(`windows_mcp` → `mac_mcp`) and the `_resolve_label` function stays identical.

Tools registered: `Click`, `Type`, `Scroll`, `Move`, `Shortcut`, `Wait`.

Key change — `Type` tool `caret_position` parameter:
- Windows had `"start"` → `Home` key via UIA
- Mac: `"start"` → `Cmd+Left` (line start) or `Cmd+Up` (document start)
- Use `Cmd+Home` as cross-app "go to start" equivalent

---

### 3.7 — Port App Tool

**File:** `src/mac_mcp/tools/app.py`

Port from Windows-MCP `tools/app.py`. Update import only, interface unchanged.

---

### 3.8 — Register New Tools

**File:** `src/mac_mcp/tools/__init__.py`

```python
from mac_mcp.tools import shell, snapshot, input, app

_MODULES = [shell, snapshot, input, app]

def register_all(mcp, *, get_desktop, get_analytics):
    for mod in _MODULES:
        mod.register(mcp, get_desktop=get_desktop, get_analytics=get_analytics)
```

---

## Completion Criteria

- [ ] `App` tool launches Safari, Chrome, Finder, Terminal by name
- [ ] `App` tool switches focus to a running app by name
- [ ] `App` tool resizes a window to given location and size
- [ ] `Click` tool clicks at coordinates — verified by cursor position
- [ ] `Click` tool resolves element labels from Snapshot and clicks center of bounding box
- [ ] `Type` tool types text into an active text field
- [ ] `Type` tool with `clear=True` clears existing text before typing
- [ ] `Scroll` tool scrolls up/down in a browser page
- [ ] `Move` tool moves mouse cursor to coordinates
- [ ] `Shortcut` tool executes `['cmd', 'c']` (copy) and `['cmd', 'v']` (paste)
- [ ] `Wait` tool pauses for the given duration
- [ ] `ruff check .` passes
