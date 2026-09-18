"""Open/stream document file facts for Workforce / HR approval surfaces."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "build_workforce_cand_doc": (
        "backend.app.modules.documents.document_open_service",
        "build_workforce_cand_doc",
    ),
    "enrich_documents_for_approval_open_urls": (
        "backend.app.modules.documents.document_open_service",
        "enrich_documents_for_approval_open_urls",
    ),
    "stream_workforce_employee_document_file": (
        "backend.app.modules.documents.document_open_service",
        "stream_workforce_employee_document_file",
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
