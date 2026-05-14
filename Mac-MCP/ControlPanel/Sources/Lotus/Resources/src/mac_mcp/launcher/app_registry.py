"""Discover installed .app bundles via Spotlight."""

import subprocess
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_SEARCH_DIRS = ["/Applications", "/System/Applications", "~/Applications"]


@lru_cache(maxsize=1)
def get_all_apps() -> dict[str, Path]:
    """Return {app_name_lower: .app bundle path} for all installed apps."""
    apps: dict[str, Path] = {}

    # Primary: Spotlight mdfind (fast, comprehensive)
    try:
        result = subprocess.run(
            ["mdfind", "kMDItemKind == 'Application'"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            p = Path(line.strip())
            if p.suffix == ".app" and p.exists():
                apps[p.stem.lower()] = p
    except Exception as e:
        logger.warning("mdfind failed: %s — falling back to directory scan", e)

    # Fallback: scan known directories
    if not apps:
        for d in _SEARCH_DIRS:
            dir_path = Path(d).expanduser()
            if dir_path.exists():
                for p in dir_path.glob("*.app"):
                    apps[p.stem.lower()] = p

    logger.debug("App registry: %d apps found", len(apps))
    return apps


def invalidate_cache() -> None:
    get_all_apps.cache_clear()
