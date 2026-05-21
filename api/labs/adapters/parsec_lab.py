"""Parsec parser preset lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result
from labs.adapters.tier2_utils import preset_definition

PRESETS = {
    "nums": {"grammar": "numbers", "input": "1 23 456"},
    "expr": {"grammar": "add", "input": "12+34"},
}


def get_definition():
    return preset_definition(
        "parsec",
        "Parser Combinator Lab",
        "Try whitelisted grammars on sample input.",
        "Pick a grammar preset and parse — see success or a precise error.",
        [("nums", "Number list", True), ("expr", "Addition", False)],
        inputs=[],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        grammar = inp.get("grammar", "numbers")
        text = clamp_text(str(inp.get("input", "")))
        ensure_foundry_path()
        from parsec import parsec as p

        if grammar == "add":
            number = p.digit.many1().map(lambda ds: int("".join(ds)))
            parser = number << p.spaces.optional() << p.string("+") << p.spaces.optional() << number
        else:
            number = p.digit.many1().map(lambda ds: int("".join(ds)))
            parser = (number << p.spaces).many().map(list)

        result = parser.parse(text)
        return ok_result(
            "parsec",
            f"Parsed: {result}",
            input_data=inp,
            visual=LabVisual(type="json-result", data={"result": str(result)}),
            explanation=["Combinators compose — failures include position hints."],
        )
    except Exception as exc:
        return error_result("parsec", str(exc))
