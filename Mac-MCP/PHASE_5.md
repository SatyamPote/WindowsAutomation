# Phase 5 — Polish, Tests, Spaces, Installer

**Goal:** Production-ready. Full test suite, Spaces awareness, launchd background service,
performance tuning, and final documentation.

**Prerequisite:** Phase 4 complete — all 16 tools functional.

**Status:** Not started

---

## Tasks

### 5.1 — Test Suite

**Directory:** `tests/`

Port every test from Windows-MCP `tests/`. Replace Windows-specific mocks with macOS equivalents.

#### Test file mapping

| Windows test | Mac test | Key changes |
|---|---|---|
| `test_desktop_utils.py` | `test_desktop_utils.py` | Update path/string helpers |
| `test_desktop_views.py` | `test_desktop_views.py` | Data models unchanged — copy verbatim |
| `test_filesystem_service.py` | `test_filesystem_service.py` | Update temp paths (`/tmp` vs `%TEMP%`) |
| `test_filesystem_views.py` | `test_filesystem_views.py` | Copy verbatim |
| `test_multi_tools.py` | `test_multi_tools.py` | Mock `pynput` instead of UIA |
| `test_paths.py` | `test_paths.py` | Update expected paths |
| `test_registry.py` | `test_defaults.py` | Rewrite for `defaults` CLI |
| `test_screenshot_capture.py` | `test_screenshot_capture.py` | Add Quartz backend test |
| `test_snapshot_display_filter.py` | `test_snapshot_display_filter.py` | Update for AX element format |
| `test_tree_service.py` | `test_tree_service.py` | Mock AX API instead of UIA |
| `test_tree_views.py` | `test_tree_views.py` | Copy verbatim |
| `test_analytics.py` | `test_analytics.py` | Copy verbatim |
| *(new)* | `test_ax_core.py` | Unit tests for AX wrapper |
| *(new)* | `test_shell_executor.py` | Unit tests for ShellExecutor / AppleScriptExecutor |
| *(new)* | `test_app_launcher.py` | Unit tests for NSWorkspace launcher |
| *(new)* | `test_permissions.py` | Unit tests for permission check |

#### Mock strategy for AX API

```python
# tests/conftest.py additions
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_ax():
    """Mock ApplicationServices AX calls for unit tests."""
    with patch("mac_mcp.ax.core.AS") as mock_as:
        mock_as.AXIsProcessTrusted.return_value = True
        mock_as.AXUIElementCreateApplication.return_value = MagicMock()
        mock_as.AXUIElementCopyAttributeValue.return_value = (0, [])  # kAXErrorSuccess
        yield mock_as

@pytest.fixture
def mock_nsworkspace():
    with patch("AppKit.NSWorkspace") as mock_ws:
        mock_app = MagicMock()
        mock_app.localizedName.return_value = "TestApp"
        mock_app.processIdentifier.return_value = 1234
        mock_ws.sharedWorkspace.return_value.frontmostApplication.return_value = mock_app
        yield mock_ws

@pytest.fixture
def mock_pynput():
    with patch("mac_mcp.desktop.service._keyboard") as mock_kb, \
         patch("mac_mcp.desktop.service._mouse") as mock_mouse:
        yield mock_kb, mock_mouse
```

#### Key new tests

**`test_ax_core.py`:**
```python
def test_get_rect_converts_coordinates(mock_ax):
    """AX uses bottom-left origin; verify conversion to top-left."""
    # Screen height 1080, element at y=800, height=100
    # Expected top = 1080 - 800 - 100 = 180
    ...

def test_ax_get_children_returns_empty_on_error(mock_ax):
    mock_ax.AXUIElementCopyAttributeValue.return_value = (-25200, None)  # kAXErrorNoValue
    result = ax_core.ax_get_children(MagicMock())
    assert result == []
```

**`test_screenshot_capture.py` additions:**
```python
def test_quartz_backend_returns_pil_image():
    # Requires Screen Recording permission — skip in CI
    pytest.importorskip("Quartz")
    ...

def test_quartz_backend_falls_through_on_nil():
    with patch("Quartz.CGWindowListCreateImage", return_value=None):
        with pytest.raises(RuntimeError, match="Screen Recording"):
            _QuartzBackend().capture(None)
```

---

### 5.2 — macOS Spaces (Virtual Desktop Awareness)

**File:** `src/mac_mcp/spaces/core.py`

macOS has no public API for Spaces. Two options:

**Option A (recommended):** No Spaces filtering. List all windows from all Spaces. Simpler,
no risk of breaking on OS updates.

**Option B:** Private CGS SPI. Works but may break on OS updates without notice.

```python
# Option B implementation (use with caution)
import ctypes
import ctypes.util

_cg = ctypes.cdll.LoadLibrary(
    ctypes.util.find_library("CoreGraphics")
    or "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
)

def get_current_space_id() -> int | None:
    """Return the CGSSpace ID of the current Space, or None if unavailable."""
    try:
        conn = _cg.CGSMainConnectionID()
        space = _cg.CGSGetActiveSpace(conn)
        return int(space) if space else None
    except Exception:
        return None

def get_window_space_ids(window_id: int) -> list[int]:
    """Return the Space IDs a window belongs to."""
    try:
        conn = _cg.CGSMainConnectionID()
        # CGSCopySpacesForWindows — returns CFArray of space IDs
        # Implementation requires CFArray bridging via pyobjc
        ...
    except Exception:
        return []
```

**Decision for Phase 5:** Implement Option A (no filtering) with a stub `spaces/core.py`
that always returns `True` for `is_window_on_current_desktop()`. Document Option B as a
future enhancement.

```python
# spaces/core.py — Phase 5 implementation
def is_window_on_current_desktop(window_id: int) -> bool:
    return True  # All spaces visible — Spaces filtering not yet implemented

def get_current_desktop() -> int:
    return 0

def get_all_desktops() -> list[int]:
    return [0]
```

---

### 5.3 — AX Tree Performance Tuning

The AX tree traversal is the slowest part of the stack (Mach IPC per attribute read).
Profile and apply these optimizations:

**a) Batch attribute reads**

Instead of calling `AXUIElementCopyAttributeValue` for each attribute separately,
use `AXUIElementCopyMultipleAttributeValues` to fetch role, title, position, size,
enabled, hidden, and children in one call:

```python
import ApplicationServices as AS

BATCH_ATTRS = [
    "AXRole", "AXTitle", "AXValue", "AXDescription",
    "AXPosition", "AXSize", "AXEnabled", "AXHidden", "AXChildren",
]

def ax_get_batch(element) -> dict:
    err, values = AS.AXUIElementCopyMultipleAttributeValues(
        element, BATCH_ATTRS, 0, None
    )
    if err != AS.kAXErrorSuccess:
        return {}
    return dict(zip(BATCH_ATTRS, values or []))
```

**b) Depth cap**

Default `MAX_TREE_DEPTH = 8` in `tree/config.py`. Expose as env var:
```python
MAX_TREE_DEPTH = int(os.getenv("MAC_MCP_TREE_DEPTH", "8"))
```

**c) Skip non-visible apps**

Skip apps with `activationPolicy != NSApplicationActivationPolicyRegular`.
Already in Phase 2 — verify it's enforced.

**d) Timeout per window**

Each window traversal in `ThreadPoolExecutor` should time out after 3s.
Already partially covered in Phase 2 — harden the timeout handling.

**e) Benchmark target**

Snapshot should complete within:
- Simple app (Terminal, TextEdit): < 2s
- Medium app (VS Code): < 5s
- Complex app (Chrome with many tabs): < 8s

---

### 5.4 — launchd Background Service

**File:** `install_scripts/com.mac-mcp.plist`

macOS background services use launchd plist files (equivalent to Windows services/registry
startup). This lets mac-mcp start automatically at login.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mac-mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/mac-mcp</string>
        <string>--transport</string>
        <string>stdio</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/mac-mcp.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mac-mcp-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANONYMIZED_TELEMETRY</key>
        <string>true</string>
    </dict>
</dict>
</plist>
```

**Install script:** `install_scripts/install.sh`

```bash
#!/bin/bash
set -e

PLIST_SRC="$(dirname "$0")/com.mac-mcp.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.mac-mcp.plist"

# Replace /path/to/mac-mcp with actual binary path
MAC_MCP_BIN=$(which mac-mcp)
sed "s|/path/to/mac-mcp|$MAC_MCP_BIN|g" "$PLIST_SRC" > "$PLIST_DST"

launchctl load "$PLIST_DST"
echo "mac-mcp installed as a login agent. It will start at next login."
echo "To start now: launchctl start com.mac-mcp"
```

**Uninstall script:** `install_scripts/uninstall.sh`

```bash
#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.mac-mcp.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "mac-mcp login agent removed."
```

---

### 5.5 — CLAUDE.md

**File:** `Mac-MCP/CLAUDE.md`

Document the project for Claude Code sessions:

```markdown
# CLAUDE.md

## Project Overview

mac-mcp is a Python MCP server that bridges AI agents with macOS, enabling desktop automation.
It exposes 16 tools via FastMCP. The architecture mirrors Windows-MCP but uses macOS-native APIs.

## Build & Development Commands

uv sync                    # Install dependencies
uv run mac-mcp             # Run the MCP server (stdio transport)
ruff format .              # Format code
ruff check .               # Lint code
pytest                     # Run all tests

## Key Differences from Windows-MCP

- uia/ → ax/               macOS Accessibility API replaces Windows UIAutomation
- powershell.py → shell.py bash/zsh + AppleScript replaces PowerShell
- dxcam → quartz           Quartz CGWindowListCreateImage replaces DirectX capture
- pywin32 → pyobjc         AppKit/NSWorkspace replaces win32gui
- registry.py → defaults.py macOS defaults system replaces Windows registry
- vdm/ → spaces/           macOS Spaces replaces Windows Virtual Desktop Manager

## Required macOS Permissions

Grant before running:
1. System Settings > Privacy & Security > Accessibility → add Terminal/your IDE
2. System Settings > Privacy & Security > Screen Recording → add Terminal/your IDE

## Architecture

See IMPLEMENTATION.md for full architecture documentation.
```

---

### 5.6 — README

**File:** `Mac-MCP/README.md`

Write user-facing documentation covering:
- What mac-mcp is
- Installation (`uv tool install mac-mcp` or `pip install mac-mcp`)
- Permission setup (with screenshots)
- Claude Desktop configuration (`claude_desktop_config.json`)
- Available tools with descriptions
- Environment variables reference
- Troubleshooting common issues (permission denied, AX not available, etc.)

**Claude Desktop config example** to include in README:
```json
{
  "mcpServers": {
    "mac-mcp": {
      "command": "mac-mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

---

### 5.7 — CI / GitHub Actions

**File:** `.github/workflows/ci.yml`

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest --timeout=30
        env:
          # Disable telemetry in CI
          ANONYMIZED_TELEMETRY: "false"
          # AX/Screen permissions not available in CI — skip those tests
          MAC_MCP_CI: "true"
```

Add a `CI` env var check in tests that need real permissions:
```python
@pytest.mark.skipif(os.getenv("MAC_MCP_CI") == "true", reason="Requires macOS permissions")
def test_real_screenshot(): ...
```

---

### 5.8 — Final Integration Test

Manual end-to-end verification checklist before declaring Phase 5 complete.

Run each of these in Claude Desktop with mac-mcp configured:

```
1. "Take a screenshot"
   → Screenshot tool returns current desktop image

2. "What apps are open?"
   → Snapshot tool returns window list

3. "Open Safari"
   → App tool launches Safari

4. "Click on the address bar in Safari"
   → Snapshot → identify address bar label → Click at coordinates

5. "Go to apple.com"
   → Type tool types URL → Shortcut Enter

6. "Copy the page title"
   → Shortcut Cmd+L (select URL) then read clipboard

7. "Open Terminal and run 'echo hello world'"
   → App launches Terminal → Shell tool executes command

8. "Show a notification saying 'test complete'"
   → Notification tool shows banner

9. "List files in ~/Downloads"
   → Filesystem tool returns directory listing

10. "What process is using the most CPU?"
    → Process tool returns process list sorted by CPU
```

---

## Completion Criteria

- [ ] `pytest` passes with ≥ 80% coverage on non-AX code
- [ ] All AX-dependent tests skipped gracefully in CI with `MAC_MCP_CI=true`
- [ ] Snapshot completes in < 5s for VS Code (benchmark)
- [ ] launchd plist installs and uninstalls cleanly
- [ ] `mac-mcp` starts at login after install
- [ ] CLAUDE.md written
- [ ] README written with permission setup instructions
- [ ] CI workflow passes on `macos-latest`
- [ ] End-to-end integration test checklist fully verified
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
