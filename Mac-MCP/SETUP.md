# Mac-MCP Setup Guide

Mac-MCP is an AI-powered macOS desktop control agent with three components:

| Component | What it does |
|-----------|-------------|
| **MCP Server** (`mac-mcp`) | FastMCP server that exposes macOS desktop tools to AI agents |
| **Bot Service** (`bot_service.py`) | Telegram bot + HTTP control API, runs as a LaunchAgent |
| **Lotus.app** | Native Swift menu-bar app that manages the bot service |

---

## Prerequisites

| Requirement | Install |
|-------------|---------|
| macOS 13 Ventura or later | — |
| Python 3.13 | `brew install python@3.13` |
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Xcode Command Line Tools | `xcode-select --install` |
| [Ollama](https://ollama.com) (optional, for AI chat) | `brew install ollama` |
| Telegram Bot Token | [@BotFather](https://t.me/BotFather) on Telegram |

---

## 1 — Clone and Install Python Dependencies

```bash
git clone <repo-url>
cd Mac-MCP

# Install all dependencies into .venv
uv sync
```

This creates `.venv/` and installs all packages from `pyproject.toml`.

---

## 2 — Configure the Bot

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Screenshot backend (auto is fine for most setups)
MAC_MCP_SCREENSHOT_BACKEND=auto

# Set to false to disable anonymous telemetry
ANONYMIZED_TELEMETRY=true
```

Bot credentials live in `config.json` (created by Lotus.app or manually):

```json
{
  "name": "Your Name",
  "telegram_token": "123456:ABC-DEF...",
  "allowed_user_id": "123456789",
  "model_name": "phi3",
  "created_at": "2026-01-01 00:00:00"
}
```

---

## 3 — Grant macOS Permissions

The MCP server and bot service need these permissions — grant them in **System Settings → Privacy & Security**:

- **Accessibility** — for simulating keyboard/mouse input
- **Screen Recording** — for screenshots
- **Files and Folders** (or Full Disk Access) — for filesystem tools

Run this to open the relevant pane:

```bash
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
```

---

## 4 — Running the MCP Server

The MCP server exposes macOS desktop tools over stdio to any MCP-compatible client (Claude, etc.).

```bash
# Run directly
uv run mac-mcp

# Or with debug logging
MAC_MCP_DEBUG=true uv run mac-mcp
```

### Claude Desktop / Claude Code integration

Add to your MCP config (e.g. `~/.claude/mcp_config.json`):

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

---

## 5 — Running the Bot Service

### Option A — Direct (foreground, for development)

```bash
uv run python bot_service.py
```

The bot starts and opens a local HTTP control API on port 40510.
Check it:

```bash
curl http://127.0.0.1:40510/api/status
```

### Option B — LaunchAgent (background, recommended for daily use)

Install and start as a per-user launchd service:

```bash
bash install_scripts/install.sh
```

The service:
- starts automatically at login (`RunAtLoad = true`)
- restarts on crash (`KeepAlive = false` — no restart loop)
- writes logs to `~/Library/Application Support/Lotus/bot.log`

Other launchctl commands:

```bash
# Start
launchctl kickstart gui/$(id -u)/com.lotus.botservice

# Stop
launchctl kill SIGTERM gui/$(id -u)/com.lotus.botservice

# View logs
tail -f ~/Library/Application\ Support/Lotus/bot.log

# Uninstall
bash install_scripts/uninstall.sh
```

---

## 6 — Building Lotus.app

Lotus.app is the menu-bar GUI for controlling the bot service.

### Build

```bash
cd ControlPanel
bash make_app.sh
```

This:
1. Compiles the Swift package (`swift build -c release`)
2. Assembles `Mac-MCP/Lotus.app` with `Info.plist` and `AppIcon.icns`
3. Ad-hoc signs the bundle

Requirements: Xcode Command Line Tools (Swift compiler + `sips`, `iconutil`, `codesign`).

### Run

```bash
open ../Lotus.app
```

Or move to Applications:

```bash
cp -R ../Lotus.app /Applications/
```

### First Launch

1. If `bot_service.py` is not auto-detected, a folder picker appears — select the `Mac-MCP/` directory.
2. The **Setup** wizard opens — enter your Telegram bot token, allowed user IDs, your name, and select an Ollama model.
3. Click **Save & Launch Bot** — the LaunchAgent is installed and the bot starts.

### Menu Bar

Click the 🌸 icon in the menu bar:
- **Show Lotus** — open the control panel
- **Toggle Bot** — start or stop the bot
- **Quit Lotus** — exit the app (bot keeps running)

Closing the window hides it; the app stays in the menu bar.

---

## 7 — Control API Reference

When the bot service is running, a lightweight HTTP API is available on `localhost:40510` (or the port in `~/Library/Application Support/Lotus/control.port`).

```bash
PORT=$(cat ~/Library/Application\ Support/Lotus/control.port)

# Status
curl http://127.0.0.1:$PORT/api/status

# Last 100 log lines
curl http://127.0.0.1:$PORT/api/logs

# Current config (token redacted)
curl http://127.0.0.1:$PORT/api/config

# Restart bot
curl -X POST http://127.0.0.1:$PORT/api/restart

# Stop bot
curl -X POST http://127.0.0.1:$PORT/api/stop
```

Example `/api/status` response:

```json
{
  "running": true,
  "pid": 1234,
  "uptime": 3601.2,
  "ollama_reachable": true,
  "ollama_model": "phi3"
}
```

---

## 8 — Directory Layout

```
Mac-MCP/
├── bot_service.py          # Telegram bot + control API entry point
├── pyproject.toml          # Python package + dependencies
├── config.json             # Bot credentials (created by setup wizard)
├── .env                    # Environment overrides
│
├── src/mac_mcp/            # Python package
│   ├── __main__.py         # MCP server entry (uv run mac-mcp)
│   ├── control_api.py      # HTTP control API server
│   ├── telegram_bot.py     # Telegram bot logic
│   └── tools/              # MCP tool implementations
│
├── install_scripts/
│   ├── install.sh          # Install + start LaunchAgent
│   ├── uninstall.sh        # Stop + remove LaunchAgent
│   └── com.lotus.botservice.plist  # Plist template
│
├── ControlPanel/           # Swift app (Lotus.app)
│   ├── Package.swift
│   ├── make_app.sh         # Build script → Mac-MCP/Lotus.app
│   └── Sources/Lotus/
│       ├── LotusApp.swift
│       ├── AppDelegate.swift
│       ├── AppState.swift
│       ├── Models/
│       ├── Services/
│       └── Views/
│
├── Lotus.app               # Built app bundle (git-ignored)
└── assets/                 # Logos, banner images
```

---

## 9 — Troubleshooting

**Bot won't start / "plist not installed"**
Run the setup wizard in Lotus.app, or run `bash install_scripts/install.sh` directly.

**Control API not responding**
Check if the service is running: `launchctl print gui/$(id -u)/com.lotus.botservice`
Check logs: `tail -50 ~/Library/Application\ Support/Lotus/bot.log`

**`swift build` fails**
Ensure Xcode CLT is installed: `xcode-select --install`
Check Swift version: `swift --version` (5.9+ required)

**Accessibility / Screen Recording denied**
Open **System Settings → Privacy & Security** and enable the permissions for Terminal (or Lotus.app).

**Ollama model not found**
Pull the model first: `ollama pull phi3`
Check Ollama is running: `ollama list`

**Port conflict on 40510**
Set a different port in the LaunchAgent plist (`LOTUS_CONTROL_PORT`) or re-run `install.sh` with the `controlPort` parameter.

---

## 10 — Uninstall

```bash
# Stop and remove LaunchAgent
bash install_scripts/uninstall.sh

# Remove app data (logs, PID file, port file)
rm -rf ~/Library/Application\ Support/Lotus/

# Remove the app
rm -rf /Applications/Lotus.app
```
