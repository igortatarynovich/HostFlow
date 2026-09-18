"""Document type / canonical reference facts (not lifecycle verdicts)."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "DOCUMENT_TYPE_DEFINITIONS": ("backend.app.document_types.definitions", "DOCUMENT_TYPE_DEFINITIONS"),
    "DocumentTypeRuntimeResolver": (
        "backend.app.services.document_type_runtime_resolver",
        "DocumentTypeRuntimeResolver",
    ),
    "DocumentTypeVersionAssignmentResolver": (
        "backend.app.services.document_type_version_assignment_resolver",
        "DocumentTypeVersionAssignmentResolver",
    ),
    "VersionAssignmentStatus": (
        "backend.app.services.document_type_version_assignment_resolver",
        "VersionAssignmentStatus",
    ),
    "canonical_codes": ("backend.app.document_types.registry", "canonical_codes"),
    "document_storage_type_matches": (
        "backend.app.services.document_type_canonical_bridge",
        "document_storage_type_matches",
    ),
    "get_doc_type_defaults": ("backend.app.services.document_catalog", "get_doc_type_defaults"),
    "get_driver_ce_schema_bundle": ("backend.app.document_types.schema_registry", "get_driver_ce_schema_bundle"),
    "hub_storage_keys_for_requirement_code": (
        "backend.app.services.document_type_canonical_bridge",
        "hub_storage_keys_for_requirement_code",
    ),
    "is_canonical_code": ("backend.app.document_types.registry", "is_canonical_code"),
    "is_runtime_alias": ("backend.app.document_types.registry", "is_runtime_alias"),
    "load_legacy_aliases_payload": ("backend.app.document_types.registry", "load_legacy_aliases_payload"),
    "normalize_input_doc_type": ("backend.app.document_types.registry", "normalize_input_doc_type"),
    "normalize_doc_type": ("backend.app.services.document_catalog", "normalize_doc_type"),
    "normalize_raw_to_document_data": (
        "backend.app.document_types.schema_registry",
        "normalize_raw_to_document_data",
    ),
    "registry_entries": ("backend.app.document_types.registry", "registry_entries"),
    "registry_entry_for": ("backend.app.document_types.registry", "registry_entry_for"),
    "validate_document_data": ("backend.app.document_types.schema_registry", "validate_document_data"),
}

__all__ = sorted(_SOURCE)


def __getattr__(name: str) -> Any:
    if name not in _SOURCE:
        raise AttributeError(name)
    import importlib

    mod_name, attr = _SOURCE[name]
    return getattr(importlib.import_module(mod_name), attr)


def __dir__() -> list[str]:
    return list(__all__)
