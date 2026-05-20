"""Repo root resolution for Foundry runners."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_foundry_root() -> Path:
    """Return absolute Foundry repository root."""
    override = os.environ.get("FOUNDRY_ROOT")
    if override:
        root = Path(override).resolve()
    else:
        # api/runner/*.py -> parents[2] is repo root
        root = Path(__file__).resolve().parents[2]
    if not (root / "README.md").is_file() or not (root / "web").is_dir():
        raise RuntimeError(f"Invalid FOUNDRY_ROOT: {root}")
    return root


def module_cwd(spec_cwd: str) -> Path:
    """Resolve whitelisted module working directory under repo root."""
    root = resolve_foundry_root()
    cwd = (root / spec_cwd).resolve()
    if not str(cwd).startswith(str(root)):
        raise ValueError(f"cwd escapes repo root: {spec_cwd}")
    return cwd
