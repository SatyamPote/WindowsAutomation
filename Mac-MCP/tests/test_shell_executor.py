"""Tests for mac_mcp.desktop.shell executors."""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch
import subprocess

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mac_mcp.desktop.shell import ShellExecutor, AppleScriptExecutor


# ---------------------------------------------------------------------------
# ShellExecutor
# ---------------------------------------------------------------------------

def test_shell_execute_success():
    output, code = ShellExecutor.execute("echo hello")
    assert "hello" in output
    assert code == 0


def test_shell_execute_stderr_captured():
    output, code = ShellExecutor.execute("ls /nonexistent_dir_xyz 2>&1")
    assert code != 0


def test_shell_execute_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep", timeout=1)):
        output, code = ShellExecutor.execute("sleep 100", timeout=1)
        assert "timed out" in output.lower()
        assert code == 1


def test_shell_execute_exception():
    with patch("subprocess.run", side_effect=OSError("no such file")):
        output, code = ShellExecutor.execute("cmd")
        assert "Error" in output
        assert code == 1


def test_shell_execute_multiline():
    output, code = ShellExecutor.execute("echo line1 && echo line2")
    assert "line1" in output
    assert "line2" in output
    assert code == 0


def test_shell_execute_exit_code():
    _, code = ShellExecutor.execute("exit 42")
    assert code == 42


# ---------------------------------------------------------------------------
# AppleScriptExecutor
# ---------------------------------------------------------------------------

def test_applescript_execute_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="osascript", timeout=1)):
        output, code = AppleScriptExecutor.execute("delay 100", timeout=1)
        assert "timed out" in output.lower()
        assert code == 1


def test_applescript_execute_exception():
    with patch("subprocess.run", side_effect=OSError("osascript not found")):
        output, code = AppleScriptExecutor.execute('return "hi"')
        assert "Error" in output
        assert code == 1


def test_applescript_execute_mocked_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "hello\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        output, code = AppleScriptExecutor.execute('return "hello"')
        assert output == "hello"
        assert code == 0


def test_applescript_notify_does_not_raise():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        AppleScriptExecutor.notify("Test", "message")
        mock_run.assert_called_once()
