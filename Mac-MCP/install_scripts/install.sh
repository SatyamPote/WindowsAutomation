#!/usr/bin/env bash
# Lotus macOS Install Script
# Installs the Lotus Telegram bot as a launchd login agent so it starts
# automatically at login (no GUI required after first run of app.py).
#
# Usage:
#   cd /path/to/Mac-MCP
#   bash install_scripts/install.sh
#
# Requirements:
#   - Python 3.13+ with mac-mcp dependencies installed (uv sync)
#   - config.json already created (run: python app.py — first-time setup)

set -euo pipefail

# ── Resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SRC="$SCRIPT_DIR/com.lotus.botservice.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.lotus.botservice.plist"
LOG_PATH="$HOME/Library/Application Support/Lotus/logs/bot_service.log"
BOT_SERVICE="$PROJECT_DIR/bot_service.py"

# ── Find Python executable ───────────────────────────────────────────────────
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
else
    echo "ERROR: Python 3 not found. Install Python 3.13+ or run: uv sync"
    exit 1
fi

echo "Using Python: $PYTHON"
echo "Project dir:  $PROJECT_DIR"
echo "Log path:     $LOG_PATH"

# ── Check config.json exists ────────────────────────────────────────────────
if [ ! -f "$PROJECT_DIR/config.json" ]; then
    echo ""
    echo "ERROR: config.json not found."
    echo "Run app.py first to complete the first-time setup:"
    echo "  python \"$PROJECT_DIR/app.py\""
    exit 1
fi

# ── Create log directory ─────────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_PATH")"

# ── Write plist ──────────────────────────────────────────────────────────────
mkdir -p "$HOME/Library/LaunchAgents"

sed \
    -e "s|PYTHON_EXECUTABLE|$PYTHON|g" \
    -e "s|BOT_SERVICE_PATH|$BOT_SERVICE|g" \
    -e "s|LOG_PATH|$LOG_PATH|g" \
    -e "s|WORKING_DIR|$PROJECT_DIR|g" \
    "$PLIST_SRC" > "$PLIST_DST"

echo "Plist written: $PLIST_DST"

# ── Unload existing agent if loaded ──────────────────────────────────────────
launchctl unload "$PLIST_DST" 2>/dev/null || true

# ── Load the new agent ───────────────────────────────────────────────────────
launchctl load "$PLIST_DST"

echo ""
echo "✅ Lotus bot service installed as a login agent."
echo "   It will start automatically at next login."
echo ""
echo "   To start it right now:"
echo "     launchctl start com.lotus.botservice"
echo ""
echo "   To view logs:"
echo "     tail -f \"$LOG_PATH\""
echo ""
echo "   To uninstall:"
echo "     bash \"$SCRIPT_DIR/uninstall.sh\""
