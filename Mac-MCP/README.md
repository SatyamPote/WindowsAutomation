<div align="center">

# 🌸 Lotus for macOS

### **Native macOS menu-bar AI control agent — universal binary, fully self-contained, drag-to-install.**

[![Version](https://img.shields.io/badge/version-v2.0.1-000000?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/SatyamPote/Lotus/releases)
[![Swift](https://img.shields.io/badge/Swift-6.0-F05138?style=for-the-badge&logo=swift&logoColor=white)](https://swift.org)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Architecture](https://img.shields.io/badge/Architecture-arm64%20%2B%20x86__64-FF6B35?style=for-the-badge)](https://en.wikipedia.org/wiki/Universal_binary)
[![Lead](https://img.shields.io/badge/Lead-@JayashBhandary-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/JayashBhandary)

⬅ **Back to project root:** [README.md](../README.md)
🪟 **Looking for the Windows version?** [Windows-MCP/README.md](../Windows-MCP/README.md)

</div>

---

## Table of Contents

- [Overview](#overview)
- [macOS-Only Highlights](#-macos-only-highlights)
- [Installation](#-installation)
- [What's Bundled Inside `Lotus.app`](#-whats-bundled-inside-lotusapp)
- [What Gets Created on First Launch](#-what-gets-created-on-first-launch)
- [Menu-Bar Controls](#-menu-bar-controls)
- [Architecture (macOS Specifics)](#%EF%B8%8F-architecture-macos-specifics)
- [Configuration](#%EF%B8%8F-configuration)
- [Troubleshooting](#-troubleshooting)
- [Building from Source](#%EF%B8%8F-building-from-source)
- [Releases & CI/CD](#%EF%B8%8F-releases--cicd)
- [Recent Releases](#-recent-releases)
- [Uninstalling](#-uninstalling)
- [Roadmap (macOS)](#%EF%B8%8F-roadmap-macos)
- [Lead](#-lead)

For the cross-platform feature tour, command reference, architecture
overview, configuration schema, and contributors list, see the
[**root README**](../README.md).

---

## Overview

**Lotus for macOS** is a native menu-bar app (`Lotus.app`) — a single
universal binary (arm64 + x86_64) that bundles its own Python package
manager (`uv`) and the entire Python bot runtime template. The DMG you
download is **truly standalone**: no `git clone`, no `uv sync`, no
Homebrew, no system Python required.

The macOS build is at **v2.0.1**. The Swift control panel manages a
`launchd` user agent (`com.lotus.botservice`) that runs the same Python
MCP server and Telegram bot used by the Windows build. State lives in
`~/Library/Application Support/Lotus/` (not inside the signed `.app`)
so the bundle remains immutable and re-signable.

---

## ✨ macOS-Only Highlights

These are in addition to the [shared feature tour](../README.md#-feature-tour).

### 🌸 Native menu-bar app
A SwiftUI window with a system-native look — toolbar, search bar,
toggles. The 🌸 menu-bar icon stays alive even when the window is
closed, so the bot keeps running with zero Dock real estate.

### 🛠 Universal binary (arm64 + x86_64)
A single `Lotus.app` runs natively on Apple Silicon and Intel Macs.
The build pipeline asserts both slices are present via `lipo -archs`
before publishing.

### 📦 Truly standalone DMG
- Bundled `uv` binary (universal, ~57 MB) — no need for system uv.
- Bundled runtime template — `bot_service.py`, `pyproject.toml`,
  `uv.lock`, and the full `mac_mcp` Python package.
- First-launch wizard rsyncs the template into a writable runtime dir
  and runs `uv sync` there. Python 3.13 + dependencies install in
  ~30–60 seconds.

### 🔄 LaunchAgent integration
- `RunAtLoad = true` — the bot starts automatically at login.
- `KeepAlive = false` — no respawn loops if it crashes hard.
- Logs to `~/Library/Application Support/Lotus/logs/bot_service.log`.

### 🎨 Polished DMG installer
- 640×639 window with a custom lotus-pond banner background.
- `Lotus.app` and `Applications` shortcut centered over the artwork.
- Drag-to-install layout with no toolbar or status bar clutter.

### 🔌 MCP server for Claude Desktop / Claude Code
The same `mac_mcp` Python package can be used as an external MCP
server. Add this to your `~/.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "mac-mcp": {
      "command": "uv",
      "args": ["--directory", "/Applications/Lotus.app/Contents/Resources/runtime-template", "run", "mac-mcp"]
    }
  }
}
```

---

## 📦 Installation

### Prerequisites

| Need | Why |
|---|---|
| macOS 13 Ventura or later | Required for SwiftUI features used in the control panel |
| ~150 MB free disk | DMG is ~40 MB; runtime + Python ~110 MB more |
| [Ollama](https://ollama.com) | Optional — required only for the AI chat features |
| Telegram bot token | From [@BotFather](https://t.me/BotFather) |

> **Nothing else** — Python, `uv`, and all dependencies are bundled or
> installed by the wizard.

### Install steps

1. **Download** [`Lotus-2.0.1.dmg`](https://github.com/SatyamPote/Lotus/releases) from the Releases page.
2. **Open the DMG**. The window shows `Lotus.app` next to an `Applications` shortcut over a lotus-pond banner.
3. **Drag `Lotus.app` onto `Applications`**.
4. Open `/Applications` in Finder, **right-click `Lotus.app` → Open** (this satisfies Gatekeeper for the ad-hoc-signed bundle). Subsequent launches don't need the right-click.
5. The 🌸 icon appears in your menu bar. Click it → **Show Lotus**.
6. The first-run wizard provisions Python 3.13 and the bot dependencies into `~/Library/Application Support/Lotus/runtime/`. Takes ~30–60 seconds the first time.
7. Enter your Telegram token, allowed Telegram user IDs, your name, and an Ollama model. Click **Save & Launch Bot**.

### Optional: silence Gatekeeper without the right-click dance

```bash
xattr -d com.apple.quarantine /Applications/Lotus.app
```

### Updating

Replace `/Applications/Lotus.app` with the new version:

1. Drag the new `Lotus.app` from a fresh DMG over the existing one in `/Applications`.
2. Click the menu bar 🌸 → **Toggle Bot** twice (off, on) — or run:
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.lotus.botservice
   ```

Your `config.json` and the existing runtime venv are preserved.

---

## 📂 What's Bundled Inside `Lotus.app`

| Path | Contents |
|---|---|
| `Contents/MacOS/Lotus` | Universal Swift menu-bar binary |
| `Contents/MacOS/Lotus_Lotus.bundle` | SPM resource bundle (bot script, Python package, lockfile) |
| `Contents/Resources/bin/uv` | Universal `uv` binary used by the installer + `launchd` service |
| `Contents/Resources/runtime-template/` | `bot_service.py`, `pyproject.toml`, `uv.lock`, `mac_mcp/` source |
| `Contents/Resources/assets/` | Logos, banner art, wizard images |
| `Contents/Resources/AppIcon.icns` | macOS app icon |
| `Contents/Info.plist` | Bundle metadata, `LSUIElement` (menu-bar app), permission descriptions |

Total: **~97 MB** uncompressed, **~40 MB** compressed in the DMG.

---

## 📂 What Gets Created on First Launch

| Path | Contents |
|---|---|
| `~/Library/Application Support/Lotus/runtime/` | Writable copy of the runtime template |
| `~/Library/Application Support/Lotus/runtime/.venv/` | Python 3.13 venv with all bot deps |
| `~/Library/Application Support/Lotus/config.json` | Bot credentials (token, allowed IDs, model) |
| `~/Library/Application Support/Lotus/logs/bot_service.log` | Runtime logs |
| `~/Library/Application Support/Lotus/control.port` | Port the local control API listens on |
| `~/Library/Application Support/Lotus/lotus_bot.pid` | PID file for the running bot |
| `~/Library/LaunchAgents/com.lotus.botservice.plist` | `launchd` plist that keeps the bot alive |

The signed `.app` is **never modified** at runtime — all writable state
lives under `Application Support/Lotus/`.

---

## 🖥 Menu-Bar Controls

Click the 🌸 icon in the menu bar:

- **Show Lotus** — opens the control panel window
- **Toggle Bot** — start/stop the `launchd` service
- **Quit Lotus** — quits the menu-bar app (the bot service keeps running independently)

Closing the control panel window hides it; the app stays in the menu
bar. The control panel is always-on-top-friendly and supports the
standard macOS window menu (⌘W to close, ⌘Q to quit).

---

## 🏗️ Architecture (macOS Specifics)

For the cross-platform 3-tier architecture diagram, see the
[root README](../README.md#-architecture). macOS-specific details:

| Component | Implementation |
|---|---|
| **Menu-bar app** | SwiftUI + AppKit, `LSUIElement = true` (no Dock icon) |
| **Background process** | Python via the bundled venv at `~/Library/Application Support/Lotus/runtime/.venv/bin/python` |
| **Process supervision** | `launchd` user agent (`com.lotus.botservice.plist`), `RunAtLoad=true`, `KeepAlive=false` |
| **Screen capture** | Quartz (`CGWindowListCreateImage`) with `screencapture` fallback |
| **Music player** | `mpv` (installed via Homebrew, optional) |
| **PDF rendering** | `reportlab` + `Pillow` |
| **Permissions** | Accessibility, Screen Recording, Files & Folders (granted in System Settings) |

### Why a writable runtime dir?

The `.app` bundle in `/Applications` is read-only after install. Any
attempt to write inside it (e.g. creating a `.venv`) breaks the code
signature and fails outright on signed/notarized builds.

Lotus solves this by separating **code** (immutable, in `.app`) from
**runtime state** (mutable, in `~/Library/Application Support/Lotus/`).
The bundled runtime-template is rsynced into the writable dir on first
launch, and the launchd plist points at the writable copy.

This also means upgrades are atomic — replace the `.app`, the existing
venv keeps working, and config / logs / port files are untouched.

---

## ⚙️ Configuration

The shared `config.json` schema is documented in the
[root README](../README.md#bot-config-configjson). On macOS it lives at:

```
~/Library/Application Support/Lotus/config.json
```

### macOS-specific environment variables

| Variable | Default | Effect |
|---|---|---|
| `MAC_MCP_SCREENSHOT_BACKEND` | `auto` | `auto`, `quartz`, or `screencapture` |
| `MAC_MCP_DEBUG` | `false` | Verbose MCP server logging |

To set these for the auto-started service, add them to the
`EnvironmentVariables` block of the launchd plist:

```bash
plutil -insert EnvironmentVariables.MAC_MCP_DEBUG \
  -string "true" \
  ~/Library/LaunchAgents/com.lotus.botservice.plist

launchctl kickstart -k gui/$(id -u)/com.lotus.botservice
```

### macOS permissions

In **System Settings → Privacy & Security**, grant Lotus.app:

- **Accessibility** — for simulating keyboard/mouse input
- **Screen Recording** — for screenshots and screen capture
- **Files and Folders** (or Full Disk Access) — for filesystem tools

The first command that needs each permission will prompt you.

---

## 🩺 Troubleshooting

### "Lotus.app is damaged and can't be opened"
Gatekeeper blocked the unsigned bundle. Right-click → **Open** once, or:
```bash
xattr -d com.apple.quarantine /Applications/Lotus.app
```

### Control panel is blank / app crashes on launch (v2.0.0)
Upgrade to **v2.0.1**. v2.0.0 was missing the SPM resource bundle
inside the .app, causing `Bundle.module` to fatal-assert when the
control panel tried to load logos.

### Bot won't start, "plist not installed"
The first-run wizard didn't complete. Open Lotus and re-run the
installer; or install the launchd agent manually:
```bash
bash install_scripts/install.sh
```

### Bot is silent in Telegram
1. Confirm the launchd service is running:
   ```bash
   launchctl print "gui/$(id -u)/com.lotus.botservice" | head -20
   ```
2. Confirm your user ID is in `allowed_user_id`. Get yours from [@userinfobot](https://t.me/userinfobot).
3. Tail the logs:
   ```bash
   tail -f ~/Library/Application\ Support/Lotus/logs/bot_service.log
   ```

### Ollama is unreachable / `ollama_reachable: false` in the dashboard
1. Start Ollama: `ollama serve`.
2. Pull the configured model: `ollama pull qwen2.5:3b`.
3. The control panel's status row goes green within ~5 seconds.

### Music plays nothing
ffmpeg + mpv must be installed. The first-run wizard offers to install
them via Homebrew (optional step). Manual install:
```bash
brew install mpv ffmpeg
```

### "Port 40510 already in use"
Set a different port in the launchd plist:
```bash
plutil -replace EnvironmentVariables.LOTUS_CONTROL_PORT \
  -string "40520" \
  ~/Library/LaunchAgents/com.lotus.botservice.plist

launchctl kickstart -k gui/$(id -u)/com.lotus.botservice
```

### `swift build` fails with "Swift tools version" mismatch
You're on an older Xcode. The Swift Package requires Swift 6
(Xcode 16+). Update Xcode from the App Store, or in CI use
`maxim-lobanov/setup-xcode@v1` with `xcode-version: '16.0'`.

---

## 🛠 Building from Source

### Prerequisites

| Need | Install |
|---|---|
| macOS 13 Ventura or later | (must be present) |
| Python 3.13 | `brew install python@3.13` |
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Xcode 16 (Swift 6) | Mac App Store |
| Xcode Command Line Tools | `xcode-select --install` |

### Build steps

```bash
git clone https://github.com/SatyamPote/Lotus.git
cd Lotus/Mac-MCP

# Python deps for the bot
uv sync

# Build the universal Swift app
bash ControlPanel/make_app.sh
# → Mac-MCP/Lotus.app  (~97 MB, arm64 + x86_64)

# Build the styled DMG
bash ControlPanel/make_dmg.sh
# → Mac-MCP/dist/Lotus-2.0.1.dmg  (~40 MB compressed)

# Or build app + DMG in one go
bash ControlPanel/make_dmg.sh --build

# Run the built app directly
open Lotus.app
```

#### Faster local builds (host-only architecture)

```bash
# Apple Silicon dev — skip the x86_64 slice
LOTUS_ARCHS="arm64" bash ControlPanel/make_app.sh
```

### Running the Swift app from Xcode

```bash
cd Mac-MCP/ControlPanel
swift build -c debug
swift run Lotus
```

The dev build walks up parent directories from the binary to find
`bot_service.py`, so you can edit Python and Swift in parallel without
rebuilding the bundle.

### Build script knobs

| Variable | Default | Effect |
|---|---|---|
| `LOTUS_ARCHS` | `arm64 x86_64` | Architectures to build (space-separated) |
| `UV_VERSION` | `0.5.4` | Version of bundled `uv` binary downloaded into the .app |

### Code style

- **Python:** `ruff` (config in `pyproject.toml`)
- **Swift:** standard `swift-format` with project defaults
- **Type checking:** `pyrefly` for Python, native Swift type system

### Tests

```bash
cd Mac-MCP
uv run pytest                              # Python bot + MCP tools
swift test --package-path ControlPanel     # Swift app (when added)
```

---

## 🏷 Releases & CI/CD

The macOS pipeline is fully automated via GitHub Actions
([`.github/workflows/swift.yml`](../.github/workflows/swift.yml)).

### Release triggers

| Trigger | What runs | What ships |
|---|---|---|
| Push tag `v*` (e.g. `v2.0.1`) | Build + publish | DMG attached to the GitHub Release |
| Manual `workflow_dispatch` (publish=false) | Build only | Workflow artifact |
| Manual `workflow_dispatch` (publish=true + version) | Build + tag + publish | DMG attached to the GitHub Release |

### Pipeline steps

1. Pins **Xcode 16 / Swift 6** on `macos-15` runners.
2. Runs `uv sync` to populate the venv.
3. Stamps the resolved version into `make_app.sh` and `make_dmg.sh`.
4. Builds the **universal** `Lotus.app`.
5. **Verifies** the binary contains both `arm64` and `x86_64` slices
   (`lipo -archs`) — fails the build otherwise.
6. Builds the **DMG** with the `dmg_banner.png` background.
7. **Verifies** the DMG mounts cleanly with `Lotus.app` + `Applications`
   inside.
8. On a tagged or manual-publish run: creates a GitHub Release with the
   DMG, `SHA256SUMS.txt`, and curated release notes from
   [`release-notes/v<version>.md`](../release-notes), with auto-generated
   PR notes appended underneath.

See [`.github/RELEASING.md`](../.github/RELEASING.md) for the full
pipeline runbook.

### Cutting a new release

```bash
# 1. Write curated release notes
cp release-notes/TEMPLATE.md release-notes/v2.1.0.md
$EDITOR release-notes/v2.1.0.md
git add release-notes/v2.1.0.md
git commit -m "release notes: v2.1.0"

# 2. Tag and push — fires the workflow
git tag -a v2.1.0 -m "Lotus v2.1.0"
git push origin v2.1.0
```

---

## 🏷 Recent Releases

| Version | Date | Highlights |
|---|---|---|
| [v2.0.1](../release-notes/v2.0.1.md) | 2026-05-09 | Patch — fix launch crash from missing SPM resource bundle. |
| [v2.0.0](../release-notes/v2.0.0.md) | 2026-05-09 | Truly standalone install — bundled `uv` + runtime template. Universal binary. |
| [v1.0.0](../release-notes/v1.0.0.md) | 2026-05-04 | First public macOS release. |

---

## 🗑 Uninstalling

```bash
# Stop and unregister the launchd service
launchctl bootout "gui/$(id -u)/com.lotus.botservice"

# Remove all Lotus state (config, logs, runtime, port file, PID file)
rm -rf ~/Library/Application\ Support/Lotus

# Remove the launchd plist
rm ~/Library/LaunchAgents/com.lotus.botservice.plist

# Drag /Applications/Lotus.app to the Trash
```

Ollama and Homebrew are **not** removed — they may be in use by other
apps. Uninstall those manually if you want a fully clean slate.

---

## 🗺️ Roadmap (macOS)

- [ ] **Apple notarization** — sign with a Developer ID cert, submit via `notarytool`, staple. Removes the Gatekeeper warning entirely.
- [ ] **Sparkle auto-updates** — generate `appcast.xml` in the workflow, point the app at it. One-click in-app updates.
- [ ] **Pre-baked `.DS_Store`** — fully styled DMG window from CI (currently CI skips Finder styling on headless runners).
- [ ] **Code-sign the bundled `uv`** so the whole app re-signs cleanly after notarization.
- [ ] **Slimmer DMG** — investigate UPX-compressed `uv` (~40% size reduction) and drop unused `mac_mcp` submodules from the runtime template.
- [ ] **Native macOS Shortcuts integration** — expose Lotus tools as Shortcuts actions for hotkey/automation use.

For cross-platform roadmap items see the
[root README](../README.md#%EF%B8%8F-roadmap).

---

## 👨‍💻 Lead

**Jayash Bhandary**

| | |
|---|---|
| 🐙 GitHub   | [@JayashBhandary](https://github.com/JayashBhandary) |
| 📧 Email    | [findjayash@gmail.com](mailto:findjayash@gmail.com) |
| 💼 LinkedIn | [linkedin.com/in/jayashbhandary](https://www.linkedin.com/in/jayashbhandary/) |
| 📸 Instagram | [@jayashbhandary_](https://www.instagram.com/jayashbhandary_/) |

Designed and built the macOS native menu-bar app (`Lotus.app`), the
universal-binary build pipeline, the standalone DMG installer with
bundled `uv` runtime, the writable runtime-dir architecture, and the
GitHub Actions release workflow. Ongoing maintainer of the macOS build.

For macOS-specific bug reports, feature requests, or pairing on a
contribution, GitHub issues are preferred — but feel free to reach
out via any of the channels above.

---

<div align="center">

⬅ [**Back to project root**](../README.md) · 🪟 [**Windows version →**](../Windows-MCP/README.md)

🌸

</div>
