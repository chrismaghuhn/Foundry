"""Interactive labs — whitelisted in-process module experiences."""

from .lab_registry import REGISTRY, get_lab_spec, validate_lab_registry
from .lab_router import router

__all__ = ["REGISTRY", "get_lab_spec", "validate_lab_registry", "router"]
