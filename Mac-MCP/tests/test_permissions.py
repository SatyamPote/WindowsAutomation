"""Tests for mac_mcp.permissions — mocks system calls."""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_check_and_warn_with_full_permissions():
    as_mock = MagicMock()
    as_mock.AXIsProcessTrusted.return_value = True

    quartz_mock = MagicMock()
    quartz_mock.CGWindowListCreateImage.return_value = MagicMock()
    quartz_mock.CGRectMake.return_value = MagicMock()

    with patch.dict("sys.modules", {"ApplicationServices": as_mock, "Quartz": quartz_mock}):
        import importlib
        import mac_mcp.permissions as perm_mod
        importlib.reload(perm_mod)
        perm_mod.check_and_warn()


def test_check_and_warn_missing_accessibility():
    as_mock = MagicMock()
    as_mock.AXIsProcessTrusted.return_value = False

    quartz_mock = MagicMock()
    quartz_mock.CGWindowListCreateImage.return_value = MagicMock()
    quartz_mock.CGRectMake.return_value = MagicMock()

    with patch.dict("sys.modules", {"ApplicationServices": as_mock, "Quartz": quartz_mock}):
        import importlib
        import mac_mcp.permissions as perm_mod
        importlib.reload(perm_mod)
        perm_mod.check_and_warn()


def test_check_and_warn_missing_screen_recording():
    as_mock = MagicMock()
    as_mock.AXIsProcessTrusted.return_value = True

    quartz_mock = MagicMock()
    quartz_mock.CGWindowListCreateImage.return_value = None
    quartz_mock.CGRectMake.return_value = MagicMock()

    with patch.dict("sys.modules", {"ApplicationServices": as_mock, "Quartz": quartz_mock}):
        import importlib
        import mac_mcp.permissions as perm_mod
        importlib.reload(perm_mod)
        perm_mod.check_and_warn()


def test_check_and_warn_import_errors():
    with patch.dict("sys.modules", {"ApplicationServices": None, "Quartz": None}):
        import importlib
        import mac_mcp.permissions as perm_mod
        importlib.reload(perm_mod)
        perm_mod.check_and_warn()
