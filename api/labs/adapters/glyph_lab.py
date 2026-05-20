"""ASCII pipeline preset lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"upper": {"text": "foundry", "pipeline": "upper"}}


def get_definition():
    return preset_definition(
        "glyph",
        "ASCII Pipeline Lab",
        "Run text through a whitelisted ASCII transform pipeline.",
        "See how small filters chain together.",
        [("upper", "Uppercase", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        text = clamp_text(str(inp.get("text", "")))
        out = text.upper() if inp.get("pipeline") == "upper" else text[::-1]
        return ok_result(
            "glyph",
            f"Output: {out}",
            input_data=inp,
            visual=LabVisual(type="scenario-log", data={"log": [f"in: {text}", f"out: {out}"]}),
            explanation=["Preset pipeline only — mirrors glyph-style transforms."],
        )
    except Exception as exc:
        return error_result("glyph", str(exc))
