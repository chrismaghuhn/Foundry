"""Turing machine step lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import error_result, merge_preset_input, ok_result
from labs.limits import MAX_STEPS

PRESETS = {
    "increment": {"machine": "binary_increment", "tape": "101", "steps": 1},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="turing",
        title="Turing Machine Lab",
        description="Step through built-in machines and watch tape and state change.",
        mission="Pick a machine, step once, and read the head position.",
        kind="visual",
        tier=1,
        safety="safe",
        primaryAction="Step",
        presets=[LabPreset(id="increment", label="Binary increment", isDefault=True)],
        inputs=[
            LabInputField(
                name="machine",
                type="select",
                label="Machine",
                default="binary_increment",
                options=[
                    {"value": "binary_increment", "label": "Binary increment"},
                    {"value": "palindrome_checker", "label": "Palindrome checker"},
                ],
            ),
            LabInputField(name="tape", type="text", label="Input tape", default="101"),
            LabInputField(name="steps", type="number", label="Steps", default=1, min=1, max=20),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        name = inp.get("machine", "binary_increment")
        tape_in = str(inp.get("tape", "101"))[:50]
        steps = min(int(inp.get("steps", 1)), MAX_STEPS)
        cursor = int(inp.get("cursor", 0))

        ensure_foundry_path()
        from turing.turing import get_machine, trace

        tm = get_machine(name)
        configs = list(trace(tm, tape_in, max_steps=steps + cursor))
        if not configs:
            return error_result("turing", "Machine produced no steps.")
        cfg = configs[min(cursor + steps, len(configs) - 1)]
        head_sym = cfg.tape.read(cfg.head_position)
        left = "".join(cfg.tape.read(cfg.head_position + i) for i in range(-5, 6))
        tape_str = left
        return ok_result(
            "turing",
            f"State {cfg.state} at step {cfg.step} — head on '{head_sym}'.",
            input_data=inp,
            result={"state": cfg.state, "step": cfg.step},
            visual=LabVisual(
                type="tape",
                data={
                    "tape": tape_str,
                    "head": cfg.head_position,
                    "state": cfg.state,
                    "step": cfg.step,
                },
            ),
            explanation=[
                "The machine reads one cell, writes, moves L/R, changes state.",
                "Halting depends on the machine definition — cap steps in the lab.",
            ],
        )
    except Exception as exc:
        return error_result("turing", str(exc))
