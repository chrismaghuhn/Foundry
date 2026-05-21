"""Lab registry parity with modules.json."""

from __future__ import annotations

import json

from labs.lab_registry import REGISTRY, validate_lab_registry
from runner.paths import resolve_foundry_root


def test_registry_matches_modules_json():
    validate_lab_registry()
    root = resolve_foundry_root()
    data = json.loads((root / "web" / "src" / "data" / "modules.json").read_text(encoding="utf-8"))
    json_ids = {m["id"] for m in data["modules"]}
    assert set(REGISTRY.keys()) == json_ids


def test_tier_counts():
    t1 = [s for s in REGISTRY.values() if s.tier == 1]
    t2 = [s for s in REGISTRY.values() if s.tier == 2]
    t3 = [s for s in REGISTRY.values() if s.tier == 3]
    assert len(t1) == 12
    assert len(t2) == 11
    assert len(t3) == 11
    assert len(REGISTRY) == len(t1) + len(t2) + len(t3)


def test_each_spec_has_metadata():
    for spec in REGISTRY.values():
        assert spec.title
        assert spec.kind in ("visual", "text", "scenario", "guided")
        assert spec.tier in (1, 2, 3)
        assert spec.safety in ("safe", "demo", "read-only")
