#!/usr/bin/env python3
"""
generate_changelog.py — build release notes from git history.

Usage:
    python scripts/generate_changelog.py                    # plain changelog.txt
    python scripts/generate_changelog.py --release          # rich markdown for GH Release
    python scripts/generate_changelog.py --output notes.md
    python scripts/generate_changelog.py --since v3.0.0     # explicit range

Categorizes commits by conventional-commit prefix into:
    ✨ New Features    (feat:, add:)
    🐛 Bug Fixes       (fix:, bug:)
    ⚡ Performance     (perf:, optimize:)
    🔒 Security        (security:, sec:)
    📝 Other Changes   (everything else)

Falls back gracefully when git history is shallow or the repo is fresh.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Iterable

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VERSION_FILE = os.path.join(REPO_ROOT, "version.json")

CATEGORIES: list[tuple[str, str, tuple[str, ...]]] = [
    ("✨ New Features",          "features", ("feat", "add", "new")),
    ("🐛 Bug Fixes",             "fixes",    ("fix", "bug", "patch")),
    ("⚡ Performance Improvements", "perf",  ("perf", "optimize", "speed")),
    ("🔒 Security Updates",      "security", ("security", "sec", "cve")),
]


def run(*args: str) -> str:
    try:
        out = subprocess.check_output(args, cwd=REPO_ROOT, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def load_version() -> str:
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def previous_tag(current_tag: str | None) -> str | None:
    """Find the most recent tag *before* current_tag (or before HEAD)."""
    tags = run("git", "tag", "--sort=-creatordate").splitlines()
    if not tags:
        return None
    if current_tag and current_tag in tags:
        idx = tags.index(current_tag)
        return tags[idx + 1] if idx + 1 < len(tags) else None
    return tags[0]


def get_commits(since: str | None) -> list[tuple[str, str]]:
    """Return [(sha, subject)] for the chosen range."""
    fmt = "%h|%s"
    rng = f"{since}..HEAD" if since else "HEAD"
    raw = run("git", "log", "--no-merges", f"--pretty=format:{fmt}", rng)
    if not raw:
        return []
    out = []
    for line in raw.splitlines():
        if "|" in line:
            sha, subj = line.split("|", 1)
            out.append((sha.strip(), subj.strip()))
    return out


def changed_files(since: str | None) -> list[str]:
    rng = f"{since}..HEAD" if since else "HEAD"
    raw = run("git", "diff", "--name-only", rng)
    return [l for l in raw.splitlines() if l.strip()]


def classify(subject: str) -> str:
    head = subject.lower().split(":", 1)[0].strip()
    head = re.sub(r"\([^)]*\)$", "", head).strip()
    for label, _key, prefixes in CATEGORIES:
        if any(head == p or head.startswith(p + "/") for p in prefixes):
            return label
    return "📝 Other Changes"


def format_text(version: str, buckets: dict[str, list[str]], files: list[str]) -> str:
    lines = [f"Lotus v{version}", "=" * (len(version) + 8), ""]
    for label, _, _ in CATEGORIES:
        items = buckets.get(label, [])
        if items:
            lines.append(label)
            lines.extend(f"  - {x}" for x in items)
            lines.append("")
    other = buckets.get("📝 Other Changes", [])
    if other:
        lines.append("📝 Other Changes")
        lines.extend(f"  - {x}" for x in other)
        lines.append("")
    if files:
        lines.append(f"Changed files ({len(files)}):")
        lines.extend(f"  - {f}" for f in files[:40])
        if len(files) > 40:
            lines.append(f"  ... and {len(files) - 40} more")
    return "\n".join(lines).rstrip() + "\n"


def format_markdown(version: str, buckets: dict[str, list[str]], files: list[str]) -> str:
    lines = [f"# 🌸 Lotus v{version}", ""]
    has_any = False
    for label, _, _ in CATEGORIES:
        items = buckets.get(label, [])
        if items:
            has_any = True
            lines.append(f"## {label}")
            lines.extend(f"- {x}" for x in items)
            lines.append("")
    other = buckets.get("📝 Other Changes", [])
    if other:
        has_any = True
        lines.append("## 📝 Other Changes")
        lines.extend(f"- {x}" for x in other)
        lines.append("")
    if not has_any:
        lines.append("_No notable commits since the previous release._")
        lines.append("")
    if files:
        lines.append("<details><summary>📂 Changed files</summary>")
        lines.append("")
        lines.extend(f"- `{f}`" for f in files[:60])
        if len(files) > 60:
            lines.append(f"- _... and {len(files) - 60} more_")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 📥 Download")
    lines.append("")
    lines.append("- **`LotusSetup.exe`** — full Windows installer (recommended)")
    lines.append("- `Lotus.exe` — standalone control panel")
    lines.append("- `LotusTray.exe` — system tray launcher")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="changelog.txt", help="Output file path")
    ap.add_argument("--release", action="store_true",
                    help="Emit GitHub-Release-flavored markdown")
    ap.add_argument("--since", default=None,
                    help="Git ref to diff from (default: previous tag)")
    args = ap.parse_args()

    version = load_version()
    since = args.since or previous_tag(f"v{version}")
    commits = get_commits(since)
    files = changed_files(since)

    buckets: dict[str, list[str]] = {}
    for sha, subj in commits:
        bucket = classify(subj)
        buckets.setdefault(bucket, []).append(f"{subj} ({sha})")

    if args.release:
        body = format_markdown(version, buckets, files)
    else:
        body = format_text(version, buckets, files)

    out_path = args.output
    if not os.path.isabs(out_path):
        out_path = os.path.join(REPO_ROOT, out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body)

    print(f"Generated {os.path.relpath(out_path, REPO_ROOT)} "
          f"({len(commits)} commits, since={since or 'beginning'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
