"""Registry parity with UI catalog and repo root resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.module_registry import REGISTRY
from runner.paths import resolve_foundry_root


def _modules_json_ids() -> set[str]:
    root = resolve_foundry_root()
    path = root / "web" / "src" / "data" / "modules.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {m["id"] for m in data["modules"]}


def test_foundry_root_contains_readme_and_web():
    root = resolve_foundry_root()
    assert (root / "README.md").is_file()
    assert (root / "web").is_dir()


def test_registry_matches_modules_json_ids():
    json_ids = _modules_json_ids()
    registry_ids = set(REGISTRY.keys())
    assert registry_ids == json_ids, (
        f"registry/json mismatch: "
        f"only in registry {registry_ids - json_ids}, "
        f"only in json {json_ids - registry_ids}"
    )


def test_registry_count_derived_from_json_not_hardcoded():
    json_ids = _modules_json_ids()
    assert len(REGISTRY) == len(json_ids)
    assert len(json_ids) > 0


def test_bastion_read_only():
    spec = REGISTRY["bastion"]
    assert spec.test_command is None
    assert spec.example_command is None
