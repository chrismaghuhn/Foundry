"""JSON query lab for prism."""

from __future__ import annotations

import json

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

SAMPLE = {
    "users": [
        {"name": "Alice", "age": 30, "tags": ["dev", "python"]},
        {"name": "Bob", "age": 17, "tags": ["student"]},
        {"name": "Carol", "age": 25, "tags": ["design"]},
    ]
}

PRESETS = {
    "adults": {"query": ".users | filter(.age >= 18) | map(.name)", "data": SAMPLE},
    "tags": {"query": ".users[0].tags | length", "data": SAMPLE},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="prism",
        title="JSON Query Lab",
        description="Run Prism pipe queries on JSON data.",
        mission="Query structured data like a tiny jq — filters, maps, and field access.",
        kind="text",
        tier=1,
        safety="safe",
        primaryAction="Run query",
        presets=[
            LabPreset(id="adults", label="Adult names", isDefault=True),
            LabPreset(id="tags", label="Count tags"),
        ],
        inputs=[
            LabInputField(
                name="query",
                type="text",
                label="Prism query",
                default=PRESETS["adults"]["query"],
            ),
            LabInputField(
                name="data",
                type="json",
                label="JSON data",
                default=json.dumps(SAMPLE),
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        query_str = clamp_text(str(inp.get("query", "")), 500)
        data_raw = inp.get("data", SAMPLE)
        if isinstance(data_raw, str):
            data = json.loads(data_raw)
        else:
            data = data_raw
        dumped = json.dumps(data)
        if len(dumped) > 10_000:
            raise ValueError("JSON data too large")

        ensure_foundry_path()
        from prism import query

        result = query(query_str, data)
        return ok_result(
            "prism",
            "Query succeeded.",
            input_data={"query": query_str},
            result={"value": result},
            visual=LabVisual(
                type="json-result",
                data={"result": result, "query": query_str},
            ),
            explanation=[
                "Pipes flow left to right: each stage transforms the value.",
                f"Result type: {type(result).__name__}.",
            ],
        )
    except Exception as exc:
        return error_result("prism", str(exc), input_data=payload.get("input", {}))
