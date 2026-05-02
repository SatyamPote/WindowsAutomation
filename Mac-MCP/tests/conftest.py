"""Shared pytest fixtures for mac-mcp tests."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AX / ApplicationServices mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ax():
    """Mock ApplicationServices AX calls so tests run without Accessibility permission."""
    ax_mock = MagicMock()
    ax_mock.kAXErrorSuccess = 0
    ax_mock.kAXErrorNoValue = -25212
    ax_mock.kAXErrorAPIDisabled = -25211
    ax_mock.AXIsProcessTrustedWithOptions.return_value = True
    ax_mock.AXUIElementCreateApplication.return_value = MagicMock()
    ax_mock.AXUIElementCreateSystemWide.return_value = MagicMock()
    ax_mock.AXUIElementCopyAttributeValue.return_value = (0, MagicMock())
    ax_mock.AXUIElementCopyMultipleAttributeValues.return_value = (0, [])
    ax_mock.AXUIElementPerformAction.return_value = 0
    ax_mock.AXUIElementSetAttributeValue.return_value = 0

    with patch.dict("sys.modules", {"ApplicationServices": ax_mock}):
        yield ax_mock


# ---------------------------------------------------------------------------
# NSWorkspace / AppKit mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_nsworkspace():
    """Mock NSWorkspace so tests run without a running macOS session."""
    mock_app = MagicMock()
    mock_app.localizedName.return_value = "TestApp"
    mock_app.processIdentifier.return_value = 1234
    mock_app.bundleIdentifier.return_value = "com.test.app"
    mock_app.isActive.return_value = True

    mock_ws = MagicMock()
    mock_ws.sharedWorkspace.return_value.frontmostApplication.return_value = mock_app
    mock_ws.sharedWorkspace.return_value.runningApplications.return_value = [mock_app]

    appkit_mock = MagicMock()
    appkit_mock.NSWorkspace = mock_ws
    appkit_mock.NSRunningApplication = MagicMock()

    with patch.dict("sys.modules", {"AppKit": appkit_mock}):
        yield mock_ws


# ---------------------------------------------------------------------------
# pynput mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pynput():
    """Mock pynput keyboard/mouse controllers."""
    mock_kb = MagicMock()
    mock_mouse = MagicMock()

    pynput_mock = MagicMock()
    pynput_mock.keyboard.Controller.return_value = mock_kb
    pynput_mock.mouse.Controller.return_value = mock_mouse
    pynput_mock.keyboard.Key = MagicMock()

    with patch.dict("sys.modules", {
        "pynput": pynput_mock,
        "pynput.keyboard": pynput_mock.keyboard,
        "pynput.mouse": pynput_mock.mouse,
    }):
        yield mock_kb, mock_mouse


# ---------------------------------------------------------------------------
# Quartz mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_quartz():
    """Mock Quartz framework calls."""
    quartz_mock = MagicMock()
    quartz_mock.CGWindowListCopyWindowInfo.return_value = []
    quartz_mock.CGWindowListCreateImage.return_value = MagicMock()
    quartz_mock.kCGWindowListOptionOnScreenOnly = 1
    quartz_mock.kCGNullWindowID = 0
    quartz_mock.kCGWindowImageDefault = 0

    with patch.dict("sys.modules", {"Quartz": quartz_mock, "Quartz.CoreGraphics": quartz_mock}):
        yield quartz_mock


# ---------------------------------------------------------------------------
# CI skip helper
# ---------------------------------------------------------------------------

requires_macos_perms = pytest.mark.skipif(
    __import__("os").getenv("MAC_MCP_CI") == "true",
    reason="Requires macOS Accessibility/Screen Recording permissions",
)
