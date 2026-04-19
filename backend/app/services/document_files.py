from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from backend.app.core.object_storage import get_object_storage, normalize_key
from backend.app.models.document import Document
from backend.app.modules.documents.storage import (
    extract_storage_key,
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


@dataclass(frozen=True)
class DocumentFileRef:
    """Backend-agnostic handle to a stored document file.

    ``local_path`` is set when the active storage backend keeps the object on
    disk (FS backend). ``download_url`` is set when the backend exposes the
    file via a direct/presigned URL (S3 backend). Exactly one of the two is
    guaranteed to be non-None for an existing file — callers use whichever is
    appropriate for their HTTP response:

    *   ``local_path`` → ``FileResponse(path)``
    *   ``download_url`` → ``RedirectResponse(url=download_url)``
    """

    local_path: Optional[Path]
    download_url: Optional[str]
    media_type: str
    filename: str


def resolve_document_file(
    doc: Document,
    *,
    version: Optional[int] = None,
) -> Tuple[Path, str, str]:
    """Back-compat wrapper — returns ``(path, media_type, filename)``.

    Raises :class:`FileNotFoundError` when the file cannot be resolved **or**
    the active backend does not expose a local filesystem path. New callers
    should use :func:`resolve_document_file_ref` instead so they can emit a
    redirect on the S3 backend.
    """
    ref = resolve_document_file_ref(doc, version=version)
    if ref.local_path is None:
        raise FileNotFoundError(
            "Document file lives in remote object storage; "
            "use resolve_document_file_ref() and redirect to download_url."
        )
    return ref.local_path, ref.media_type, ref.filename


def resolve_document_file_ref(
    doc: Document,
    *,
    version: Optional[int] = None,
) -> DocumentFileRef:
    """Return a :class:`DocumentFileRef` for the latest/requested file.

    Works against both storage backends and raises :class:`FileNotFoundError`
    when nothing is stored or the entry points at a missing file.
    """
    entries = _as_entries(getattr(doc, "files", None))
    entry = select_file_entry(entries, version=version) if entries else None
    storage = get_object_storage()

    if entry:
        media_type = file_entry_media_type(entry)
        filename = entry.get("name") or getattr(doc, "filename", None) or "document"
        local = storage.local_path("")
        if local is not None:
            file_path = resolve_file_path(entry)
            if not file_path.exists():
                raise FileNotFoundError("Stored document file not found on disk")
            return DocumentFileRef(
                local_path=file_path,
                download_url=None,
                media_type=media_type,
                filename=filename or file_path.name,
            )
        # S3-backed — hand back a presigned URL.
        key = extract_storage_key(entry)
        if not key:
            raise FileNotFoundError("Document file entry is missing a storage key")
        try:
            url = storage.presigned_get_url(key)
        except Exception as exc:  # pragma: no cover - defensive
            raise FileNotFoundError(f"Failed to presign document file: {exc}") from exc
        return DocumentFileRef(
            local_path=None,
            download_url=url,
            media_type=media_type,
            filename=filename,
        )

    # Legacy fallback for documents that only carry `Document.path`.
    raw_path = getattr(doc, "path", None)
    if not raw_path:
        raise FileNotFoundError("Document does not have an associated file")

    rel = _normalize_storage_path(str(raw_path))
    local = storage.local_path("")
    if local is None:
        # S3 backend — treat `Document.path` as the storage key.
        key = normalize_key(rel)
        try:
            url = storage.presigned_get_url(key)
        except Exception as exc:  # pragma: no cover - defensive
            raise FileNotFoundError(f"Failed to presign document file: {exc}") from exc
        filename = getattr(doc, "filename", None) or Path(rel).name
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return DocumentFileRef(
            local_path=None,
            download_url=url,
            media_type=media_type,
            filename=filename,
        )

    uploads_root = get_uploads_root()
    candidate = (uploads_root / rel).resolve()
    if not candidate.exists():
        raise FileNotFoundError("Stored document file not found on disk")

    filename = getattr(doc, "filename", None) or candidate.name
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return DocumentFileRef(
        local_path=candidate,
        download_url=None,
        media_type=media_type,
        filename=filename,
    )


__all__ = ["DocumentFileRef", "resolve_document_file", "resolve_document_file_ref"]
