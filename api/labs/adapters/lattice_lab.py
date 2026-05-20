"""CRDT merge lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import error_result, merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"counter": {"replicaA": 3, "replicaB": 5}}


def get_definition():
    return preset_definition(
        "lattice",
        "CRDT Merge Lab",
        "Merge two G-Counter replicas.",
        "Each replica increments locally — merge should sum counts.",
        [("counter", "G-Counter merge", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        a = int(inp.get("replicaA", 3))
        b = int(inp.get("replicaB", 5))
        ensure_foundry_path()
        from lattice.lattice import GCounter

        c1, c2 = GCounter("a"), GCounter("b")
        c1.increment(a)
        c2.increment(b)
        merged = c1.merge(c2)
        total = merged.value()
        return ok_result(
            "lattice",
            f"Merged counter value: {total}.",
            input_data=inp,
            visual=LabVisual(
                type="replicas",
                data={"replicaA": a, "replicaB": b, "merged": total},
            ),
            explanation=[
                "G-Counters merge by per-node max then sum — commutative and associative.",
            ],
        )
    except Exception as exc:
        return error_result("lattice", str(exc))
