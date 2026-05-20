"""Helpers for Tier-2 preset labs."""

from __future__ import annotations

from labs.lab_models import LabDefinition, LabInputField, LabPreset


def preset_definition(
    module_id: str,
    title: str,
    description: str,
    mission: str,
    presets: list[tuple[str, str, bool]],
    *,
    primary: str = "Run",
    inputs: list[LabInputField] | None = None,
) -> LabDefinition:
    return LabDefinition(
        moduleId=module_id,
        title=title,
        description=description,
        mission=mission,
        kind="scenario",
        tier=2,
        safety="safe",
        primaryAction=primary,
        presets=[LabPreset(id=p[0], label=p[1], isDefault=p[2]) for p in presets],
        inputs=inputs or [],
    )
