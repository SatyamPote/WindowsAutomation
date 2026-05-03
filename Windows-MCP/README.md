# 🌸 Lotus Windows AI Control Agent (v2.1.0-PROD)

**Lotus** is an advanced, autonomous AI agent that gives you complete, natural language control over your Windows PC directly from **Telegram**. Created by [Satyam Pote](https://github.com/SatyamPote), Lotus combines seamless background execution with a robust local AI inference engine to bring actual intelligence to your desktop.

---

## 🚀 Key Features

- **🗣️ Advanced Voice Feedback**: Assistant speaks every action and completion at **MAX volume**. Local playback is synchronized with **Telegram Voice Notes** sent directly to your phone.
- **🎙️ Voice Control**: Remotely enable/disable voice or instantly stop playback with `voice on`, `voice off`, and `stop voice`.
- **🤖 Local AI Inference**: Uses local models (Phi3, Mistral, Llama3) via Ollama. Private, fast, and secure.
- **📱 Telegram Integration**: Control your PC from anywhere in the world using the secure Telegram API.
- **🎵 Music & Playlists**: Create, manage, and play entire song queues. Supports commands like `play playlist chill`.
- **📹 Native Screen Recording**: Record your PC screen for any duration (e.g., `record screen 10`) and get the video file sent to your Telegram automatically.
- **📥 Media & Downloads**: Automatically download YouTube videos/audio or web images via `yt-dlp` and play media using `mpv`.
- **💬 WhatsApp Automation**: Send WhatsApp messages and attachments directly from Telegram using deep UI automation.
- **⚙️ Complete System Access**: Lock, sleep, shutdown, explore files, execute PowerShell, run python scripts, and manage the clipboard.
- **🔋 Battery & Status Alerts**: Get immediate Telegram alerts when your laptop battery runs low.
- **📦 Autonomous Installer**: A robust Inno Setup installer that handles Python, dependencies, Ollama, and bot configuration entirely automatically.

## 🛠️ Available Commands

Lotus registers these commands natively in your Telegram menu:
- `/start` — Show the interactive dashboard buttons
- `/help` — Show the full command and capability list
- `/version` — Check for updates from GitHub
- `/voice` — Voice Control: on/off/stop
- `/playlist` — List your music playlists
- `/status` — View your PC's real-time CPU and RAM usage
- `/admin` — Show creator and owner details
- `/contacts` — List all saved WhatsApp contacts
- `/storage` — Check the managed storage usage

**Natural Language Examples (No slashes needed):**
- `"voice on"` / `"voice off"` — Toggle assistant voice
- `"stop voice"` — Mute currently playing assistant voice
- `"record screen 10"` — Capture 10 seconds of desktop video
- `"play playlist party"` — Start sequential music playback
- `"take a screenshot"`
- `"download youtube https://..."`
- `"shutdown pc"` / `"restart pc"`
- `"close notepad"`

## 📦 Installation

We provide a **fully automated Windows Installer** (`LotusSetup.exe`) that sets up everything for you.

1. Download the latest `LotusSetup.exe` from the [Releases](https://github.com/SatyamPote/Lotus/releases) page.
2. Run the installer. It will autonomously:
   - Check for Python and install it if missing.
   - Configure your Telegram Bot credentials.
   - Install Ollama and download your preferred AI model.
3. Once installed, Lotus will run quietly in the background and can be managed via the System Tray.

## 👨‍💻 Creator

**Satyam Pote**
- GitHub: [@SatyamPote](https://github.com/SatyamPote)
- Email: satyampote9999@gmail.com

Open-source and built for Windows power users. Feel free to open issues or contribute!
