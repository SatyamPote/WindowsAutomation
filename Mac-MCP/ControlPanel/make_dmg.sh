#!/usr/bin/env bash
# Build a drag-to-install DMG for Lotus.app
#
# Usage:
#   cd Mac-MCP/ControlPanel
#   bash make_dmg.sh            # uses existing Mac-MCP/Lotus.app
#   bash make_dmg.sh --build    # rebuilds Lotus.app first
#
# Output:
#   Mac-MCP/dist/Lotus-<version>.dmg

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"   # Mac-MCP/
APP_NAME="Lotus"
APP_PATH="$PROJECT_DIR/$APP_NAME.app"
VERSION="2.0.0"
VOL_NAME="Lotus $VERSION"
DIST_DIR="$PROJECT_DIR/dist"
DMG_PATH="$DIST_DIR/$APP_NAME-$VERSION.dmg"
STAGING="$SCRIPT_DIR/.build/dmg-staging"
TMP_DMG="$SCRIPT_DIR/.build/$APP_NAME-tmp.dmg"
BG_IMG="$PROJECT_DIR/assets/dmg_banner.png"

echo "══════════════════════════════════════"
echo "  Building $APP_NAME DMG"
echo "══════════════════════════════════════"

# ── 1. Optionally rebuild app ────────────────────────────────────────────────
if [[ "${1:-}" == "--build" ]]; then
    echo "▸ Rebuilding $APP_NAME.app…"
    bash "$SCRIPT_DIR/make_app.sh"
fi

if [ ! -d "$APP_PATH" ]; then
    echo "✗ $APP_PATH not found. Run with --build or run make_app.sh first."
    exit 1
fi

# ── 2. Stage ─────────────────────────────────────────────────────────────────
echo "▸ Staging files…"
rm -rf "$STAGING" "$TMP_DMG"
mkdir -p "$STAGING" "$DIST_DIR"

cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# Optional background image (Finder shows it when DMG is opened)
if [ -f "$BG_IMG" ]; then
    mkdir -p "$STAGING/.background"
    cp "$BG_IMG" "$STAGING/.background/background.png"
fi

# ── 3. Create writable DMG ───────────────────────────────────────────────────
echo "▸ Creating writable DMG…"
hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$STAGING" \
    -ov \
    -fs HFS+ \
    -format UDRW \
    "$TMP_DMG" >/dev/null

# ── 4. Mount, style, unmount ─────────────────────────────────────────────────
echo "▸ Styling DMG window…"
# Detach any leftover volume from a previous run
hdiutil detach "/Volumes/$VOL_NAME" -quiet 2>/dev/null || true

# Mount under /Volumes so Finder sees it
hdiutil attach "$TMP_DMG" -noautoopen >/dev/null
MOUNT_DIR="/Volumes/$VOL_NAME"
sleep 2

# CI runners are headless — Finder may not be running or may not accept
# AppleScript. Skip styling there; the DMG itself is still produced.
if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "  ⚠ CI environment detected — skipping Finder window styling"
else
    # Make sure Finder is up before sending it AppleScript
    open -a Finder >/dev/null 2>&1 || true
    sleep 1

    # Apply window layout via AppleScript. Failures here are non-fatal.
    osascript <<APPLESCRIPT || true
tell application "Finder"
    tell disk "$VOL_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 120, 840, 759}
        set viewOptions to icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 128
        set text size of viewOptions to 13
        try
            set background picture of viewOptions to file ".background:background.png"
        end try
        set position of item "$APP_NAME.app" of container window to {160, 320}
        set position of item "Applications" of container window to {480, 320}
        update without registering applications
        delay 1
        close
    end tell
end tell
APPLESCRIPT
fi

sync
hdiutil detach "$MOUNT_DIR" -quiet || hdiutil detach "$MOUNT_DIR" -force -quiet

# ── 5. Convert to compressed read-only DMG ───────────────────────────────────
echo "▸ Compressing final DMG…"
rm -f "$DMG_PATH"
hdiutil convert "$TMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH" >/dev/null
rm -f "$TMP_DMG"

# ── 6. Sign ──────────────────────────────────────────────────────────────────
echo "▸ Ad-hoc signing DMG…"
codesign --force --sign - "$DMG_PATH" 2>&1 | sed 's/^/  /' || true

SIZE=$(du -sh "$DMG_PATH" | cut -f1)
echo ""
echo "══════════════════════════════════════"
echo "  ✅ $DMG_PATH  ($SIZE)"
echo "══════════════════════════════════════"
echo ""
echo "  Test it:"
echo "    open \"$DMG_PATH\""
