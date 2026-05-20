"""Enigma encrypt/decrypt lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "demo": {"text": "HELLO", "preset": "default", "mode": "encrypt"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="enigma",
        title="Enigma Lab",
        description="Encrypt and decrypt with rotor machine presets.",
        mission="Type a message and flip rotors — see how substitution changes each letter.",
        kind="text",
        tier=1,
        safety="demo",
        primaryAction="Encrypt",
        presets=[LabPreset(id="demo", label="HELLO → ciphertext", isDefault=True)],
        inputs=[
            LabInputField(name="text", type="text", label="Text", default="HELLO"),
            LabInputField(
                name="mode",
                type="select",
                label="Mode",
                default="encrypt",
                options=[
                    {"value": "encrypt", "label": "Encrypt"},
                    {"value": "decrypt", "label": "Decrypt"},
                ],
            ),
            LabInputField(
                name="preset",
                type="select",
                label="Machine preset",
                default="default",
                options=[{"value": "default", "label": "Default rotors"}],
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        text = clamp_text(str(inp.get("text", "")).upper())
        mode = inp.get("mode", "encrypt")
        ensure_foundry_path()
        from enigma.enigma import Enigma, quick_decrypt, quick_encrypt

        if mode == "decrypt":
            out = quick_decrypt(text)
        else:
            out = quick_encrypt(text)
        return ok_result(
            "enigma",
            f"{'Decrypted' if mode == 'decrypt' else 'Encrypted'}: {out}",
            input_data=inp,
            result={"output": out},
            visual=LabVisual(
                type="json-result",
                data={"input": text, "output": out, "mode": mode},
            ),
            explanation=[
                "Each key press advances rotors before substitution.",
                "Plugboard and reflector make the cipher reciprocal.",
            ],
        )
    except Exception as exc:
        return error_result("enigma", str(exc))
