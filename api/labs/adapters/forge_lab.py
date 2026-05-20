"""FSM event simulator lab."""

from __future__ import annotations

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabInputField, LabPreset, LabRunResult, LabVisual
from labs.adapters._helpers import error_result, merge_preset_input, ok_result

PRESETS = {
    "door": {"event": "coin"},
}


def _door_machine():
    ensure_foundry_path()
    from forge.forge import Event, State, StateMachineBuilder, state

    locked = state("locked", initial=True)
    unlocked = state("unlocked")
    coin = Event("coin")
    push = Event("push")
    return (
        StateMachineBuilder("door")
        .add_states(locked, unlocked)
        .add_events(coin, push)
        .add_transition(locked, coin, unlocked)
        .add_transition(unlocked, push, locked)
        .add_transition(unlocked, coin, unlocked)
        .build()
    )


def get_definition() -> LabDefinition:
    return LabDefinition(
        moduleId="forge",
        title="FSM Lab",
        description="Fire events on a tiny state machine and read the transition log.",
        mission="You're at a locked door — insert a coin, then push. What state are you in?",
        kind="visual",
        tier=1,
        safety="safe",
        primaryAction="Send event",
        presets=[LabPreset(id="door", label="Locked door", isDefault=True)],
        inputs=[
            LabInputField(
                name="event",
                type="select",
                label="Event",
                default="coin",
                options=[
                    {"value": "coin", "label": "coin"},
                    {"value": "push", "label": "push"},
                ],
            ),
        ],
    )


def run_lab(payload: dict) -> LabRunResult:
    try:
        inp = merge_preset_input(payload, PRESETS)
        event_name = inp.get("event", "coin")
        log = list(inp.get("log") or [])
        current = inp.get("currentState", "locked")

        ensure_foundry_path()
        from forge.forge import Event, StateMachineInstance

        machine = _door_machine()
        inst = StateMachineInstance(machine)
        if current == "unlocked":
            inst._current_state = machine.states["unlocked"]
        ev = Event(event_name)
        info = inst.send(ev, raise_on_invalid=False)
        new_state = inst.state.name
        entry = {
            "event": event_name,
            "from": current,
            "to": new_state,
            "ok": info.result.value if hasattr(info, "result") else str(info),
        }
        log.append(entry)
        return ok_result(
            "forge",
            f"Event '{event_name}' → state {new_state}.",
            input_data=inp,
            result={"state": new_state, "log": log},
            visual=LabVisual(
                type="fsm",
                data={"state": new_state, "log": log, "events": ["coin", "push"]},
            ),
            explanation=[
                "Forge validates transitions at build time.",
                "Invalid events are rejected without changing state.",
            ],
        )
    except Exception as exc:
        return error_result("forge", str(exc))
