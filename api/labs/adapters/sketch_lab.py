"""Bloom filter / sketch lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "bloom": {"items": "apple,banana,cherry", "query": "banana"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="sketch",
        title="Bloom Filter Lab",
        description="Add strings to a Bloom filter and probe membership (approximate).",
        mission="Insert a few items — see why false positives can happen, never false negatives.",
        kind="visual",
        tier=1,
        safety="safe",
        primaryAction="Probe",
        presets=[LabPreset(id="bloom", label="Fruit basket", isDefault=True)],
        inputs=[
            LabInputField(
                name="items",
                type="text",
                label="Items (comma-separated)",
                default="apple,banana,cherry",
            ),
            LabInputField(name="query", type="text", label="Query", default="banana"),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        items_raw = clamp_text(str(inp.get("items", "")))
        query = clamp_text(str(inp.get("query", "")))
        items = [x.strip() for x in items_raw.split(",") if x.strip()][:50]
        ensure_foundry_path()
        from sketch.sketch import BloomFilter, bloom_fpr

        bf = BloomFilter(expected_items=max(len(items), 1), false_positive_rate=0.05)
        for it in items:
            bf.add(it)
        maybe = bf.contains(query)
        return ok_result(
            "sketch",
            f"'{query}' → {'maybe present' if maybe else 'definitely not present'}.",
            input_data=inp,
            result={
                "maybe": maybe,
                "count": len(items),
                "bitsSet": bf.count,
            },
            visual=LabVisual(
                type="sketch-stats",
                data={
                    "items": items,
                    "query": query,
                    "maybe": maybe,
                    "approxFpr": bloom_fpr(bf.num_bits, bf.num_hashes, max(len(items), 1)),
                },
            ),
            explanation=[
                "Bloom filters trade exactness for tiny memory.",
                "A 'maybe' can be a false positive; 'no' is always correct.",
            ],
        )
    except Exception as exc:
        return error_result("sketch", str(exc))
