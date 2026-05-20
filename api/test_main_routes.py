"""HTTP route smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "README.md" in data["root"] or "foundry" in data["root"].lower()


def test_list_modules():
    r = client.get("/api/modules")
    assert r.status_code == 200
    modules = r.json()["modules"]
    assert len(modules) > 0
    graph = next(m for m in modules if m["moduleId"] == "graph")
    assert graph["testAvailable"] is True


def test_unknown_module_404():
    r = client.post("/api/modules/not-a-real-module/test")
    assert r.status_code == 404
