"""FastAPI routes for interactive labs."""

from __future__ import annotations

import asyncio
import importlib
from typing import Any

from fastapi import APIRouter, HTTPException

from labs.import_path import ensure_foundry_path
from labs.lab_models import LabDefinition, LabRunRequest, LabRunResult, LabSummary, LabsListResponse
from labs.lab_registry import REGISTRY, get_lab_spec, validate_lab_registry
from labs.limits import LAB_TIMEOUT_S

router = APIRouter(tags=["labs"])

_adapter_cache: dict[str, Any] = {}


def _load_adapter(spec_module: str, module_id: str):
    key = f"{spec_module}:{module_id}"
    if key in _adapter_cache:
        return _adapter_cache[key]
    ensure_foundry_path()
    if spec_module == "protocol_guided":
        from labs.adapters.protocol_guided import ProtocolLab

        adapter = ProtocolLab(module_id)
    else:
        mod = importlib.import_module(f"labs.adapters.{spec_module}")
        adapter = mod
    _adapter_cache[key] = adapter
    return adapter


def _get_definition(spec_module: str, module_id: str) -> LabDefinition:
    adapter = _load_adapter(spec_module, module_id)
    if hasattr(adapter, "get_definition"):
        return adapter.get_definition()
    raise RuntimeError(f"Adapter {spec_module} missing get_definition")


def _run_lab(spec_module: str, module_id: str, payload: dict) -> LabRunResult:
    adapter = _load_adapter(spec_module, module_id)
    if hasattr(adapter, "run_lab"):
        return adapter.run_lab(payload)
    raise RuntimeError(f"Adapter {spec_module} missing run_lab")


@router.get("", response_model=LabsListResponse)
def list_labs() -> LabsListResponse:
    labs = [
        LabSummary(
            moduleId=s.module_id,
            title=s.title,
            kind=s.kind,  # type: ignore[arg-type]
            tier=s.tier,  # type: ignore[arg-type]
            safety=s.safety,  # type: ignore[arg-type]
        )
        for s in REGISTRY.values()
    ]
    labs.sort(key=lambda x: x.moduleId)
    return LabsListResponse(labs=labs)


@router.get("/{module_id}", response_model=LabDefinition)
def get_lab(module_id: str) -> LabDefinition:
    spec = get_lab_spec(module_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown lab: {module_id}")
    return _get_definition(spec.adapter, module_id)


@router.post("/{module_id}/run", response_model=LabRunResult)
async def run_lab_route(module_id: str, body: LabRunRequest) -> LabRunResult:
    spec = get_lab_spec(module_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown lab: {module_id}")
    payload = {
        "presetId": body.presetId,
        "input": body.input,
        "action": body.action,
    }
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_run_lab, spec.adapter, module_id, payload),
            timeout=LAB_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        return LabRunResult(
            moduleId=module_id,
            status="error",
            summary=f"Lab timed out after {LAB_TIMEOUT_S}s.",
            explanation=["Try a smaller input or preset."],
            timeoutMs=LAB_TIMEOUT_S * 1000,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def validate_on_startup() -> None:
    validate_lab_registry()
