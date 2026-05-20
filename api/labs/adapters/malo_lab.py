"""Data/log store scenario lab."""

from __future__ import annotations

from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"append": {}}


def get_definition():
    return preset_definition(
        "malo",
        "Log Store Lab",
        "Append-only log with read snapshot.",
        "Append events and read them back in order.",
        [("append", "Append events", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    inp = merge_preset_input(payload, PRESETS)
    events = ["user.login", "item.create", "user.logout"]
    return ok_result(
        "malo",
        f"Log holds {len(events)} events.",
        input_data=inp,
        visual=LabVisual(type="scenario-log", data={"log": events}),
        explanation=["Malo-style tamper-evident logs — educational snapshot."],
    )
