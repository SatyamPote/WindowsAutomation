"""
Lotus - Project Overview Web Server
Serves a project info page on port 5000 for the Replit environment.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lotus - AI Control Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0d1117;
    color: #e6edf3;
    min-height: 100vh;
  }
  .hero {
    text-align: center;
    padding: 60px 20px 40px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-bottom: 1px solid #21262d;
  }
  .hero h1 { font-size: 3rem; font-weight: 700; margin-bottom: 12px; }
  .hero .tagline {
    font-size: 1.1rem;
    color: #8b949e;
    max-width: 600px;
    margin: 0 auto 24px;
    line-height: 1.6;
  }
  .badges { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-bottom: 16px; }
  .badge {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.8rem;
    color: #58a6ff;
  }
  .container { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }
  .section { margin-bottom: 40px; }
  .section h2 {
    font-size: 1.4rem;
    font-weight: 600;
    margin-bottom: 20px;
    color: #f0f6fc;
    border-left: 3px solid #58a6ff;
    padding-left: 12px;
  }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
  .card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 20px;
    transition: border-color 0.2s;
  }
  .card:hover { border-color: #58a6ff; }
  .card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 8px; color: #f0f6fc; }
  .card p { font-size: 0.88rem; color: #8b949e; line-height: 1.5; }
  .platform-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .platform-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 24px;
  }
  .platform-card h3 { font-size: 1.1rem; font-weight: 600; margin-bottom: 6px; }
  .platform-card .version { font-size: 0.8rem; color: #8b949e; margin-bottom: 16px; }
  .platform-card ul { list-style: none; }
  .platform-card ul li {
    font-size: 0.85rem;
    color: #8b949e;
    padding: 3px 0;
  }
  .platform-card ul li::before { content: "→ "; color: #58a6ff; }
  .cmd-table { width: 100%; border-collapse: collapse; }
  .cmd-table th {
    background: #21262d;
    padding: 10px 14px;
    text-align: left;
    font-size: 0.85rem;
    font-weight: 600;
    color: #8b949e;
    border: 1px solid #30363d;
  }
  .cmd-table td {
    padding: 8px 14px;
    font-size: 0.85rem;
    border: 1px solid #21262d;
    color: #e6edf3;
  }
  .cmd-table tr:hover td { background: #161b22; }
  code {
    background: #21262d;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.85em;
    color: #79c0ff;
  }
  .arch-box {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 24px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    color: #8b949e;
    white-space: pre;
    overflow-x: auto;
    line-height: 1.6;
  }
  .note {
    background: #1c2128;
    border: 1px solid #30363d;
    border-left: 4px solid #f0883e;
    border-radius: 6px;
    padding: 16px 20px;
    font-size: 0.9rem;
    color: #8b949e;
    margin-bottom: 30px;
  }
  .note strong { color: #f0883e; }
  @media (max-width: 600px) {
    .platform-grid { grid-template-columns: 1fr; }
    .hero h1 { font-size: 2rem; }
  }
</style>
</head>
<body>
<div class="hero">
  <img src="/static/img/lotus.png" alt="Lotus" style="width:120px;height:120px;display:block;margin:0 auto 16px;filter:drop-shadow(0 6px 24px rgba(236,64,122,0.35))">
  <h1 style="background:linear-gradient(90deg,#ff4d9d,#ff8fc8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Lotus</h1>
  <p class="tagline">Autonomous AI Control Agent for Windows &amp; macOS — driven from Telegram, powered by local AI.</p>
  <div class="badges">
    <span class="badge">Windows v3.0.0-REFACTOR</span>
    <span class="badge">macOS v2.0.1</span>
    <span class="badge">Python 3.13</span>
    <span class="badge">Telegram Bot</span>
    <span class="badge">Ollama Local AI</span>
    <span class="badge">FastMCP</span>
  </div>
</div>

<div class="container">

  <div class="note">
    <strong>Note:</strong> Lotus is designed to run on Windows and macOS as a native desktop agent.
    This page is a project overview running in the Replit development environment (Linux).
    To use Lotus, install it on your Windows or macOS machine following the platform guides below.
  </div>

  <div class="section">
    <h2>What's New in v3.0.0 (Windows Refactor)</h2>
    <div class="cards">
      <div class="card"><h3>🎯 Strict Router</h3><p>Apps vs files cleanly separated. AI fallback only fires for genuine chat — never overrides commands. Unknown commands return a clear error instead of silently going to AI.</p></div>
      <div class="card"><h3>🎵 Music Stability</h3><p>mpv now uses a named-pipe IPC server. Pause, resume, and volume actually work. <code>_kill_mpv</code> only kills our own pid — your other mpv instances are safe.</p></div>
      <div class="card"><h3>🛡️ Real Deduplication</h3><p>Same command sent twice within 3s is dropped. No more accidental double-execute when Telegram retries.</p></div>
      <div class="card"><h3>📨 Single-Reply Frame</h3><p>One centralized formatter wraps every response. No nested markdown, no duplicate "Processing..." + "Done" pairs.</p></div>
      <div class="card"><h3>🔍 Better Research</h3><p>Wikipedia <em>search</em> first, then page resolution. DDG scraper updated to current HTML. Fewer "not found" replies.</p></div>
      <div class="card"><h3>🧹 Cleanup</h3><p>scratch/ removed, dead playlist code consolidated, no more tuple-vs-dict ambiguity in command results.</p></div>
    </div>
  </div>

  <div class="section">
    <h2>Platform Overview</h2>
    <div class="platform-grid">
      <div class="platform-card">
        <h3>🪟 Windows</h3>
        <div class="version">v2.2.0-STABLE &nbsp;·&nbsp; Lead: @SatyamPote</div>
        <ul>
          <li>System-tray GUI (customtkinter)</li>
          <li>PyInstaller standalone bundle</li>
          <li>Inno Setup autonomous installer</li>
          <li>WhatsApp automation via UIA</li>
          <li>PowerShell system hooks</li>
          <li>Hidden pythonw.exe service</li>
        </ul>
      </div>
      <div class="platform-card">
        <h3>🍎 macOS</h3>
        <div class="version">v2.0.1 &nbsp;·&nbsp; Lead: @JayashBhandary</div>
        <ul>
          <li>Native Swift 6 / SwiftUI menu-bar app</li>
          <li>Universal binary DMG installer</li>
          <li>launchd user agent supervision</li>
          <li>Quartz / AppKit / atomacos</li>
          <li>Bundled uv Python runtime</li>
          <li>Control API on localhost:40510</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Key Features</h2>
    <div class="cards">
      <div class="card">
        <h3>⚖️ Priority Routing</h3>
        <p>Commands are matched against a hardened chain — System &gt; Files &gt; Music &gt; Research — before the LLM ever sees them. Deterministic, no hallucinations.</p>
      </div>
      <div class="card">
        <h3>🔍 Research Engine</h3>
        <p>Wikipedia → DuckDuckGo → web scraping pipeline. Produces a structured PDF report and inline images via Telegram.</p>
      </div>
      <div class="card">
        <h3>🤖 Local AI (Ollama)</h3>
        <p>Default: <code>qwen2.5:3b</code>. Runs on 8 GB RAM. Swap to any Ollama model with zero code changes. Nothing leaves your machine.</p>
      </div>
      <div class="card">
        <h3>🎵 Music System</h3>
        <p>Single-instance enforcement. Stream audio via yt-dlp, control playback, adjust volume — all from Telegram.</p>
      </div>
      <div class="card">
        <h3>📹 Screen Capture</h3>
        <p>Take screenshots, record screen videos (ffmpeg), download YouTube audio/video — all triggered remotely.</p>
      </div>
      <div class="card">
        <h3>🔐 Private by Default</h3>
        <p>Allowlist authentication by Telegram user ID. Loopback-only control API. Local LLM only. Config stored at mode 0600.</p>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Architecture</h2>
    <div class="arch-box">Telegram (user)
    │  long-poll updates
    ▼
bot_service.py (background)
    ├── telegram_bot   ── command parse, priority chain
    └── control_api    ── GET /api/status, /api/logs, POST /api/restart
            │
    ┌───────▼────────────────────────────────────┐
    │  MCP-style tool surface (mac_mcp/win_mcp)  │
    │  - desktop (mouse, keyboard, screenshot)   │
    │  - filesystem (find, open, ls, cd)         │
    │  - media (yt-dlp, ffmpeg, mpv)             │
    │  - research (wiki, DDG, scrape, PDF)       │
    │  - tts / voice                             │
    └───────┬────────────────────────────────────┘
            │
    ┌───────▼────────┐    ┌──────────────────────┐
    │  Ollama daemon │    │  Native GUI           │
    │  localhost:    │    │  Lotus.app / Tray     │
    │  11434         │    │  (status + control)   │
    └────────────────┘    └──────────────────────┘</div>
  </div>

  <div class="section">
    <h2>Command Reference</h2>
    <table class="cmd-table">
      <tr><th>Category</th><th>Command</th><th>Description</th></tr>
      <tr><td>Files</td><td><code>find &lt;query&gt;</code></td><td>Fuzzy search across user dirs</td></tr>
      <tr><td>Files</td><td><code>open &lt;filename&gt;</code></td><td>Open in default application</td></tr>
      <tr><td>Files</td><td><code>send &lt;filename&gt;</code></td><td>Upload file to Telegram</td></tr>
      <tr><td>Files</td><td><code>ls</code> / <code>cd</code> / <code>tree</code></td><td>Directory navigation</td></tr>
      <tr><td>Music</td><td><code>play &lt;song&gt;</code></td><td>Search and stream audio via yt-dlp</td></tr>
      <tr><td>Music</td><td><code>pause</code> / <code>resume</code> / <code>stop</code></td><td>Playback control</td></tr>
      <tr><td>Music</td><td><code>volume up</code> / <code>volume down</code></td><td>System volume</td></tr>
      <tr><td>Research</td><td><code>research &lt;topic&gt;</code></td><td>Multi-source research → PDF report</td></tr>
      <tr><td>Research</td><td><code>chat &lt;prompt&gt;</code></td><td>One-shot Ollama LLM completion</td></tr>
      <tr><td>Research</td><td><code>say &lt;text&gt;</code></td><td>Local TTS + Telegram voice note</td></tr>
      <tr><td>System</td><td><code>dashboard</code></td><td>Battery, CPU, RAM, disk, uptime, IP</td></tr>
      <tr><td>System</td><td><code>take screenshot</code></td><td>Capture desktop as PNG</td></tr>
      <tr><td>System</td><td><code>record screen &lt;sec&gt;</code></td><td>Screen video capture</td></tr>
      <tr><td>System</td><td><code>lock</code> / <code>sleep</code> / <code>shutdown</code></td><td>Power management</td></tr>
    </table>
  </div>

  <div class="section">
    <h2>Quick Start</h2>
    <div class="cards">
      <div class="card">
        <h3>1. Get a Telegram bot token</h3>
        <p>Message <code>@BotFather</code> on Telegram to create a bot and get a token. Get your user ID from <code>@userinfobot</code>.</p>
      </div>
      <div class="card">
        <h3>2. Install Ollama</h3>
        <p>Download from <code>ollama.com</code>, then run: <code>ollama pull qwen2.5:3b</code></p>
      </div>
      <div class="card">
        <h3>3. Install Lotus</h3>
        <p>Windows: run <code>LotusSetup.exe</code>. macOS: mount the DMG and launch <code>Lotus.app</code>.</p>
      </div>
      <div class="card">
        <h3>4. Configure &amp; Start</h3>
        <p>Enter your token and user ID in the GUI wizard. DM your bot: <code>dashboard</code>, <code>take screenshot</code>, or <code>play lo-fi</code>.</p>
      </div>
    </div>
  </div>

</div>
</body>
</html>
"""


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok", "project": "lotus"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith("/static/"):
            rel = self.path[len("/static/"):].split("?")[0]
            safe = os.path.normpath(rel).lstrip(os.sep).lstrip("/")
            path = os.path.join(STATIC_DIR, safe)
            if os.path.isfile(path) and path.startswith(STATIC_DIR):
                ext = os.path.splitext(path)[1].lower()
                ctype = {
                    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".svg": "image/svg+xml", ".css": "text/css", ".js": "application/javascript",
                }.get(ext, "application/octet-stream")
                with open(path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_response(404)
            self.end_headers()
            return

        body = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Lotus project overview running at http://0.0.0.0:{port}")
    server.serve_forever()
