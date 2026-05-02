"""Tests for mac_mcp.spaces.core stub."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mac_mcp.spaces.core import get_all_desktops, get_current_desktop, is_window_on_current_desktop


def test_is_window_on_current_desktop_always_true():
    assert is_window_on_current_desktop(0) is True
    assert is_window_on_current_desktop(12345) is True


def test_get_current_desktop():
    assert get_current_desktop() == 0


def test_get_all_desktops():
    desktops = get_all_desktops()
    assert isinstance(desktops, list)
    assert len(desktops) >= 1
