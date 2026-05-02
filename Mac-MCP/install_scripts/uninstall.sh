#!/usr/bin/env bash
# Lotus macOS Uninstall Script
# Removes the Lotus launchd login agent.
#
# Usage:
#   bash install_scripts/uninstall.sh

set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.lotus.botservice.plist"

if [ ! -f "$PLIST" ]; then
    echo "Lotus login agent not installed (plist not found)."
    exit 0
fi

# Stop the running agent if active
launchctl stop com.lotus.botservice 2>/dev/null || true
launchctl unload "$PLIST" 2>/dev/null || true

rm -f "$PLIST"

echo "✅ Lotus login agent removed."
echo "   The bot will no longer start at login."
echo ""
echo "   Your config and logs are preserved at:"
echo "     $HOME/Library/Application Support/Lotus/"
echo ""
echo "   To delete all Lotus data:"
echo "     rm -rf \"$HOME/Library/Application Support/Lotus\""
