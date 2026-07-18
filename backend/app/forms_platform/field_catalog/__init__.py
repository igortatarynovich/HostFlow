"""Forms Field Catalog — P1.1 Registry + P1.2 Descriptors public surface."""

from __future__ import annotations

from backend.app.forms_platform.field_catalog.descriptors import (
    DESCRIPTOR_CONTRACT,
    DESCRIPTOR_KINDS,
    ComponentDescriptor,
    ComponentDescriptors,
    parse_descriptor,
    parse_descriptors,
)
from backend.app.forms_platform.field_catalog.models import (
    ComponentRecord,
    build_component_record,
)
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
    "DESCRIPTOR_CONTRACT",
    "DESCRIPTOR_KINDS",
    "ComponentDescriptor",
    "ComponentDescriptors",
    "ComponentRecord",
    "ComponentSemver",
    "FieldCatalogRegistry",
    "build_component_record",
    "compare_versions",
    "is_compatible",
    "parse_component_version",
    "parse_descriptor",
    "parse_descriptors",
    "platform_registry",
    "register_components",
    "reset_platform_registry",
]
