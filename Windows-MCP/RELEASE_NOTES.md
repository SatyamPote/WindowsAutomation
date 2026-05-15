# 🌸 Lotus v3.1.0 — Production Release

## 🚀 Key Features
- **Modern Dark UI**: A complete overhaul with a premium glass-morphism aesthetic.
- **Background Persistence**: The bot runs as a separate background service that stays active even if you close the control panel.
- **Integrated Media Engine**: Built-in support for `mpv` and `yt-dlp` for music playback and downloads.
- **Screen Recording**: Capture your desktop with high-quality MP4 output via Telegram commands.
- **Smart Pathing**: Self-healing architecture that finds tools (mpv, yt-dlp) regardless of where they are installed.
- **Windows Defender Integration**: Automated security exclusions to prevent performance throttling.

## 📦 Installation
1. Download **`LotusSetup.exe`**.
2. Run the installer (Windows might show a "SmartScreen" warning since it's a new app—click *More Info* -> *Run anyway*).
3. Open the **Lotus** app from your desktop.
4. Follow the **First-Time Setup** to link your Telegram bot token.

## 🛠 Technical Fixes
- Resolved `PackageNotFoundError` during PyInstaller bundling.
- Fixed `mpv` discovery issues in production builds.
- Implemented robust PID tracking for background services.
- Added `/record` and `/status` command handlers.

---
**Developer:** Satyam Pote  
**Project:** [Lotus Automation Agent](https://github.com/Lotus-agent/Lotus)
