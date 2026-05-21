"""Regex / NFA match lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "digits": {"pattern": r"\d+", "text": "abc123def"},
    "word": {"pattern": r"[a-z]+", "text": "hello42"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="phantom",
        title="Regex Match Lab",
        description="Test patterns against text and see NFA match steps.",
        mission="Pick a pattern preset and watch which states stay active per character.",
        kind="visual",
        tier=1,
        safety="safe",
        primaryAction="Match",
        presets=[
            LabPreset(id="digits", label="Digits run", isDefault=True),
            LabPreset(id="word", label="Word letters"),
        ],
        inputs=[
            LabInputField(name="pattern", type="text", label="Pattern", default=r"\d+"),
            LabInputField(name="text", type="text", label="Input", default="abc123def"),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        pattern = clamp_text(str(inp.get("pattern", "")), 200)
        text = clamp_text(str(inp.get("text", "")), 500)
        ensure_foundry_path()
        from phantom.phantom import match

        result = match(pattern, text)
        steps = [
            {
                "position": s.position,
                "char": s.char,
                "active": len(s.active_states),
                "note": s.note,
            }
            for s in result.steps[:50]
        ]
        return ok_result(
            "phantom",
            f"{'Match' if result.matched else 'No match'} at [{result.match_start}:{result.match_end}].",
            input_data=inp,
            result={"matched": result.matched},
            visual=LabVisual(
                type="regex-trace",
                data={"steps": steps, "pattern": pattern, "text": text},
            ),
            explanation=[
                "Phantom compiles regex to an NFA and simulates ε-closure per step.",
                "Educational trace — not a production regex engine.",
            ],
        )
    except Exception as exc:
        return error_result("phantom", str(exc))
