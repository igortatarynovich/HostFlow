"""Forms Field Catalog — P1.1 Registry public surface."""

from __future__ import annotations

from backend.app.forms_platform.field_catalog.models import ComponentRecord
from backend.app.forms_platform.field_catalog.registry import (
    CATALOG_REGISTRY_CONTRACT,
    FieldCatalogRegistry,
    platform_registry,
    register_components,
    reset_platform_registry,
)
from backend.app.forms_platform.field_catalog.versioning import (
    ComponentSemver,
    compare_versions,
    is_compatible,
    parse_component_version,
)

__all__ = [
    "CATALOG_REGISTRY_CONTRACT",
    "ComponentRecord",
    "ComponentSemver",
    "FieldCatalogRegistry",
    "compare_versions",
    "is_compatible",
    "parse_component_version",
    "platform_registry",
    "register_components",
    "reset_platform_registry",
]
