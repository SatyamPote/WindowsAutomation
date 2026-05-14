"""Tests for mac_mcp.filesystem.service — uses real /tmp, no macOS permissions needed."""
from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import mac_mcp.filesystem.service as svc


@pytest.fixture
def tmp(tmp_path):
    """A temp dir with some files for testing."""
    (tmp_path / "file_a.txt").write_text("hello world")
    (tmp_path / "file_b.py").write_text("print('hi')")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.md").write_text("# heading")
    return tmp_path


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------

def test_list_directory_returns_entries(tmp):
    result = svc.list_directory(str(tmp))
    assert "file_a.txt" in result
    assert "subdir" in result


def test_list_directory_empty(tmp_path):
    result = svc.list_directory(str(tmp_path))
    assert "empty" in result.lower()


def test_list_directory_nonexistent():
    result = svc.list_directory("/nonexistent/path/xyz_abc")
    assert "Error" in result


def test_list_directory_pattern(tmp):
    result = svc.list_directory(str(tmp), pattern="*.txt")
    assert "file_a.txt" in result
    assert "file_b.py" not in result


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------

def test_get_file_info_file(tmp):
    result = svc.get_file_info(str(tmp / "file_a.txt"))
    assert "File" in result
    assert ".txt" in result


def test_get_file_info_directory(tmp):
    result = svc.get_file_info(str(tmp / "subdir"))
    assert "Directory" in result


def test_get_file_info_nonexistent():
    result = svc.get_file_info("/no/such/file.xyz")
    assert "Error" in result


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

def test_read_file_text(tmp):
    result = svc.read_file(str(tmp / "file_a.txt"))
    assert "hello world" in result


def test_read_file_nonexistent():
    result = svc.read_file("/no/such/file.txt")
    assert "Error" in result


def test_read_file_with_offset(tmp):
    p = tmp / "multiline.txt"
    p.write_text("line1\nline2\nline3\n")
    result = svc.read_file(str(p), offset=2, limit=1)
    assert "line2" in result


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def test_write_file_creates_file(tmp_path):
    p = str(tmp_path / "new.txt")
    result = svc.write_file(p, "test content")
    assert "Written" in result
    assert Path(p).read_text() == "test content"


def test_write_file_append(tmp_path):
    p = str(tmp_path / "append.txt")
    svc.write_file(p, "line1\n")
    svc.write_file(p, "line2\n", append=True)
    content = Path(p).read_text()
    assert "line1" in content
    assert "line2" in content


def test_write_file_creates_parents(tmp_path):
    p = str(tmp_path / "a" / "b" / "c.txt")
    result = svc.write_file(p, "nested")
    assert "Written" in result
    assert Path(p).exists()


# ---------------------------------------------------------------------------
# copy_path / move_path
# ---------------------------------------------------------------------------

def test_copy_file(tmp):
    src = str(tmp / "file_a.txt")
    dst = str(tmp / "copy.txt")
    result = svc.copy_path(src, dst)
    assert "Copied" in result
    assert Path(dst).exists()
    assert Path(src).exists()


def test_copy_file_no_overwrite(tmp):
    src = str(tmp / "file_a.txt")
    dst = str(tmp / "file_b.py")
    result = svc.copy_path(src, dst)
    assert "Error" in result


def test_move_file(tmp):
    src = str(tmp / "file_b.py")
    dst = str(tmp / "moved.py")
    result = svc.move_path(src, dst)
    assert "Moved" in result
    assert Path(dst).exists()
    assert not Path(src).exists()


# ---------------------------------------------------------------------------
# delete_path
# ---------------------------------------------------------------------------

def test_delete_file(tmp):
    p = str(tmp / "file_a.txt")
    result = svc.delete_path(p)
    assert "Deleted" in result
    assert not Path(p).exists()


def test_delete_nonexistent():
    result = svc.delete_path("/no/such/file.txt")
    assert "Error" in result


def test_delete_nonempty_dir_without_recursive(tmp):
    result = svc.delete_path(str(tmp / "subdir"))
    assert "Error" in result or "not empty" in result


def test_delete_dir_recursive(tmp):
    result = svc.delete_path(str(tmp / "subdir"), recursive=True)
    assert "Deleted" in result
    assert not (tmp / "subdir").exists()


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------

def test_search_files(tmp):
    result = svc.search_files(str(tmp), "*.txt")
    assert "file_a.txt" in result


def test_search_files_no_match(tmp):
    result = svc.search_files(str(tmp), "*.nonexistent")
    assert "No matches" in result


# ---------------------------------------------------------------------------
# get_latest_file
# ---------------------------------------------------------------------------

def test_get_latest_file(tmp):
    result = svc.get_latest_file(str(tmp))
    assert "Latest File" in result


def test_get_latest_file_empty_dir(tmp_path):
    result = svc.get_latest_file(str(tmp_path))
    assert "No files" in result


# ---------------------------------------------------------------------------
# bulk_delete_by_extension
# ---------------------------------------------------------------------------

def test_bulk_delete_by_extension(tmp):
    result = svc.bulk_delete_by_extension(str(tmp), ".txt")
    assert "Deleted" in result
    assert not (tmp / "file_a.txt").exists()


def test_bulk_delete_by_extension_no_match(tmp):
    result = svc.bulk_delete_by_extension(str(tmp), ".xyz")
    assert "No files" in result


# ---------------------------------------------------------------------------
# organize_folder
# ---------------------------------------------------------------------------

def test_organize_folder(tmp):
    (tmp / "photo.jpg").write_bytes(b"\xff\xd8\xff")
    result = svc.organize_folder(str(tmp))
    assert "Organized" in result or "moved" in result.lower()
    assert (tmp / "Images" / "photo.jpg").exists()
