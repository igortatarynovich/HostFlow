"""Owner summary / checklist / pack / workflow facts for neighbour consumers."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "CandDoc": ("backend.app.api.v1.candidate_documents", "CandDoc"),
    "DOCUMENT_PACK_DEFINITIONS": (
        "backend.app.modules.documents.pack_definitions",
        "DOCUMENT_PACK_DEFINITIONS",
    ),
    "apply_template_to_candidate_impl": (
        "backend.app.api.v1.candidate_documents",
        "apply_template_to_candidate_impl",
    ),
    "compute_candidate_checklist": (
        "backend.app.modules.documents.rules_engine",
        "compute_candidate_checklist",
    ),
    "compute_owner_summary": ("backend.app.modules.documents.owner_summary", "compute_owner_summary"),
    "document_has_stored_file": ("backend.app.services.document_workflow", "document_has_stored_file"),
    "fetch_candidate_documents_summary_response": (
        "backend.app.modules.documents.router",
        "fetch_candidate_documents_summary_response",
    ),
    "required_codes_for_pack": (
        "backend.app.modules.documents.pack_definitions",
        "required_codes_for_pack",
    ),
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
