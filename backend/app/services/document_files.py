from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from backend.app.models.document import Document
from backend.app.modules.documents.storage import (
    file_entry_media_type,
    get_uploads_root,
    resolve_file_path,
    select_file_entry,
)


def _normalize_storage_path(value: str) -> str:
    rel = value.strip().lstrip("/\\")
    if rel.startswith("uploads/"):
        rel = rel[len("uploads/") :]
    return rel


def _as_entries(raw: Any) -> Sequence[Dict[str, Any]]:
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    return []


def resolve_document_file(
    doc: Document,
    *,
    version: Optional[int] = None,
) -> Tuple[Path, str, str]:
    """
    Returns (path, media_type, filename) for the latest file attached to the document.
    Raises FileNotFoundError if nothing is stored.
    """
    entries = _as_entries(getattr(doc, "files", None))
    entry = select_file_entry(entries, version=version) if entries else None
    if entry:
        file_path = resolve_file_path(entry)
        media_type = file_entry_media_type(entry)
        filename = entry.get("name") or getattr(doc, "filename", None) or file_path.name
        return file_path, media_type, filename

    raw_path = getattr(doc, "path", None)
    if not raw_path:
        raise FileNotFoundError("Document does not have an associated file")

    rel = _normalize_storage_path(str(raw_path))
    uploads_root = get_uploads_root()
    candidate = (uploads_root / rel).resolve()
    if not candidate.exists():
        raise FileNotFoundError("Stored document file not found on disk")

    filename = getattr(doc, "filename", None) or candidate.name
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return candidate, media_type, filename


__all__ = ["resolve_document_file"]
