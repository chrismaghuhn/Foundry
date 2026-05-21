"""Pydantic models for interactive lab API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .limits import LAB_TIMEOUT_S

LabKind = Literal["visual", "text", "scenario", "guided"]
LabTier = Literal[1, 2, 3]
LabSafety = Literal["safe", "demo", "read-only"]
LabStatus = Literal["ok", "error"]
InputType = Literal["select", "text", "textarea", "json", "number", "checkbox"]


class LabInputField(BaseModel):
    name: str
    type: InputType
    label: str
    default: Any = None
    options: list[dict[str, str]] | None = None
    min: float | None = None
    max: float | None = None


class LabPreset(BaseModel):
    id: str
    label: str
    description: str | None = None
    isDefault: bool = False


class LabDefinition(BaseModel):
    moduleId: str
    title: str
    description: str
    mission: str
    mode: str = "interactive"
    kind: LabKind
    tier: LabTier
    safety: LabSafety
    primaryAction: str = "Run"
    inputs: list[LabInputField] = Field(default_factory=list)
    presets: list[LabPreset] = Field(default_factory=list)
    securityNote: str | None = None


class LabSummary(BaseModel):
    moduleId: str
    title: str
    kind: LabKind
    tier: LabTier
    safety: LabSafety


class LabsListResponse(BaseModel):
    labs: list[LabSummary]


class LabRunRequest(BaseModel):
    presetId: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    action: str | None = None


class LabVisual(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class LabRunResult(BaseModel):
    moduleId: str
    status: LabStatus
    summary: str
    input: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    visual: LabVisual | None = None
    explanation: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timeoutMs: int = LAB_TIMEOUT_S * 1000
