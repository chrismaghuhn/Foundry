"""Schedule/timeline scenario lab."""

from __future__ import annotations

from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"daily": {}}


def get_definition():
    return preset_definition(
        "chrono",
        "Timeline Lab",
        "Simulated schedule with tasks and deadlines.",
        "Watch a day of jobs get ordered by time.",
        [("daily", "Daily schedule", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    inp = merge_preset_input(payload, PRESETS)
    log = ["09:00 ingest", "12:00 transform", "17:00 publish"]
    return ok_result(
        "chrono",
        "Three tasks scheduled — no real clock started.",
        input_data=inp,
        visual=LabVisual(type="scenario-log", data={"log": log}),
        explanation=["Chrono teaches scheduling concepts in-process only."],
    )
