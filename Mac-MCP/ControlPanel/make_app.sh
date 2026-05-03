#!/usr/bin/env bash
# Build Lotus.app from the Swift Package and place it in Mac-MCP/
#
# Usage:
#   cd Mac-MCP/ControlPanel
#   bash make_app.sh
#
# Requirements:
#   - Xcode Command Line Tools (xcode-select --install)
#   - swift, sips, iconutil, codesign in PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"   # Mac-MCP/
APP_NAME="Lotus"
BUNDLE_ID="com.lotus.controlpanel"
VERSION="1.0.0"
BUILD_DIR="$SCRIPT_DIR/.build/release"
APP_DEST="$PROJECT_DIR/$APP_NAME.app"
ASSETS="$PROJECT_DIR/assets"
LOGO="$ASSETS/lotus_logo.png"

echo "══════════════════════════════════════"
echo "  Building $APP_NAME.app"
echo "══════════════════════════════════════"
echo "  Project: $PROJECT_DIR"
echo "  Output:  $APP_DEST"
echo ""

# ── 1. Build release binary ──────────────────────────────────────────────────
echo "▸ Building Swift package (release)…"
cd "$SCRIPT_DIR"
swift build -c release
echo "  ✓ Binary at $BUILD_DIR/$APP_NAME"

# ── 2. App bundle structure ──────────────────────────────────────────────────
echo "▸ Creating app bundle…"
rm -rf "$APP_DEST"
CONTENTS="$APP_DEST/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
mkdir -p "$MACOS" "$RESOURCES"

cp "$BUILD_DIR/$APP_NAME" "$MACOS/$APP_NAME"

# ── 3. Info.plist ─────────────────────────────────────────────────────────────
echo "▸ Writing Info.plist…"
cat > "$CONTENTS/Info.plist" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>

    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>

    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>

    <key>CFBundleVersion</key>
    <string>$VERSION</string>

    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>

    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>

    <key>CFBundlePackageType</key>
    <string>APPL</string>

    <key>CFBundleSignature</key>
    <string>????</string>

    <key>CFBundleIconFile</key>
    <string>AppIcon</string>

    <key>NSPrincipalClass</key>
    <string>NSApplication</string>

    <key>NSHighResolutionCapable</key>
    <true/>

    <!-- Hide dock icon; app lives in the menu bar -->
    <key>LSUIElement</key>
    <true/>

    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>

    <!-- Required for running launchctl subprocesses -->
    <key>NSAppleEventsUsageDescription</key>
    <string>Lotus uses launchctl to manage the bot service.</string>
</dict>
</plist>
PLIST_EOF

# ── 4. App icon (.icns) ───────────────────────────────────────────────────────
echo "▸ Generating AppIcon.icns from ${LOGO}..."

if [ -f "$LOGO" ]; then
    ICONSET_DIR="$SCRIPT_DIR/.build/AppIcon.iconset"
    rm -rf "$ICONSET_DIR"
    mkdir -p "$ICONSET_DIR"

    # Helper: resize source PNG and copy to one or more iconset filenames
    mk_icon() {
        local sz=$1; shift
        local tmp="$ICONSET_DIR/_tmp.png"
        sips -z "$sz" "$sz" "$LOGO" --out "$tmp" > /dev/null 2>&1
        for name in "$@"; do cp "$tmp" "$ICONSET_DIR/$name"; done
        rm -f "$tmp"
    }

    mk_icon 16   icon_16x16.png
    mk_icon 32   icon_16x16@2x.png icon_32x32.png
    mk_icon 64   icon_32x32@2x.png
    mk_icon 128  icon_128x128.png
    mk_icon 256  icon_128x128@2x.png icon_256x256.png
    mk_icon 512  icon_256x256@2x.png icon_512x512.png
    mk_icon 1024 icon_512x512@2x.png

    iconutil -c icns "$ICONSET_DIR" -o "$RESOURCES/AppIcon.icns"
    rm -rf "$ICONSET_DIR"
    echo "  ✓ AppIcon.icns generated"
else
    echo "  ⚠ $LOGO not found — skipping icon (app will use default)"
fi

# ── 5. Ad-hoc code signing ────────────────────────────────────────────────────
echo "▸ Ad-hoc signing…"
codesign --force --deep --sign - "$APP_DEST" 2>&1 && echo "  ✓ Signed"

# ── 6. Summary ────────────────────────────────────────────────────────────────
SIZE=$(du -sh "$APP_DEST" | cut -f1)
echo ""
echo "══════════════════════════════════════"
echo "  ✅ $APP_DEST  ($SIZE)"
echo "══════════════════════════════════════"
echo ""
echo "  Run the app:"
echo "    open \"$APP_DEST\""
echo ""
echo "  Move to Applications:"
echo "    cp -R \"$APP_DEST\" /Applications/"
echo ""
echo "  The app reads Mac-MCP config from:"
echo "    $PROJECT_DIR/config.json"
echo ""
