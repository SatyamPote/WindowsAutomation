#!/usr/bin/env python3
"""
version_bump.py — bump the Lotus version in version.json (single source of truth).

Usage:
    python scripts/version_bump.py patch        # 3.0.0 -> 3.0.1
    python scripts/version_bump.py minor        # 3.0.0 -> 3.1.0
    python scripts/version_bump.py major        # 3.0.0 -> 4.0.0
    python scripts/version_bump.py set 3.2.5    # explicit
    python scripts/version_bump.py --dry-run patch

Also updates installer.iss `AppVersion=...` to keep them in sync.
After bumping, commit + push will trigger .github/workflows/release.yml.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VERSION_FILE = os.path.join(REPO_ROOT, "version.json")
INSTALLER_FILE = os.path.join(REPO_ROOT, "installer.iss")


def parse(v: str) -> tuple[int, int, int]:
    head = v.lstrip("vV").split("-")[0].split("+")[0]
    parts = head.split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as e:
        raise SystemExit(f"Invalid version '{v}': {e}")


def bump(current: str, level: str) -> str:
    a, b, c = parse(current)
    if level == "major":
        return f"{a + 1}.0.0"
    if level == "minor":
        return f"{a}.{b + 1}.0"
    if level == "patch":
        return f"{a}.{b}.{c + 1}"
    raise SystemExit(f"Unknown bump level: {level}")


def update_installer_iss(new_version: str) -> bool:
    if not os.path.isfile(INSTALLER_FILE):
        return False
    with open(INSTALLER_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    new_text, n = re.subn(
        r"^(AppVersion\s*=\s*).+$",
        rf"\g<1>{new_version}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0:
        return False
    with open(INSTALLER_FILE, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Bump Lotus version")
    ap.add_argument("level", choices=["major", "minor", "patch", "set"])
    ap.add_argument("value", nargs="?", help="Required when level=set")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(VERSION_FILE):
        raise SystemExit(f"Missing {VERSION_FILE}")

    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    current = data.get("version", "0.0.0")

    if args.level == "set":
        if not args.value:
            raise SystemExit("`set` requires a value, e.g. `set 3.2.5`")
        new_version = ".".join(str(p) for p in parse(args.value))
    else:
        new_version = bump(current, args.level)

    print(f"Current: {current}")
    print(f"New:     {new_version}")

    if args.dry_run:
        print("(dry-run; no files changed)")
        return 0

    data["version"] = new_version
    data["build_date"] = date.today().isoformat()

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"✓ Updated {os.path.relpath(VERSION_FILE, REPO_ROOT)}")

    if update_installer_iss(new_version):
        print(f"✓ Updated {os.path.relpath(INSTALLER_FILE, REPO_ROOT)} (AppVersion)")
    else:
        print(f"! Could not patch AppVersion in {INSTALLER_FILE}")

    print()
    print(f"Next: git commit -am 'Release v{new_version}' && git push")
    print("→ .github/workflows/release.yml will build and publish automatically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
