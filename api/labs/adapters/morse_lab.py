"""Huffman coding lab (morse package)."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {"short": {"text": "hello"}}


def get_definition():
    return preset_definition(
        "morse",
        "Huffman Coding Lab",
        "Build a Huffman tree and encode text (package name is morse, content is Huffman).",
        "Type a short word — see code lengths and compressed size.",
        [("short", "Encode \"hello\"", True)],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        text = clamp_text(str(inp.get("text", "hello")), 200)
        ensure_foundry_path()
        from morse.morse import encode, build_tree

        bits, tree = encode(text)
        return ok_result(
            "morse",
            f"Encoded {len(text)} chars → {len(bits)} bits.",
            input_data=inp,
            visual=LabVisual(
                type="huffman",
                data={"text": text, "bits": bits[:80], "bitLength": len(bits)},
            ),
            explanation=[
                "Frequent symbols get shorter codes — optimal prefix codes.",
                "This module implements Huffman, not Morse telegraphy.",
            ],
        )
    except Exception as exc:
        return error_result("morse", str(exc))
