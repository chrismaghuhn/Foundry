"""Ensure Foundry packages are importable from lab adapters."""

from __future__ import annotations

import sys

from runner.paths import resolve_foundry_root

_configured = False


def ensure_foundry_path() -> None:
    global _configured
    if _configured:
        return
    root = str(resolve_foundry_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    _configured = True
