"""Factory for Tier-3 guided / read-only labs."""

from __future__ import annotations

from typing import Any

from labs.lab_models import (
    LabDefinition,
    LabInputField,
    LabPreset,
    LabRunResult,
    LabVisual,
)
from labs.adapters._helpers import PROTOCOL_WARNING, ok_result


def make_guided_definition(
    module_id: str,
    title: str,
    description: str,
    mission: str,
    presets: list[tuple[str, str, bool]],
    *,
    read_only: bool = False,
) -> LabDefinition:
    return LabDefinition(
        moduleId=module_id,
        title=title,
        description=description,
        mission=mission,
        kind="guided",
        tier=3,
        safety="read-only" if read_only else "demo",
        primaryAction="Run demo",
        securityNote=PROTOCOL_WARNING if not read_only else None,
        presets=[
            LabPreset(id=p[0], label=p[1], isDefault=p[2])
            for p in presets
        ],
        inputs=[],
    )


def run_guided_scenario(
    module_id: str,
    scenario: dict[str, Any],
    input_data: dict[str, Any],
) -> LabRunResult:
    cards = scenario.get("cards", [])
    log = scenario.get("log", [])
    visual_type = scenario.get("visualType", "guided-cards")
    return ok_result(
        module_id,
        scenario.get("summary", "Demo scenario completed."),
        input_data=input_data,
        result={"log": log, "cards": cards},
        visual=LabVisual(type=visual_type, data={"cards": cards, "log": log}),
        explanation=scenario.get("explanation", []),
        warnings=[PROTOCOL_WARNING],
    )
