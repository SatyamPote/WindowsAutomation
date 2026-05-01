<div align="center">

<img width="500" height="500" alt="Lotus Logo" src="https://github.com/user-attachments/assets/47150caa-e1dc-4cf7-a351-f06af310194a" />

# 🪷 Lotus

### AI-Powered Windows Control Agent

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%207--11-blue)](https://github.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![MCP](https://img.shields.io/badge/MCP-Lotus-8A2BE2)](https://github.com/SatyamPote/Lotus)

**Control your entire Windows PC remotely through Telegram — powered by AI.**

[Features](#-features) · [Installation](#-installation) · [Commands](#-telegram-bot-commands) · [Music Player](#-music-player) · [MCP Tools](#-mcp-tools-reference)

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Telegram Bot Commands](#-telegram-bot-commands)
- [Music Player](#-music-player)
- [MCP Tools Reference](#-mcp-tools-reference)
- [Environment Variables](#-environment-variables)
- [Startup & Registry](#-startup--registry)
- [Lotus GUI Details](#-lotus-gui--control-panel)
- [Development](#-development)
- [Security](#-security)
- [Known Limitations](#-known-limitations)
- [License & Credits](#-license--credits)

---

## 🔭 Overview

**Lotus** is a two-layer Windows automation system built for power users who want full remote control of their PC from anywhere using Telegram.

| Layer | Name | Purpose |
|:---:|:---:|:---|
| **1** | **Lotus Desktop App** | CustomTkinter GUI — configure, start/stop bot, manage startup |
| **2** | **Lotus / Windows-MCP** | MCP server bridging AI agents to Windows OS (16 automation tools) |

Together they form an end-to-end remote control pipeline:

```
📱 Your Telegram  ──►  🤖 Lotus Bot  ──►  🖥️ Windows MCP Engine  ──►  💻 Your PC
```

> The bot runs as a **fully independent background process**. Closing the GUI does **not** stop the bot — it keeps running silently.

### 👑 Single Owner System
Lotus is built for personal automation. It features a hardcoded **Owner System** to reject unknown contributors:
- **Admin/Owner:** Satyam Pote ([GitHub](https://github.com/SatyamPote))
- **Access Control:** The bot will ONLY respond to your specific Telegram ID. Any unknown ID is strictly rejected.

---

## 🏗️ Architecture

```
WindowsAutomation/
│
├── app.py                  ← Lotus GUI (CustomTkinter control panel)
├── bot_service.py          ← Background bot process (PID-tracked, auto-restart)
├── config.json             ← Runtime config (token, user IDs, name)
├── install_startup.bat     ← Windows startup CLI installer
├── requirements.txt        ← Lotus layer dependencies
│
├── assets/
│   └── lotus_logo.png      ← Brand logo
│
├── data/
│   ├── apps_cache.json     ← Cached installed apps list
│   └── users.json          ← Telegram user store
│
├── storage/                # ⚠️ Auto-cleaned local storage (EXCLUDED from GitHub)
│   ├── audio/              # Downloaded mp3/m4a files
│   ├── videos/             # Downloaded mp4 files
│   ├── images/             # Downloaded image collections
│   ├── files/              # Direct file downloads
│   └── temp/               # Ephemeral logs/cache (auto-deleted)
│
├── logs/                   ← Auto-generated log files
│
└── Windows-MCP/            ← Lotus MCP Engine (sub-project)
    ├── pyproject.toml       ← Package config (v0.7.4)
    └── src/windows_mcp/     ← Main Python package
        ├── __main__.py      ← MCP server (16 tools)
        ├── telegram_bot.py  ← Full Telegram bot
        ├── media/           ← Music player (TUI + mpv)
        ├── desktop/         ← Screenshots, mouse, keyboard
        ├── tree/            ← Windows accessibility tree
        ├── uia/             ← UIAutomation COM wrappers
        ├── launcher/        ← App detection & launch
        ├── contacts/        ← Contact manager
        └── watchdog/        ← UI focus monitor
```

### Process Flow

```
System Boot
    │
    ▼
Registry Run Key (HKCU\...\Run)
    │
    ▼
bot_service.py  ────────────────►  telegram_bot.py (in-process)
    │                                     │
    │  writes PID file                    ▼
    ▼                            Handles Telegram messages
lotus_bot.pid ◄── app.py reads   Executes Windows commands
                  (GUI optional) Auto-restarts on crash (5x backoff)
```

---

## ✨ Features (V2)

### 🤖 Telegram Bot (No API Dependency)
- Remote control your Windows PC from **any device with Telegram**
- **Strict user ID allowlist** — only you can control your PC
- **100% rule-based** — no external AI APIs required (zero cost)
- All commands are **case-insensitive** (`CD`, `cd`, `Cd` all work)
- Time-aware greeting system (morning/afternoon/evening)

### ⚠️ Smart Confirmation System
- Dangerous commands (`shutdown`, `restart`, `delete`, `close all apps`) require **yes/no confirmation**
- **10-second timeout** — if you don't respond, the command is cancelled
- Safe commands execute instantly without confirmation

### 🎵 Music Player (White TUI Terminal)
- Say `play <song>` and a **visible terminal window** opens on your desktop
- **Strictly White Theme**: Clean, high-contrast interface
- **Bulletproof Stop**: Process-tree killing ensures instant cleanup
- Commands: `play`, `pause`, `resume`, `stop`, `next`, `volume up/down`

### 📥 Download Manager
- `download youtube <url>` — Select quality (360p/720p/1080p) or audio-only (MP3)
- `download images <topic>` — Bulk download images from the web
- `download <url>` — Download any file from a URL
- All downloads show progress in a **visible terminal window**
- **Structured Storage:** Saves cleanly to `storage/videos`, `storage/audio`, `storage/files`
- **Auto Clean System:** Automatically deletes `temp/` files every 3 commands and trims oldest files if `storage/` exceeds 2GB!

### 🔊 Voice Output (TTS)
- `speak <text>` — Convert text to speech and send as audio file
- Uses Windows SAPI (pyttsx3) — works offline, no API needed

### 🔗 Multi-Command Support
- Run multiple commands in one message: `open chrome and play music`
- Supports ` and ` and ` then ` as separators
- Each sub-command executes sequentially with individual results

### 🖥️ Desktop Control
- Open any app: `openapp chrome`, `openapp spotify`
- Close apps: `close chrome`, `close all apps`
- Take and send screenshots to Telegram
- Navigate files: `ls`, `cd <folder>`, `open <file>`, `send <file>`

### 📦 Storage (2 GB)
- Auto-cleanup when storage exceeds 2 GB (deletes oldest files to reach 1.5 GB)
- Runs after every file creation and every 3 commands
- `storage status` — shows current usage

### 💬 Messaging
- Send WhatsApp messages: `send hello to John`
- Uses UIAutomation to control WhatsApp Desktop

### 🌐 Web & Search
- `search AI news` — Opens Google search
- `openapp github.com` — Opens websites

### 🗂️ File Management
- Fuzzy search across Downloads, Desktop, Documents
- Open, send (≤50 MB), and delete files with confirmation
- Terminal-like navigation (`ls`, `cd`)

### 🤖 MCP Server (Lotus)
- **16 automation tools** for any MCP-compatible AI client
- Works with Claude Desktop, Perplexity, Gemini CLI, Cursor
- Transport: stdio, SSE, Streamable HTTP
- Latency: **0.2 – 0.9 seconds** per action

---

## 📁 Project Structure

| File | Size | Description |
|:---|:---:|:---|
| `app.py` | 25 KB | Lotus GUI — CustomTkinter control panel |
| `bot_service.py` | 5.4 KB | Background bot runner with PID tracking |
| `config.json` | ~200 B | Runtime config (created on first setup) |
| `requirements.txt` | ~220 B | Pip packages for Lotus layer |
| `install_startup.bat` | 2.1 KB | Interactive startup installer |
| `Windows-MCP/src/windows_mcp/telegram_bot.py` | 50 KB | Full Telegram bot (V2) |
| `Windows-MCP/src/windows_mcp/media/music_player.py` | ~6 KB | Music player controller |
| `Windows-MCP/src/windows_mcp/media/player_tui.py` | ~8 KB | Music TUI (visible terminal) |
| `Windows-MCP/src/windows_mcp/media/downloader.py` | ~6 KB | Download manager (YouTube, images, URLs) |
| `Windows-MCP/src/windows_mcp/media/download_tui.py` | ~9 KB | Download TUI (visible terminal progress) |

---

## 📥 Installation

### System Requirements

| Requirement | Details |
|:---|:---|
| **OS** | Windows 7, 8, 8.1, 10, or 11 |
| **Python** | 3.13 or higher |
| **UV** | Astral UV package manager |
| **Language** | Windows set to English (for App-Tool) |

### Step 1 — Install Python 3.13+

Download from [python.org](https://python.org). Check **"Add Python to PATH"** during install.

### Step 2 — Install UV Package Manager

```powershell
pip install uv
```

Or using PowerShell:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### Step 3 — Clone the Repository

```bash
git clone https://github.com/SatyamPote/Lotus.git
cd Lotus
```

### Step 4 — Install Dependencies

```powershell
# Lotus layer
pip install -r requirements.txt

# Lotus / MCP layer
cd Windows-MCP
uv sync
```

### Step 5 — Install Music Player Binaries (Optional)

Place these in `Windows-MCP/bin/` or add to system PATH:

| Binary | Download |
|:---|:---|
| `mpv.exe` | [mpv.io](https://mpv.io/installation/) |
| `yt-dlp.exe` | [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases) |

### Step 6 — First-Time Setup

```powershell
python app.py
```

The setup wizard will ask for:

1. **Telegram Bot Token** — get from [@BotFather](https://t.me/BotFather)
2. **Your Telegram User ID(s)** — find with [@userinfobot](https://t.me/userinfobot)
3. **Your Name** — for personalised greetings

### Step 7 — Enable Windows Startup (Optional)

Run `install_startup.bat` and select option **1**, or use the toggle in the app (auto-enabled).

---

## ⚙️ Configuration

### config.json (auto-generated on first setup)

```json
{
  "bot_token": "123456:ABC-DEF...",
  "allowed_user_ids": "123456789,987654321",
  "user_name": "YourName",
  "created_at": "2026-05-01 13:00:00"
}
```

### Windows-MCP/.env

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ALLOWED_USER_IDS=123456789

# Lotus — No external AI APIs needed (100% rule-based)
```

> ⚠️ **Never commit `.env` to a public repository!**

---

## 🤖 Telegram Bot Commands (V2)

> All commands are **case-insensitive** (`cd`, `CD`, `Cd` all work).  
> Dangerous commands require **yes/no confirmation** with a 10-second timeout.  
> `/help` sends a **3-page detailed guide** with examples for every command.

### Slash Commands

| Command | Description |
|:---|:---|
| `/start` | Welcome screen with 8 quick-action buttons + real examples |
| `/help` | 3-page detailed command guide with usage examples |
| `/owner` | Developer info — Satyam Pote, GitHub, email, project |
| `/admin` | Same as `/owner` |
| `/logs` | View last 20 activity log entries |
| `/storage` | Show storage usage (current MB / 2048 MB) + file count |
| `/status` | Live CPU & RAM usage |

#### `/start` Preview
```
Hello Satyam 👋
Welcome to Lotus — your Windows Control Agent.

🎵 Music     — play kesariya
📥 Downloads — download youtube <url>
🖥️ Apps      — openapp chrome
📁 Files     — find report.pdf
🔊 Voice     — speak hello world
📸 Screenshot— take screenshot
🔗 Multi-cmd — open chrome and play music

⚡ 100% local — no AI APIs needed
🔒 Only you can control your PC

[🎵 Music] [📥 Downloads] [🖥️ Apps]
[📁 Files] [📸 Screenshot] [⚙️ System]
[📊 Status] [📋 Full Help]
```

---

### 🎵 Music Commands

| Command | Description |
|:---|:---|
| `play <song>` | Search YouTube and play — **opens visible terminal player** |
| `pause` | Pause current playback |
| `resume` | Resume paused playback |
| `stop` | Stop music and close the player window |
| `next` | Skip to next track |
| `volume up` | Increase volume |
| `volume down` | Decrease volume |

**Usage Examples:**
```
play kesariya
play arijit singh mashup
play lofi hip hop beats
pause
resume
volume up
stop
```

---

### 📥 Download Commands

| Command | Description |
|:---|:---|
| `download youtube <url>` | Download video — bot asks quality (360p/720p/1080p) or audio MP3 |
| `download images <topic>` | Bulk download images by topic |
| `download <url>` | Download any file from a URL |
| `download cancel` | Cancel active download |

**Usage Examples:**
```
download youtube https://youtu.be/dQw4w9WgXcQ
download images sports cars
download images nature wallpaper
download https://example.com/report.pdf
download cancel
```

**YouTube Download Flow:**
```
You:  download youtube https://youtu.be/xyz
Bot:  🎬 YouTube Download
      🔗 https://youtu.be/xyz
      Select quality:
      [360p] [720p] [1080p]
      [🎵 Audio Only (MP3)]
You:  (tap 720p)
Bot:  📥 Downloading YouTube
      🖥️ A download window has opened on your desktop.
```

> Downloads open a **visible terminal window** with real-time progress (speed, ETA, %).  
> Files saved to `storage/downloads/` or `storage/images/`.

---

### 🔊 Voice Commands

| Command | Description |
|:---|:---|
| `speak <text>` | Convert text to speech — sends audio file via Telegram |

**Usage Examples:**
```
speak hello how are you
speak meeting starts at 3pm
speak good morning everyone
```

---

### 🖥️ App Commands

| Command | Description |
|:---|:---|
| `openapp <name>` | Open any application |
| `close <name>` | Close an app by name |
| `close all apps` | Close all user apps (⚠️ confirmation required) |

**Usage Examples:**
```
openapp chrome
openapp spotify
openapp notepad
openapp vscode
close chrome
close all apps
```

---

### 📁 File Commands

| Command | Description |
|:---|:---|
| `ls` | List files in current folder |
| `cd <folder>` | Navigate into folder |
| `cd ..` | Go up one directory |
| `find <file>` | Fuzzy search across Downloads, Desktop, Documents |
| `open <file>` | Open file with default app |
| `send <file>` | Upload file to Telegram (≤50 MB) |
| `delete <file>` | Delete file (⚠️ confirmation required) |

**Usage Examples:**
```
ls
cd Downloads
cd ..
find report
find budget.xlsx
open resume.pdf
send project.zip
delete old_report.pdf
```

**Delete Flow:**
```
You:  delete report.pdf
Bot:  ⚠️ Confirm delete report.pdf?
      Reply yes to confirm.
You:  yes
Bot:  ✅ Deleted: report.pdf
```

---

### ⚡ System Commands

| Command | Description |
|:---|:---|
| `take screenshot` | Capture and send screenshot |
| `send screenshot` | Send most recent screenshot |
| `lock` | Lock the workstation |
| `sleep` | Put PC to sleep |
| `shutdown` | Shutdown PC (⚠️ confirmation) |
| `restart` | Restart PC (⚠️ confirmation) |
| `search <query>` | Open Google search in browser |
| `send <msg> to <name>` | Send WhatsApp message |
| `show logs` / `clear logs` | View/clear activity logs |
| `storage status` | Show storage usage |

**Usage Examples:**
```
take screenshot
lock
search python tutorial
send hello to John
show logs
storage status
```

**Shutdown Flow:**
```
You:  shutdown
Bot:  ⚠️ Are you sure you want to shutdown?
      Reply yes within 10 seconds to confirm, or no to cancel.
You:  yes
Bot:  ✅ System shutdown initiated.
```

---

### 🔗 Multi-Command

Run multiple commands in **one message** using `and` or `then`:

| Example | What Happens |
|:---|:---|
| `open chrome and play music` | Opens Chrome → plays music |
| `take screenshot then send screenshot` | Captures → sends |
| `close chrome and openapp spotify` | Closes Chrome → opens Spotify |
| `openapp notepad and openapp chrome` | Opens both apps |

> Max 5 sub-commands per message. Each executes sequentially with individual results.

---

## 🎵 Music Player

When you type `play <song>` in Telegram, a **visible CMD window** opens on your desktop running a TUI (Terminal User Interface) music player.

### What You See on Screen (Strictly White Theme)

```
  ╔═════════════════════════════════════════════════════════════╗
  ║                    LOTUS  MUSIC  PLAYER                    ║
  ╚═════════════════════════════════════════════════════════════╝

  [ >> PLAYING ]

  Track  : Kesariya - Arijit Singh | Brahmastra

  ─────────────────────────────────────────────────────────────

  0:00 [░░░░░░░░░█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] ?:??

  Volume : [████████████████████] 100%

  ─────────────────────────────────────────────────────────────

  Controls (via Telegram):
    play <song>      Play a new song
    pause            Pause playback
    resume           Resume playback
    stop             Stop & close player
    next             Skip track
    volume up/down   Adjust volume
```

### Advanced Reliability
- **Visible Feedback**: You can always see exactly what's playing on your PC screen.
- **Process-Tree Killer**: When you say `stop`, the bot doesn't just ask nicely — it scans the entire system for orphaned player windows and force-closes them along with the media engine.
- **Zero-Color ANSI**: Designed to work perfectly in any terminal (CMD, PowerShell, Windows Terminal) with zero weird color codes.

---

### Required Binaries

| Binary | Source |
|:---|:---|
| `mpv.exe` | [mpv.io](https://mpv.io) or place in `Windows-MCP/bin/` |
| `yt-dlp.exe` | [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases) or place in `Windows-MCP/bin/` |

---

## 🔨 MCP Tools Reference

Lotus exposes **16 tools** to any MCP-compatible AI client:

| Tool | Description |
|:---|:---|
| `Click` | Click at given screen coordinates |
| `Type` | Type text into a UI element |
| `Scroll` | Scroll vertically or horizontally |
| `Move` | Move mouse or drag to coordinates |
| `Shortcut` | Press keyboard shortcuts (Ctrl+C, Alt+Tab, etc.) |
| `Wait` | Pause execution for a defined duration |
| `Screenshot` | Fast screenshot with cursor + window list |
| `Snapshot` | Full UI tree capture with element IDs |
| `App` | Launch, resize, move, or switch apps |
| `Shell` | Execute PowerShell commands |
| `Scrape` | Scrape entire webpage content |
| `MultiSelect` | Select multiple items with bulk coordinate resolution |
| `MultiEdit` | Type into multiple fields at once |
| `Clipboard` | Read or set clipboard content |
| `Process` | List or kill processes |
| `Notification` | Send Windows toast notification |
| `Registry` | Read, write, delete Registry values |

### MCP Client Integration Example

```json
{
  "mcpServers": {
    "windows-mcp": {
      "command": "uvx",
      "args": ["windows-mcp"],
      "env": {
        "WINDOWS_MCP_SCREENSHOT_SCALE": "0.5",
        "ANONYMIZED_TELEMETRY": "false"
      }
    }
  }
}
```

### Supported Clients

Claude Desktop · Claude Code · Perplexity · Gemini CLI · Qwen Code · Codex CLI · Cursor

---

## 🌍 Environment Variables

### MCP Server

| Variable | Default | Description |
|:---|:---:|:---|
| `WINDOWS_MCP_SCREENSHOT_SCALE` | `1.0` | Scale 0.1–1.0 (use 0.5 on 4K) |
| `WINDOWS_MCP_SCREENSHOT_BACKEND` | `auto` | `auto` / `dxcam` / `mss` / `pillow` |
| `WINDOWS_MCP_PROFILE_SNAPSHOT` | off | Set `1` for timing logs |
| `WINDOWS_MCP_DEBUG` | `false` | Set `1` for DEBUG logs |
| `ANONYMIZED_TELEMETRY` | `true` | Set `false` to disable |

### Telegram Bot

| Variable | Required | Description |
|:---|:---:|:---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token from @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | ✅ | Comma-separated user IDs |

> **Lotus does not require any AI API keys.** All commands are parsed using a fast, rule-based engine.

---

## 🤖 Local AI (Ollama) — Optional Extension

Lotus works **100% without AI APIs**, but if you want to add AI-powered natural language understanding in the future, you can use **Ollama** for free, private, local AI:

### Recommended Small Models

| Model | Size | Best For | Command |
|:---|:---|:---|:---|
| **Phi-3 Mini** | 2.3 GB | Speed & Low RAM | `ollama run phi3` |
| **Llama 3 (8B)** | 4.7 GB | Smartest logic | `ollama run llama3` |
| **Mistral** | 4.1 GB | General tasks | `ollama run mistral` |

### Setup (for future AI features)
1. Install [Ollama](https://ollama.com).
2. Download your preferred model: `ollama pull phi3`.
3. Ollama runs locally at `http://localhost:11434`.

---

## 🚀 Startup & Registry

Lotus registers the **bot service** to auto-start on Windows login:

```
Registry Key  : HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Value Name    : LotusControlPanel
Value Data    : "C:\...\pythonw.exe" "C:\...\bot_service.py"
```

> Only `bot_service.py` runs at startup — lightweight and silent. The GUI is opened manually.

### install_startup.bat Options

| Option | Action |
|:---:|:---|
| `1` | Enable startup (add registry entry) |
| `2` | Disable startup (remove entry) |
| `3` | Start bot now (background) |
| `4` | Open control panel (GUI) |
| `5` | Exit |

---

## 🎨 Lotus GUI — Control Panel

### First-Time Setup Screen
- Collects: Bot Token, User IDs, Name
- Validates token format
- Saves to `config.json`

### Control Panel Screen
- **Bot Status Card** — live: Running (PID) / Stopped
- **Start / Stop Bot** buttons
- **Startup Toggle** — permanently enabled
- **Change Settings / Reset Setup** utilities
- **Console Output** — live timestamped log
- **Status polling** every 5 seconds

### Color Palette

| Token | Hex | Usage |
|:---|:---:|:---|
| Background | `#080808` | Main window |
| Card | `#111111` | Panel surfaces |
| Accent Blue | `#3b82f6` | Primary accent |
| Green | `#3fb950` | Running / Start |
| Red | `#f85149` | Stopped / Stop |
| Yellow | `#e3a54a` | Warnings |

---

## 🛠️ Development

### Commands

```bash
uv sync                    # Install dependencies
uv run windows-mcp         # Run MCP server
ruff format .              # Format code
ruff check .               # Lint code
pytest                     # Run tests
```

### Code Style

| Rule | Value |
|:---|:---|
| Linter | Ruff (line-length 100) |
| Naming | `snake_case` functions, `PascalCase` classes |
| Type Hints | Required on all signatures |
| Docstrings | Google style |

### Package Info

| Field | Value |
|:---|:---|
| Name | `windows-mcp` |
| Version | `0.7.4` |
| Python | `>=3.13` |
| CLI 1 | `windows-mcp` |
| CLI 2 | `Lotus-bot` |

---

## 🔒 Security

> ⚠️ **Lotus operates with FULL SYSTEM ACCESS. Irreversible operations are possible.**

- **User ID Allowlist** — only authorized users can send commands
- **Confirmation Dialogs** — dangerous commands require button press
- **No Credential Logging** — API keys never written to logs
- **Anonymous Telemetry** — only tool names + errors (opt-out with `ANONYMIZED_TELEMETRY=false`)
- **Recommended** — use VM or Windows Sandbox for MCP server

### Sensitive Files (Never Commit)

| File | Contains |
|:---|:---|
| `.env` | API keys and tokens |
| `config.json` | Bot token + user IDs |
| `logs/` | Command history |

---

## ⚠️ Known Limitations

| Limitation | Status |
|:---|:---:|
| Cannot select specific text ranges in paragraphs | ⌛ In progress |
| Type-Tool types entire text as one block | ⌛ In progress |
| Cannot play video games | ❌ Not planned |
| First MCP startup takes 1–2 min | Expected |

---

## 📜 License & Credits

**MIT License** — see [LICENSE](LICENSE) for details.

### Built With

| Library | Purpose |
|:---|:---|
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | Telegram bot framework |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Modern GUI widgets |
| [FastMCP](https://github.com/jlowin/fastmcp) | MCP server framework |
| [mpv](https://mpv.io) | Media player |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | YouTube audio extraction |
| [psutil](https://github.com/giampaolo/psutil) | Process management |
| [Pillow](https://python-pillow.org) | Image processing |

### Citation

```bibtex
@software{
  author    = {Satyam Pote},
  title     = {Lotus: AI Windows Remote Control via Telegram},
  year      = {2024},
  publisher = {GitHub},
  url       = {https://github.com/SatyamPote/Lotus}
}
```

---

<div align="center">

Made with ❤️ by [Satyam Pote](https://github.com/SatyamPote)

[![GitHub](https://img.shields.io/badge/follow-%40SatyamPote-181717?logo=github&style=flat)](https://github.com/SatyamPote)
[![LinkedIn](https://img.shields.io/badge/Connect-%40SatyamPote-0A66C2?logo=linkedin&style=flat)](https://www.linkedin.com/in/satyam-pote)

</div>
