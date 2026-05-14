"""Tests for mac_mcp.filesystem.views data models."""
import sys
import os
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mac_mcp.filesystem.views import File, Directory, format_size, MAX_READ_SIZE, MAX_RESULTS


# ---------------------------------------------------------------------------
# format_size
# ---------------------------------------------------------------------------

def test_format_size_bytes():
    assert format_size(512) == "512 B"


def test_format_size_kilobytes():
    assert format_size(2048) == "2.0 KB"


def test_format_size_megabytes():
    assert "MB" in format_size(5 * 1024 * 1024)


def test_format_size_gigabytes():
    assert "GB" in format_size(2 * 1024 ** 3)


def test_format_size_zero():
    assert format_size(0) == "0 B"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_max_read_size():
    assert MAX_READ_SIZE == 10 * 1024 * 1024


def test_max_results():
    assert MAX_RESULTS == 500


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------

def _make_file(**kwargs):
    defaults = dict(
        path="/tmp/test.txt",
        type="file",
        size=1024,
        created=datetime(2024, 1, 1, 0, 0, 0),
        modified=datetime(2024, 6, 1, 12, 0, 0),
        accessed=datetime(2024, 6, 2, 9, 0, 0),
        read_only=False,
        extension=".txt",
    )
    defaults.update(kwargs)
    return File(**defaults)


def test_file_to_string_contains_path():
    f = _make_file()
    assert "/tmp/test.txt" in f.to_string()


def test_file_to_string_contains_size():
    f = _make_file(size=2048)
    assert "2.0 KB" in f.to_string()


def test_file_to_string_contains_extension():
    f = _make_file(extension=".txt")
    assert ".txt" in f.to_string()


def test_file_to_string_contains_read_only():
    f = _make_file(read_only=True)
    assert "True" in f.to_string()


def test_file_to_string_with_contents():
    f = _make_file(type="directory", contents_files=10, contents_dirs=3)
    s = f.to_string()
    assert "10 files" in s
    assert "3 directories" in s


def test_file_to_string_with_link_target():
    f = _make_file(link_target="/original/path")
    assert "/original/path" in f.to_string()


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------

def test_directory_to_string_dir():
    d = Directory(name="Documents", is_dir=True, size=0)
    s = d.to_string()
    assert "DIR" in s
    assert "Documents" in s


def test_directory_to_string_file():
    d = Directory(name="notes.txt", is_dir=False, size=512)
    s = d.to_string()
    assert "FILE" in s
    assert "notes.txt" in s
    assert "512 B" in s


def test_directory_to_string_relative_path():
    d = Directory(name="notes.txt", is_dir=False, size=1024)
    s = d.to_string(relative_path="subdir/notes.txt")
    assert "subdir/notes.txt" in s
