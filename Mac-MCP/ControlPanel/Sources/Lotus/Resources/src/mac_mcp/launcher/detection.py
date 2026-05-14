"""Fuzzy app name resolution."""

from pathlib import Path
from thefuzz import process as fuzzy
from mac_mcp.launcher.app_registry import get_all_apps


def find_app(name: str) -> tuple[str, Path] | None:
    """Fuzzy-match an app name. Returns (matched_name, path) or None."""
    apps = get_all_apps()
    if not apps:
        return None

    name_lower = name.lower()

    # Exact match first
    if name_lower in apps:
        return name_lower, apps[name_lower]

    # Partial match
    for key, path in apps.items():
        if name_lower in key or key in name_lower:
            return key, path

    # Fuzzy match
    result = fuzzy.extractOne(name_lower, list(apps.keys()))
    if result is None:
        return None
    matched, score = result
    if score < 55:
        return None
    return matched, apps[matched]
