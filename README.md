<div align="center">

# 🌸 Lotus

### **Autonomous AI Control Agent for Windows & macOS — driven from Telegram, powered by local AI.**

[![Windows](https://img.shields.io/badge/Windows-v2.2.0--STABLE-0078D4?style=for-the-badge&logo=windows&logoColor=white)](Windows-MCP/README.md)
[![macOS](https://img.shields.io/badge/macOS-v2.0.1-000000?style=for-the-badge&logo=apple&logoColor=white)](Mac-MCP/README.md)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Swift](https://img.shields.io/badge/Swift-6.0-F05138?style=for-the-badge&logo=swift&logoColor=white)](https://swift.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-000000?style=for-the-badge)](https://ollama.com)

**Lotus turns your computer into an AI-controlled remote workstation.**
Send natural-language commands from Telegram, and Lotus operates your
desktop — opening files, playing music, taking screenshots, running
research, and chatting with you using a private, local LLM. No cloud,
no data leakage, no surprises.

</div>

---

## ⚡ Pick your platform

| | Windows | macOS |
|---|---|---|
| **Latest version** | v2.2.0-STABLE | v2.0.1 |
| **Installer** | `LotusSetup.exe` (Inno Setup, autonomous) | `Lotus-2.0.1.dmg` (drag-to-install) |
| **GUI** | System-tray control panel | Native Swift menu-bar app (`Lotus.app`) |
| **Background service** | Hidden `pythonw.exe` via scheduled task | `launchd` user agent (`com.lotus.botservice`) |
| **Source** | [`Windows-MCP/`](Windows-MCP/README.md) | [`Mac-MCP/`](Mac-MCP/README.md) |
| **Lead** | [@SatyamPote](https://github.com/SatyamPote) | [@JayashBhandary](https://github.com/JayashBhandary) |
| **Read this for install / dev** | **[Windows guide →](Windows-MCP/README.md)** | **[macOS guide →](Mac-MCP/README.md)** |

> **TL;DR for first-time users:**
> 1. Get a Telegram bot token from [@BotFather](https://t.me/BotFather) and your Telegram user ID from [@userinfobot](https://t.me/userinfobot).
> 2. Install [Ollama](https://ollama.com) and pull a small model: `ollama pull qwen2.5:3b`.
> 3. Follow the platform-specific install guide above.
> 4. DM your bot. Try `dashboard`, `take screenshot`, or `play lo-fi`.

---

## Table of Contents

- [What is Lotus?](#what-is-lotus)
- [Feature Tour](#-feature-tour)
- [Command Reference](#%EF%B8%8F-command-reference)
- [Architecture](#-architecture)
- [Configuration](#%EF%B8%8F-configuration)
- [Privacy & Security](#-privacy--security)
- [Repository Layout](#-repository-layout)
- [Contributors](#-contributors)
- [License](#-license)

---

## What is Lotus?

**Lotus** is a cross-platform AI agent that bridges your computer and
Telegram. It runs as a background service, listens to messages from a
small set of allowed Telegram users, interprets them, and translates
them into real actions on your machine — file lookups, app automation,
music playback, screen capture, deep research, and conversational AI.

The intelligence layer is fully local: Lotus integrates with
[**Ollama**](https://ollama.com) to run open-weight LLMs (Llama, Qwen,
Phi, etc.) on your own hardware. **Nothing about your files, your
queries, or your conversations leaves the machine** — except, of
course, the Telegram messages you choose to send.

The two flavors share the same philosophy and the same MCP-style tool
surface, but each is implemented natively for its platform. Pick the
right guide above for installation, build instructions, troubleshooting,
and platform-specific architecture details.

---

## 🚀 Feature Tour

These features are available on **both Windows and macOS**.

### ⚖️ Strict Priority Routing
Commands are matched against a hardened priority chain — **System >
Files > Music > Research** — *before* the LLM ever sees them. This
guarantees that literal commands like `open report.pdf` or `volume up`
execute deterministically and don't get hallucinated into something
else. The AI is invoked only for genuinely ambiguous or open-ended
queries.

### 🔍 Multi-Source Research Engine
The `research <topic>` command runs a tiered pipeline:

1. **Wikipedia** — primary structured source, fast and citation-friendly
2. **DuckDuckGo Instant Answer API** — fallback for current events
3. **Web scraping with `markdownify`** — final fallback for arbitrary URLs

Results are aggregated, the LLM produces a structured summary, and you
receive a **professional PDF report** plus inline images via Telegram.

### 🗣️ Voice Feedback
Every action emits a spoken confirmation in a clear, natural female
voice. Local TTS plays through your speakers; the same audio is sent as
a **Telegram Voice Note** for remote acknowledgement when you're away
from the machine.

### 📦 Managed Storage with Auto-Cleaning
Lotus reserves a 2 GB sandbox under your user data dir for downloads,
research artifacts, and screen recordings. An LRU cleanup keeps it
under quota — your disk doesn't fill up if you forget about it.

### 🎵 Stable Music System
Single-instance enforcement: only one player is ever alive at a time,
so queueing a new song cleanly stops the previous one.

- `play <query>` — searches and streams via `yt-dlp`
- `pause` / `resume` / `stop`
- `next` / `prev` — through the session queue
- `volume up` / `volume down` — system mixer hooks

### 🤖 Private Local AI (Ollama)
Default model: `qwen2.5:3b` — runs comfortably on a recent MacBook or
any PC with 8 GB RAM. Want bigger? Swap to `llama3.1:8b`, `phi4`, or
any model in the [Ollama library](https://ollama.com/library) — Lotus
picks it up without code changes.

### 📹 Screen & Media Tools
- `take screenshot` — instant PNG of the current desktop
- `record screen <seconds>` — captures video (ffmpeg under the hood)
- `download <youtube-url>` — pulls audio or video via `yt-dlp`

### 🖼️ Polished Telegram UI
Every reply is wrapped in a clean monospaced frame with a header
banner. File listings, dashboards, and research summaries are visually
distinct and pleasant to read on mobile.

---

## 🛠️ Command Reference

A condensed catalog. Type `help` to your bot for an in-chat version.
All commands work identically on Windows and macOS.

### 📂 File Management
| Command | What it does |
|---|---|
| `find <query>` | Fuzzy search across user dirs and the storage sandbox |
| `open <filename>` | Open the file in its default application |
| `send <filename>` | Upload the file to Telegram |
| `ls` | List the current working directory |
| `cd <path>` | Change the bot's working directory |
| `tree` | Print a directory tree (depth-limited) |

### 🎵 Media & Music
| Command | What it does |
|---|---|
| `play <song name>` | Search + stream audio |
| `pause` / `resume` / `stop` | Standard playback control |
| `volume up` / `down` | System volume nudge |
| `next` / `prev` | Skip in the session queue |
| `now playing` | Show current track and elapsed time |

### 🔍 Research & Intelligence
| Command | What it does |
|---|---|
| `research <topic>` | Wikipedia → DDG → scrape → PDF |
| `list research` | Most recent reports with timestamps |
| `say <text>` | Speak text via local TTS + Telegram voice note |
| `chat <prompt>` | One-shot LLM completion (Ollama) |

### 🖥️ System Control
| Command | What it does |
|---|---|
| `dashboard` | Battery, CPU, RAM, disk, uptime, IP |
| `lock` / `sleep` / `shutdown` | Power management |
| `take screenshot` | Capture the desktop as PNG |
| `record screen <seconds>` | Capture a screen video |

> Platform-specific commands (e.g. `whatsapp send` on Windows) are
> documented in the per-platform READMEs.

---

## 🏗️ Architecture

Lotus is a three-tier system on both platforms.

```
┌────────────────────────────────────────────────────────┐
│                       Telegram                         │  ← user
└──────────────────────────┬─────────────────────────────┘
                           │  long-poll updates
┌──────────────────────────▼─────────────────────────────┐
│            bot_service.py (background)                 │
│                                                        │
│  ┌──────────────────┐   ┌────────────────────────┐    │
│  │ telegram_bot     │   │ control_api (HTTP)     │    │
│  │  - command parse │   │  - GET /api/status     │    │
│  │  - priority chain│   │  - GET /api/logs       │    │
│  └────────┬─────────┘   │  - POST /api/restart   │    │
│           │             └────────────────────────┘    │
│  ┌────────▼─────────────────────────────────────┐     │
│  │ MCP-style tool surface (mac_mcp / win_mcp)   │     │
│  │  - desktop (mouse, keyboard, screenshot)     │     │
│  │  - filesystem (find, open, ls, cd)           │     │
│  │  - media (yt-dlp, ffmpeg, mpv)               │     │
│  │  - research (wiki, DDG, scrape, PDF)         │     │
│  │  - tts / voice                               │     │
│  └────────┬─────────────────────────────────────┘     │
└───────────┼───────────────────────────────────────────┘
            │
┌───────────▼────────────┐    ┌──────────────────────┐
│      Ollama daemon     │    │    Native GUI        │
│   (local LLM, http)    │    │ Lotus.app / Tray     │
│                        │    │ (status + control)   │
└────────────────────────┘    └──────────────────────┘
```

- **Telegram bot** — `python-telegram-bot`, long-polling, gated by an
  allowlist of user IDs. Anything from outside the list is dropped.
- **MCP server** — `fastmcp`-based tool surface that's exposed to both
  the bot loop and (optionally) external MCP clients like Claude Desktop.
- **Control API** — a tiny `uvicorn` HTTP server on `localhost:40510`,
  used by the GUI to query status and trigger restarts. Bound to
  loopback only.
- **GUI** — a thin client over the control API. The bot service is
  authoritative; the GUI never owns state.
- **Ollama** — out-of-process local LLM server. Lotus speaks to it over
  HTTP at `http://127.0.0.1:11434`.

The platform-specific process supervision and bundle layout are
documented in each platform's README:

- [Windows architecture details →](Windows-MCP/README.md#-architecture-windows-specifics)
- [macOS architecture details →](Mac-MCP/README.md#-architecture-macos-specifics)

### Why Telegram?

- **Universal** — the same client works on iOS, Android, web, and desktop.
- **Free message API** — no SMS / Twilio dependencies.
- **Bot tokens are revocable** — if a token leaks you regenerate it via BotFather.
- **End-to-end optional** — Lotus uses standard bot API, but you can
  layer a private channel or Telegram MTProxy if you want extra hop
  secrecy.

---

## ⚙️ Configuration

### Bot config (`config.json`)

The schema is identical on both platforms. The location differs:

| Platform | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\Lotus\config.json` |
| macOS   | `~/Library/Application Support/Lotus/config.json` |

| Field | Type | Description |
|---|---|---|
| `name` | string | Display name (used in greetings: "Hello \<name\>") |
| `telegram_token` | string | Bot token from BotFather |
| `allowed_user_id` | string | Comma-separated list of Telegram user IDs allowed to issue commands |
| `model_name` | string | Ollama model identifier — must already be `ollama pull`'d |
| `created_at` | string | ISO-8601 timestamp written by the wizard |

Example:

```json
{
  "name": "Jayash",
  "telegram_token": "1234567890:ABC-defGhIjKlmNoPqRStUvWxYz1234567890",
  "allowed_user_id": "1327255784,9876543210",
  "model_name": "qwen2.5:3b",
  "created_at": "2026-05-09 00:33:21"
}
```

### Shared environment variables

| Variable | Default | Effect |
|---|---|---|
| `LOTUS_CONTROL_PORT` | `40510` | Port the local control API listens on |
| `ANONYMIZED_TELEMETRY` | `true` | Set to `false` to disable optional PostHog event reporting |

Platform-specific environment variables are documented in each
platform's README.

### Control API (localhost-only)

```bash
PORT=40510   # or read from the platform's port file

curl http://127.0.0.1:$PORT/api/status     # service health + uptime
curl http://127.0.0.1:$PORT/api/logs       # last 100 log lines
curl http://127.0.0.1:$PORT/api/config     # current config (token redacted)
curl -X POST http://127.0.0.1:$PORT/api/restart
curl -X POST http://127.0.0.1:$PORT/api/stop
```

The native GUI on each platform uses this same surface — there is no
private API.

---

## 🔐 Privacy & Security

Lotus is designed to be **private by default**:

- ✅ **Local LLM only** — Ollama runs on your machine. Prompts and
  conversations never touch a third-party API.
- ✅ **Allowlist authentication** — Telegram user IDs not in
  `allowed_user_id` are silently ignored. The bot does not respond,
  log, or acknowledge them.
- ✅ **Loopback control API** — bound to `127.0.0.1` only; not exposed
  on any network interface.
- ✅ **No outbound telemetry by default** for the macOS app's
  installer steps. Set `ANONYMIZED_TELEMETRY=false` in `.env` to also
  disable the bot's optional PostHog events.
- ✅ **Token storage** — `config.json` is mode `0600` after the
  wizard writes it. The macOS Swift GUI redacts tokens in the
  **Settings** view.

### Threat model (briefly)

| Concern | Mitigation |
|---|---|
| Bot token leaks | Revoke via BotFather, regenerate, rewrite `config.json` |
| Allowed user phone gets compromised | Remove their ID from `allowed_user_id`, restart |
| Local code execution by a permitted user | Lotus *is* a remote-control agent; trust the allowlist accordingly |
| Network sniffer on home wifi | Telegram traffic is TLS; control API is loopback |
| Malicious DMG / EXE | Verify the SHA-256 from the Release page against `SHA256SUMS.txt` |

---

## 📁 Repository Layout

```
Lotus/
├── README.md                      ← you are here (connector)
│
├── Windows-MCP/                   # Windows AI agent
│   ├── README.md                  ← Windows install + dev guide
│   └── ...                        # Inno Setup, tray app, command engine
│
├── Mac-MCP/                       # macOS native menu-bar app + bot
│   ├── README.md                  ← macOS install + dev guide
│   ├── ControlPanel/              # Swift Package — Lotus.app source
│   ├── src/mac_mcp/               # Python MCP server + Telegram bot
│   ├── bot_service.py             # bot service entry point
│   ├── pyproject.toml
│   └── SETUP.md
│
├── release-notes/                 # per-release curated notes (vX.Y.Z.md)
│   ├── README.md
│   ├── TEMPLATE.md
│   ├── v1.0.0.md
│   ├── v2.0.0.md
│   └── v2.0.1.md
│
└── .github/
    ├── workflows/swift.yml        # macOS build & release pipeline
    └── RELEASING.md               # pipeline runbook
```

---

## 👥 Contributors

Lotus is the product of two leads, one on each platform:

<table>
<tr>
<td align="center">
<a href="https://github.com/SatyamPote">
<img src="https://github.com/SatyamPote.png" width="120" alt="Satyam Pote"><br>
<b>Satyam Pote</b>
</a><br>
<sub>Project creator · Windows lead</sub><br>
<sub><a href="https://github.com/SatyamPote">@SatyamPote</a></sub><br>
<br>
<i>Designed and built the original Lotus agent, the Windows tray app,
the priority routing engine, the multi-source research pipeline, and
the Inno Setup deployment story.</i>
</td>
<td align="center">
<a href="https://github.com/JayashBhandary">
<img src="https://github.com/JayashBhandary.png" width="120" alt="Jayash Bhandary"><br>
<b>Jayash Bhandary</b>
</a><br>
<sub>macOS lead</sub><br>
<sub><a href="https://github.com/JayashBhandary">@JayashBhandary</a></sub><br>
<sub>📧 <a href="mailto:findjayash@gmail.com">findjayash@gmail.com</a></sub><br>
<sub>💼 <a href="https://www.linkedin.com/in/jayashbhandary/">LinkedIn</a> · 📸 <a href="https://www.instagram.com/jayashbhandary_/">Instagram</a></sub><br>
<br>
<i>Designed and built the macOS native menu-bar app (`Lotus.app`),
the universal-binary build pipeline, the standalone DMG installer
with bundled `uv` runtime, the writable runtime-dir architecture,
and the GitHub Actions release workflow.</i>
</td>
</tr>
</table>

### Contributing

Pull requests and issues are welcome. Please:

1. Open an issue first for anything non-trivial — saves you from
   building something we'd want differently.
2. For UI work, include a screenshot or short screen recording.
3. For new MCP tools, add a docstring describing the user-facing
   command, expected arguments, and what state it touches.
4. Keep curated release notes in [`release-notes/`](release-notes) up
   to date — they ship as the GitHub Release body.

---

## 📜 License

This project is released under the MIT License — see
[`LICENSE`](LICENSE) for the full text.

The bundled `uv` binary used by the macOS installer is distributed
under the [MIT/Apache-2.0 license](https://github.com/astral-sh/uv) by
Astral. Ollama models you pull are subject to their respective
upstream licenses.

---

<div align="center">

**Built for stability. Built for privacy. Built for both Windows and Mac.**

🌸

[**Windows guide →**](Windows-MCP/README.md) · [**macOS guide →**](Mac-MCP/README.md)

</div>
