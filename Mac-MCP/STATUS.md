# Lotus Mac-MCP — Project Status

**Last updated:** 2026-05-03  
**Branch:** `main`

---

## What Is This

Lotus Mac-MCP is a macOS desktop-automation system with three layers:

| Layer | What it does |
|---|---|
| **MCP server** (`mac-mcp`) | FastMCP server exposing 11 tool groups to any MCP client (Claude Desktop, etc.) |
| **Telegram bot** | Remote-control your Mac via Telegram messages |
| **Control Panel** (`app.py`) | Native-looking macOS GUI to configure and manage everything |

---

## Completed Work

### Phase 1 — Core Infrastructure ✅
- `pyproject.toml` with all dependencies (`fastmcp`, `pyobjc-*`, `pynput`, `psutil`, etc.)
- `src/mac_mcp/__init__.py`, `__main__.py`, `config.py`, `paths.py`
- `analytics.py` — PostHog telemetry (ported unchanged from Windows-MCP)
- `permissions.py` — Accessibility + Screen Recording permission check/warn

### Phase 2 — macOS APIs ✅
- `ax/` — full AXUIElement wrapper replacing Windows UIAutomation
  - `core.py` — element get/set, find by role/label, coordinate conversion
  - `controls.py` — role-specific helpers (click, type, scroll, toggle)
  - `enums.py` — AX role / attribute / action constants
  - `events.py` — AXObserver focus-change monitoring
- `desktop/service.py` — Desktop orchestrator using NSWorkspace + AX + pynput
- `desktop/screenshot.py` — `mss` primary backend + Quartz fallback
- `desktop/shell.py` — `ShellExecutor` (bash) + `AppleScriptExecutor` (osascript)
- `desktop/views.py` — `DesktopState`, `Window`, `Status`, `Size` data models
- `desktop/utils.py` — Unicode Private Use Area char stripper
- `tree/` — AX accessibility tree traversal (replaces Windows UIA TreeWalker)
  - `service.py` — recursive tree build with timeout + depth cap
  - `views.py` — `TreeElementNode`, `BoundingBox`, `Center`, `TreeState`
  - `config.py` — AX role to interaction-type mapping
- `watchdog/service.py` — AXObserver focus-change watchdog
- `launcher/` — NSWorkspace-based app launch/switch
  - `app_launcher.py` — launch by name, switch by name
  - `app_registry.py` — fuzzy app name resolution
  - `detection.py` — scan `/Applications`, `~/Applications`
- `spaces/core.py` — macOS Spaces stub (Option A: all windows visible)

### Phase 3 — Input Tools ✅
- `tools/input.py` — Click, Type, Scroll, Move, Shortcut, Wait
- `tools/app.py` — App launch/switch/resize via NSWorkspace
- `tools/shell.py` — Shell command execution + AppleScript
- `tools/snapshot.py` — Screenshot + AX tree snapshot

### Phase 4 — Extended Tools ✅
- `tools/filesystem.py` — Read, write, copy, move, delete, search, organize
- `tools/clipboard.py` — Read/write clipboard via `pbcopy`/`pbpaste`
- `tools/process.py` — List processes, kill by name or PID
- `tools/scrape.py` — Web scraping with `requests` + `markdownify`
- `tools/notification.py` — macOS banner notifications via osascript
- `tools/defaults.py` — macOS `defaults` CLI wrapper (read/write/delete prefs)
- `tools/multi.py` — Multi-select (Cmd+click) + multi-edit
- `filesystem/service.py` — Full filesystem service (list, read, write, copy, move, delete, search, organize, bulk-delete)
- `filesystem/views.py` — `File`, `Directory` dataclasses + `format_size`

### Phase 5 — Polish (Partial) ✅
- `spaces/core.py` — Spaces stub (get_current_desktop, is_window_on_current_desktop)
- `install_scripts/install.sh` — launchd agent installer
- `install_scripts/uninstall.sh` — launchd agent remover
- `install_scripts/com.lotus.botservice.plist` — launchd plist template
- Tests started: `test_desktop_utils.py`, `test_filesystem_views.py`, `test_filesystem_service.py`, `test_analytics.py`, `test_paths.py`, `test_shell_executor.py`, `test_permissions.py`, `test_spaces.py`

### Telegram Bot ✅
- `src/mac_mcp/telegram_bot.py` (1090 lines) — full bot implementation:
  - Auth via `TELEGRAM_ALLOWED_USER_IDS`
  - Commands: `/start`, `/help`, `/status`, `/screenshot`, `/logs`
  - Natural-language commands: `open`, `close`, `switch`, `run`, `bash`, `find`, `send`, `delete`, `screenshot`, `lock`, `sleep`, `shutdown`, `restart`, `kill`, `ps`, `clipboard`, `copy`, `paste`, `search`, `download`, `dashboard`, `shortcut`, `set`, `memory list`, `forget`
  - Inline keyboard menus for file selection and YouTube quality
  - Ollama AI chat fallback via local HTTP API
  - Battery alert background thread
  - Clipboard tracker background thread
  - Confirmation prompts for destructive operations
  - Activity logging + stats tracking

### Bot Service ✅
- `bot_service.py` — standalone background process manager
  - PID file management
  - Signal handling (SIGTERM, SIGINT)
  - Auto-restart with exponential backoff (up to 5 retries)
  - Reads config from `config.json`

### Control Panel ✅
- `app.py` — CustomTkinter GUI
  - First-time setup screen (token, allowed user IDs, name, Ollama model)
  - Control panel with start/stop bot buttons
  - Real-time status polling every 5 seconds
  - Live log viewer (tails `bot_service.log`)
  - Start-on-login toggle (installs/removes launchd agent)
  - Settings + Reset buttons
  - Hides to background on window close (bot keeps running)

---

## File Structure

```
Mac-MCP/
├── app.py                          ← GUI control panel (CustomTkinter)
├── bot_service.py                  ← Background bot process manager
├── pyproject.toml                  ← Dependencies + build config
├── config.json                     ← Runtime config (created by app.py)
├── .env                            ← Dev env vars template
│
├── assets/
│   ├── lotus_logo.png
│   ├── logo_white.png
│   ├── banner.png
│   └── bg_pond.png
│
├── install_scripts/
│   ├── install.sh                  ← launchd agent installer
│   ├── uninstall.sh                ← launchd agent remover
│   └── com.lotus.botservice.plist  ← launchd plist template
│
├── src/mac_mcp/
│   ├── __init__.py
│   ├── __main__.py                 ← FastMCP CLI entrypoint
│   ├── analytics.py
│   ├── config.py
│   ├── paths.py
│   ├── permissions.py
│   ├── telegram_bot.py             ← Full Telegram bot
│   │
│   ├── ax/                         ← macOS Accessibility API wrapper
│   │   ├── core.py
│   │   ├── controls.py
│   │   ├── enums.py
│   │   └── events.py
│   │
│   ├── desktop/                    ← Desktop orchestration
│   │   ├── service.py
│   │   ├── screenshot.py
│   │   ├── shell.py
│   │   ├── utils.py
│   │   └── views.py
│   │
│   ├── tree/                       ← AX accessibility tree
│   │   ├── service.py
│   │   ├── views.py
│   │   └── config.py
│   │
│   ├── filesystem/
│   │   ├── service.py
│   │   └── views.py
│   │
│   ├── launcher/
│   │   ├── app_launcher.py
│   │   ├── app_registry.py
│   │   └── detection.py
│   │
│   ├── spaces/
│   │   └── core.py                 ← Spaces stub (Option A)
│   │
│   ├── watchdog/
│   │   └── service.py
│   │
│   └── tools/                      ← MCP tool definitions (11 groups)
│       ├── __init__.py
│       ├── app.py
│       ├── clipboard.py
│       ├── defaults.py
│       ├── filesystem.py
│       ├── input.py
│       ├── multi.py
│       ├── notification.py
│       ├── process.py
│       ├── scrape.py
│       ├── shell.py
│       └── snapshot.py
│
└── tests/
    ├── conftest.py
    ├── test_analytics.py
    ├── test_desktop_utils.py
    ├── test_desktop_views.py
    ├── test_filesystem_service.py
    ├── test_filesystem_views.py
    ├── test_paths.py
    ├── test_permissions.py
    ├── test_shell_executor.py
    └── test_spaces.py
```

---

## Data Flow

```
User (Telegram) ──→ telegram_bot.py ──→ mac_mcp tools ──→ macOS APIs
                        ↕
                  Ollama (local LLM)
                        ↕
                    config.json
```

```
app.py (GUI) ──→ bot_service.py ──→ telegram_bot.py
    ↕
launchd agent (start on login)
```

---

## Not Yet Done

| Item | File | Notes |
|---|---|---|
| Tests complete | `tests/` | ~40% done; views, filesystem, shell passing — AX/screenshot need mocks |
| CLAUDE.md | `CLAUDE.md` | Developer guide for Claude Code sessions |
| README.md | `README.md` | User-facing install + usage docs |
| CI workflow | `.github/workflows/ci.yml` | GitHub Actions on `macos-latest` |
| PyInstaller bundle | `Lotus.spec` | Build distributable `.app` |
| Menu bar icon | `app.py` | NSStatusItem so app lives in macOS menu bar |
| Ollama model picker | `app.py` | Dropdown that auto-fetches from `ollama list` |
| Browser tool | `tools/browser.py` | Playwright-based web control (partially planned) |
| Spaces Option B | `spaces/core.py` | Private CGS SPI for real desktop filtering |

---

## How to Run

```bash
# 1. Install dependencies
uv sync

# 2. Launch the GUI — first run will ask for Telegram token + Ollama model
python app.py

# 3. Or run the bot directly (no GUI)
python bot_service.py

# 4. Or start the MCP server for Claude Desktop
uv run mac-mcp
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "mac-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/Mac-MCP", "run", "mac-mcp"]
    }
  }
}
```
