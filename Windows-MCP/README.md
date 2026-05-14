<div align="center">

# 🌸 Lotus for Windows

### **Native Windows AI control agent — Telegram-driven, locally hosted, system-tray native.**

[![Version](https://img.shields.io/badge/version-v2.2.0--STABLE-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/SatyamPote/Lotus/releases)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Installer](https://img.shields.io/badge/Installer-Inno%20Setup-FF6B35?style=for-the-badge)](https://jrsoftware.org/isinfo.php)
[![Lead](https://img.shields.io/badge/Lead-@SatyamPote-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/SatyamPote)

⬅ **Back to project root:** [README.md](../README.md)
🍎 **Looking for the Mac version?** [Mac-MCP/README.md](../Mac-MCP/README.md)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Windows-Only Features](#-windows-only-features)
- [Telegram Command Menu](#-telegram-command-menu)
- [Natural-Language Command Examples](#-natural-language-command-examples)
- [Installation](#-installation)
- [First-Run Configuration](#%EF%B8%8F-first-run-configuration)
- [System-Tray Controls](#-system-tray-controls)
- [Architecture (Windows Specifics)](#-architecture-windows-specifics)
- [File Layout](#-file-layout)
- [Environment Variables](#%EF%B8%8F-environment-variables)
- [Troubleshooting](#-troubleshooting)
- [Building from Source](#%EF%B8%8F-building-from-source)
- [Roadmap (Windows)](#%EF%B8%8F-roadmap-windows)
- [Lead](#-lead)

For the cross-platform feature tour, command reference, architecture
overview, configuration schema, and contributors list, see the
[**root README**](../README.md).

---

## Overview

**Lotus for Windows** is the original Lotus implementation — an
autonomous AI agent that runs as a hidden background process and exposes
your Windows PC to Telegram. It's deployed via a fully autonomous
Inno Setup installer (`LotusSetup.exe`) that handles every prerequisite
end-to-end: Python, Ollama, model download, and Telegram bot
configuration.

The Windows build is at **v2.2.0-STABLE** and is the more mature of
the two platforms. Years of iteration have produced a hardened command
engine, deep WhatsApp UI automation, native screen-capture integration,
and battery / status alerting that surfaces directly in your Telegram
chat.

---

## 🚀 Windows-Only Features

These are in addition to the [shared feature tour](../README.md#-feature-tour).

### 💬 WhatsApp Automation
Send WhatsApp messages and attachments directly from Telegram using
deep UI automation against the WhatsApp desktop app. Contacts are
managed in `contacts.json` and listed via `/contacts`.

### 🎙️ Voice Control via Telegram
Toggle the assistant's voice on/off remotely or instantly mute the
currently-playing voice clip:
- `/voice on` / `/voice off` / `/voice stop`
- `voice on` / `voice off` (natural language equivalents)

### 🎵 Music Playlists
Create, manage, and play entire song queues with the `playlist`
command family:
- `/playlist` — list saved playlists
- `play playlist chill` — start sequential playback
- Sessions persist across restarts.

### 📱 Native Telegram Menu
Lotus registers commands directly in your Telegram bot menu so the
common ones are one tap away on mobile. Currently registered:

| Command | Action |
|---|---|
| `/start` | Show interactive dashboard buttons |
| `/help` | Show the full command and capability list |
| `/version` | Check for updates from GitHub |
| `/voice` | Voice control: on / off / stop |
| `/playlist` | List your music playlists |
| `/status` | Real-time CPU and RAM usage |
| `/admin` | Show creator and owner details |
| `/contacts` | List all saved WhatsApp contacts |
| `/storage` | Check the managed storage usage |

### 🔋 Battery & Status Alerts
Get an automatic Telegram alert when your laptop battery drops below
20% or hits a critical threshold — useful when the laptop is in another
room and you forgot to plug it in.

### 🛡️ Autonomous Inno Setup Installer
The crown jewel of the Windows build:

- Detects whether Python 3.13 is installed; if not, downloads + installs silently.
- Installs Ollama and pulls your chosen model in the background.
- Writes `config.json` from the installer wizard answers.
- Registers a hidden scheduled task that auto-starts at logon.
- Creates Start menu shortcuts and a clean uninstaller.

---

## 📋 Telegram Command Menu

See the [shared command reference](../README.md#%EF%B8%8F-command-reference)
for the cross-platform commands. The Windows build adds:

| Command | What it does |
|---|---|
| `whatsapp send <contact> <message>` | Drives the WhatsApp desktop app via UIA |
| `whatsapp attach <contact> <file>` | Sends a file via WhatsApp |
| `download youtube <url>` | Pulls audio or video via `yt-dlp` |
| `record screen <seconds>` | Native ffmpeg screen capture |
| `voice on` / `voice off` / `stop voice` | Voice toggle / mute |

---

## 🗨️ Natural-Language Command Examples

Lotus's priority router catches plain-English variants without slashes:

- `"voice on"` / `"voice off"` — Toggle assistant voice
- `"stop voice"` — Mute the currently playing assistant voice
- `"record screen 10"` — Capture 10 seconds of desktop video
- `"play playlist party"` — Start sequential music playback
- `"take a screenshot"`
- `"download youtube https://..."`
- `"shutdown pc"` / `"restart pc"`
- `"close notepad"`

---

## 📦 Installation

### Prerequisites
**Lotus's installer handles all of these automatically — listed here for transparency.**

| Need | Auto-installed? |
|---|---|
| Windows 7 / 8 / 10 / 11 | (must be present) |
| Python 3.13 | ✅ Silent install if missing |
| [Ollama](https://ollama.com) | ✅ Silent install if missing |
| Telegram Bot Token | ❓ You provide it in the wizard |
| `pythonw.exe` runtime | ✅ Bundled |

### Install steps

1. **Download `LotusSetup.exe`** from the [Releases](https://github.com/SatyamPote/Lotus/releases) page.
2. **Right-click → Run as administrator** (only required for the very first install — needed to register the auto-start scheduled task).
3. The Inno Setup wizard walks you through:
   - **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
   - **Allowed Telegram User ID(s)** — comma-separated for multi-user (get yours from [@userinfobot](https://t.me/userinfobot))
   - **Ollama model name** — e.g. `qwen2.5:3b`, `llama3.1:8b`, `phi4`
   - **Storage location** — defaults to `%LOCALAPPDATA%\Lotus`
4. Lotus self-installs Python (if missing), Ollama (if missing), and pulls the configured model in the background.
5. Click **Finish** — Lotus appears in your **system tray** and registers a logon-triggered scheduled task.
6. DM your bot to confirm it's alive: `/start`.

### Updating

The installer is idempotent — running a newer `LotusSetup.exe` over an
existing install preserves your `config.json` and contacts but
refreshes the agent code, dependencies, and shortcuts.

You can also check for updates from inside Telegram with `/version`.

### Uninstalling

Either:

- **Settings → Apps → Lotus → Uninstall**, or
- Run **`Uninstall Lotus.lnk`** from the Start menu

The uninstaller:

- Stops the running tray agent
- Removes the auto-start scheduled task
- Deletes the `%LOCALAPPDATA%\Lotus` storage dir (after confirmation)
- Removes Start menu shortcuts and the registry keys

> Ollama and Python are **not** removed — they may be in use by other
> apps. Uninstall those manually if you want a fully clean slate.

---

## ⚙️ First-Run Configuration

If you skipped the wizard or want to edit credentials later, edit:

```
%LOCALAPPDATA%\Lotus\config.json
```

Schema is identical to the [shared schema](../README.md#bot-config-configjson).

After editing, restart the agent from the system-tray menu:
**🌸 Lotus → Restart Agent**.

---

## 🖥 System-Tray Controls

Right-click the 🌸 icon in the system tray:

- **Show Dashboard** — opens the control panel window
- **Restart Agent** — gracefully reloads `config.json`
- **Stop Agent** — stops the bot but keeps the tray app
- **Edit Config** — opens `config.json` in the default editor
- **View Logs** — tail `bot_service.log`
- **Check for Updates** — `/version` equivalent
- **Quit Lotus** — fully exits (the scheduled task will respawn it next logon)

---

## 🏗 Architecture (Windows Specifics)

For the cross-platform 3-tier architecture diagram, see the
[root README](../README.md#-architecture). Windows-specific deviations:

| Component | Implementation |
|---|---|
| **Background process** | Hidden `pythonw.exe` running `bot_service.py` |
| **Process supervision** | Scheduled task (`Lotus*`) at logon, run as user, hidden window |
| **Tray GUI** | Tkinter / customtkinter with system-tray hooks via `pystray` |
| **Screen capture** | `mss` for screenshots, `ffmpeg` for video |
| **WhatsApp automation** | Microsoft UI Automation (`comtypes` + `pywinauto`) |
| **Music player** | `mpv` via subprocess |
| **PDF rendering** | `reportlab` + `Pillow` |
| **Storage root** | `%LOCALAPPDATA%\Lotus\` |

---

## 📁 File Layout

```
Windows-MCP/
├── README.md                  ← this file
├── ROOT_README.md             # legacy — pre-split version of the root README
├── INSTALLER_README.md        # Inno Setup project notes
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
│
├── app.py                     # Tray GUI entry point
├── bot_service.py             # Background bot service entry point
├── installer.iss              # Inno Setup project source
├── manifest.json              # update-check manifest
├── contacts.json              # WhatsApp contacts (user-managed)
├── build.bat                  # local build script (PyInstaller + Inno Setup)
│
├── assets/                    # icons, banners, audio prompts
├── bin/                       # bundled binaries (ffmpeg, mpv)
├── data/                      # storage sandbox
├── install_scripts/           # installer pre/post-install scripts
└── src/                       # MCP tool surface (filesystem, media, research, …)
```

```
%LOCALAPPDATA%\Lotus\
├── config.json
├── contacts.json
├── logs\
│   └── bot_service.log
├── storage\
│   ├── downloads\
│   ├── research\
│   └── screenshots\
└── lotus_bot.pid
```

---

## ⚙️ Environment Variables

Beyond the [shared variables](../README.md#shared-environment-variables):

| Variable | Default | Effect |
|---|---|---|
| `WINDOWS_MCP_SCREENSHOT_SCALE` | `1.0` | Scale factor for screenshots (`0.1`–`1.0`). Lower on 1440p/4K to stay under Telegram's image limits. |
| `WINDOWS_MCP_SCREENSHOT_BACKEND` | `auto` | `auto`, `dxcam`, `mss`, or `pillow`. |
| `WINDOWS_MCP_PROFILE_SNAPSHOT` | _off_ | Set to `1` / `true` to log per-stage timing for Screenshot/Snapshot. |
| `WINDOWS_MCP_DEBUG` | `false` | Set to `1` / `true` to enable debug logging. Also exposed as a `--debug` CLI flag. |

To set these for the auto-started agent, add them to the **Environment**
section of the scheduled task in **Task Scheduler**, or write them to
your user-level environment via `setx`.

---

## 🩺 Troubleshooting

### Bot is silent in Telegram
1. Confirm the scheduled task is running:
   ```powershell
   Get-ScheduledTask -TaskName "Lotus*"
   ```
2. Confirm your user ID is in `allowed_user_id` in `config.json`. Get yours from [@userinfobot](https://t.me/userinfobot).
3. Tail the logs:
   ```powershell
   Get-Content "$env:LOCALAPPDATA\Lotus\logs\bot_service.log" -Wait
   ```

### Tray icon is missing
The tray app crashed or was quit. Re-launch from:
```
Start menu → Lotus → Lotus
```
Or restart your machine — the scheduled task will respawn it.

### Ollama is unreachable
1. Confirm Ollama is running: `ollama list` should print without error.
2. Pull the configured model: `ollama pull qwen2.5:3b`.
3. The dashboard's status row goes green within ~5 seconds.

### "Port 40510 already in use"
Set a different port in the scheduled task's environment, or open
**Task Scheduler → Lotus** → Properties → Environment Variables, and
add `LOTUS_CONTROL_PORT=40520`.

### WhatsApp automation isn't sending messages
- Confirm WhatsApp Desktop is installed and signed in.
- The first run after a Windows update may need you to focus the
  WhatsApp window once so UIA can hook it.
- Run `whatsapp test <contact>` to send a smoke-test message.

### `LotusSetup.exe` flagged by SmartScreen
The installer is not yet code-signed. Click **More info → Run anyway**.
A code-signing certificate is on the [roadmap](#%EF%B8%8F-roadmap-windows).

---

## 🛠 Building from Source

### Prerequisites

| Need | Install |
|---|---|
| Python 3.13 | [python.org](https://www.python.org/) |
| `uv` | `irm https://astral.sh/uv/install.ps1 \| iex` |
| Visual Studio Build Tools | required for some native deps |
| Inno Setup 6+ | [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php) |
| PyInstaller | `pip install pyinstaller` |

### Build steps

```powershell
# Clone and install Python deps
git clone https://github.com/SatyamPote/Lotus.git
cd Lotus\Windows-MCP
uv sync

# Run the tray app from source for development
uv run python app.py

# Run the bot service from source
uv run python bot_service.py

# Build the standalone EXE bundle
build.bat

# Build the Inno Setup installer (after build.bat)
iscc installer.iss
# → output\LotusSetup.exe
```

### Code style

- **Formatter / linter:** `ruff` (line length 100, double quotes)
- **Naming:** PEP 8 — `snake_case` functions/variables, `PascalCase` classes
- **Type hints:** required on function signatures
- **Docstrings:** Google-style for public functions/classes

---

## 🗺️ Roadmap (Windows)

- [ ] **MSIX installer** — modern packaging alongside the Inno Setup EXE
- [ ] **Code-signing certificate** — eliminate SmartScreen warnings
- [ ] **Multi-user mode** — per-user config and storage sandboxes within a single install
- [ ] **Plugin loader** — drop a Python file into a `~\.lotus\plugins\` dir to extend the MCP tool surface
- [ ] **Deeper WhatsApp integration** — group chats, voice notes, sticker support

For cross-platform roadmap items see the
[root README](../README.md#%EF%B8%8F-roadmap).

---

## 👨‍💻 Leads

### Windows Lead — Satyam Pote

| | |
|---|---|
| 🐙 GitHub | [@SatyamPote](https://github.com/SatyamPote) |
| 📧 Email  | [satyampote9999@gmail.com](mailto:satyampote9999@gmail.com) |

Designed and built the original Lotus agent, the Windows tray app, the
priority routing engine, the multi-source research pipeline, and the
Inno Setup deployment story. Ongoing maintainer of the Windows build.

### macOS Lead — Jayash Bhandary

| | |
|---|---|
| 🐙 GitHub   | [@JayashBhandary](https://github.com/JayashBhandary) |
| 📧 Email    | [findjayash@gmail.com](mailto:findjayash@gmail.com) |
| 💼 LinkedIn | [linkedin.com/in/jayashbhandary](https://www.linkedin.com/in/jayashbhandary/) |
| 📸 Instagram | [@jayashbhandary_](https://www.instagram.com/jayashbhandary_/) |

Built the macOS port — see the [macOS guide](../Mac-MCP/README.md) for
details. For macOS-specific issues, please reach out via the channels
above or open an issue tagged `macos`.

---

<div align="center">

⬅ [**Back to project root**](../README.md) · 🍎 [**Mac version →**](../Mac-MCP/README.md)

🌸

</div>
