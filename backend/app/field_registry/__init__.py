"""Field Registry package (Platform Core)."""

from backend.app.field_registry.candidate_layout_bridge import resolve_effective_candidate_card_layout
from backend.app.field_registry.registry import FieldRegistry
from backend.app.field_registry.resolver import list_canonical_fields_for_scope, resolve_effective_card_layout
from backend.app.field_registry.seed import ensure_platform_field_registry_catalog, ensure_tenant_field_registry_defaults

__all__ = [
    "FieldRegistry",
    "ensure_platform_field_registry_catalog",
    "ensure_tenant_field_registry_defaults",
    "list_canonical_fields_for_scope",
    "resolve_effective_card_layout",
    "resolve_effective_candidate_card_layout",
]
