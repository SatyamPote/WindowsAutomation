"""Tests for mac_mcp.desktop.utils — pure string helpers, no permissions needed."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mac_mcp.desktop.utils import remove_private_use_chars


def test_remove_private_use_chars_clean_string():
    assert remove_private_use_chars("hello world") == "hello world"


def test_remove_private_use_chars_removes_private_use():
    # U+E000 is in the BMP private use area
    text = "helloworld"
    result = remove_private_use_chars(text)
    assert "" not in result
    assert "helloworld" == result


def test_remove_private_use_chars_removes_supplementary_private_use():
    # U+F0000 is in supplementary private use area A
    text = "abc\U000f0000def"
    result = remove_private_use_chars(text)
    assert "abcdef" == result


def test_remove_private_use_chars_empty_string():
    assert remove_private_use_chars("") == ""


def test_remove_private_use_chars_only_private_use():
    text = ""
    result = remove_private_use_chars(text)
    assert result == ""


def test_remove_private_use_chars_preserves_unicode():
    text = "日本語テスト"
    assert remove_private_use_chars(text) == text


def test_remove_private_use_chars_mixed():
    text = "Title\nContent"
    result = remove_private_use_chars(text)
    assert result == "Title\nContent"
