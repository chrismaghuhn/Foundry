"""Game of Life lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import error_result, merge_preset_input, ok_result
from labs.limits import MAX_GRID_H, MAX_GRID_W

PRESETS = {
    "blinker": {"pattern": "blinker", "action": "step"},
    "glider": {"pattern": "glider", "action": "step"},
}


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="automata",
        title="Game of Life Lab",
        description="Conway's Game of Life on a toroidal grid — step and watch patterns evolve.",
        mission="Load a classic pattern and step forward. Can you predict the next generation?",
        kind="visual",
        tier=1,
        safety="safe",
        primaryAction="Step",
        presets=[
            LabPreset(id="blinker", label="Blinker", isDefault=True),
            LabPreset(id="glider", label="Glider"),
        ],
        inputs=[
            LabInputField(
                name="pattern",
                type="select",
                label="Pattern",
                default="blinker",
                options=[
                    {"value": "blinker", "label": "Blinker"},
                    {"value": "glider", "label": "Glider"},
                    {"value": "block", "label": "Block"},
                ],
            ),
            LabInputField(
                name="action",
                type="select",
                label="Action",
                default="step",
                options=[
                    {"value": "step", "label": "Step"},
                    {"value": "reset", "label": "Reset pattern"},
                ],
            ),
        ],
    )


def _grid_from_state(state: dict | None) -> tuple:
    ensure_foundry_path()
    from automata.automata import GameOfLife

    w = min(int((state or {}).get("width", 20)), MAX_GRID_W)
    h = min(int((state or {}).get("height", 15)), MAX_GRID_H)
    life = GameOfLife(width=w, height=h)
    cells = (state or {}).get("cells") or []
    for c in cells:
        if isinstance(c, (list, tuple)) and len(c) >= 2:
            life.set_cell(int(c[0]), int(c[1]), True)
    return life


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        state = inp.get("state") or {}
        action = inp.get("action", "step")
        pattern = inp.get("pattern", "blinker")

        ensure_foundry_path()
        from automata.automata import GameOfLife

        if action == "reset" or not state.get("cells"):
            life = GameOfLife(width=20, height=15)
            life.add_pattern(pattern)
            gen = 0
        else:
            life = _grid_from_state(state)
            life.step()
            gen = int(state.get("generation", 0)) + 1

        cells = [[x, y] for x, y in life.cells]
        return ok_result(
            "automata",
            f"Generation {gen} — {len(cells)} live cells.",
            input_data={"pattern": pattern, "action": action},
            result={"generation": gen, "liveCount": len(cells)},
            visual=LabVisual(
                type="grid",
                data={
                    "width": life.width,
                    "height": life.height,
                    "cells": cells,
                    "generation": gen,
                },
            ),
            explanation=[
                "B3/S23: birth on 3 neighbors, survival on 2–3.",
                "Edges wrap — the grid is a torus.",
            ],
        )
    except Exception as exc:
        return error_result("automata", str(exc))
