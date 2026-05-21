"""Tier-3 guided labs for protocol modules and bastion."""

from __future__ import annotations

from labs.lab_models import LabDefinition, LabRunResult
from labs.adapters._guided import make_guided_definition, run_guided_scenario

SCENARIOS: dict[str, dict] = {
    "nexus": {
        "overview": {
            "summary": "Nexus wires multiple Foundry pieces into one integration sketch.",
            "cards": [
                {"title": "Role", "body": "Composition root for demos — not a deployed service mesh."},
                {"title": "Try locally", "body": "Use the Technical runner to execute nexus_integration.py when curious."},
            ],
            "log": ["Preset: integration overview"],
            "explanation": [
                "Integration modules show how packages compose.",
                "No live network calls in this guided lab.",
            ],
        }
    },
    "reactor": {
        "pipeline": {
            "summary": "Reactor models an event pipeline with stages and handlers.",
            "cards": [
                {"title": "Stages", "body": "Events flow through transforms — think ETL in miniature."},
                {"title": "Safety", "body": "Demo only; no production stream guarantees."},
            ],
            "log": ["Stage A → Stage B → sink (simulated)"],
            "explanation": ["Use runner examples for full stdout trace."],
        }
    },
    "forge_vm": {
        "bytecode": {
            "summary": "Forge VM executes bytecode for the Forge DSL — stack machine view.",
            "cards": [
                {"title": "VM", "body": "Loads opcodes and runs a small program counter loop."},
            ],
            "log": ["LOAD 1", "LOAD 2", "ADD", "HALT"],
            "explanation": ["Pair with forge FSM lab for complementary views."],
        }
    },
    "bastion": {
        "security": {
            "summary": "Bastion documents defense-in-depth patterns — read-only in the lab.",
            "cards": [
                {"title": "Layers", "body": "Input validation → authZ → audit → rate limits."},
                {"title": "No execution", "body": "This module is documentation-first; runner tests are disabled."},
            ],
            "log": [],
            "explanation": [
                "Study the package README and examples offline.",
                "Do not treat sketches as production security controls.",
            ],
            "visualType": "guided-cards",
        }
    },
    "audit": {
        "trail": {
            "summary": "Audit builds tamper-evident log chains for teaching.",
            "cards": [{"title": "Hash chain", "body": "Each entry links to the previous digest."}],
            "log": ["entry_1 hash=ab12…", "entry_2 prev=ab12…"],
            "explanation": ["Educational integrity demo — not a compliance system."],
        }
    },
    "tribunal": {
        "vote": {
            "summary": "Tribunal simulates quorum voting across nodes.",
            "cards": [{"title": "Quorum", "body": "Majority must agree before a decision is recorded."}],
            "log": ["node_a: yes", "node_b: yes", "node_c: no → approved"],
            "explanation": ["Consensus toy — not Byzantine fault tolerant production code."],
        }
    },
    "signal": {
        "handshake": {
            "summary": "Signal demonstrates encrypted handshake message flow.",
            "cards": [{"title": "Ephemeral keys", "body": "Shows message types without real network IO."}],
            "log": ["HELLO → CHALLENGE → SESSION (simulated)"],
            "explanation": ["Crypto pedagogy only."],
        }
    },
    "ledger": {
        "chain": {
            "summary": "Ledger appends blocks with previous-hash linkage.",
            "cards": [{"title": "Blocks", "body": "Immutable sequence for classroom discussion."}],
            "log": ["block#1", "block#2 prev=…"],
            "explanation": ["Not a cryptocurrency node."],
        }
    },
    "pact": {
        "promise": {
            "summary": "Pact models promises between parties with conditions.",
            "cards": [{"title": "Parties", "body": "A and B agree on terms; state tracks fulfillment."}],
            "log": ["draft → active → fulfilled (simulated)"],
            "explanation": ["Contract flow illustration."],
        }
    },
    "witness": {
        "attest": {
            "summary": "Witness records attestations about observed events.",
            "cards": [{"title": "Attestation", "body": "Third party signs they saw a fact at time T."}],
            "log": ["observe → sign → verify (simulated)"],
            "explanation": ["Trust model explainer."],
        }
    },
    "specter": {
        "stealth": {
            "summary": "Specter explores covert channel concepts in code form.",
            "cards": [{"title": "Covert", "body": "Shows why side channels matter in protocol design."}],
            "log": ["channel_setup (simulated)", "no real exfiltration"],
            "explanation": ["For security learning — never deploy as tooling."],
        }
    },
}

META: dict[str, tuple[str, str, str, bool]] = {
    "nexus": ("Nexus Integration Tour", "See how modules plug together.", "Follow the guided integration story.", False),
    "reactor": ("Reactor Pipeline Demo", "Event stages in order.", "Watch a fake pipeline run.", False),
    "forge_vm": ("Forge VM Walkthrough", "Bytecode execution concept.", "Step through VM ops on paper.", False),
    "bastion": ("Bastion Security Map", "Architecture cards only.", "Read the defense layers.", True),
    "audit": ("Audit Trail Demo", "Hash-linked entries.", "See chained integrity.", False),
    "tribunal": ("Tribunal Vote Demo", "Quorum decision.", "Simulated votes.", False),
    "signal": ("Signal Handshake Demo", "Message choreography.", "Simulated handshake.", False),
    "ledger": ("Ledger Chain Demo", "Linked blocks.", "Walk the chain.", False),
    "pact": ("Pact Agreement Demo", "Lifecycle of a pact.", "States of a promise.", False),
    "witness": ("Witness Attestation Demo", "Observe and attest.", "Simulated attestation.", False),
    "specter": ("Specter Covert Demo", "Covert channel awareness.", "Why side channels matter.", False),
}


def _module_id_from_adapter(adapter_name: str) -> str:
    return adapter_name.replace("_guided", "").replace("_lab", "")


def make_protocol_adapter(module_id: str):
    title, desc, mission, read_only = META[module_id]
    presets = [(k, k.replace("_", " ").title(), i == 0) for i, k in enumerate(SCENARIOS[module_id])]

    def get_definition() -> LabDefinition:
        return make_guided_definition(
            module_id, title, desc, mission, presets, read_only=read_only
        )

    def run_lab(payload: dict) -> LabRunResult:
        preset_id = payload.get("presetId") or list(SCENARIOS[module_id].keys())[0]
        scenario = SCENARIOS[module_id].get(preset_id, list(SCENARIOS[module_id].values())[0])
        return run_guided_scenario(module_id, scenario, {"presetId": preset_id})

    return get_definition, run_lab


class ProtocolLab:
    """Adapter instance bound to one protocol module id."""

    def __init__(self, module_id: str):
        self.module_id = module_id

    def get_definition(self) -> LabDefinition:
        title, desc, mission, read_only = META[self.module_id]
        presets = [
            (k, k.replace("_", " ").title(), i == 0)
            for i, k in enumerate(SCENARIOS[self.module_id])
        ]
        return make_guided_definition(
            self.module_id, title, desc, mission, presets, read_only=read_only
        )

    def run_lab(self, payload: dict) -> LabRunResult:
        preset_id = payload.get("presetId") or list(SCENARIOS[self.module_id].keys())[0]
        scenario = SCENARIOS[self.module_id].get(
            preset_id, list(SCENARIOS[self.module_id].values())[0]
        )
        return run_guided_scenario(self.module_id, scenario, {"presetId": preset_id})
