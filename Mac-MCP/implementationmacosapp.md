# Lotus macOS App — Implementation Plan

**Goal:** Turn `bot_service.py` into a proper macOS LaunchAgent service under the name
"Lotus", and replace `app.py` (CustomTkinter) with a native Swift macOS app that talks
to the running service via a local HTTP control API.

Chat (Telegram bot) is NOT replicated in the app — it works as-is through Telegram.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  User's Mac                                                  │
│                                                              │
│  ┌──────────────────┐         HTTP on              ┌──────────────────────────┐
│  │  Lotus.app       │   localhost:40510            │  Lotus Service           │
│  │  (Swift/SwiftUI) │◄────────────────────────────►│  (Python LaunchAgent)    │
│  │                  │                              │                          │
│  │  • Menu bar icon │  GET  /api/status            │  com.lotus.botservice    │
│  │  • Setup wizard  │  GET  /api/logs              │                          │
│  │  • Control panel │  POST /api/restart           │  ┌──────────────────┐   │
│  │  • Log viewer    │  POST /api/stop              │  │  Telegram Bot    │   │
│  │  • Settings      │  GET  /api/config            │  │  (unchanged)     │   │
│  └──────────────────┘  POST /api/config            │  └──────────────────┘   │
│                                                    │                          │
│  launchctl ──────────────────────────────────────► │  PID file, log file     │
│  (start / stop / enable-at-login)                  └──────────────────────────┘
│                                                              │
│                                                    ┌─────────▼────────────┐
│                                                    │  MCP Server           │
│                                                    │  (FastMCP / mac-mcp)  │
│                                                    └──────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

The Swift app never touches the Telegram network directly. It only manages the service
(start, stop, restart, configure) and displays live log output.

---

## Component Breakdown

### 1. Lotus Service (Python — modified `bot_service.py`)

Runs as a macOS LaunchAgent: `com.lotus.botservice`

**Responsibilities (unchanged):**
- Telegram bot lifecycle (auto-restart with backoff)
- Writes PID to `~/Library/Application Support/Lotus/lotus_bot.pid`
- Writes logs to `~/Library/Application Support/Lotus/logs/bot_service.log`

**Added: lightweight control HTTP server**
- Starts an `aiohttp` server on `127.0.0.1:40510` alongside the bot
- Runs on a background asyncio task inside the same event loop as the bot
- Exposes a REST API for the Swift app

```
GET  /api/status   → service health, uptime, telegram status, ollama status
GET  /api/logs     → last N lines of log file (query param: lines=100)
GET  /api/config   → current config (token is redacted)
POST /api/config   → update config fields (requires service restart to take effect)
POST /api/restart  → graceful restart of the bot (not the control server)
POST /api/stop     → shut down the entire service (launchd will restart if KeepAlive)
GET  /api/version  → service version string
```

**Control port file:**
`~/Library/Application Support/Lotus/control.port` — written at startup so the Swift app
always knows the current port even if it's overridden by env var.

---

### 2. LaunchAgent Plist (`com.lotus.botservice`)

Location: `~/Library/LaunchAgents/com.lotus.botservice.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lotus.botservice</string>

    <key>ProgramArguments</key>
    <array>
        <string>/path/to/uv</string>
        <string>run</string>
        <string>python</string>
        <string>/path/to/Mac-MCP/bot_service.py</string>
    </array>

    <key>RunAtLoad</key>
    <false/>                      <!-- Swift app controls when it starts -->

    <key>KeepAlive</key>
    <false/>                      <!-- No auto-restart; app handles that -->

    <key>WorkingDirectory</key>
    <string>/path/to/Mac-MCP</string>

    <key>StandardOutPath</key>
    <string>~/Library/Application Support/Lotus/logs/bot_service.log</string>

    <key>StandardErrorPath</key>
    <string>~/Library/Application Support/Lotus/logs/bot_service.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>LOTUS_CONTROL_PORT</key>
        <string>40510</string>
    </dict>
</dict>
</plist>
```

**Service lifecycle commands the Swift app uses:**
```
launchctl bootstrap  gui/$(id -u) ~/Library/LaunchAgents/com.lotus.botservice.plist
launchctl bootout    gui/$(id -u)/com.lotus.botservice
launchctl kickstart  gui/$(id -u)/com.lotus.botservice
launchctl kill       SIGTERM gui/$(id -u)/com.lotus.botservice
launchctl print      gui/$(id -u)/com.lotus.botservice   ← for status
```

---

### 3. Lotus.app (Swift / SwiftUI)

**Identity:**
| Field | Value |
|---|---|
| Bundle ID | `com.lotus.controlpanel` |
| App name | Lotus |
| Minimum macOS | 13.0 (Ventura) |
| UI framework | SwiftUI + AppKit |
| Build system | Xcode project or Swift Package |

**App mode:** Background app (no persistent dock icon)
- `LSUIElement = true` in Info.plist hides dock icon by default
- Window appears on first launch (setup) and when user clicks menu bar icon
- Closing the window hides it; app keeps running in menu bar

---

## Swift App Structure

```
ControlPanel/
├── Package.swift                        (or Lotus.xcodeproj)
├── Sources/
│   └── Lotus/
│       ├── LotusApp.swift               @main entry, WindowGroup
│       ├── AppDelegate.swift            NSStatusItem (🌸), window lifecycle
│       │
│       ├── Views/
│       │   ├── ContentView.swift        routes to Setup or ControlPanel
│       │   ├── SetupView.swift          first-launch wizard
│       │   ├── ControlPanelView.swift   main dashboard
│       │   └── Components/
│       │       ├── StatusBadge.swift    reusable running/stopped indicator
│       │       ├── LogConsole.swift     scrollable log viewer
│       │       └── OllamaModelPicker.swift
│       │
│       ├── Services/
│       │   ├── LotusServiceClient.swift  HTTP client for /api/* endpoints
│       │   ├── ServiceManager.swift      launchctl wrapper (start/stop/enable-login)
│       │   ├── OllamaClient.swift        GET localhost:11434/api/tags
│       │   └── AppState.swift            @Observable shared state, polling
│       │
│       └── Models/
│           ├── AppConfig.swift           Codable config, load/save config.json
│           ├── ServiceStatus.swift       Decodable from /api/status
│           └── Theme.swift               color + font constants
│
└── Info.plist                            LSUIElement = true, bundle metadata
```

---

## Screen Designs

### Setup Wizard (first launch or after reset)

```
┌────────────────────────────────────┐
│  [Lotus banner image]              │
│                                    │
│  🌸 Lotus                          │
│  macOS Remote Control Agent        │
│  ─────────────────────────         │
│  Setup                             │
│                                    │
│  Telegram Bot Token                │
│  [_______________________________] │
│                                    │
│  Allowed User IDs (comma-sep)      │
│  [_______________________________] │
│                                    │
│  Your Name                         │
│  [_______________________________] │
│                                    │
│  Ollama Model    [phi3 ▼]  [⟳]     │
│  brew install ollama → ollama pull │
│                                    │
│  ⚠ error message if any           │
│                                    │
│  [    💾 Save & Launch Bot    ]    │
└────────────────────────────────────┘
```

### Control Panel (main view)

```
┌────────────────────────────────────┐
│  🌸 Lotus                          │
│  Hello Jayash 👋                    │
│  🤖 qwen2.5:3b   ← green if alive  │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ 🟢  Bot Status               │  │
│  │     Running  (PID 12345)     │  │
│  └──────────────────────────────┘  │
│                                    │
│  [ ▶  START BOT  ]                 │
│  [ ⏹  STOP BOT   ]   ← disabled   │
│                                    │
│  ─────────────────────────         │
│  🚀 Start on Login    [toggle]     │
│     Auto-launch bot at login       │
│  🔒 Closing hides to menu bar      │
│  ─────────────────────────         │
│                                    │
│  [ ⚙ Settings ]  [ 🔄 Reset ]     │
│                                    │
│  Console Output                    │
│  ┌──────────────────────────────┐  │
│  │[12:01:05] Lotus ready.       │  │
│  │[12:01:06] Bot started PID …  │  │
│  └──────────────────────────────┘  │
│                                    │
│  macOS Remote Control Agent        │
└────────────────────────────────────┘
```

---

## Data Flow

### App → Service Communication

```
Swift LotusServiceClient
    │
    ├─ GET /api/status  (every 5 s via Timer)
    │       → ServiceStatus { running, pid, uptime, telegramOk, ollamaModel, ollamaOk }
    │
    ├─ GET /api/logs?lines=200  (every 1 s when panel visible)
    │       → LogResponse { lines: ["[HH:MM:SS] text", ...] }
    │
    ├─ POST /api/config  (on Settings save)
    │       body: { name, telegram_token, allowed_user_id, model_name }
    │       → { ok: true }
    │
    └─ POST /api/restart  (after config change)
            → { ok: true }
```

### Service Lifecycle (via ServiceManager)

```
Start bot:
  1. Check if plist exists → bootstrap if not
  2. launchctl kickstart gui/$(id -u)/com.lotus.botservice
  3. Wait up to 3 s for /api/status to return { running: true }

Stop bot:
  1. POST /api/stop  (clean shutdown via service API)
  2. Fallback: launchctl kill SIGTERM gui/$(id -u)/com.lotus.botservice

Enable at login:
  1. Write plist with RunAtLoad = true, reload with bootout + bootstrap

Disable at login:
  1. Write plist with RunAtLoad = false, reload
```

---

## File Changes Summary

### Files to modify (Python)

| File | Change |
|---|---|
| `bot_service.py` | Add `start_control_server()` coroutine; run alongside bot loop |
| `install_scripts/com.lotus.botservice.plist` | Update to use `uv run python`, set WorkingDirectory |
| `install_scripts/install.sh` | Update plist template with real paths at install time |

### New Python file

| File | Purpose |
|---|---|
| `src/mac_mcp/control_api.py` | aiohttp app with all `/api/*` endpoints |

### Files to delete (Python)

| File | Reason |
|---|---|
| `app.py` | Replaced by Swift app |

### New Swift project

| Location | Content |
|---|---|
| `ControlPanel/` | Full Swift Package / Xcode project |

---

## API Contract

### `GET /api/status`

```json
{
  "running": true,
  "pid": 12345,
  "uptime_seconds": 3620,
  "telegram_connected": true,
  "ollama_model": "qwen2.5:3b",
  "ollama_reachable": true,
  "service_version": "1.0.0",
  "control_port": 40510
}
```

### `GET /api/logs?lines=100`

```json
{
  "lines": [
    "[12:01:05] Bot service starting…",
    "[12:01:06] Telegram connected",
    "[12:01:07] Ollama reachable: qwen2.5:3b"
  ]
}
```

### `GET /api/config`

```json
{
  "name": "Jayash",
  "telegram_token": "798254****:AAE***",
  "allowed_user_id": "1327255784",
  "model_name": "qwen2.5:3b",
  "created_at": "2026-05-03 04:15:58"
}
```

Token is partially redacted (first 8 chars + `****` + last 6 chars) in GET response.
Full token accepted in POST.

### `POST /api/config`

```json
{
  "name": "Jayash",
  "telegram_token": "7982547653:AAEWm-5WGSyt3GEImjmjZ8mrOGo1CbME1RA",
  "allowed_user_id": "1327255784",
  "model_name": "llama3.2"
}
```

Response: `{ "ok": true }` — caller must call `POST /api/restart` to apply changes.

### `POST /api/restart`

Body: empty. Restarts only the Telegram bot loop (not the control server). Returns
`{ "ok": true }` immediately; poll `/api/status` to confirm reconnection.

### `POST /api/stop`

Body: empty. Shuts down the entire service process cleanly. Returns `{ "ok": true }`
then the process exits (no more responses). The Swift app then uses launchctl to confirm.

---

## Implementation Phases

### Phase 1 — Python Service Hardening (1–2 days)

- [ ] Create `src/mac_mcp/control_api.py` with `aiohttp` server
- [ ] Modify `bot_service.py` to start control server as an asyncio task
- [ ] Write `control.port` file at startup
- [ ] Update `install_scripts/` plist with correct paths and WorkingDirectory
- [ ] Manually test all `/api/*` endpoints with `curl`

Completion check: `curl http://localhost:40510/api/status` returns JSON while bot runs.

### Phase 2 — Swift App Skeleton (2–3 days)

- [ ] Create `ControlPanel/Package.swift` (or Xcode project)
- [ ] `LotusApp.swift` + `AppDelegate.swift` (menu bar icon, window lifecycle)
- [ ] `ContentView.swift` + routing logic
- [ ] `AppConfig.swift` + `ServiceStatus.swift` models
- [ ] `LotusServiceClient.swift` — all HTTP calls
- [ ] `ServiceManager.swift` — launchctl wrapper
- [ ] `AppState.swift` — polling, state publishing

Completion check: App launches, connects to running service, shows status.

### Phase 3 — UI Screens (2–3 days)

- [ ] `SetupView.swift` — full setup wizard with validation
- [ ] `ControlPanelView.swift` — dashboard with all controls
- [ ] `LogConsole.swift` — real-time log tail with auto-scroll
- [ ] `OllamaModelPicker.swift` — async dropdown with refresh
- [ ] `StatusBadge.swift` + `Theme.swift`
- [ ] Accessibility: VoiceOver labels, keyboard navigation

Completion check: Full round-trip — save config in app → service restarts → status
updates in panel.

### Phase 4 — Service Lifecycle Integration (1–2 days)

- [ ] `ServiceManager` start: bootstrap plist → kickstart → poll status
- [ ] `ServiceManager` stop: POST /api/stop + launchctl fallback
- [ ] Enable/disable at login (write plist with RunAtLoad, reload)
- [ ] Handle service not installed (prompt to install on first launch)
- [ ] Handle port conflict detection + fallback port

Completion check: Start/Stop/Login-Toggle all work correctly including Mac restart test.

### Phase 5 — Polish & Distribution (1 day)

- [ ] App icon (Lotus logo → 1024×1024 `AppIcon.appiconset`)
- [ ] Info.plist: `LSUIElement`, `NSHighResolutionCapable`, version strings
- [ ] `install.sh` updated to also install `Lotus.app` into `/Applications`
- [ ] Error handling: service offline banner, config missing state
- [ ] Smooth transitions between Setup and ControlPanel views
- [ ] Notarization / ad-hoc signing notes in README

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| IPC mechanism | HTTP on localhost:40510 | Simple, debuggable with curl, no privilege escalation |
| Service type | LaunchAgent (user-level) | Runs as the logged-in user; can access Accessibility/Screen Recording |
| HTTP library (Python) | `aiohttp` (already a dep via `python-telegram-bot`) | Same event loop as Telegram bot; no extra thread |
| Window style | SwiftUI WindowGroup + `LSUIElement=true` | Native macOS, no dock icon, window persists when hidden |
| Bot command in plist | `uv run python bot_service.py` | Ensures correct virtualenv; falls back to `.venv/bin/python` |
| Log delivery | Pull (GET /api/logs every 1 s) | Simpler than streaming; 1 s lag is acceptable |
| Config storage | `config.json` in Mac-MCP dir (unchanged) | No migration; both Python and Swift read the same file |

---

## Paths Reference

| File | Path |
|---|---|
| Config | `{Mac-MCP}/config.json` |
| PID file | `~/Library/Application Support/Lotus/lotus_bot.pid` |
| Control port | `~/Library/Application Support/Lotus/control.port` |
| Bot log | `~/Library/Application Support/Lotus/logs/bot_service.log` |
| App log | `~/Library/Application Support/Lotus/logs/lotus_app.log` |
| LaunchAgent plist | `~/Library/LaunchAgents/com.lotus.botservice.plist` |
| App bundle | `/Applications/Lotus.app` (or `{Mac-MCP}/Lotus.app` for dev) |

---

## What the Swift App Does NOT Do

- No Telegram chat UI — Telegram app handles all conversations
- No MCP server management — `mac-mcp` is a separate CLI tool
- No file browser / process list — those are MCP tools, not app features
- No media player / download UI — Telegram bot handles those commands
- No Ollama chat — Telegram bot's AI fallback handles that

The Swift app is purely a **service management panel**: configure credentials,
start/stop the background service, and watch logs.
