# Phase 4 — Remaining Tools

**Goal:** Full tool parity with Windows-MCP. All 16 tools functional.

**Prerequisite:** Phase 3 complete.

**Status:** Not started

---

## Tool Inventory

| Tool | Source file | Effort | Notes |
|---|---|---|---|
| `Filesystem` | `tools/filesystem.py` | None | os/pathlib — copy verbatim |
| `Clipboard` | `tools/clipboard.py` | None | pyperclip — copy verbatim |
| `Process` | `tools/process.py` | None | psutil — copy verbatim |
| `Wait` | `tools/input.py` | None | Already in Phase 3 |
| `Scrape` | `tools/scrape.py` | None | playwright — copy verbatim |
| `Notification` | `tools/notification.py` | Low | osascript replace |
| `Shell` | `tools/shell.py` | Low | Done in Phase 1 |
| `Defaults` | `tools/defaults.py` | Low | Replaces Registry tool |
| `Browser` | `tools/browser.py` | Low | Update process name detection |
| `FileManager` | `tools/fm.py` | Low | Update macOS paths |
| `MultiSelect` | `tools/multi.py` | Medium | AX multi-element selection |
| `MultiEdit` | `tools/multi.py` | Medium | AX multi-element editing |

---

## Tasks

### 4.1 — Zero-change Tools (copy verbatim, update imports only)

These tools have no Windows-specific code. Copy from Windows-MCP and replace all
`windows_mcp` imports with `mac_mcp`.

**`src/mac_mcp/tools/filesystem.py`**
- Tools: `Filesystem`
- Uses: `os`, `pathlib`, `shutil` — fully cross-platform
- No changes beyond import namespace

**`src/mac_mcp/tools/clipboard.py`**
- Tools: `Clipboard`
- Uses: `pyperclip` — uses `pbcopy`/`pbpaste` on macOS automatically
- No changes beyond import namespace

**`src/mac_mcp/tools/process.py`**
- Tools: `Process`
- Uses: `psutil` — cross-platform
- No changes beyond import namespace

**`src/mac_mcp/tools/scrape.py`**
- Tools: `Scrape`
- Uses: `playwright` — cross-platform
- No changes beyond import namespace

---

### 4.2 — Notification Tool

**File:** `src/mac_mcp/tools/notification.py`

Windows-MCP used Windows toast notifications via `win32api` or `plyer`.
Replace with `osascript`.

```python
from mac_mcp.desktop.shell import AppleScriptExecutor
from mac_mcp.analytics import with_analytics
from fastmcp import Context
from mcp.types import ToolAnnotations

def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Notification",
        description=(
            "Show a macOS notification or dialog. Keywords: notify, alert, message, popup, toast. "
            "Use mode='notification' for a banner notification (non-blocking). "
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
        mode: str = "notification",
        ctx: Context = None,
    ) -> str:
        if mode == "dialog":
            script = f'display dialog "{message}" with title "{title}" buttons {{"OK"}}'
        else:
            script = f'display notification "{message}" with title "{title}"'

        _, code = AppleScriptExecutor.execute(script)
        if code != 0:
            return f"Notification failed (exit {code}). Check Automation permission."
        return f"Notification sent: {title} — {message}"
```

---

### 4.3 — Defaults Tool (replaces Registry)

**File:** `src/mac_mcp/tools/defaults.py`

Replaces `tools/registry.py`. macOS stores app preferences as plist files under
`~/Library/Preferences/`. The `defaults` CLI reads/writes them.

```python
import subprocess
from mac_mcp.analytics import with_analytics
from fastmcp import Context
from mcp.types import ToolAnnotations
from typing import Literal

def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Defaults",
        description=(
            "Read or write macOS user defaults (app preferences). "
            "Keywords: defaults, preferences, plist, settings, app config. "
            "Equivalent to the macOS 'defaults' command. "
            "Use read to query a preference, write to set one, delete to remove one."
        ),
        annotations=ToolAnnotations(
            title="Defaults",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Defaults-Tool")
    def defaults_tool(
        action: Literal["read", "write", "delete", "read-all"],
        domain: str,
        key: str | None = None,
        value: str | None = None,
        value_type: Literal["string", "int", "float", "bool", "array", "dict"] = "string",
        ctx: Context = None,
    ) -> str:
        match action:
            case "read":
                cmd = ["defaults", "read", domain] + ([key] if key else [])
            case "read-all":
                cmd = ["defaults", "read", domain]
            case "write":
                if key is None or value is None:
                    return "Error: key and value required for write"
                type_flag = {
                    "string": "-string", "int": "-integer", "float": "-float",
                    "bool": "-bool", "array": "-array", "dict": "-dict",
                }.get(value_type, "-string")
                cmd = ["defaults", "write", domain, key, type_flag, value]
            case "delete":
                cmd = ["defaults", "delete", domain] + ([key] if key else [])
            case _:
                return f"Unknown action: {action}"

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = (result.stdout + result.stderr).strip()
        return f"{output}\nExit code: {result.returncode}"
```

---

### 4.4 — Browser Tool

**File:** `src/mac_mcp/tools/browser.py`

Port from Windows-MCP `tools/browser.py`. Update process name detection — macOS uses
different executable names than Windows `.exe` files.

**Process name mapping:**

| Browser | Windows process | macOS process |
|---|---|---|
| Chrome | `chrome.exe` | `Google Chrome` |
| Edge | `msedge.exe` | `Microsoft Edge` |
| Firefox | `firefox.exe` | `firefox` |
| Safari | *(not on Windows)* | `Safari` |
| Arc | *(not on Windows)* | `Arc` |
| Brave | *(Windows: `brave.exe`)* | `Brave Browser` |

```python
BROWSER_PROCESS_NAMES = {
    "chrome":   "Google Chrome",
    "edge":     "Microsoft Edge",
    "firefox":  "firefox",
    "safari":   "Safari",
    "arc":      "Arc",
    "brave":    "Brave Browser",
}

def detect_active_browser() -> str | None:
    """Return browser name if the frontmost app is a known browser."""
    import AppKit
    app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return None
    name = app.localizedName() or ""
    for browser, proc_name in BROWSER_PROCESS_NAMES.items():
        if proc_name.lower() in name.lower():
            return browser
    return None
```

**Safari note:** playwright does not support Safari. When Safari is active, the DOM extraction
path falls back to AX tree only. Add a check:

```python
if browser == "safari":
    logger.info("Safari detected — DOM extraction not available, using AX tree only")
    return ax_tree_only_snapshot()
```

---

### 4.5 — File Manager Tool

**File:** `src/mac_mcp/tools/fm.py`

Port from Windows-MCP `tools/fm.py`. Update default paths for macOS:

| Windows path | macOS path |
|---|---|
| `C:\Users\<user>\Desktop` | `~/Desktop` |
| `C:\Users\<user>\Downloads` | `~/Downloads` |
| `C:\Users\<user>\Documents` | `~/Documents` |
| `%APPDATA%` | `~/Library/Application Support` |
| `%TEMP%` | `/tmp` or `$TMPDIR` |

Use `platformdirs` for cross-platform resolution — already in deps:
```python
from platformdirs import user_desktop_dir, user_downloads_dir, user_documents_dir
```

Finder integration for "reveal in Finder":
```python
subprocess.run(["open", "-R", str(path)])  # Reveals file in Finder
subprocess.run(["open", str(path)])        # Opens file/folder
```

---

### 4.6 — Multi-Select / Multi-Edit Tools

**File:** `src/mac_mcp/tools/multi.py`

Port from Windows-MCP `tools/multi.py`. Uses AX element selection instead of UIA.

**MultiSelect** — select multiple elements (e.g., list items, checkboxes):
```python
def multi_select(desktop, labels: list[int]) -> str:
    results = []
    for label in labels:
        el = desktop.tree.get_element_by_label(label)
        if el is None:
            results.append(f"Label {label}: not found")
            continue
        bb = el.bounding_box
        x = bb.x + bb.width // 2
        y = bb.y + bb.height // 2
        # Hold Cmd for multi-select on macOS (vs Ctrl on Windows)
        desktop.click(loc=[x, y], button="left", clicks=1, modifier="cmd")
        results.append(f"Label {label}: selected")
    return "\n".join(results)
```

**MultiEdit** — edit multiple text elements:
```python
def multi_edit(desktop, edits: list[dict]) -> str:
    # edits: [{"label": 5, "text": "new value"}, ...]
    results = []
    for edit in edits:
        label = edit.get("label")
        text = edit.get("text", "")
        el = desktop.tree.get_element_by_label(label)
        if el is None:
            results.append(f"Label {label}: not found")
            continue
        bb = el.bounding_box
        desktop.type_text(text, loc=[bb.x + bb.width // 2, bb.y + bb.height // 2], clear=True)
        results.append(f"Label {label}: edited")
    return "\n".join(results)
```

Note: Multi-select modifier key on macOS is `Cmd`, not `Ctrl` as on Windows.
Add a `modifier` parameter to `Desktop.click()`:
```python
def click(self, loc, button="left", clicks=1, modifier: str | None = None) -> None:
    if modifier:
        key = _KEY_ALIASES.get(modifier.lower())
        with _keyboard.pressed(key):
            self._do_click(loc, button, clicks)
    else:
        self._do_click(loc, button, clicks)
```

---

### 4.7 — Register All Tools

**File:** `src/mac_mcp/tools/__init__.py`

```python
from mac_mcp.tools import (
    app, shell, filesystem, snapshot, input, scrape,
    multi, clipboard, process, notification, defaults,
    browser, fm,
)

_MODULES = [
    app, shell, filesystem, snapshot, input, scrape,
    multi, clipboard, process, notification, defaults,
    browser, fm,
]

def register_all(mcp, *, get_desktop, get_analytics):
    for mod in _MODULES:
        mod.register(mcp, get_desktop=get_desktop, get_analytics=get_analytics)
```

---

### 4.8 — Update Entry Point Server Name

**File:** `src/mac_mcp/__main__.py`

Update the server description:
```python
instructions = """
mac-mcp provides tools to interact directly with the macOS desktop,
enabling AI agents to operate the desktop on the user's behalf.
"""
```

---

## Completion Criteria

- [ ] `Filesystem` tool lists, reads, writes, copies, and deletes files
- [ ] `Clipboard` tool reads and writes clipboard content
- [ ] `Process` tool lists running processes and can kill by PID or name
- [ ] `Scrape` tool fetches and returns page content via playwright
- [ ] `Notification` tool shows a banner notification (non-blocking)
- [ ] `Notification` tool shows a dialog and waits for OK
- [ ] `Defaults` tool reads `com.apple.dock` preferences
- [ ] `Defaults` tool writes and deletes a test preference key
- [ ] `Browser` tool detects Chrome/Firefox/Safari as the active app
- [ ] `Browser` tool DOM extraction works for Chrome and Firefox
- [ ] `Browser` tool falls back to AX tree for Safari
- [ ] `FileManager` tool opens Finder to a given path
- [ ] `MultiSelect` selects multiple list items with Cmd+click
- [ ] `MultiEdit` edits multiple text fields sequentially
- [ ] All 16 tools registered and visible in `fastmcp list-tools`
- [ ] `ruff check .` passes
