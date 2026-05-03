# 🌸 Lotus Windows AI Control Agent (v2.2.0-STABLE)

**Lotus** is an advanced, autonomous AI agent that gives you complete, natural language control over your Windows PC directly from **Telegram**. Created by [Satyam Pote](https://github.com/SatyamPote), Lotus combines seamless background execution with a robust local AI inference engine to bring actual intelligence to your desktop.

---

## 🚀 Key Features (Stability Update v2.2.0)

- **⚖️ Strict Priority Routing**: A hardened command engine that ensures **System > Files > Music > Research** commands bypass the AI entirely for 100% reliability. Direct file matches in your storage and download folders work instantly.
- **🔍 Multi-Source Research Engine**: Now uses a tiered fallback system (**Wikipedia → DuckDuckGo → Web Scraping**) to ensure every research request returns deep results, images, and a professional PDF report.
- **🗣️ Advanced Voice Feedback**: Assistant speaks every action in a **sweet female tone**. Local playback is synchronized with **Telegram Voice Notes** for remote confirmation.
- **📦 Managed Storage & Auto-Cleaning**: 2GB managed storage for research and downloads with intelligent auto-cleaning of old data.
- **🎵 Stable Music System**: Single-instance control ensures only one player runs at a time. Supports `play`, `pause`, `stop`, `volume`, `next`, and `previous` with aggressive process management.
- **🤖 Private Local AI**: Integrates with Ollama for secure, offline chat and complex task analysis.
- **📹 Screen & Media Tools**: Record screen, take screenshots, and download YouTube videos/audio directly from your chat.
- **🖼️ Professional UI Framing**: Every response is delivered in a clean, framed block for readability and a premium aesthetic.

## 🛠️ Essential Command Guide

### 📂 File Management
- `find <query>` — Search all user directories and storage.
- `open <filename>` — Instantly open a file on your PC.
- `send <filename>` — Upload a file from your PC to Telegram.
- `ls` / `cd` — Shell-like navigation through your folders.

### 🎵 Media & Music
- `play <song name>` — Search and stream audio.
- `stop` / `pause` / `resume` — Standard playback control.
- `volume up` / `volume down` — Remote volume adjustment.
- `next` / `prev` — Skip tracks in the session queue.

### 🔍 Research & Intelligence
- `research <topic>` — Start a deep-dive with PDF and image generation.
- `list research` — Show your most recent reports.
- `say <text>` — Make Lotus talk through your PC speakers.

### 🖥️ System Control
- `dashboard` — View real-time stats, battery, and storage.
- `lock` / `sleep` / `shutdown` — Remote power management.
- `take screenshot` — Capture current desktop view.
- `record screen <seconds>` — Capture video of your activity.

---

## 📦 Installation & Deployment

Lotus is designed for zero-config deployment using the `LotusSetup.exe` (Inno Setup).

1. Download the latest installer from the [Releases](https://github.com/SatyamPote/Lotus/releases) page.
2. Run the installer; it will configure Python, Ollama, and your Bot Token autonomously.
3. Start Lotus, and your PC is now under your remote control.

## 👨‍💻 Creator

**Satyam Pote**
- GitHub: [@SatyamPote](https://github.com/SatyamPote)
- Project: [Lotus-Agent](https://github.com/SatyamPote/Lotus)

Built for stability. Built for Windows. 🌸
