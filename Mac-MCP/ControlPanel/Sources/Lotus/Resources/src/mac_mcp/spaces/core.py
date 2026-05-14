"""macOS Spaces (Virtual Desktop) awareness.

Phase 5 implementation: Option A — no filtering. All windows from all Spaces
are visible. Spaces filtering may be added in a future release using the
private CGS SPI (Option B), but that API is undocumented and may break on
macOS updates without notice.
"""


def is_window_on_current_desktop(window_id: int) -> bool:
    return True


def get_current_desktop() -> int:
    return 0


def get_all_desktops() -> list[int]:
    return [0]
