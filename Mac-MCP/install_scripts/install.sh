#!/usr/bin/env bash
# Lotus macOS Install Script
# Registers bot_service.py as a launchd login agent (com.lotus.botservice).
#
# Usage:
#   cd /path/to/Mac-MCP
#   bash install_scripts/install.sh
#
# Requirements:
#   - Python 3.13+ with mac-mcp dependencies installed (uv sync)
#   - config.json must exist (run the Lotus app first-time setup)

set -euo pipefail

# ── Resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_DST="$HOME/Library/LaunchAgents/com.lotus.botservice.plist"
LOG_DIR="$HOME/Library/Application Support/Lotus/logs"
LOG_PATH="$LOG_DIR/bot_service.log"
BOT_SERVICE="$PROJECT_DIR/bot_service.py"
CONTROL_PORT="${LOTUS_CONTROL_PORT:-40510}"

# ── Check config.json ────────────────────────────────────────────────────────
if [ ! -f "$PROJECT_DIR/config.json" ]; then
    echo ""
    echo "ERROR: config.json not found at $PROJECT_DIR/config.json"
    echo "Run the Lotus app first to complete first-time setup."
    exit 1
fi

# ── Find Python runtime ──────────────────────────────────────────────────────
# Prefer uv (ensures the right virtualenv), then .venv, then system python3.

if command -v uv &>/dev/null; then
    RUNTIME_TYPE="uv"
    UV_PATH="$(command -v uv)"
    echo "Runtime:    uv → $UV_PATH"
elif [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    RUNTIME_TYPE="venv"
    VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
    echo "Runtime:    venv → $VENV_PYTHON"
elif command -v python3 &>/dev/null; then
    RUNTIME_TYPE="system"
    SYS_PYTHON="$(command -v python3)"
    echo "Runtime:    system → $SYS_PYTHON"
else
    echo "ERROR: No Python 3 found. Install Python 3.13+ or run: uv sync"
    exit 1
fi

echo "Project:    $PROJECT_DIR"
echo "Log:        $LOG_PATH"
echo "Control port: $CONTROL_PORT"

# ── Create directories ───────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
mkdir -p "$HOME/Library/LaunchAgents"

# ── Build ProgramArguments XML ───────────────────────────────────────────────
# Different runtimes need different argument arrays.

case "$RUNTIME_TYPE" in
    uv)
        PROG_ARGS="        <string>$UV_PATH</string>
        <string>run</string>
        <string>python</string>
        <string>$BOT_SERVICE</string>"
        ;;
    venv)
        PROG_ARGS="        <string>$VENV_PYTHON</string>
        <string>$BOT_SERVICE</string>"
        ;;
    system)
        PROG_ARGS="        <string>$SYS_PYTHON</string>
        <string>$BOT_SERVICE</string>"
        ;;
esac

# ── Write plist ──────────────────────────────────────────────────────────────
# We generate the plist directly rather than using sed on the template so the
# ProgramArguments array works correctly for both single-executable and
# multi-argument (uv run python ...) invocations.

cat > "$PLIST_DST" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lotus.botservice</string>

    <key>ProgramArguments</key>
    <array>
$PROG_ARGS
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>

    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>ANONYMIZED_TELEMETRY</key>
        <string>true</string>
        <key>LOTUS_CONTROL_PORT</key>
        <string>$CONTROL_PORT</string>
    </dict>
</dict>
</plist>
PLIST_EOF

echo "Plist:      $PLIST_DST"

# ── Unload any existing agent ────────────────────────────────────────────────
# Try modern bootout first, fall back to deprecated unload for older macOS.
launchctl bootout "gui/$(id -u)/com.lotus.botservice" 2>/dev/null || \
    launchctl unload "$PLIST_DST" 2>/dev/null || true

# ── Load the new agent ───────────────────────────────────────────────────────
# bootstrap is the modern replacement for launchctl load.
if launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null; then
    LOAD_OK=1
else
    launchctl load "$PLIST_DST" 2>/dev/null && LOAD_OK=1 || LOAD_OK=0
fi

echo ""
if [ "${LOAD_OK:-0}" -eq 1 ]; then
    echo "✅ Lotus service installed (com.lotus.botservice)"
    echo "   The bot will start automatically at next login."
    echo ""
    echo "   Start it right now:"
    echo "     launchctl kickstart gui/\$(id -u)/com.lotus.botservice"
    echo ""
    echo "   Check status:"
    echo "     launchctl print gui/\$(id -u)/com.lotus.botservice"
    echo ""
    echo "   View logs:"
    echo "     tail -f \"$LOG_PATH\""
    echo ""
    echo "   Control API (once the service is running):"
    echo "     curl http://127.0.0.1:$CONTROL_PORT/api/status"
    echo ""
    echo "   Uninstall:"
    echo "     bash \"$SCRIPT_DIR/uninstall.sh\""
else
    echo "⚠  Service registered but could not be loaded automatically."
    echo "   Try: launchctl bootstrap gui/\$(id -u) \"$PLIST_DST\""
fi
