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
VERSION="2.0.0"
APP_DEST="$PROJECT_DIR/$APP_NAME.app"
ASSETS="$PROJECT_DIR/assets"
LOGO="$ASSETS/lotus_logo.png"

# Architectures to build. Override with LOTUS_ARCHS="arm64" for a host-only build.
LOTUS_ARCHS="${LOTUS_ARCHS:-arm64 x86_64}"
ARCH_ARGS=()
for a in $LOTUS_ARCHS; do ARCH_ARGS+=(--arch "$a"); done

echo "══════════════════════════════════════"
echo "  Building $APP_NAME.app"
echo "══════════════════════════════════════"
echo "  Project: $PROJECT_DIR"
echo "  Output:  $APP_DEST"
echo ""

# ── 1. Build release binary ──────────────────────────────────────────────────
echo "▸ Building Swift package (release) for: $LOTUS_ARCHS"
cd "$SCRIPT_DIR"
swift build -c release "${ARCH_ARGS[@]}"
# Resolve the actual output dir (single-arch → .build/release,
# multi-arch → .build/apple/Products/Release).
BUILD_DIR="$(swift build -c release "${ARCH_ARGS[@]}" --show-bin-path)"
BIN="$BUILD_DIR/$APP_NAME"
test -x "$BIN" || { echo "✗ Built binary not found at $BIN"; exit 1; }
echo "  ✓ Binary at $BIN"
echo "  ✓ Architectures: $(lipo -archs "$BIN")"

# ── 2. App bundle structure ──────────────────────────────────────────────────
echo "▸ Creating app bundle…"
rm -rf "$APP_DEST"
CONTENTS="$APP_DEST/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
mkdir -p "$MACOS" "$RESOURCES"

cp "$BIN" "$MACOS/$APP_NAME"

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

# ── 4b. Bundle uv binary ─────────────────────────────────────────────────────
# uv is a fast, self-contained Python package manager. Bundling it makes
# Lotus.app standalone — no system uv, brew, or python required at install.
echo "▸ Bundling uv binary…"
UV_BIN_DIR="$RESOURCES/bin"
mkdir -p "$UV_BIN_DIR"

if [ -x "$UV_BIN_DIR/uv" ]; then
    echo "  ✓ uv already bundled"
else
    # Download both arch tarballs and lipo into a universal binary
    UV_VERSION="${UV_VERSION:-0.5.4}"
    UV_DL="$SCRIPT_DIR/.build/uv-download"
    rm -rf "$UV_DL"; mkdir -p "$UV_DL"

    for ARCH_PAIR in "aarch64-apple-darwin:arm64" "x86_64-apple-darwin:x86_64"; do
        TRIPLE="${ARCH_PAIR%:*}"
        ARCH="${ARCH_PAIR#*:}"
        TARBALL="uv-$TRIPLE.tar.gz"
        URL="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$TARBALL"
        echo "  Downloading uv $UV_VERSION ($ARCH)…"
        curl -fsSL "$URL" -o "$UV_DL/$TARBALL"
        tar -xzf "$UV_DL/$TARBALL" -C "$UV_DL"
        cp "$UV_DL/uv-$TRIPLE/uv" "$UV_DL/uv-$ARCH"
    done

    lipo -create "$UV_DL/uv-arm64" "$UV_DL/uv-x86_64" -output "$UV_BIN_DIR/uv"
    chmod +x "$UV_BIN_DIR/uv"
    rm -rf "$UV_DL"
    echo "  ✓ uv bundled at $UV_BIN_DIR/uv ($(lipo -archs "$UV_BIN_DIR/uv"))"
fi

# ── 4c. Bundle project source for runtime sync ───────────────────────────────
# bot_service.py + pyproject.toml + uv.lock + src/ are already exposed via
# Bundle.module (Package.swift resources), but we also stage a clean copy
# under Resources/runtime-template so InstallManager can rsync it out to the
# user's writable Application Support dir on first launch.
echo "▸ Staging runtime template…"
TEMPLATE_DIR="$RESOURCES/runtime-template"
rm -rf "$TEMPLATE_DIR"; mkdir -p "$TEMPLATE_DIR"
cp "$PROJECT_DIR/bot_service.py" "$TEMPLATE_DIR/"
cp "$PROJECT_DIR/pyproject.toml" "$TEMPLATE_DIR/"
cp "$PROJECT_DIR/uv.lock"        "$TEMPLATE_DIR/"
# rsync src/ but strip __pycache__, .egg-info, .DS_Store, .pyc
rsync -a \
    --exclude='__pycache__' \
    --exclude='*.egg-info' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    "$PROJECT_DIR/src/" "$TEMPLATE_DIR/src/"
echo "  ✓ Runtime template at $TEMPLATE_DIR ($(du -sh "$TEMPLATE_DIR" | cut -f1))"

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
