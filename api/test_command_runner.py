"""Command runner behavior with mocked subprocess."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from runner.command_runner import (
    EXAMPLE_TIMEOUT_S,
    TEST_TIMEOUT_S,
    run_command,
    timeout_for_action,
)


def test_timeout_for_action():
    assert timeout_for_action("test") == TEST_TIMEOUT_S
    assert timeout_for_action("example") == EXAMPLE_TIMEOUT_S


def test_unavailable_when_no_command():
    result = run_command("bastion", "test", "bastion", None)
    assert result.status == "unavailable"
    assert result.command == []
    assert result.exit_code is None
    assert result.timeout_ms == TEST_TIMEOUT_S * 1000


@patch("runner.command_runner.subprocess.run")
def test_passed_on_exit_zero(mock_run: MagicMock):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["python", "-m", "pytest", "-q"],
        returncode=0,
        stdout="ok",
        stderr="",
    )
    result = run_command(
        "graph",
        "test",
        "graph",
        ["python", "-m", "pytest", "-q"],
    )
    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.timeout_ms == 30000
    mock_run.assert_called_once()
    call_kw = mock_run.call_args.kwargs
    assert call_kw["shell"] is False
    assert call_kw["timeout"] == TEST_TIMEOUT_S


@patch("runner.command_runner.subprocess.run")
def test_example_uses_shorter_timeout(mock_run: MagicMock):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["python", "examples.py"],
        returncode=0,
        stdout="",
        stderr="",
    )
    run_command("prism", "example", "prism", ["python", "examples.py"])
    assert mock_run.call_args.kwargs["timeout"] == EXAMPLE_TIMEOUT_S


@patch("runner.command_runner.subprocess.run")
def test_timeout_status(mock_run: MagicMock):
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd=["python", "examples.py"],
        timeout=EXAMPLE_TIMEOUT_S,
        output="partial",
        stderr="",
    )
    result = run_command(
        "prism",
        "example",
        "prism",
        ["python", "examples.py"],
    )
    assert result.status == "timeout"
    assert result.timeout_ms == EXAMPLE_TIMEOUT_S * 1000


@patch("runner.command_runner.subprocess.run")
def test_truncates_large_stdout(mock_run: MagicMock):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="x" * 50_000,
        stderr="",
    )
    result = run_command("graph", "test", "graph", ["python", "-m", "pytest", "-q"])
    assert result.truncated is True
    assert len(result.stdout) <= 40_000 + 20
