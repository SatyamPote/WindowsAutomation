"""
Lotus auto-update checker.

Compares the local version (from version.json or VERSION constant)
against the latest GitHub release and returns a friendly status string.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import requests

logger = logging.getLogger(__name__)

LOCAL_VERSION_FALLBACK = "3.0.0"
GITHUB_API_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
DEFAULT_REPO = "SatyamPote/Lotus"


def _project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def load_local_version() -> dict[str, Any]:
    """Load version.json from the install dir; fall back to defaults."""
    candidates = [
        os.path.join(_project_root(), "version.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "version.json"),
    ]
    for path in candidates:
        path = os.path.normpath(path)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read %s: %s", path, e)
    return {
        "version": LOCAL_VERSION_FALLBACK,
        "github_repo": DEFAULT_REPO,
        "release_url": f"https://github.com/{DEFAULT_REPO}/releases/latest",
    }


def _parse_semver(v: str) -> tuple[int, ...]:
    """Best-effort semver parse: '3.0.0-PROD' -> (3, 0, 0)."""
    head = v.lstrip("vV").split("-")[0].split("+")[0]
    parts: list[int] = []
    for piece in head.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def check_for_updates(timeout: float = 6.0) -> dict[str, Any]:
    """Hit GitHub releases and compare to local version.

    Returns:
        {
          "current": "3.0.0",
          "latest":  "3.0.1" | None,
          "is_outdated": bool,
          "url": "<release page>",
          "message": "<markdown summary for Telegram>"
        }
    """
    local = load_local_version()
    current = local.get("version", LOCAL_VERSION_FALLBACK)
    repo = local.get("github_repo", DEFAULT_REPO)
    release_url = local.get("release_url", f"https://github.com/{repo}/releases/latest")

    out = {
        "current": current,
        "latest": None,
        "is_outdated": False,
        "url": release_url,
        "message": "",
    }

    try:
        r = requests.get(
            GITHUB_API_LATEST.format(repo=repo),
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 404:
            out["message"] = (
                f"🌸 *Lotus v{current}*\n"
                "_No published GitHub releases yet — you're on the latest dev build._"
            )
            return out
        r.raise_for_status()
        data = r.json()
        latest = (data.get("tag_name") or data.get("name") or "").strip()
        if not latest:
            raise ValueError("empty tag_name from GitHub")
        out["latest"] = latest
        out["url"] = data.get("html_url") or release_url
        out["is_outdated"] = _parse_semver(latest) > _parse_semver(current)

        if out["is_outdated"]:
            out["message"] = (
                f"🚀 *Update available!*\n"
                f"You have: `v{current}`\n"
                f"Latest:  `{latest}`\n\n"
                f"[Download here]({out['url']})"
            )
        else:
            out["message"] = (
                f"✅ *Lotus v{current}* is up to date.\n"
                f"Latest release: `{latest}`"
            )
        return out

    except requests.RequestException as e:
        logger.warning("Update check network error: %s", e)
        out["message"] = (
            f"🌸 *Lotus v{current}*\n"
            "_Could not reach GitHub. Check your internet connection._"
        )
        return out
    except Exception as e:
        logger.exception("Update check failed: %s", e)
        out["message"] = (
            f"🌸 *Lotus v{current}*\n_Update check failed: {e}_"
        )
        return out
