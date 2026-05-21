"""Secret sharing lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import CRYPTO_WARNING, clamp_text, error_result, merge_preset_input, ok_result

PRESETS = {
    "hello": {"secret": "Foundry", "n": 5, "k": 3, "selected": [1, 3, 5]},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="shamir",
        title="Secret Sharing Lab",
        description="Split a secret into shares and reconstruct from any k of them.",
        mission="Pick threshold k and see why k−1 shares reveal nothing.",
        kind="visual",
        tier=1,
        safety="demo",
        primaryAction="Split & reconstruct",
        securityNote=CRYPTO_WARNING,
        presets=[LabPreset(id="hello", label="Split \"Foundry\"", isDefault=True)],
        inputs=[
            LabInputField(name="secret", type="text", label="Secret", default="Foundry"),
            LabInputField(name="n", type="number", label="Shares (n)", default=5, min=2, max=10),
            LabInputField(name="k", type="number", label="Threshold (k)", default=3, min=2, max=10),
            LabInputField(
                name="selected",
                type="text",
                label="Share indices to combine (comma-separated)",
                default="1,3,5",
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        secret = clamp_text(str(inp.get("secret", "")), 200)
        n = int(inp.get("n", 5))
        k = int(inp.get("k", 3))
        if k > n or n < 2 or k < 2:
            return error_result("shamir", "Need 2 ≤ k ≤ n.")
        sel_raw = inp.get("selected", "1,2,3")
        if isinstance(sel_raw, list):
            indices = [int(x) for x in sel_raw]
        else:
            indices = [int(x.strip()) for x in str(sel_raw).split(",") if x.strip()]

        ensure_foundry_path()
        from shamir.shamir import combine_string, split_string

        shares = split_string(secret, n, k)
        if len(indices) < k:
            return error_result(
                "shamir",
                f"Select at least {k} share indices to reconstruct.",
                input_data=inp,
            )
        picked = [shares[i - 1] for i in indices if 1 <= i <= n][:k]
        if len(picked) < k:
            return error_result("shamir", "Invalid share indices.", input_data=inp)
        recovered = combine_string(picked)
        share_data = [
            {"index": i + 1, "x": s.x, "bytes": len(s.data)}
            for i, s in enumerate(shares)
        ]
        return ok_result(
            "shamir",
            f"Reconstructed: \"{recovered}\" ({'match' if recovered == secret else 'mismatch'}).",
            input_data=inp,
            result={"recovered": recovered, "shares": share_data},
            visual=LabVisual(
                type="shares",
                data={"shares": share_data, "selected": indices, "k": k, "n": n},
            ),
            explanation=[
                f"Polynomial of degree {k - 1} hides the secret; any {k} points determine it.",
                "Fewer than k shares give no information (in this educational field).",
            ],
            warnings=[CRYPTO_WARNING],
        )
    except Exception as exc:
        return error_result("shamir", str(exc))
