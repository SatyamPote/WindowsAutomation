#!/usr/bin/env bash
# scripts/cleanup_git.sh
# One-shot Git LFS / large-file cleanup for the Lotus repo.
# Run this from the Replit shell when the agent cannot push directly:
#
#     bash scripts/cleanup_git.sh
#
# Then push using the Replit Git pane (or `git push origin main`).

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
echo "Repo root: $(pwd)"

BLOB="attached_assets/Lotus_1778779174337.exe"

echo "── 1) Untrack the 59 MB LFS binary"
if git ls-files --error-unmatch "$BLOB" >/dev/null 2>&1; then
    git rm --cached "$BLOB"
    echo "   ✓ untracked $BLOB"
else
    echo "   • already untracked"
fi

echo "── 2) Untrack any other accidentally-tracked generated files"
PATTERNS=(
    "dist/*" "build/*" "installer_output/*"
    "**/__pycache__/*" "*.pyc" "*.pyo"
    "*.log" "*.pid"
    "storage/*" "logs/*" "reports/*" "data/*"
    "*.mp4" "*.mp3" "*.wav" "*.webm"
    "attached_assets/*.exe" "attached_assets/*.zip"
    "attached_assets/*.dmg" "attached_assets/*.msi"
)
for p in "${PATTERNS[@]}"; do
    git rm -r --cached --ignore-unmatch -- "$p" >/dev/null 2>&1 || true
done
echo "   ✓ done"

echo "── 3) Drop .gitattributes (disables LFS for new pushes)"
if [[ -f .gitattributes ]]; then
    rm -f .gitattributes
    echo "   ✓ removed .gitattributes"
else
    echo "   • already absent"
fi

echo "── 4) Stage .gitignore (explicit — never `git add -A`)"
git add .gitignore
# .gitattributes was deleted — record that deletion explicitly
git add -u .gitattributes 2>/dev/null || true

echo "── 5) Status preview"
# Disable pipefail for the preview — `head` closing the pipe early is normal
# and would otherwise abort the script before commit under `set -o pipefail`.
set +o pipefail
git --no-optional-locks status -sb 2>/dev/null | head -25 || true
set -o pipefail

echo
echo "── 6) Commit"
git commit -m "Clean repo: drop LFS binary, untrack generated files, harden .gitignore" || {
    echo "   • nothing to commit (already clean)"
}

echo
echo "✅ Local cleanup complete."
echo "   Now push:  git push origin main"
echo "   Or use the Replit Git pane (recommended for auth)."
