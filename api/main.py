"""Foundry localhost runner API — whitelisted test/example commands only."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from runner import (
    get_spec,
    resolve_foundry_root,
    run_command,
    validate_registry,
)
from runner.response_models import HealthResponse, ModuleSummary, ModulesListResponse, RunResult

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_registry()
    yield


app = FastAPI(title="Foundry Runner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, root=str(resolve_foundry_root()))


@app.get("/api/modules", response_model=ModulesListResponse)
def list_modules() -> ModulesListResponse:
    from runner.module_registry import REGISTRY

    modules = [
        ModuleSummary(
            moduleId=spec.module_id,
            cwd=spec.cwd,
            testAvailable=spec.test_command is not None,
            exampleAvailable=spec.example_command is not None,
        )
        for spec in REGISTRY.values()
    ]
    modules.sort(key=lambda m: m.module_id)
    return ModulesListResponse(modules=modules)


@app.post("/api/modules/{module_id}/test", response_model=RunResult)
def run_module_test(module_id: str) -> RunResult:
    spec = get_spec(module_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_id}")
    return run_command(
        module_id,
        "test",
        spec.cwd,
        spec.test_command,
    )


@app.post("/api/modules/{module_id}/example", response_model=RunResult)
def run_module_example(module_id: str) -> RunResult:
    spec = get_spec(module_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_id}")
    return run_command(
        module_id,
        "example",
        spec.cwd,
        spec.example_command,
    )
