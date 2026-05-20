"""Safe Rune expression lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "sum": {"expr": "1 + 2 * 3"},
    "nested": {"expr": "(10 + 5) * 2"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="rune",
        title="Rune Formula Lab",
        description="Evaluate bounded expressions with visible fuel limits.",
        mission="Run a preset formula and see fuel consumed — execution stops when fuel runs out.",
        kind="text",
        tier=1,
        safety="safe",
        primaryAction="Evaluate",
        presets=[
            LabPreset(id="sum", label="1 + 2 * 3", isDefault=True),
            LabPreset(id="nested", label="(10 + 5) * 2"),
        ],
        inputs=[
            LabInputField(
                name="expr",
                type="select",
                label="Expression",
                default="1 + 2 * 3",
                options=[
                    {"value": "1 + 2 * 3", "label": "1 + 2 * 3"},
                    {"value": "(10 + 5) * 2", "label": "(10 + 5) * 2"},
                    {"value": "100 / 4 + 1", "label": "100 / 4 + 1"},
                ],
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        expr = clamp_text(str(inp.get("expr", "")), 200)
        ensure_foundry_path()
        from rune.rune import ExecutionLimits, Rune

        engine = Rune(limits=ExecutionLimits(max_fuel=500, max_depth=32))
        value = engine.evaluate(expr)
        fuel_used = getattr(engine, "fuel_used", None) or engine._fuel_used if hasattr(engine, "_fuel_used") else "n/a"
        return ok_result(
            "rune",
            f"Result: {value}",
            input_data=inp,
            result={"value": value, "fuelUsed": fuel_used},
            visual=LabVisual(
                type="json-result",
                data={"expr": expr, "value": value, "fuelUsed": fuel_used},
            ),
            explanation=[
                "Rune uses fuel and depth caps instead of arbitrary loops.",
                "Only preset expressions in this lab — no user-defined functions.",
            ],
        )
    except Exception as exc:
        return error_result("rune", str(exc))
