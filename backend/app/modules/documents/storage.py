from __future__ import annotations

import json
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_maker
from ...models.document import Document
from ...models.enums import DocumentProcessType, DocumentStatus
from backend.app.services.document_catalog import normalize_process_type, normalize_status
from backend.app.services.document_workflow import auto_status as compute_auto_status
from backend.app.modules.documents.crud import _as_date

_HERE = Path(__file__).resolve()
_BACKEND_ROOT = _HERE.parents[3]
_DEFAULT_UPLOAD_ROOT = _BACKEND_ROOT / "uploads"
_UPLOADS_PREFIX = "/uploads/"


def get_uploads_root() -> Path:
    root = os.environ.get("UPLOAD_DIR")
    if root:
        try:
            return Path(root).resolve()
        except Exception:
            pass
    return _DEFAULT_UPLOAD_ROOT.resolve()


def sanitize_filename(name: Optional[str]) -> str:
    if not name:
        return "document"
    base, ext = os.path.splitext(name)
    base = base.strip()
    base = re.sub(r"[^\w.\-]+", "-", base, flags=re.UNICODE)
    base = base.strip("-_.")
    if not base:
        base = "document"
    ext = ext.lower()
    return f"{base}{ext}"


def _normalize_files(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        result: List[Dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                result.append(dict(item))
        return result
    return []


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(value).astimezone(timezone.utc)
        except Exception:
            return None
    return None


def _isoformat(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _assign_versions(files: List[Dict[str, Any]]) -> None:
    decorated: List[Tuple[datetime, int, Dict[str, Any]]] = []
    for idx, entry in enumerate(files):
        ts = _parse_timestamp(entry.get("uploaded_at"))
        if ts is None:
            ts = datetime.min.replace(tzinfo=timezone.utc)
        decorated.append((ts, idx, entry))
    decorated.sort(key=lambda item: (item[0], item[1]))
    for version, (_, _, entry) in enumerate(decorated, start=1):
        entry["version"] = version
    files.sort(key=lambda item: item.get("version", 0))


def _build_public_url(rel_path: str) -> str:
    clean = rel_path.replace("\\", "/").lstrip("/")
    return f"{_UPLOADS_PREFIX}{clean}"


def _build_entry(
    rel_path: str,
    *,
    original_name: Optional[str],
    size: int,
    mime: Optional[str],
    uploaded_by: Optional[str],
    version: int,
    timestamp: datetime,
) -> Dict[str, Any]:
    storage_path = rel_path.replace("\\", "/").lstrip("/")
    url = _build_public_url(storage_path)
    guessed_mime = mime or mimetypes.guess_type(original_name or storage_path)[0]
    entry: Dict[str, Any] = {
        "name": original_name or Path(storage_path).name,
        "url": url,
        "size": size,
        "mime": guessed_mime or "application/octet-stream",
        "uploaded_at": _isoformat(timestamp),
        "uploaded_by": uploaded_by,
        "version": version,
        "storage_path": storage_path,
    }
    return entry


def _normalize_extra(raw: Any) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
        if isinstance(parsed, list):
            return {"history": parsed}
        return {}
    if isinstance(raw, list):
        # legacy records stored the history array directly
        return {"history": raw}
    return {}


async def register_document_upload(
    document_id: str,
    rel_path: str,
    *,
    original_name: Optional[str],
    size: int,
    mime: Optional[str],
    uploaded_by: Optional[str],
) -> Optional[Dict[str, Any]]:
    rel_path = rel_path.replace("\\", "/").lstrip("/")
    try:
        UUID(document_id)
    except Exception:
        return None

    timestamp = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        doc = await session.get(Document, document_id)
        if not doc:
            return None

        files = _normalize_files(doc.files)
        _assign_versions(files)
        next_version = (max((int(f.get("version", 0)) for f in files), default=0) + 1)
        entry = _build_entry(
            rel_path,
            original_name=original_name or Path(rel_path).name,
            size=size,
            mime=mime,
            uploaded_by=uploaded_by,
            version=next_version,
            timestamp=timestamp,
        )

        files = [f for f in files if f.get("url") != entry["url"]]
        files.append(entry)
        _assign_versions(files)

        doc.files = files
        doc.filename = entry.get("name")
        doc.path = entry.get("url")

        extra = _normalize_extra(doc.extra)
        raw_history = extra.get("history")
        if isinstance(raw_history, list):
            history = [
                dict(item) if isinstance(item, dict) else item for item in raw_history
            ]
        else:
            history = []
        action = "upload" if len(files) == 1 else "replace"
        history.append(
            {
                "action": action,
                "version": entry.get("version"),
                "file": entry.get("name"),
                "url": entry.get("url"),
                "size": entry.get("size"),
                "mime": entry.get("mime"),
                "timestamp": entry.get("uploaded_at"),
                "uploaded_by": uploaded_by,
            }
        )
        extra["history"] = history
        doc.extra = extra

        process_type = (
            doc.process_type
            if isinstance(doc.process_type, DocumentProcessType)
            else normalize_process_type(doc.process_type, DocumentProcessType.none)
        )
        current_status = (
            doc.status
            if isinstance(doc.status, DocumentStatus)
            else normalize_status(doc.status)
        )
        doc.status = compute_auto_status(
            current_status,
            process_type=process_type,
            workflow=doc.workflow,
            has_files=True,
            expire_date=_as_date(doc.expire_date),
        )
        if doc.status == DocumentStatus.approved and getattr(doc, "verified_at", None) is None:
            doc.verified_at = timestamp

        doc.updated_at = timestamp
        doc.version = (int(getattr(doc, "version", 0)) + 1)

        session.add(doc)
        await session.commit()
        return entry


async def ensure_document_files(session: AsyncSession, doc: Document) -> List[Dict[str, Any]]:
    files = _normalize_files(doc.files)
    root = get_uploads_root()
    doc_dir = root / "documents" / str(doc.id)
    changed = False
    existing_urls = {f.get("url") for f in files if isinstance(f, dict)}

    if doc_dir.is_dir():
        for path in sorted(p for p in doc_dir.iterdir() if p.is_file()):
            storage_path = path.relative_to(root).as_posix()
            url = _build_public_url(storage_path)
            if url in existing_urls:
                continue
            stat = path.stat()
            timestamp = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            entry = _build_entry(
                storage_path,
                original_name=path.name,
                size=stat.st_size,
                mime=mimetypes.guess_type(path.name)[0],
                uploaded_by=None,
                version=0,
                timestamp=timestamp,
            )
            files.append(entry)
            existing_urls.add(url)
            changed = True

    valid_entries: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url or url in seen_urls:
            continue
        try:
            candidate = resolve_file_path(entry)
        except ValueError:
            changed = True
            continue
        if not candidate.exists():
            changed = True
            continue
        valid_entries.append(dict(entry))
        seen_urls.add(url)

    files = valid_entries

    _assign_versions(files)

    if files:
        latest = files[-1]
        if doc.filename != latest.get("name"):
            doc.filename = latest.get("name")
            changed = True
        if doc.path != latest.get("url"):
            doc.path = latest.get("url")
            changed = True

    extra = _normalize_extra(doc.extra)
    raw_history = extra.get("history")
    if isinstance(raw_history, list):
        history = [
            dict(item) if isinstance(item, dict) else item for item in raw_history
        ]
    else:
        history = []
    known_history_urls = {
        item.get("url") for item in history if isinstance(item, dict)
    }
    for entry in files:
        url = entry.get("url")
        if url and url not in known_history_urls:
            history.append(
                {
                    "action": "imported",
                    "version": entry.get("version"),
                    "file": entry.get("name"),
                    "url": url,
                    "size": entry.get("size"),
                    "mime": entry.get("mime"),
                    "timestamp": entry.get("uploaded_at"),
                    "uploaded_by": entry.get("uploaded_by"),
                }
            )
            known_history_urls.add(url)
            changed = True
    extra["history"] = history

    if changed:
        doc.files = files
        doc.extra = extra
        doc.updated_at = datetime.now(timezone.utc)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
    else:
        doc.files = files
        doc.extra = extra

    return files


def select_file_entry(
    files: Sequence[Dict[str, Any]],
    *,
    version: Optional[int] = None,
    name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not files:
        return None
    candidates: List[Dict[str, Any]] = [f for f in files if isinstance(f, dict)]
    if version is not None:
        for entry in candidates:
            if entry.get("version") == version:
                return entry
    if name:
        for entry in reversed(candidates):
            if entry.get("name") == name:
                return entry
    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            item.get("version", 0),
            item.get("uploaded_at") or "",
        ),
    )
    return sorted_candidates[-1] if sorted_candidates else None


def resolve_file_path(entry: Dict[str, Any]) -> Path:
    root = get_uploads_root()
    storage_path = entry.get("storage_path")
    if storage_path:
        candidate = root / storage_path
    else:
        url = (entry.get("url") or "").lstrip()
        if not url.startswith(_UPLOADS_PREFIX):
            raise ValueError("Document file entry does not contain a valid url")
        relative = url[len(_UPLOADS_PREFIX) :].lstrip("/")
        candidate = root / relative
    resolved = candidate.resolve()
    uploads_root = root.resolve()
    if uploads_root not in resolved.parents and resolved != uploads_root:
        raise ValueError("Resolved document path escapes uploads root")
    return resolved


def file_entry_media_type(entry: Dict[str, Any]) -> str:
    mime = entry.get("mime")
    if mime:
        return mime
    url = entry.get("url")
    if isinstance(url, str):
        mime_guess = mimetypes.guess_type(url)[0]
        if mime_guess:
            return mime_guess
    return "application/octet-stream"


__all__ = [
    "ensure_document_files",
    "file_entry_media_type",
    "register_document_upload",
    "resolve_file_path",
    "sanitize_filename",
    "select_file_entry",
]
