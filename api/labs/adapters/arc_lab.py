"""ARC cache scenario lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"trace": {"keys": ["a", "b", "a", "c"]}}


def get_definition():
    return preset_definition(
        "arc",
        "ARC Cache Lab",
        "Simulate adaptive replacement cache hits and misses.",
        "Replay a key trace — see T1/T2 promotions.",
        [("trace", "Key trace", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    inp = merge_preset_input(payload, PRESETS)
    keys = inp.get("keys") or ["a", "b", "a", "c"]
    ensure_foundry_path()
    from arc.arc import ArcCacheSync

    cache = ArcCacheSync(capacity=2)
    log = []
    for k in keys:
        hit = cache.get(k) is not None
        if not hit:
            cache.put(k, k)
        log.append(f"{k}: {'hit' if hit else 'miss'}")
    return ok_result(
        "arc",
        f"Processed {len(keys)} lookups.",
        input_data=inp,
        visual=LabVisual(type="scenario-log", data={"log": log}),
        explanation=["ARC adapts between LRU and LFU zones — deterministic demo."],
    )
