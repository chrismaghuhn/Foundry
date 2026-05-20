"""Execute whitelisted module commands with timeouts and output caps."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Literal

from .paths import module_cwd
from .response_models import RunAction, RunResult, RunStatus

EXAMPLE_TIMEOUT_S = 8
TEST_TIMEOUT_S = 30
MAX_OUTPUT_CHARS = 40_000

RunActionType = Literal["test", "example"]


def timeout_for_action(action: RunActionType) -> int:
    if action == "test":
        return TEST_TIMEOUT_S
    return EXAMPLE_TIMEOUT_S


def _runner_env() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text, False
    return text[:MAX_OUTPUT_CHARS] + "\n… [truncated]", True


def run_command(
    module_id: str,
    action: RunActionType,
    cwd_rel: str,
    command: list[str] | None,
) -> RunResult:
    timeout_s = timeout_for_action(action)
    timeout_ms = timeout_s * 1000

    if not command:
        return RunResult(
            moduleId=module_id,
            action=action,
            status="unavailable",
            command=[],
            cwd=cwd_rel,
            exitCode=None,
            durationMs=0,
            timeoutMs=timeout_ms,
            stdout="",
            stderr="",
            truncated=False,
        )

    cwd = module_cwd(cwd_rel)
    start = time.perf_counter()

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=False,
            env=_runner_env(),
            encoding="utf-8",
            errors="replace",
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        stdout, trunc_out = _truncate(completed.stdout or "")
        stderr, trunc_err = _truncate(completed.stderr or "")
        status: RunStatus = "passed" if completed.returncode == 0 else "failed"
        return RunResult(
            moduleId=module_id,
            action=action,
            status=status,
            command=command,
            cwd=cwd_rel,
            exitCode=completed.returncode,
            durationMs=duration_ms,
            timeoutMs=timeout_ms,
            stdout=stdout,
            stderr=stderr,
            truncated=trunc_out or trunc_err,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        stdout, trunc_out = _truncate(exc.stdout or "" if exc.stdout else "")
        stderr, trunc_err = _truncate(exc.stderr or "" if exc.stderr else "")
        return RunResult(
            moduleId=module_id,
            action=action,
            status="timeout",
            command=command,
            cwd=cwd_rel,
            exitCode=None,
            durationMs=duration_ms,
            timeoutMs=timeout_ms,
            stdout=stdout,
            stderr=stderr or f"Command timed out after {timeout_s}s.",
            truncated=trunc_out or trunc_err,
        )
    except OSError as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return RunResult(
            moduleId=module_id,
            action=action,
            status="failed",
            command=command,
            cwd=cwd_rel,
            exitCode=None,
            durationMs=duration_ms,
            timeoutMs=timeout_ms,
            stdout="",
            stderr=str(exc),
            truncated=False,
        )
