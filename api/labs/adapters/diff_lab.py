"""Text diff lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "lines": {
        "textA": "alpha\nbeta\ngamma",
        "textB": "alpha\nbeta line\ndelta\ngamma",
    },
    "words": {"textA": "hello world", "textB": "hello brave world"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="diff",
        title="Text Diff Lab",
        description="Compare two texts and see insert, delete, and keep chunks.",
        mission="Change text A or B and watch the minimal edit script appear.",
        kind="text",
        tier=1,
        safety="safe",
        primaryAction="Compare",
        presets=[
            LabPreset(id="lines", label="Line diff", isDefault=True),
            LabPreset(id="words", label="Word diff"),
        ],
        inputs=[
            LabInputField(name="textA", type="textarea", label="Text A", default=PRESETS["lines"]["textA"]),
            LabInputField(name="textB", type="textarea", label="Text B", default=PRESETS["lines"]["textB"]),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        text_a = clamp_text(str(inp.get("textA", "")))
        text_b = clamp_text(str(inp.get("textB", "")))
        ensure_foundry_path()
        from diff.diff import EditType, diff_lines

        if "\n" in text_a or "\n" in text_b:
            result = diff_lines(text_a, text_b)
        else:
            from diff.diff import diff as char_diff

            result = char_diff(list(text_a), list(text_b))

        chunks = []
        for edit in result.edits:
            if edit.type == EditType.EQUAL:
                kind = "keep"
            elif edit.type == EditType.INSERT:
                kind = "insert"
            else:
                kind = "delete"
            chunks.append({"kind": kind, "text": str(edit.value)})

        ins = sum(1 for c in chunks if c["kind"] == "insert")
        dele = sum(1 for c in chunks if c["kind"] == "delete")
        return ok_result(
            "diff",
            f"Edit distance {result.edit_distance}: {ins} inserts, {dele} deletes.",
            input_data={"textA": text_a, "textB": text_b},
            result={"editDistance": result.edit_distance, "chunks": chunks},
            visual=LabVisual(type="diff-chunks", data={"chunks": chunks}),
            explanation=[
                "Myers-style diff finds a short edit script between sequences.",
                "Green = kept, amber = inserted, red = removed.",
            ],
        )
    except Exception as exc:
        return error_result("diff", str(exc))
