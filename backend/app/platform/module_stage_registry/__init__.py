"""Module Stage Registry — platform existence surface (LI-1+)."""

from backend.app.platform.module_stage_registry.existence import (
    REGISTRY_PATH,
    is_stage_registered,
    is_stage_registered_qualified,
    list_registered_stage_keys,
    qualified_stage_id,
)

__all__ = [
    "REGISTRY_PATH",
    "is_stage_registered",
    "is_stage_registered_qualified",
    "list_registered_stage_keys",
    "qualified_stage_id",
]
