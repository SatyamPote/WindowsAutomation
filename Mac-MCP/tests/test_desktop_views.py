"""Tests for mac_mcp.desktop.views data models."""
import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# tree.views imports tabulate — ensure it's available
from mac_mcp.tree.views import BoundingBox, TreeState
from mac_mcp.desktop.views import Browser, Status, Window, Size, DesktopState


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

def test_browser_has_process_chrome():
    assert Browser.has_process("Google Chrome") is True


def test_browser_has_process_case_insensitive():
    assert Browser.has_process("google chrome") is True


def test_browser_has_process_no_match():
    assert Browser.has_process("Notepad") is False


def test_browser_has_process_safari():
    assert Browser.has_process("Safari") is True


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

def test_status_values():
    assert Status.MAXIMIZED.value == "Maximized"
    assert Status.MINIMIZED.value == "Minimized"
    assert Status.NORMAL.value == "Normal"
    assert Status.HIDDEN.value == "Hidden"


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------

def _make_window(name="TestApp", status=Status.NORMAL):
    bb = BoundingBox(x=0, y=0, width=800, height=600)
    return Window(
        name=name,
        is_browser=False,
        depth=0,
        status=status,
        bounding_box=bb,
        handle=1234,
        process_id=1234,
    )


def test_window_to_row():
    w = _make_window()
    row = w.to_row()
    assert row[0] == "TestApp"
    assert row[2] == "Normal"
    assert row[3] == 800
    assert row[4] == 600
    assert row[5] == 1234


def test_window_is_browser_flag():
    bb = BoundingBox(x=0, y=0, width=1280, height=800)
    w = Window(
        name="Google Chrome",
        is_browser=True,
        depth=0,
        status=Status.MAXIMIZED,
        bounding_box=bb,
        handle=5678,
        process_id=5678,
    )
    assert w.is_browser is True


# ---------------------------------------------------------------------------
# Size
# ---------------------------------------------------------------------------

def test_size_to_string():
    s = Size(width=1920, height=1080)
    assert s.to_string() == "(1920,1080)"


# ---------------------------------------------------------------------------
# DesktopState
# ---------------------------------------------------------------------------

def test_desktop_state_active_desktop_to_string():
    state = DesktopState(
        active_desktop={"name": "Desktop 1"},
        all_desktops=[{"name": "Desktop 1"}],
        active_window=None,
        windows=[],
    )
    result = state.active_desktop_to_string()
    assert "Desktop 1" in result


def test_desktop_state_active_window_none():
    state = DesktopState(
        active_desktop={},
        all_desktops=[],
        active_window=None,
        windows=[],
    )
    assert "No active window" in state.active_window_to_string()


def test_desktop_state_windows_empty():
    state = DesktopState(
        active_desktop={},
        all_desktops=[],
        active_window=None,
        windows=[],
    )
    assert "No windows" in state.windows_to_string()


def test_desktop_state_windows_to_string_with_windows():
    w = _make_window("Finder")
    state = DesktopState(
        active_desktop={"name": "Desktop 1"},
        all_desktops=[{"name": "Desktop 1"}],
        active_window=w,
        windows=[w],
    )
    result = state.windows_to_string()
    assert "Finder" in result


def test_desktop_state_desktops_to_string():
    state = DesktopState(
        active_desktop={"name": "Desktop 1"},
        all_desktops=[{"name": "Desktop 1"}, {"name": "Desktop 2"}],
        active_window=None,
        windows=[],
    )
    result = state.desktops_to_string()
    assert "Desktop 2" in result
