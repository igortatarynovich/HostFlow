"""Module Registry package (Platform Core)."""

from __future__ import annotations

from backend.app.module_registry.resolver import is_module_installed, list_available_module_codes, list_installed_modules
from backend.app.module_registry.seed import ensure_module_registry_baseline, ensure_tenant_module_installations

__all__ = [
    "ensure_module_registry_baseline",
    "ensure_tenant_module_installations",
    "is_module_installed",
    "list_available_module_codes",
    "list_installed_modules",
]
