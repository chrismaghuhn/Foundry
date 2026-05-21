"""Lab adapter behavior and safety checks."""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from main import app
from labs.lab_registry import REGISTRY

client = TestClient(app)

LABS_ROOT = pathlib.Path(__file__).resolve().parent / "labs"


def test_no_subprocess_in_labs():
    text = ""
    for path in LABS_ROOT.rglob("*.py"):
        text += path.read_text(encoding="utf-8")
    assert "subprocess" not in text
    assert "shell=True" not in text
    assert "eval(" not in text
    assert "exec(" not in text


@pytest.mark.parametrize("module_id", ["graph", "diff", "prism", "shamir", "automata"])
def test_tier1_default_preset_ok(module_id: str):
    spec = REGISTRY[module_id]
    defn = client.get(f"/api/labs/{module_id}").json()
    preset = next(p for p in defn["presets"] if p.get("isDefault"))
    r = client.post(f"/api/labs/{module_id}/run", json={"presetId": preset["id"], "input": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body.get("visual") or body.get("explanation")


def test_unknown_lab_404():
    assert client.get("/api/labs/no-such-module").status_code == 404


def test_oversized_text_rejected():
    r = client.post(
        "/api/labs/diff/run",
        json={"input": {"textA": "x" * 6000, "textB": "y"}},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "error"


def test_list_labs():
    r = client.get("/api/labs")
    assert r.status_code == 200
    assert len(r.json()["labs"]) == len(REGISTRY)
