"""Reactive stream scenario lab."""

from __future__ import annotations

from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"stream": {}}


def get_definition():
    return preset_definition(
        "flux",
        "Event Stream Lab",
        "Map/filter/reduce over a finite event list.",
        "Events propagate through operators in order.",
        [("stream", "Filter evens", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    inp = merge_preset_input(payload, PRESETS)
    events = list(range(1, 8))
    out = [e for e in events if e % 2 == 0]
    log = [f"emit {e}" for e in events] + [f"keep {e}" for e in out]
    return ok_result(
        "flux",
        f"Kept {len(out)} of {len(events)} events.",
        input_data=inp,
        visual=LabVisual(type="scenario-log", data={"log": log}),
        explanation=["Finite stream — no background tasks."],
    )
