"""Candidate document list / check facts (not Hub storage layout)."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "create_document_check": ("backend.app.modules.documents.crud", "create_document_check"),
    "get_last_document_checks_map": ("backend.app.modules.documents.crud", "get_last_document_checks_map"),
    "list_candidate_documents": ("backend.app.modules.documents.crud", "list_candidate_documents"),
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
