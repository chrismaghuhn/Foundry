"""Lisp preset lab."""

from __future__ import annotations

import importlib.util

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import error_result, merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition
from runner.paths import resolve_foundry_root

PRESETS = {"add": {"expr": "(+ 1 2)"}, "list": {"expr": "(cons 1 (cons 2 nil))"}}


def get_definition():
    return preset_definition(
        "lisp",
        "Lisp Expression Lab",
        "Evaluate curated Lisp presets safely.",
        "Pick a preset — no arbitrary file or network access.",
        [("add", "(+ 1 2)", True), ("list", "Build a list", False)],
        inputs=[],
    )


def _eval_expr(expr: str):
    ensure_foundry_path()
    root = resolve_foundry_root()
    path = root / "lisp" / "lisp.py"
    spec = importlib.util.spec_from_file_location("lisp_mod", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    interp = mod.Interpreter()
    return interp.run(expr)


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        expr = inp.get("expr", "(+ 1 2)")
        val = _eval_expr(expr)
        return ok_result(
            "lisp",
            f"Result: {val}",
            input_data=inp,
            visual=LabVisual(type="json-result", data={"expr": expr, "value": str(val)}),
            explanation=["Preset expressions only — full interpreter runs in-process."],
        )
    except Exception as exc:
        return error_result("lisp", str(exc))
