"""Resolve Claude Desktop data directories across installation types.

When Claude Desktop is installed as a Windows Package App (MSIX, e.g. via
Microsoft Store), Windows virtualizes ``%APPDATA%`` into a per-package
location::

    %LOCALAPPDATA%\\Packages\\<PackageFamilyName>\\LocalCache\\Roaming\\Claude

The standard (non-packaged) installation uses::

    %APPDATA%\\Claude

This module probes both locations and returns the first one that exists.
"""

from pathlib import Path
import glob
import logging
import os

logger = logging.getLogger(__name__)

# Known MSIX package-family prefix for Claude Desktop.  The suffix after the
# underscore is a publisher-id hash that is stable across versions.
_CLAUDE_PACKAGE_PREFIX = "Claude_"


def get_claude_data_dir() -> Path | None:
    """Return the Claude Desktop data directory, or ``None`` if not found.

    Resolution order:

    1. **MSIX path** - ``%LOCALAPPDATA%\\Packages\\Claude_*\\LocalCache\\Roaming\\Claude``
    2. **Standard path** - ``%APPDATA%\\Claude``

    Returns ``None`` when neither location exists (Claude may not be installed).
    """
    msix_dir = _find_msix_claude_dir()
    if msix_dir is not None:
        logger.info("Detected MSIX Claude Desktop data dir: %s", msix_dir)
        return msix_dir

    standard_dir = _find_standard_claude_dir()
    if standard_dir is not None:
        logger.info("Detected standard Claude Desktop data dir: %s", standard_dir)
        return standard_dir

    logger.debug("Claude Desktop data directory not found")
    return None


def get_claude_config_path() -> Path | None:
    """Return the path to ``claude_desktop_config.json``, or ``None``."""
    data_dir = get_claude_data_dir()
    if data_dir is None:
        return None
    config_path = data_dir / "claude_desktop_config.json"
    return config_path if config_path.is_file() else None


def is_msix_install() -> bool:
    """Return ``True`` if Claude Desktop appears to be an MSIX installation."""
    return _find_msix_claude_dir() is not None


def _find_msix_claude_dir() -> Path | None:
    """Probe ``%LOCALAPPDATA%\\Packages`` for a Claude MSIX package directory."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None

    packages_dir = Path(local_appdata) / "Packages"
    if not packages_dir.is_dir():
        return None

    # Match directories like Claude_pzs8sxrjxfjjc (the publisher-id suffix
    # varies, so we use a glob).
    pattern = str(packages_dir / f"{_CLAUDE_PACKAGE_PREFIX}*")
    for match in glob.glob(pattern):
        candidate = Path(match) / "LocalCache" / "Roaming" / "Claude"
        if candidate.is_dir():
            return candidate

    return None


def _find_standard_claude_dir() -> Path | None:
    """Probe ``%APPDATA%\\Claude`` for a standard (non-MSIX) install."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None

    candidate = Path(appdata) / "Claude"
    return candidate if candidate.is_dir() else None


def get_lotus_bin_dir() -> Path:
    """Find the Lotus 'bin' directory containing mpv, yt-dlp, ffmpeg."""
    import sys

    # All candidate locations, checked in order
    candidates = []

    # 1. Frozen exe (PyInstaller) — check next to the .exe first
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys.executable).parent / "bin")

    # 2. Relative to this source file (src/windows_mcp/ → up to Lotus/)
    # This is primary for development environments
    src_root = Path(__file__).resolve().parent.parent.parent  # Windows-MCP
    candidates.append(src_root / "bin")
    candidates.append(src_root.parent / "bin")  # Lotus project root

    # 3. Search upward from this file for any ancestor with bin/
    curr = Path(__file__).resolve().parent
    for _ in range(10):
        candidates.append(curr / "bin")
        if curr.parent == curr:
            break
        curr = curr.parent

    # 4. Standard install paths (Inno Setup default)
    candidates.append(Path(r"C:\Program Files (x86)\Lotus\bin"))
    candidates.append(Path(r"C:\Program Files\Lotus\bin"))

    # 5. ProgramData (fallback)
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    candidates.append(Path(program_data) / "Lotus" / "bin")

    # Return the first candidate that actually exists on disk AND has the tools
    # We keep track of the first directory that actually exists as a fallback
    fallback_dir = None

    for p in candidates:
        if p.is_dir():
            if fallback_dir is None:
                fallback_dir = p
            
            # Check for mpv.exe (root or subfolder) AND yt-dlp.exe
            has_mpv = (p / "mpv.exe").exists() or (p / "mpv" / "mpv.exe").exists()
            has_ytdlp = (p / "yt-dlp.exe").exists()
            
            if has_mpv and has_ytdlp:
                return p

    # If we found a directory that exists but doesn't have both, return it as a fallback
    if fallback_dir:
        return fallback_dir

    # Absolute fallback — return the standard install path
    return Path(r"C:\Program Files (x86)\Lotus\bin")


def get_lotus_storage_dir() -> Path:
    """Return the global storage directory in ProgramData."""
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    base = Path(program_data) / "Lotus" / "storage"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_lotus_data_dir() -> Path:
    """Return the global data directory in ProgramData."""
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    base = Path(program_data) / "Lotus" / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_lotus_log_dir() -> Path:
    """Return the global logs directory in ProgramData."""
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    base = Path(program_data) / "Lotus" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base
