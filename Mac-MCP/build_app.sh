#!/usr/bin/env bash
# Build Lotus.app using PyInstaller
#
# Usage:
#   bash build_app.sh            # build
#   bash build_app.sh --clean    # remove dist/ and build/ first

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${1:-}" == "--clean" ]]; then
    echo "Cleaning previous build…"
    rm -rf dist build
fi

# Use the project venv if available
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "ERROR: Python not found."
    exit 1
fi

echo "Python: $($PYTHON --version)"

# Install pyinstaller if not present
"$PYTHON" -m pip install pyinstaller --quiet

echo ""
echo "Building Lotus.app…"
"$PYTHON" -m PyInstaller Lotus.spec --noconfirm

if [ -d "dist/Lotus.app" ]; then
    echo ""
    echo "✅ Build complete: dist/Lotus.app"
    echo ""
    echo "   To run:    open dist/Lotus.app"
    echo "   To install: cp -r dist/Lotus.app /Applications/"
    echo ""
    echo "   NOTE: On first launch macOS will ask you to grant"
    echo "   Accessibility and Screen Recording permissions."
else
    echo "❌ Build failed — check output above."
    exit 1
fi
