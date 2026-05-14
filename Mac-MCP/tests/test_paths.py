"""Tests for mac_mcp.paths — just verifies the path constants make sense."""
from __future__ import annotations

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mac_mcp.paths import APP_NAME, DATA_DIR, CACHE_DIR


def test_app_name():
    assert APP_NAME == "mac-mcp"


def test_data_dir_is_path():
    assert isinstance(DATA_DIR, Path)


def test_cache_dir_is_path():
    assert isinstance(CACHE_DIR, Path)


def test_data_dir_under_home_or_library():
    path_str = str(DATA_DIR).lower()
    assert "mac-mcp" in path_str


def test_cache_dir_under_home_or_library():
    path_str = str(CACHE_DIR).lower()
    assert "mac-mcp" in path_str
