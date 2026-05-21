"""Lambda calculus reduction lab."""

from __future__ import annotations

import importlib.util
import sys

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result
from runner.paths import resolve_foundry_root

PRESETS = {
    "add": {"expr": "(add 1 2)"},
    "id": {"expr": "(I y)"},
    "mul": {"expr": "(mul 2 3)"},
}


def _load_lambda_calc():
    """Load lambda_calc without importing package name 'lambda' (reserved keyword)."""
    ensure_foundry_path()
    path = resolve_foundry_root() / "lambda" / "lambda_calc.py"
    spec = importlib.util.spec_from_file_location("lambda_calc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load lambda_calc module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lambda_calc"] = mod
    spec.loader.exec_module(mod)
    return mod


def _term_display(term) -> str:
    text = str(term)
    return text.replace("\u03bb", "\\")


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="lambda",
        title="Lambda Stepper",
        description="Reduce curated lambda terms with Church numerals and stdlib names.",
        mission="Pick a preset expression and watch beta-reduction.",
        kind="text",
        tier=1,
        safety="safe",
        primaryAction="Reduce",
        presets=[
            LabPreset(id="add", label="add 1 2 → 3", isDefault=True),
            LabPreset(id="id", label="Identity (I y)"),
            LabPreset(id="mul", label="mul 2 3 → 6"),
        ],
        inputs=[
            LabInputField(
                name="expr",
                type="select",
                label="Expression preset",
                default="(add 1 2)",
                options=[
                    {"value": "(add 1 2)", "label": "add 1 2 (Church)"},
                    {"value": "(I y)", "label": "I y (identity)"},
                    {"value": "(mul 2 3)", "label": "mul 2 3 (Church)"},
                    {"value": "((λx.x) 5)", "label": "((λx.x) 5)"},
                ],
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        expr = clamp_text(str(inp.get("expr", "(add 1 2)")), 200)
        lc = _load_lambda_calc()

        term = lc.parse(expr)
        expanded = lc.expand_stdlib(term)
        steps = lc.reduce_steps(expanded)
        final = lc.evaluate(expr)

        step_strs = [
            f"{_term_display(s.before)}  =>  {_term_display(s.after)}"
            for s in steps[:8]
        ]
        if not step_strs:
            step_strs = [f"Normal form: {_term_display(final)}"]

        summary = f"Normal form: {_term_display(final)}"
        n = lc.Church.to_int(final)
        if n is not None:
            summary = f"Church numeral value: {n}"

        return ok_result(
            "lambda",
            summary,
            input_data=inp,
            result={"steps": len(steps), "final": _term_display(final)},
            visual=LabVisual(
                type="json-result",
                data={"steps": step_strs, "final": _term_display(final)},
            ),
            explanation=[
                f"Beta-reduction took {len(steps)} step(s) after expanding stdlib names.",
                "Use add/mul/I from the stdlib — not raw (+ 1 2) syntax.",
            ],
        )
    except Exception as exc:
        return error_result("lambda", str(exc))
