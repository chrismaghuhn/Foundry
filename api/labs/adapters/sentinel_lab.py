"""Health check scenario lab."""

from __future__ import annotations

from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"probe": {}}


def get_definition():
    return preset_definition(
        "sentinel",
        "Watchdog Lab",
        "Simulated health checks with pass/fail streak.",
        "Run probes and see when a circuit opens.",
        [("probe", "Three probes", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    inp = merge_preset_input(payload, PRESETS)
    log = ["probe#1 ok", "probe#2 ok", "probe#3 fail → degrade"]
    return ok_result(
        "sentinel",
        "Circuit degraded after failed probe.",
        input_data=inp,
        visual=LabVisual(type="scenario-log", data={"log": log}),
        explanation=["Sentinel-style monitoring without real sockets."],
    )
