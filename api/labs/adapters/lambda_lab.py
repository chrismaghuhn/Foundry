"""Lambda calculus reduction lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "add": {"expr": "(+ 1 2)"},
    "id": {"expr": "((λx.x) 5)"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="lambda",
        title="Lambda Stepper",
        description="Reduce curated lambda terms one step at a time.",
        mission="Pick a preset expression and watch beta-reduction.",
        kind="text",
        tier=1,
        safety="safe",
        primaryAction="Reduce",
        presets=[
            LabPreset(id="add", label="(+ 1 2)", isDefault=True),
            LabPreset(id="id", label="Identity function"),
        ],
        inputs=[
            LabInputField(
                name="expr",
                type="select",
                label="Expression preset",
                default="(+ 1 2)",
                options=[
                    {"value": "(+ 1 2)", "label": "(+ 1 2)"},
                    {"value": "((λx.x) 5)", "label": "((λx.x) 5)"},
                    {"value": "(* 3 4)", "label": "(* 3 4)"},
                ],
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        expr = clamp_text(str(inp.get("expr", "(+ 1 2)")), 200)
        ensure_foundry_path()
        import importlib.util
        from runner.paths import resolve_foundry_root

        path = resolve_foundry_root() / "lambda" / "lambda_calc.py"
        spec = importlib.util.spec_from_file_location("lambda_calc", path)
        lc = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(lc)

        term = lc.parse(expr)
        steps = lc.reduce_steps(term)
        final = lc.reduce(term)
        step_strs = [str(s) for s in steps[:10]]
        return ok_result(
            "lambda",
            f"Normal form: {final}",
            input_data=inp,
            result={"steps": len(steps), "final": str(final)},
            visual=LabVisual(
                type="json-result",
                data={"steps": step_strs, "final": str(final)},
            ),
            explanation=[
                f"Reduction took {len(steps)} step(s) for this preset.",
                "Only whitelisted presets — no arbitrary host access.",
            ],
        )
    except Exception as exc:
        return error_result("lambda", str(exc))
