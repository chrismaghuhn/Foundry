"""Coordination scenario lab."""

from __future__ import annotations

from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"lock": {}}


def get_definition():
    return preset_definition(
        "styx",
        "Coordination Lab",
        "Simulated lock acquire/release between workers.",
        "See who holds the lock — no real threads spawned.",
        [("lock", "Two workers", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    inp = merge_preset_input(payload, PRESETS)
    log = ["worker_a acquire", "worker_b wait", "worker_a release", "worker_b acquire"]
    return ok_result(
        "styx",
        "Lock handed off without deadlock.",
        input_data=inp,
        visual=LabVisual(type="scenario-log", data={"log": log}),
        explanation=["Coordination patterns in a short scripted trace."],
    )
