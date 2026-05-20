"""Lab registry — one spec per modules.json id."""

from __future__ import annotations

from dataclasses import dataclass

LabKind = str
LabTier = int


@dataclass(frozen=True)
class LabSpec:
    module_id: str
    title: str
    kind: LabKind
    tier: LabTier
    safety: str
    adapter: str


def _t1(mid: str, title: str, adapter: str) -> LabSpec:
    return LabSpec(mid, title, "visual", 1, "safe", adapter)


def _t2(mid: str, title: str, adapter: str) -> LabSpec:
    return LabSpec(mid, title, "scenario", 2, "safe", adapter)


def _t3(mid: str, title: str, *, read_only: bool = False) -> LabSpec:
    safety = "read-only" if read_only else "demo"
    return LabSpec(mid, title, "guided", 3, safety, "protocol_guided")


_SPECS: list[LabSpec] = [
    _t1("graph", "Pathfinding Lab", "graph_lab"),
    _t1("shamir", "Secret Sharing Lab", "shamir_lab"),
    _t1("diff", "Text Diff Lab", "diff_lab"),
    _t1("automata", "Game of Life Lab", "automata_lab"),
    _t2("lisp", "Lisp Expression Lab", "lisp_lab"),
    _t2("parsec", "Parser Combinator Lab", "parsec_lab"),
    _t1("turing", "Turing Machine Lab", "turing_lab"),
    _t1("lambda", "Lambda Stepper", "lambda_lab"),
    _t1("enigma", "Enigma Lab", "enigma_lab"),
    _t2("morse", "Huffman Coding Lab", "morse_lab"),
    _t1("phantom", "Regex Match Lab", "phantom_lab"),
    _t2("lattice", "CRDT Merge Lab", "lattice_lab"),
    _t1("sketch", "Bloom Filter Lab", "sketch_lab"),
    _t2("glyph", "ASCII Pipeline Lab", "glyph_lab"),
    _t1("forge", "FSM Lab", "forge_lab"),
    _t1("rune", "Rune Formula Lab", "rune_lab"),
    _t1("prism", "JSON Query Lab", "prism_lab"),
    _t2("malo", "Log Store Lab", "malo_lab"),
    _t2("chrono", "Timeline Lab", "chrono_lab"),
    _t2("arc", "ARC Cache Lab", "arc_lab"),
    _t2("sentinel", "Watchdog Lab", "sentinel_lab"),
    _t2("flux", "Event Stream Lab", "flux_lab"),
    _t2("styx", "Coordination Lab", "styx_lab"),
    _t3("nexus", "Nexus Integration Tour"),
    _t3("reactor", "Reactor Pipeline Demo"),
    _t3("forge_vm", "Forge VM Walkthrough"),
    _t3("bastion", "Bastion Security Map", read_only=True),
    _t3("audit", "Audit Trail Demo"),
    _t3("tribunal", "Tribunal Vote Demo"),
    _t3("signal", "Signal Handshake Demo"),
    _t3("ledger", "Ledger Chain Demo"),
    _t3("pact", "Pact Agreement Demo"),
    _t3("witness", "Witness Attestation Demo"),
    _t3("specter", "Specter Covert Demo"),
]

REGISTRY: dict[str, LabSpec] = {s.module_id: s for s in _SPECS}


def get_lab_spec(module_id: str) -> LabSpec | None:
    return REGISTRY.get(module_id)


def validate_lab_registry() -> None:
    import json
    from pathlib import Path

    from runner.paths import resolve_foundry_root

    root = resolve_foundry_root()
    data = json.loads((root / "web" / "src" / "data" / "modules.json").read_text(encoding="utf-8"))
    json_ids = {m["id"] for m in data["modules"]}
    reg_ids = set(REGISTRY.keys())
    if json_ids != reg_ids:
        missing = json_ids - reg_ids
        extra = reg_ids - json_ids
        raise RuntimeError(f"Lab registry mismatch. missing={missing} extra={extra}")
