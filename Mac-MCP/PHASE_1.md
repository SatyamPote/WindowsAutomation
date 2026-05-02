# Phase 1 — Foundation

**Goal:** The `mac-mcp` CLI starts successfully, takes screenshots, and runs shell commands.
No UI tree, no input simulation yet.

**Status:** Not started

---

## Tasks

### 1.1 — Project Scaffold

Create the base project structure and config files.

**Files to create:**

```
Mac-MCP/
├── pyproject.toml
├── .python-version
├── .gitignore
├── .env.example
├── CLAUDE.md
└── src/
    └── mac_mcp/
        ├── __init__.py
        ├── __main__.py
        ├── analytics.py
        ├── config.py
        └── paths.py
```

**`pyproject.toml`** — package definition:
```toml
[project]
name = "mac-mcp"
version = "0.1.0"
description = "Mac-MCP – AI macOS Desktop Control via MCP"
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

[project.optional-dependencies]
dev = [
    "ruff>=0.9.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]

[project.scripts]
mac-mcp = "mac_mcp.__main__:main"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "W"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**`src/mac_mcp/__init__.py`** — empty file.

**`src/mac_mcp/config.py`** — debug mode toggle:
```python
import logging
import os

def enable_debug() -> None:
    logging.basicConfig(level=logging.DEBUG)

def is_debug() -> bool:
    return os.getenv("MAC_MCP_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
```

**`src/mac_mcp/paths.py`** — platform paths (identical logic to Windows version, paths differ):
```python
from platformdirs import user_data_dir, user_cache_dir
from pathlib import Path

APP_NAME = "mac-mcp"
DATA_DIR = Path(user_data_dir(APP_NAME))
CACHE_DIR = Path(user_cache_dir(APP_NAME))
```

**`src/mac_mcp/analytics.py`** — copy from Windows-MCP verbatim, no changes needed.

---

### 1.2 — Screenshot Backends

**File:** `src/mac_mcp/desktop/screenshot.py`

Three backends in priority order: `quartz` (10) → `mss` (20) → `pillow` (100).
The same pluggable `_ScreenshotBackend` registry pattern as Windows, but `dxcam` is gone
and `quartz` is new.

**`_QuartzBackend`** implementation:
```python
import Quartz
from PIL import Image
import numpy as np

class _QuartzBackend(_ScreenshotBackend):
    name = "quartz"
    priority = 10

    def capture(self, capture_rect) -> Image.Image:
        if capture_rect is None:
            region = Quartz.CGRectInfinite
        else:
            region = Quartz.CGRectMake(
                capture_rect.left,
                capture_rect.top,
                capture_rect.right - capture_rect.left,
                capture_rect.bottom - capture_rect.top,
            )

        image_ref = Quartz.CGWindowListCreateImage(
            region,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault,
        )
        if image_ref is None:
            raise RuntimeError(
                "Quartz capture returned nil — Screen Recording permission may be missing"
            )

        width = Quartz.CGImageGetWidth(image_ref)
        height = Quartz.CGImageGetHeight(image_ref)
        cs = Quartz.CGColorSpaceCreateDeviceRGB()
        ctx = Quartz.CGBitmapContextCreate(
            None, width, height, 8, width * 4, cs,
            Quartz.kCGImageAlphaPremultipliedLast,
        )
        Quartz.CGContextDrawImage(ctx, Quartz.CGRectMake(0, 0, width, height), image_ref)
        buf = Quartz.CGBitmapContextGetData(ctx)
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)
        return Image.fromarray(arr[:, :, :3], "RGB")
```

**`_MssBackend`** and **`_PillowBackend`** — identical to Windows-MCP, copy verbatim.

**`Rect` dataclass** — define locally (replaces `uia.Rect`):
```python
from dataclasses import dataclass

@dataclass
class Rect:
    left: int
    top: int
    right: int
    bottom: int
```

**Environment variable:** `MAC_MCP_SCREENSHOT_BACKEND` (replaces `WINDOWS_MCP_SCREENSHOT_BACKEND`).

---

### 1.3 — Shell Executor

**File:** `src/mac_mcp/desktop/shell.py`

Replaces `desktop/powershell.py`. Two executors:

```python
import subprocess

class ShellExecutor:
    @staticmethod
    def execute(command: str, timeout: int = 30) -> tuple[str, int]:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return output, result.returncode


class AppleScriptExecutor:
    @staticmethod
    def execute(script: str, timeout: int = 10) -> tuple[str, int]:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.returncode

    @staticmethod
    def notify(title: str, message: str) -> None:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)
```

---

### 1.4 — Desktop Views

**File:** `src/mac_mcp/desktop/views.py`

Copy `desktop/views.py` from Windows-MCP verbatim. The data models (`DesktopState`, `Window`,
`Size`, `BoundingBox`, `Status`, `Browser`) are platform-agnostic.

---

### 1.5 — Desktop Service Stub

**File:** `src/mac_mcp/desktop/service.py`

Implement only what Phase 1 needs. Full implementation comes in Phase 3.

```python
import AppKit
from mac_mcp.desktop import screenshot as screenshot_capture
from mac_mcp.desktop.views import DesktopState, Size

class Desktop:
    def __init__(self):
        self.desktop_state = None

    def get_screen_size(self) -> Size:
        frame = AppKit.NSScreen.mainScreen().frame()
        return Size(
            width=int(frame.size.width),
            height=int(frame.size.height),
        )

    def screenshot(self, scale: float = 1.0):
        image, backend = screenshot_capture.capture(capture_rect=None)
        if scale != 1.0:
            w, h = image.size
            image = image.resize((int(w * scale), int(h * scale)))
        return image, backend
```

---

### 1.6 — Permission Check

**File:** `src/mac_mcp/permissions.py`

```python
import logging
import Quartz
import ApplicationServices

logger = logging.getLogger(__name__)

def check_and_warn() -> None:
    missing = []

    if not ApplicationServices.AXIsProcessTrusted():
        missing.append(
            "Accessibility — System Settings > Privacy & Security > Accessibility"
        )

    test = Quartz.CGWindowListCreateImage(
        Quartz.CGRectMake(0, 0, 1, 1),
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault,
    )
    if test is None:
        missing.append(
            "Screen Recording — System Settings > Privacy & Security > Screen Recording"
        )

    if missing:
        for m in missing:
            logger.warning("Missing permission: %s", m)
        logger.warning(
            "Some tools will not work until permissions are granted. "
            "Restart mac-mcp after granting."
        )
```

---

### 1.7 — Shell Tool

**File:** `src/mac_mcp/tools/shell.py`

Tool renamed from `PowerShell` to `Shell`. Same interface, uses `ShellExecutor`.

```python
from mac_mcp.desktop.shell import ShellExecutor
from mac_mcp.analytics import with_analytics
from fastmcp import Context
from mcp.types import ToolAnnotations

def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Shell",
        description=(
            "Execute shell commands via bash/zsh. Keywords: shell, run, execute, terminal, "
            "command line, script. Full access to the macOS shell — filesystem, processes, "
            "network, scripting. Use for any system operation not covered by dedicated tools."
        ),
        annotations=ToolAnnotations(
            title="Shell",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    @with_analytics(get_analytics(), "Shell-Tool")
    def shell_tool(command: str, timeout: int = 30, ctx: Context = None) -> str:
        output, code = ShellExecutor.execute(command, timeout)
        return f"Output: {output}\nExit code: {code}"
```

---

### 1.8 — Entry Point

**File:** `src/mac_mcp/__main__.py`

Mirror of Windows `__main__.py` with two key differences:
- Remove `asyncio.WindowsSelectorEventLoopPolicy()` — does not exist on macOS
- Remove `NO_COLOR` env var workaround (only needed for Windows stdio pipe)
- Call `permissions.check_and_warn()` in lifespan

```python
from contextlib import asynccontextmanager
from mac_mcp.config import enable_debug
from fastmcp import FastMCP
import asyncio, logging, os, click

from mac_mcp import permissions

logger = logging.getLogger(__name__)

desktop = None
analytics = None

def _get_desktop():
    return desktop

def _get_analytics():
    return analytics

def _build_mcp() -> FastMCP:
    from mac_mcp.analytics import PostHogAnalytics
    from mac_mcp.desktop.service import Desktop
    from mac_mcp.tools import register_all

    @asynccontextmanager
    async def lifespan(app):
        global desktop, analytics
        permissions.check_and_warn()
        if os.getenv("ANONYMIZED_TELEMETRY", "true").lower() != "false":
            analytics = PostHogAnalytics()
        desktop = Desktop()
        try:
            yield
        finally:
            if analytics:
                await analytics.close()

    mcp = FastMCP(name="mac-mcp", lifespan=lifespan)
    register_all(mcp, get_desktop=_get_desktop, get_analytics=_get_analytics)
    return mcp

@click.command()
@click.option("--transport", default="stdio",
              type=click.Choice(["stdio", "sse", "streamable-http"]))
@click.option("--host", default="localhost")
@click.option("--port", default=8000, type=int)
@click.option("--debug", is_flag=True, default=False)
def main(transport, host, port, debug):
    if debug:
        enable_debug()
    mcp = _build_mcp()
    mcp.run(transport=transport, show_banner=False)

if __name__ == "__main__":
    main()
```

---

### 1.9 — Tools Init (Phase 1 subset)

**File:** `src/mac_mcp/tools/__init__.py`

Register only Shell for now. Add more tools as phases complete.

```python
from mac_mcp.tools import shell

_MODULES = [shell]

def register_all(mcp, *, get_desktop, get_analytics):
    for mod in _MODULES:
        mod.register(mcp, get_desktop=get_desktop, get_analytics=get_analytics)
```

---

## Completion Criteria

- [ ] `uv sync` installs all dependencies without errors
- [ ] `uv run mac-mcp --transport stdio` starts without crashing
- [ ] Permission warnings appear in logs if Accessibility/Screen Recording not granted
- [ ] `Shell` tool executes `echo hello` and returns `hello`
- [ ] `Shell` tool executes `ls /tmp` and returns directory listing
- [ ] Screenshot capture works (Quartz backend when permissions granted, mss/pillow fallback)
- [ ] `ruff check .` passes with no errors
