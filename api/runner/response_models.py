"""API response models for module runners."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RunAction = Literal["test", "example"]
RunStatus = Literal["passed", "failed", "timeout", "unavailable"]


class RunResult(BaseModel):
    module_id: str = Field(alias="moduleId")
    action: RunAction
    status: RunStatus
    command: list[str]
    cwd: str
    exit_code: int | None = Field(alias="exitCode")
    duration_ms: int = Field(alias="durationMs")
    timeout_ms: int = Field(alias="timeoutMs")
    stdout: str
    stderr: str
    truncated: bool

    model_config = {"populate_by_name": True}


class ModuleSummary(BaseModel):
    module_id: str = Field(alias="moduleId")
    cwd: str
    test_available: bool = Field(alias="testAvailable")
    example_available: bool = Field(alias="exampleAvailable")

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    ok: bool = True
    root: str


class ModulesListResponse(BaseModel):
    modules: list[ModuleSummary]
