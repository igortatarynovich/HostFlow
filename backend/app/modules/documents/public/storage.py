"""Upload path helpers published as Documents storage facts (not Hub ORM)."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "get_uploads_root": ("backend.app.modules.documents.storage", "get_uploads_root"),
    "sanitize_filename": ("backend.app.modules.documents.storage", "sanitize_filename"),
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
