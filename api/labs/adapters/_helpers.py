"""Shared helpers for lab adapters."""

from __future__ import annotations

import json
from typing import Any

from labs.lab_models import LabRunResult, LabVisual
from labs.limits import MAX_JSON_CHARS, MAX_TEXT_CHARS

CRYPTO_WARNING = (
    "Educational demo only — not audited for production cryptography or key management."
)
PROTOCOL_WARNING = (
    "Learning demo — reference protocol sketch, not production-ready security."
)


def clamp_text(value: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(value) > limit:
        raise ValueError(f"Text exceeds {limit} characters")
    return value


def parse_json_field(value: Any, limit: int = MAX_JSON_CHARS) -> Any:
    if isinstance(value, str):
        if len(value) > limit:
            raise ValueError(f"JSON exceeds {limit} characters")
        return json.loads(value)
    if isinstance(value, (dict, list)):
        dumped = json.dumps(value)
        if len(dumped) > limit:
            raise ValueError(f"JSON exceeds {limit} characters")
        return value
    raise ValueError("Expected JSON object or string")


def ok_result(
    module_id: str,
    summary: str,
    *,
    input_data: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    visual: LabVisual | None = None,
    explanation: list[str] | None = None,
    warnings: list[str] | None = None,
) -> LabRunResult:
    w = list(warnings or [])
    return LabRunResult(
        moduleId=module_id,
        status="ok",
        summary=summary,
        input=input_data or {},
        result=result or {},
        visual=visual,
        explanation=explanation or [],
        warnings=w,
    )


def error_result(
    module_id: str,
    message: str,
    *,
    input_data: dict[str, Any] | None = None,
) -> LabRunResult:
    return LabRunResult(
        moduleId=module_id,
        status="error",
        summary=message,
        input=input_data or {},
        explanation=["Check your inputs and try a preset."],
    )


def merge_preset_input(payload: dict, presets: dict[str, dict]) -> dict[str, Any]:
    preset_id = payload.get("presetId") or payload.get("preset_id")
    base: dict[str, Any] = {}
    if preset_id and preset_id in presets:
        base = dict(presets[preset_id])
    user = payload.get("input") or {}
    if isinstance(user, dict):
        base.update(user)
    return base
