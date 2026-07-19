"""Forms Field Catalog — P1.1–P1.4 public surface."""

from __future__ import annotations

from backend.app.forms_platform.field_catalog.descriptors import (
    DESCRIPTOR_CONTRACT,
    DESCRIPTOR_KINDS,
    ComponentDescriptor,
    ComponentDescriptors,
    parse_descriptor,
    parse_descriptors,
)
from backend.app.forms_platform.field_catalog.extensions import (
    BASIC_COMPONENT_IDS,
    EXTENSION_CONTRACT,
    ExtensionRegistrationFailure,
    ModuleRegistrationResult,
    assert_not_basic_override,
    get_component_source,
    list_catalog_for_builder,
    register_extension_component,
    register_module_components,
)
from backend.app.forms_platform.field_catalog.models import (
    SOURCE_PLATFORM,
    ComponentRecord,
    build_component_record,
    module_source,
    parse_source,
)
from backend.app.forms_platform.field_catalog.registry import (
    CATALOG_REGISTRY_CONTRACT,
    FieldCatalogRegistry,
    platform_registry,
    register_components,
    reset_platform_registry,
)
from backend.app.forms_platform.field_catalog.stdlib import (
    STANDARD_COMPONENT_IDS,
    STDLIB_COMPONENT_VERSION,
    STDLIB_CONTRACT,
    bootstrap_platform_standard_library,
    iter_standard_library_records,
    register_standard_library,
    standard_library_component_ids,
)
from backend.app.forms_platform.field_catalog.versioning import (
    ComponentSemver,
    compare_versions,
    is_compatible,
    parse_component_version,
)

__all__ = [
    "BASIC_COMPONENT_IDS",
    "CATALOG_REGISTRY_CONTRACT",
    "DESCRIPTOR_CONTRACT",
    "DESCRIPTOR_KINDS",
    "EXTENSION_CONTRACT",
    "SOURCE_PLATFORM",
    "STANDARD_COMPONENT_IDS",
    "STDLIB_COMPONENT_VERSION",
    "STDLIB_CONTRACT",
    "ComponentDescriptor",
    "ComponentDescriptors",
    "ComponentRecord",
    "ComponentSemver",
    "ExtensionRegistrationFailure",
    "FieldCatalogRegistry",
    "ModuleRegistrationResult",
    "assert_not_basic_override",
    "bootstrap_platform_standard_library",
    "build_component_record",
    "compare_versions",
    "get_component_source",
    "is_compatible",
    "iter_standard_library_records",
    "list_catalog_for_builder",
    "module_source",
    "parse_component_version",
    "parse_descriptor",
    "parse_descriptors",
    "parse_source",
    "platform_registry",
    "register_components",
    "register_extension_component",
    "register_module_components",
    "register_standard_library",
    "reset_platform_registry",
    "standard_library_component_ids",
]
