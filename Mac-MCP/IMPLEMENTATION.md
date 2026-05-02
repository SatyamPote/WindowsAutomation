# Mac-MCP Implementation Plan

Port of Windows-MCP to macOS. Same architecture, same 16 MCP tools, same FastMCP server — all
Windows-specific APIs replaced with native macOS equivalents.

---

## Project Identity

| Field | Value |
|---|---|
| Package name | `mac_mcp` |
| CLI entrypoint | `mac-mcp` |
| Server name | `mac-mcp` |
| Python | 3.13+ |
| Package manager | UV |
| Linter/formatter | Ruff |

---

## Target Architecture

```
Mac-MCP/
├── src/
│   └── mac_mcp/
│       ├── __init__.py
│       ├── __main__.py            # Entry point (click CLI + FastMCP server)
│       ├── analytics.py           # PostHog telemetry — unchanged from Windows
│       ├── config.py              # Config — strip Windows-specific env vars
│       ├── paths.py               # platformdirs-based paths — unchanged
│       ├── ax/                    # Replaces uia/ — macOS Accessibility API
│       │   ├── __init__.py
│       │   ├── core.py            # AXUIElement wrapper (replaces uia/core.py)
│       │   ├── controls.py        # AX role-specific helpers
│       │   ├── enums.py           # AX role/attribute/action constants
│       │   └── events.py          # AXObserver focus event monitoring
│       ├── desktop/
│       │   ├── __init__.py
│       │   ├── service.py         # Desktop orchestrator — NSWorkspace + AX
│       │   ├── screenshot.py      # mss + Quartz backends (dxcam dropped)
│       │   ├── applescript.py     # Replaces powershell.py
│       │   ├── utils.py
│       │   └── views.py           # DesktopState, Window, Size, BoundingBox — unchanged
│       ├── tree/
│       │   ├── __init__.py
│       │   ├── service.py         # AX tree traversal (replaces UIA TreeWalker)
│       │   ├── views.py           # TreeElementNode, ScrollElementNode — unchanged
│       │   └── config.py          # AX role configs (replaces UIA control types)
│       ├── watchdog/
│       │   ├── __init__.py
│       │   ├── service.py         # AXObserver-based focus monitoring
│       │   └── event_handlers.py
│       ├── spaces/                # Replaces vdm/ — macOS Spaces
│       │   ├── __init__.py
│       │   └── core.py
│       ├── launcher/              # NSWorkspace-based app launching
│       │   ├── __init__.py
│       │   ├── app_launcher.py
│       │   ├── app_registry.py
│       │   └── detection.py
│       ├── contacts/              # WhatsApp contact management — unchanged
│       │   └── contact_manager.py
│       ├── media/                 # yt-dlp + mpv — both work on Mac unchanged
│       │   ├── __init__.py
│       │   ├── downloader.py
│       │   ├── download_tui.py
│       │   ├── music_player.py
│       │   └── player_tui.py
│       ├── tools/                 # MCP tool definitions — interfaces unchanged
│       │   ├── __init__.py
│       │   ├── _snapshot_helpers.py
│       │   ├── app.py
│       │   ├── browser.py
│       │   ├── clipboard.py
│       │   ├── filesystem.py
│       │   ├── fm.py
│       │   ├── input.py
│       │   ├── multi.py
│       │   ├── notification.py
│       │   ├── process.py
│       │   ├── scrape.py
│       │   ├── shell.py           # bash/zsh replaces PowerShell
│       │   └── snapshot.py
│       └── telegram_bot.py        # Unchanged
├── tests/
├── assets/
├── pyproject.toml
├── CLAUDE.md
└── IMPLEMENTATION.md
```

---

## API Mapping: Windows → macOS

### 1. UI Accessibility — `uia/` → `ax/`

This is the largest replacement. The entire `uia/` layer wraps the Windows COM UIAutomation API.
On macOS the equivalent is the AX (Accessibility) API via `ApplicationServices`.

| Windows (`uia/`) | macOS (`ax/`) | Notes |
|---|---|---|
| `IUIAutomation` COM interface | `AXUIElementCreateApplication()` | Core AX factory |
| `IUIAutomationElement` | `AXUIElementRef` (via `atomacos`) | Per-element handle |
| `TreeWalker` (parent/child/sibling) | Recursive `AXChildren` attribute | AX has no walker; traverse manually |
| `UIAutomationEventHandler` | `AXObserver` + CFRunLoop | Async focus/value notifications |
| `GetForegroundWindow()` | `NSWorkspace.frontmostApplication()` | Active app |
| `EnumWindows()` | `NSWorkspace.runningApplications()` | All running apps |
| `GetWindowRect()` | `AXPosition` + `AXSize` attributes | Window geometry |
| `SetForegroundWindow()` | `NSRunningApplication.activateWithOptions_()` | Focus a window |
| `comtypes` / `ctypes.windll` | `pyobjc` + `ctypes.cdll` (`.dylib`) | Binding strategy |

**Primary library:** [`atomacos`](https://github.com/dementrock/atomacos) — pure Python wrapper
over `ApplicationServices` AX API. Handles `AXUIElement` creation, attribute reads, action
invocation, and observer setup.

**Fallback:** Direct `pyobjc` calls via `ApplicationServices` for anything `atomacos` doesn't expose.

#### `ax/core.py` — key functions to implement

```python
# Mirrors uia/core.py public surface
def get_frontmost_app() -> AXUIElement          # NSWorkspace frontmost
def get_all_windows() -> list[AXUIElement]      # All app windows
def get_window_rect(win: AXUIElement) -> Rect   # AXPosition + AXSize
def set_foreground(win: AXUIElement) -> None    # activateWithOptions_
def get_screen_size() -> tuple[int, int]        # NSScreen.mainScreen().frame()
def get_virtual_screen_rect() -> Rect           # NSScreen bounds union
def get_monitors_rect() -> list[Rect]           # NSScreen.screens()
```

#### `ax/events.py` — AXObserver (replaces UIAutomation event handler)

```python
# AXObserver watches for focus change notifications on the system
# Equivalent to Windows UIAutomationFocusChangedEventHandler
observer = AXObserver(app_pid, focus_changed_callback)
observer.add_notification(kAXFocusedUIElementChangedNotification)
observer.start()  # runs on CFRunLoop
```

---

### 2. Win32 GUI calls → AppKit / NSWorkspace

All `win32gui`, `win32process`, `win32con` imports in `desktop/service.py` are replaced:

| Windows | macOS | Import |
|---|---|---|
| `win32gui.GetForegroundWindow()` | `NSWorkspace.sharedWorkspace().frontmostApplication()` | `AppKit` |
| `win32gui.GetWindowText()` | `AXTitle` attribute | `atomacos` |
| `win32gui.ShowWindow(SW_MAXIMIZE)` | `AXRaiseWindow` + resize to screen | `atomacos` |
| `win32gui.SetWindowPos()` | `AXPosition` + `AXSize` set | `atomacos` |
| `win32process.GetWindowThreadProcessId()` | `NSRunningApplication.processIdentifier` | `AppKit` |
| `win32con.*` constants | `AppKit.*` / `Quartz.*` constants | — |

---

### 3. Screenshot — `desktop/screenshot.py`

`dxcam` (DirectX-only) is dropped. `mss` and Pillow already work on macOS. A native Quartz
backend is added as the high-performance option.

| Windows backend | macOS backend | Priority |
|---|---|---|
| `dxcam` (DirectX) | **DROPPED** | — |
| `mss` | `mss` — unchanged, cross-platform | 20 |
| `pillow` (`ImageGrab`) | `pillow` — unchanged | 100 |
| *(none)* | **`quartz`** (new, `CGWindowListCreateImage`) | 10 |

**New `_QuartzBackend`:**

```python
import Quartz

class _QuartzBackend(_ScreenshotBackend):
    name = "quartz"
    priority = 10

    def capture(self, capture_rect: Rect | None) -> Image.Image:
        region = CGRectMake(x, y, w, h) if capture_rect else CGRectInfinite
        image_ref = CGWindowListCreateImage(
            region,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
            kCGWindowImageDefault,
        )
        # Convert CGImageRef → PIL Image via bitmap data
        ...
```

**Environment variable rename:** `WINDOWS_MCP_SCREENSHOT_BACKEND` → `MAC_MCP_SCREENSHOT_BACKEND`
Valid values: `auto`, `quartz`, `mss`, `pillow`.

---

### 4. Input Simulation — `uia.SendKeys` / mouse → Quartz CGEvents

| Windows | macOS |
|---|---|
| `uia.SendKeys("{Ctrl}c")` | `CGEventCreateKeyboardEvent(None, kVK_ANSI_C, True)` |
| `uia.MouseMove(x, y)` | `CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x,y), ...)` |
| `uia.Click(x, y)` | `CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, ...)` |
| `win32con` key codes | `Quartz` key codes (`kVK_*` constants from `Carbon`) |

**Implementation strategy:** Use `pynput` as the primary abstraction.
It wraps `Quartz` CGEvents internally and is simpler to use. Fall back to raw `Quartz` calls
for anything `pynput` doesn't support (e.g., synthetic media keys).

```python
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
```

The `_escape_text_for_sendkeys()` helper in `desktop/service.py` maps to `pynput` key names
(different from UIA special key names — needs a new key alias table).

---

### 5. PowerShell → Shell / AppleScript — `desktop/applescript.py`

`desktop/powershell.py` is replaced by two executors:

**`ShellExecutor`** — for filesystem/process operations:
```python
import subprocess

class ShellExecutor:
    @staticmethod
    def execute(command: str, timeout: int = 30) -> tuple[str, int]:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout + result.stderr, result.returncode
```

**`AppleScriptExecutor`** — for app/window control:
```python
class AppleScriptExecutor:
    @staticmethod
    def execute(script: str, timeout: int = 10) -> tuple[str, int]:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
```

The `tools/shell.py` tool is renamed from `PowerShell` to `Shell` and uses `ShellExecutor`.
The tool description updates accordingly (bash/zsh instead of PowerShell).

---

### 6. Virtual Desktop Manager → Spaces — `spaces/core.py`

`vdm/core.py` uses a Windows COM interface with no macOS public API equivalent.

**Option A (recommended for v1):** Skip Spaces awareness entirely. The tool is not user-facing;
it only affects window enumeration filtering. On Mac, show all windows regardless of Space.

**Option B (advanced):** Use the private `CGSCopySpaces` CoreGraphics SPI:
```python
import ctypes
cgs = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
# CGSCopySpaces, CGSCopyWindowsWithOptionsAndTags — undocumented, may break on OS updates
```

Plan: implement Option A in Phase 1, revisit Option B in Phase 3.

---

### 7. Registry Tool → `defaults` / plist — `tools/defaults.py`

`tools/registry.py` reads/writes the Windows registry. macOS equivalent is the `defaults` system
(plist files under `~/Library/Preferences/`).

Replace `registry.py` with `defaults.py`:

```python
# Tool renamed from "Registry" to "Defaults"
# Reads/writes macOS user defaults (app preferences)
# Uses: subprocess.run(["defaults", "read/write/delete", domain, key, value])
```

---

### 8. Notification — `tools/notification.py`

| Windows | macOS |
|---|---|
| Windows toast notifications | `osascript display notification "msg" with title "title"` |
| `win32api.MessageBox` | `osascript display dialog "msg"` |

```python
class AppleScriptExecutor:
    @staticmethod
    def notify(title: str, message: str) -> None:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script])
```

---

### 9. Clipboard — `tools/clipboard.py`

`pyperclip` is already cross-platform and works on macOS via `pbcopy`/`pbpaste`.
No changes required. If `pyperclip` is dropped, use `AppKit.NSPasteboard` directly.

---

### 10. App Launcher — `launcher/`

| Windows | macOS |
|---|---|
| `subprocess.Popen(["start", name])` | `NSWorkspace.openApplication(at:configuration:)` |
| Registry-based app discovery | `mdfind` (Spotlight) + `/Applications` scan |
| `.exe` paths | `.app` bundles |

```python
import AppKit

workspace = AppKit.NSWorkspace.sharedWorkspace()
workspace.openApplication_withArguments_environment_(app_url, [], {})

# App discovery via Spotlight:
# subprocess.run(["mdfind", "kMDItemKind == 'Application'"], ...)
```

---

### 11. Browser DOM Extraction — `desktop/service.py`

Browser detection already works via process name matching (`chrome`, `firefox`, `safari`).
The DOM extraction path uses `playwright` which is already cross-platform. No changes needed
except updating process name detection (e.g., `Google Chrome` on Mac vs `chrome.exe` on Windows).

---

## Dependencies

### Drop (Windows-only)
```
comtypes       # Windows COM
dxcam          # DirectX screenshot
pywin32        # win32gui, win32process, win32con
```

### Add (macOS-specific)
```
pyobjc-framework-ApplicationServices   # AX Accessibility API
pyobjc-framework-Quartz                # CGEvents (input) + CGWindowListCreateImage (screenshot)
pyobjc-framework-AppKit                # NSWorkspace, NSRunningApplication, NSScreen
atomacos                               # High-level AX tree wrapper
pynput                                 # Cross-platform keyboard/mouse input
```

### Unchanged (cross-platform)
```
fastmcp, click, pillow, mss, psutil, requests, markdownify,
thefuzz, python-levenshtein, posthog, platformdirs, python-dotenv,
playwright, yt-dlp, tabulate, cryptography, openai, google-genai,
python-telegram-bot, python-docx, openpyxl, reportlab, pytesseract,
ollama, uuid7
```

### New `pyproject.toml` deps block
```toml
[project]
name = "mac-mcp"
requires-python = ">=3.13"
dependencies = [
    "click>=8.2.1",
    "fastmcp>=3.0",
    "pillow>=11.2.1",
    "mss>=9.0.0",
    "pynput>=1.7.0",
    "pyobjc-framework-ApplicationServices>=10.0",
    "pyobjc-framework-Quartz>=10.0",
    "pyobjc-framework-AppKit>=10.0",
    "atomacos>=3.0.0",
    "psutil>=7.0.0",
    "fuzzywuzzy>=0.18.0",
    "python-levenshtein>=0.27.1",
    "markdownify>=1.1.0",
    "requests>=2.32.3",
    "posthog>=7.4.0",
    "platformdirs>=4.3.8",
    "python-dotenv>=1.0.0",
    "tabulate>=0.9.0",
    "thefuzz>=0.22.1",
    "uuid7>=0.1.0",
    "playwright>=1.42.0",
    "cryptography>=42.0.0",
    "openai>=1.0.0",
    "google-genai>=0.5.0",
    "python-telegram-bot>=21.0",
    "python-docx>=1.1.0",
    "openpyxl>=3.1.2",
    "reportlab>=4.1.0",
    "pytesseract>=0.3.10",
    "ollama>=0.4.0",
    "yt-dlp>=2024.0.0",
]

[project.scripts]
mac-mcp = "mac_mcp.__main__:main"
```

---

## macOS Permission Requirements

macOS requires explicit user grants for three categories. The server will fail silently without them.

| Permission | Where to grant | Required for |
|---|---|---|
| **Accessibility** | System Settings → Privacy & Security → Accessibility | AX tree, click, type, scroll, window control |
| **Screen Recording** | System Settings → Privacy & Security → Screen Recording | Screenshot, Snapshot |
| **Automation** | Granted per-app on first AppleScript run | App switching, notifications via osascript |

Add a startup permission check in `__main__.py` lifespan:

```python
import Quartz
import ApplicationServices

def check_permissions() -> list[str]:
    missing = []
    if not ApplicationServices.AXIsProcessTrusted():
        missing.append("Accessibility (System Settings > Privacy > Accessibility)")
    # Screen recording: attempt a 1x1 capture and check for nil
    test = Quartz.CGWindowListCreateImage(
        Quartz.CGRectMake(0, 0, 1, 1),
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault,
    )
    if test is None:
        missing.append("Screen Recording (System Settings > Privacy > Screen Recording)")
    return missing
```

If permissions are missing, log a clear warning with the exact steps. Do not crash — tools that
don't need the permission (Shell, Filesystem, Notification) should still work.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MAC_MCP_SCREENSHOT_BACKEND` | `auto` | `auto`, `quartz`, `mss`, `pillow` |
| `MAC_MCP_SCREENSHOT_SCALE` | `1.0` | Scale factor `0.1`–`1.0` |
| `MAC_MCP_PROFILE_SNAPSHOT` | _(off)_ | Set `1`/`true` to log per-stage timing |
| `MAC_MCP_DEBUG` | `false` | Debug mode / verbose logging |
| `ANONYMIZED_TELEMETRY` | `true` | Set `false` to disable PostHog |

---

## MCP Tools: Status After Port

| Tool | Windows impl | macOS impl | Changes |
|---|---|---|---|
| `App` | `win32gui` + UIA | `NSWorkspace` + AX | Medium |
| `PowerShell` → **`Shell`** | `PowerShellExecutor` | `ShellExecutor` (bash/zsh) | Low |
| `Screenshot` / `Snapshot` | dxcam/mss/pillow + UIA tree | quartz/mss/pillow + AX tree | Medium |
| `Click` | `uia.MouseClick` | `pynput` / Quartz CGEvent | Low |
| `Type` | `uia.SendKeys` | `pynput` keyboard | Low |
| `Scroll` | `uia.WheelScroll` | `pynput` mouse scroll | Low |
| `Move` | `uia.MouseMove` | `pynput` mouse move | Low |
| `Shortcut` | `uia.SendKeys` key combos | `pynput` key combos | Low |
| `Wait` | `time.sleep` | `time.sleep` | None |
| `Scrape` | `playwright` | `playwright` | None |
| `MultiSelect` / `MultiEdit` | UIA multi-element | AX multi-element | Medium |
| `Clipboard` | `pyperclip` | `pyperclip` (pbcopy/pbpaste) | None |
| `Process` | `psutil` | `psutil` | None |
| `Notification` | Windows toast | `osascript display notification` | Low |
| `Registry` → **`Defaults`** | `winreg` | `defaults` CLI | Low |
| `Filesystem` | `os`/`pathlib` | `os`/`pathlib` | None |

---

## Implementation Phases

### Phase 1 — Foundation (scaffold + screenshot + shell)
**Goal:** Server starts, `Shell` and `Screenshot` tools work.

1. Create project scaffold (`pyproject.toml`, `src/mac_mcp/`, `__main__.py`, `config.py`)
2. Port `analytics.py`, `paths.py` — unchanged
3. Implement `desktop/screenshot.py` — Quartz + mss + pillow backends, drop dxcam
4. Implement `desktop/applescript.py` + `ShellExecutor`
5. Replace `tools/shell.py` (`PowerShell` → `Shell` using bash/zsh)
6. Stub `Desktop` class in `desktop/service.py` with just `get_screen_size()` and `screenshot()`
7. Wire up `__main__.py` — FastMCP server starts, `Screenshot` tool functional
8. Add startup permission check

**Deliverable:** `mac-mcp` CLI starts, takes screenshots, runs shell commands.

---

### Phase 2 — AX Layer + UI Tree
**Goal:** `Snapshot` tool works — full AX tree extraction.

1. Implement `ax/enums.py` — AX role constants, attribute names, action names
2. Implement `ax/core.py` — `get_frontmost_app`, `get_all_windows`, `get_window_rect`,
   `set_foreground`, `get_screen_size`, `get_virtual_screen_rect`, `get_monitors_rect`
3. Implement `ax/controls.py` — role-specific attribute helpers (buttons, text fields, lists…)
4. Implement `ax/events.py` — `AXObserver` focus monitoring
5. Implement `tree/config.py` — AX role → interactive/scrollable classification
6. Implement `tree/service.py` — recursive AX children traversal with `ThreadPoolExecutor`
7. Implement `tree/views.py` — `TreeElementNode`, `ScrollElementNode`, `TreeState` (unchanged shapes)
8. Implement `watchdog/service.py` — AXObserver wrapper starting on a background thread
9. Wire `Desktop` to `Tree` and `WatchDog` in lifespan
10. Port `tools/_snapshot_helpers.py` and `tools/snapshot.py`

**Deliverable:** `Snapshot` tool returns annotated screenshot + full UI element tree.

---

### Phase 3 — Input + Window Control
**Goal:** All input tools and `App` tool work.

1. Implement keyboard input in `desktop/service.py` using `pynput`
   - Build Mac key alias table (replaces `_KEY_ALIASES` for Win UIA key names)
2. Implement mouse input — click, move, scroll via `pynput`
3. Port `tools/input.py` — `Click`, `Type`, `Scroll`, `Move`, `Shortcut`, `Wait`
4. Implement `launcher/app_launcher.py` — `NSWorkspace.openApplication`
5. Implement `launcher/app_registry.py` — Spotlight `mdfind` + `/Applications` scan
6. Implement `launcher/detection.py` — `.app` bundle detection
7. Port `desktop/service.py` — `app()` method (launch/resize/switch) using `NSWorkspace` + AX
8. Port `tools/app.py`

**Deliverable:** Launch, resize, switch apps. Click, type, scroll, keyboard shortcuts.

---

### Phase 4 — Remaining Tools
**Goal:** Full tool parity with Windows-MCP.

1. `tools/filesystem.py` — unchanged (os/pathlib)
2. `tools/clipboard.py` — unchanged (pyperclip)
3. `tools/process.py` — unchanged (psutil)
4. `tools/notification.py` — `osascript display notification`
5. `tools/scrape.py` — unchanged (playwright)
6. `tools/browser.py` — update process name detection (`Google Chrome`, `Safari`, `Firefox`)
7. `tools/multi.py` — port to AX multi-element selection
8. `tools/defaults.py` — replace `registry.py` with macOS `defaults` CLI wrapper
9. `tools/fm.py` — filesystem manager, update for macOS paths

**Deliverable:** All 16 tools functional.

---

### Phase 5 — Polish + Spaces + Tests
**Goal:** Production-ready.

1. Implement `spaces/core.py` — Spaces awareness via private CGS SPI (or skip)
2. Port test suite — update all Windows-specific mocks to macOS equivalents
3. Write `CLAUDE.md` for Mac-MCP
4. Performance tuning — AX tree traversal is slower than UIA; profile and optimize
5. Installer / launch agent setup (launchd plist for background startup)
6. `assets/` — Mac-specific icons, banner

---

## Key Implementation Notes

### AX tree traversal is slower than Windows UIA
UIA's `TreeWalker` is implemented in native C++ in-process. AX calls cross the process boundary
via Mach IPC. Expect `tree/service.py` to be 2–5× slower than Windows. Mitigations:
- Limit traversal depth (default 8, configurable)
- Use `ThreadPoolExecutor` per top-level window (same as Windows)
- Cache element refs aggressively between snapshots

### `atomacos` vs raw `pyobjc`
`atomacos` is easier but may not expose every AX attribute. Plan: use `atomacos` for the common
path (children, position, size, title, role, actions) and drop to raw `pyobjc` calls for
anything it doesn't expose (e.g., `AXSubrole`, `AXDocument`, custom attributes).

### pynput needs Accessibility permission
`pynput` uses the same AX API for input injection. It will fail silently if Accessibility
permission is not granted. The startup permission check covers this.

### Safari browser DOM extraction
`playwright` does not support Safari. For the `Snapshot` browser DOM extraction path:
- Chrome/Chromium → playwright (same as Windows)
- Firefox → playwright (same as Windows)
- Safari → fall back to AX tree only (no DOM extraction)

### `asyncio.WindowsSelectorEventLoopPolicy` → remove
`__main__.py` sets `asyncio.WindowsSelectorEventLoopPolicy()` before starting the server.
This line must be removed — it doesn't exist on macOS and will raise `AttributeError`.
Use the default event loop policy (uvloop optional for performance).

### Key code rename
`_KEY_ALIASES` in `desktop/service.py` maps user-facing key names to UIA `SendKeys` names.
On Mac, `pynput` uses its own key names (`Key.ctrl`, `Key.cmd`, etc.). The alias table needs
a full replacement. Notable differences:
- `windows` / `command` → `Key.cmd` (not `Key.win`)
- `option` / `alt` → `Key.alt`
- `backspace` → `Key.backspace`
- `capslock` → `Key.caps_lock`
