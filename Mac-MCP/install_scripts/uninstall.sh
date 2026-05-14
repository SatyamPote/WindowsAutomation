#!/usr/bin/env bash
# Lotus macOS Uninstall Script
# Removes the com.lotus.botservice launchd login agent.
#
# Usage:
#   bash install_scripts/uninstall.sh

set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.lotus.botservice.plist"
SERVICE="gui/$(id -u)/com.lotus.botservice"

if [ ! -f "$PLIST" ]; then
    echo "Lotus service not installed (plist not found at $PLIST)."
    exit 0
fi

# Stop the running agent first (ignore errors if not running)
launchctl kill SIGTERM "$SERVICE" 2>/dev/null || true
sleep 1

# Unload with modern bootout, fall back to deprecated unload
launchctl bootout "$SERVICE" 2>/dev/null || \
    launchctl unload "$PLIST" 2>/dev/null || true

rm -f "$PLIST"

# Clean up the port file so the app knows the service is gone
PORT_FILE="$HOME/Library/Application Support/Lotus/control.port"
rm -f "$PORT_FILE"

echo "✅ Lotus service removed."
echo "   The bot will no longer start at login."
echo ""
echo "   Config and logs are preserved at:"
echo "     $HOME/Library/Application Support/Lotus/"
echo ""
echo "   To delete all Lotus data:"
echo "     rm -rf \"$HOME/Library/Application Support/Lotus\""
