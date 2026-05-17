from __future__ import annotations

import json
import mimetypes
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, root_validator
from sqlalchemy import and_, or_, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx
from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.core.settings import settings
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.security.document_events import (
    emit_document_security_event_v1,
    url_looks_presigned,
)
from backend.app.security.event_taxonomy import (
    EVENT_DOCUMENT_FILE_DOWNLOADED,
    EVENT_DOCUMENT_SIGNED_URL_DENIED,
    EVENT_DOCUMENT_SIGNED_URL_GENERATED,
)
from backend.app.services.own_company_doc_scope import (
    documents_scope_clause,
    ensure_candidate_own_company_scope,
    ensure_document_own_company_matches,
    resolved_document_own_company_id,
)
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.services.extractors import auto_fill_from_file
from backend.app.services import billing_restrictions, candidate_notifications
from backend.app.services import candidate_telegram_notifications as candidate_tg_notifications
from backend.app.services import reminders as reminders_service
from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.services.handoff import (
    is_client_tenant,
    has_pending_handoff_for_client,
    client_has_accepted_handoff,
    can_client_edit,
)
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    is_recruitment_recruiter_write_locked_by_handoff,
)
from backend.app.services.audit import log_audit_event
from backend.app.services.document_catalog import (
    doc_type_requires_user_comment,
    get_doc_type_defaults,
    normalize_doc_type,
    normalize_kind,
    normalize_process_type,
    normalize_requested_from,
    normalize_status as normalize_status_enum,
    prepare_template_documents,
)
from backend.app.modules.documents import crud as documents_crud
from backend.app.services.document_files import (
    resolve_document_file,
    resolve_document_file_ref,
)
from backend.app.services.tenant_quota import (
    ensure_tenant_document_quota,
    ensure_tenant_storage_bytes_fits,
    sum_file_entries_bytes,
)
from backend.app.services.document_workflow import (
    WORKFLOW_DEFINITIONS,
    auto_status as compute_auto_status,
    default_workflow,
    normalize_workflow,
)
from backend.app.models.document_template import DocumentTemplate

try:
    from backend.app.models.document_type import DocumentType  # type: ignore
except Exception:  # pragma: no cover
    DocumentType = None  # type: ignore

router = APIRouter(prefix="/candidates", tags=["candidate-documents"])
DOCUMENT_ROLES = (Role.manager, Role.admin, Role.recruiter, Role.compliance_officer)
DOCUMENT_MUTATE_ROLES = (*DOCUMENT_ROLES, Role.client_manager, Role.client_processor)

STATUSES = {status.value for status in DocumentStatus}

@router.get("/document-types")
async def list_document_types(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    """Return available document types. Falls back to an empty list if the model is absent."""
    db, tenant_id = db_tenant
    if DocumentType is None:
        return []
    rows = await documents_crud.list_document_types(db, str(tenant_id))
    result = []
    for r in rows:
        meta_schema = getattr(r, "metadata_schema", None) or {}
        required_files = getattr(r, "required_files", None) or {}
        expiry_rule = getattr(r, "expiry_rule", None) or {}
        duplicate_policy = getattr(r, "duplicate_policy", None)
        kind_value = (
            r.kind.value if isinstance(getattr(r, "kind", None), DocumentKind) else getattr(r, "kind", None)
        )
        requested_from_value = (
            r.requested_from.value
            if isinstance(getattr(r, "requested_from", None), DocumentRequestedFrom)
            else getattr(r, "requested_from", None)
        )
        process_type_value = (
            r.process_type.value if isinstance(getattr(r, "process_type", None), DocumentProcessType) else getattr(r, "process_type", None)
        )
        result.append(
            {
                "id": getattr(r, "id", None),
                "code": getattr(r, "code", None) or getattr(r, "key", None),
                "key": getattr(r, "code", None) or getattr(r, "key", None),
                "name": getattr(r, "name", None),
                "title": getattr(r, "title", None) or {},
                "description": getattr(r, "description", None),
                "kind": kind_value,
                "requested_from": requested_from_value,
                "process_type": process_type_value,
                "default_expire_in_days": getattr(r, "default_expire_in_days", None),
                "valid_days": getattr(r, "default_expire_in_days", None),
                "aliases": list(getattr(r, "aliases", []) or []),
                "required_meta": list(getattr(r, "required_meta", []) or []),
                "owner_summary_weight": int(getattr(r, "owner_summary_weight", 0) or 0),
                "i18n_key": getattr(r, "i18n_key", None),
                "requires_custom_name": bool(getattr(r, "requires_custom_name", False)),
                "is_active": bool(getattr(r, "is_active", True)),
                "required": bool(getattr(r, "is_active", True)),
                "meta_schema": meta_schema,
                "metadata_schema": meta_schema,
                "required_files": required_files,
                "expiry_rule": expiry_rule,
                "duplicate_policy": duplicate_policy.value if hasattr(duplicate_policy, "value") else duplicate_policy,
                "orderable": bool(getattr(r, "orderable", False)),
            }
        )
    return result


# ----- time/json helpers -----
def _utc_naive() -> datetime:
    return datetime.utcnow().replace(tzinfo=None)


def _utc_aware() -> datetime:
    return datetime.now(timezone.utc)


def _load_extra(s: Optional[str]) -> Dict[str, Any]:
    if not s:
        return {}
    try:
        j = json.loads(s)
        return j if isinstance(j, dict) else {}
    except Exception:
        return {}


def _normalize_status(value: Optional[str]) -> str:
    try:
        return normalize_status_enum(value).value
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status")


def _kind_or_422(value: Optional[str], fallback: DocumentKind) -> DocumentKind:
    try:
        return normalize_kind(value, fallback)
    except ValueError as exc:  # pragma: no cover - validation path
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _requested_from_or_422(
    value: Optional[str], fallback: DocumentRequestedFrom
) -> DocumentRequestedFrom:
    try:
        return normalize_requested_from(value, fallback)
    except ValueError as exc:  # pragma: no cover - validation path
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _to_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _process_type_or_422(
    value: Optional[str], fallback: DocumentProcessType
) -> DocumentProcessType:
    try:
        return normalize_process_type(value, fallback)
    except ValueError as exc:  # pragma: no cover - validation path
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _coerce_kind(value: Any) -> DocumentKind:
    if isinstance(value, DocumentKind):
        return value
    if value:
        try:
            return DocumentKind(str(value))
        except ValueError:
            return DocumentKind.driver
    return DocumentKind.driver


def _coerce_requested_from(value: Any) -> DocumentRequestedFrom:
    if isinstance(value, DocumentRequestedFrom):
        return value
    if value:
        try:
            return DocumentRequestedFrom(str(value))
        except ValueError:
            return DocumentRequestedFrom.driver
    return DocumentRequestedFrom.driver


def _coerce_process_type(value: Any) -> DocumentProcessType:
    if isinstance(value, DocumentProcessType):
        return value
    if value:
        try:
            return DocumentProcessType(str(value))
        except ValueError:
            return DocumentProcessType.none
    return DocumentProcessType.none


def _coerce_status(value: Any) -> DocumentStatus:
    try:
        return normalize_status_enum(value)
    except ValueError:
        return DocumentStatus.missing


def _dict_files_to_list(data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not data or not isinstance(data, dict):
        return []
    out: List[Dict[str, Any]] = []
    for key, value in data.items():
        if isinstance(value, dict):
            entry = {"name": key}
            entry.update({k: v for k, v in value.items() if v is not None})
            out.append(entry)
        else:
            out.append({"name": key, "url": value})
    return out


def _normalize_user_comment(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    comment = value.strip()
    return comment or None


def _extract_user_comment(
    explicit: Optional[str],
    meta_payload: Dict[str, Any],
    *,
    fallback: Optional[str] = None,
) -> Optional[str]:
    if explicit is not None:
        comment = _normalize_user_comment(explicit)
        if comment is not None:
            return comment
        return None
    meta_value = meta_payload.get("user_comment")
    if isinstance(meta_value, str):
        comment = _normalize_user_comment(meta_value)
        if comment is not None:
            return comment
    return fallback


def _ensure_comment_requirement(doc_type: str, comment: Optional[str]) -> None:
    if doc_type_requires_user_comment(doc_type) and not comment:
        raise HTTPException(
            status_code=422,
            detail="user_comment required for doc_type 'additional_document'",
        )


# ---- uploads root ----
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_UPLOAD_ROOT = os.environ.get("UPLOADS_DIR") or os.path.join(_BACKEND_ROOT, "uploads")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _public_url(rel_path: str) -> str:
    rel = (rel_path or "").lstrip("/\\")
    return f"/uploads/{rel.replace(os.sep, '/')}"


def _candidate_document_download_url(candidate_id: str, document_id: str) -> str:
    return f"/api/v1/candidates/{candidate_id}/documents/{document_id}/file"



def _days_left(d: Optional[date]) -> Optional[int]:
    if not d:
        return None
    return (d - date.today()).days


# --- helper: recalc candidate.docs_progress ---
async def _recalc_docs_progress(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    own_company_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Recalculate and persist candidate.docs_progress based on rows in documents.

    This path updates only ``Candidate.docs_progress`` and ``updated_at`` (no
    ``stage`` / ``status``). It is intentionally **not** blocked by the agency
    recruitment handoff lock: it mirrors document state for UI/analytics while
    document mutations themselves remain guarded by ``_check_document_edit_permission``.

    Document rows are scoped with ``resolved_document_own_company_id`` so the
    aggregate matches per-own-company document visibility (same as upload paths).
    """
    cand = (
        await db.execute(
            select(Candidate).where(
                Candidate.id == str(candidate_id),
                Candidate.tenant_id == str(tenant_id),
                Candidate.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if cand is None:
        return {"total": 0, "uploaded": 0, "ready": 0, "submitted": 0, "planned": 0}

    effective_own = resolved_document_own_company_id(cand, own_company_id)
    base = and_(
        Document.tenant_id == str(tenant_id),
        Document.candidate_id == str(candidate_id),
        Document.deleted_at.is_(None),
    )
    scope = documents_scope_clause(effective_own)
    if scope is not None:
        stmt = select(Document).join(Candidate, Candidate.id == Document.candidate_id).where(and_(base, scope))
    else:
        stmt = select(Document).where(base)
    rows = (await db.execute(stmt)).scalars().all()

    total = len(rows)
    uploaded = 0
    ready = 0
    submitted = 0
    planned = 0

    for r in rows:
        status_value = getattr(r, "status", None)
        if not status_value:
            ex = r.extra if isinstance(r.extra, dict) else _load_extra(r.extra)
            status_value = ex.get("status") if isinstance(ex, dict) else None
        status_enum = _coerce_status(status_value)
        status = status_enum.value

        files_list = []
        if isinstance(getattr(r, "files", None), list):
            files_list = [f for f in getattr(r, "files") if isinstance(f, dict)]

        has_file = False
        if r.path and str(r.path).strip():
            has_file = True
        elif files_list:
            has_file = any(str(f.get("url") or "").strip() for f in files_list)
        else:
            ex = r.extra if isinstance(r.extra, dict) else _load_extra(r.extra)
            files_data = ex.get("files") if isinstance(ex, dict) else None
            if isinstance(files_data, dict):
                has_file = any(str(v).strip() for v in files_data.values())

        if has_file:
            uploaded += 1
        if status_enum == DocumentStatus.approved:
            ready += 1
        if status_enum == DocumentStatus.in_progress:
            submitted += 1
        if status_enum == DocumentStatus.missing:
            planned += 1

    payload = {
        "total": total,
        "uploaded": uploaded,
        "ready": ready,
        "submitted": submitted,
        "planned": planned,
    }

    # Persist to Candidate.docs_progress (stored as JSON/text)
    await db.execute(
        update(Candidate)
        .where(Candidate.id == str(candidate_id))
        .values(docs_progress=json.dumps(payload, ensure_ascii=False), updated_at=_utc_naive())
    )
    await db.commit()
    return payload


async def _get_candidate_or_404(
    db: AsyncSession, candidate_id: UUID, tenant_id_hint: Optional[UUID]
) -> Candidate:
    if tenant_id_hint:
        row = await db.execute(
            select(Candidate).where(
                Candidate.id == str(candidate_id),
                Candidate.tenant_id == str(tenant_id_hint),
                Candidate.deleted_at.is_(None),
            )
        )
        cand = row.scalar_one_or_none()
        if cand:
            return cand
    row2 = await db.execute(
        select(Candidate).where(
            Candidate.id == str(candidate_id),
            Candidate.deleted_at.is_(None),
        )
    )
    cand2 = row2.scalar_one_or_none()
    if cand2:
        return cand2
    raise HTTPException(status_code=404, detail="Candidate not found")


# --------- схемы ---------
class CandDoc(BaseModel):
    id: str
    candidate_id: str
    key: str
    doc_type: str
    custom_name: Optional[str] = None
    title: Optional[str] = None
    kind: str
    requested_from: str
    process_type: str
    status: str = DocumentStatus.missing.value
    number: Optional[str] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    note: Optional[str] = None
    user_comment: Optional[str] = None
    files: Dict[str, Any] = Field(default_factory=dict)
    file_list: List[Dict[str, Any]] = Field(default_factory=list)
    filename: Optional[str] = None
    file_url: Optional[str] = None
    workflow: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
    days_left: Optional[int] = None

    @classmethod
    def from_document(cls, d: Document, *, hr_workforce_view: bool = False) -> "CandDoc":
        meta = d.meta if isinstance(d.meta, dict) else _load_extra(getattr(d, "meta", None))
        files_list = getattr(d, "files", None) or []
        files_dict: Dict[str, Any] = {}
        if isinstance(meta, dict):
            raw_files = meta.get("files")
            if isinstance(raw_files, dict):
                files_dict = raw_files
        if not files_dict and isinstance(files_list, list):
            for idx, file_item in enumerate(files_list):
                if isinstance(file_item, dict):
                    name = str(file_item.get("name") or idx)
                    files_dict[name] = file_item

        status_value: str
        if isinstance(d.status, DocumentStatus):
            status_value = d.status.value
        else:
            status_value = _normalize_status(str(d.status) if d.status else None)

        primary_file = None
        if isinstance(files_list, list):
            primary_file = next(
                (f for f in files_list if isinstance(f, dict) and f.get("url")),
                None,
            )

        file_url: Optional[str] = None
        if isinstance(primary_file, dict):
            file_url = primary_file.get("url")
        elif getattr(d, "path", None):
            file_url = _public_url(d.path)

        if (
            not hr_workforce_view
            and getattr(d, "candidate_id", None)
            and getattr(d, "id", None)
        ):
            file_url = _candidate_document_download_url(str(d.candidate_id), str(d.id))
        elif hr_workforce_view:
            file_url = None

        issue_date = getattr(d, "issue_date", None)
        expire_date = getattr(d, "expire_date", None)
        custom_name = getattr(d, "custom_name", None)
        title = custom_name or (meta.get("title") if isinstance(meta, dict) else None) or d.doc_type
        note = meta.get("note") if isinstance(meta, dict) else None
        workflow = getattr(d, "workflow", None) or (meta.get("workflow") if isinstance(meta, dict) else None) or {}

        return cls(
            id=d.id,
            candidate_id=cast(str, d.candidate_id),
            key=d.doc_type,
            doc_type=d.doc_type,
            custom_name=custom_name,
            title=title,
            kind=d.kind.value if isinstance(d.kind, DocumentKind) else str(d.kind or DocumentKind.driver.value),
            requested_from=(
                d.requested_from.value
                if isinstance(d.requested_from, DocumentRequestedFrom)
                else str(d.requested_from or DocumentRequestedFrom.driver.value)
            ),
            process_type=(
                d.process_type.value
                if isinstance(d.process_type, DocumentProcessType)
                else str(d.process_type or DocumentProcessType.none.value)
            ),
            status=status_value,
            number=d.number or (meta.get("number") if isinstance(meta, dict) else None),
            issued_at=issue_date,
            expires_at=expire_date,
            note=note,
            user_comment=getattr(d, "user_comment", None) or (meta.get("user_comment") if isinstance(meta, dict) else None),
            files=files_dict or {},
            file_list=[fi for fi in files_list if isinstance(fi, dict)],
            filename=d.filename or (primary_file.get("name") if isinstance(primary_file, dict) else None),
            file_url=file_url,
            workflow=workflow if isinstance(workflow, dict) else {},
            meta=meta if isinstance(meta, dict) else {},
            days_left=_days_left(expire_date),
        )


class CandDocCreate(BaseModel):
    key: Optional[str] = None
    doc_type: Optional[str] = None
    title: Optional[str] = None
    custom_name: Optional[str] = None
    kind: Optional[str] = None
    requested_from: Optional[str] = None
    process_type: Optional[str] = None
    status: str = DocumentStatus.missing.value
    number: Optional[str] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    note: Optional[str] = None
    user_comment: Optional[str] = None
    files: Optional[Dict[str, Any]] = None
    workflow: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    override_reason: Optional[str] = Field(
        default=None,
        description="Privileged bypass when recruitment is handoff-locked (administrator/supervisor/superadmin).",
    )

    def normalized_status(self) -> str:
        return _normalize_status(self.status)


class CandDocUpdate(BaseModel):
    key: Optional[str] = None
    doc_type: Optional[str] = None
    title: Optional[str] = None
    custom_name: Optional[str] = None
    kind: Optional[str] = None
    requested_from: Optional[str] = None
    process_type: Optional[str] = None
    status: Optional[str] = None
    number: Optional[str] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    note: Optional[str] = None
    user_comment: Optional[str] = None
    files: Optional[Dict[str, Any]] = None
    workflow: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    override_reason: Optional[str] = Field(
        default=None,
        description="Privileged bypass when recruitment is handoff-locked (administrator/supervisor/superadmin).",
    )

    def normalized_status(self) -> Optional[str]:
        if self.status is None:
            return None
        return _normalize_status(self.status)


class ApplyTemplatePayload(BaseModel):
    template_id: Optional[UUID] = None
    template_code: Optional[str] = None
    override_reason: Optional[str] = Field(
        default=None,
        description="Privileged bypass when recruitment is handoff-locked (administrator/supervisor/superadmin).",
    )

    @root_validator(pre=True)
    def _ensure_identifier(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get("template_id") and not values.get("template_code"):
            raise ValueError("template_id or template_code required")
        return values


class AppliedTemplateResponse(BaseModel):
    template_id: str
    template_code: str
    template_name: str
    documents: List[CandDoc]


# --------- list ---------
@router.get(
    "/candidate/{candidate_id}/documents",
    response_model=List[CandDoc],
    dependencies=[Depends(require_roles(*DOCUMENT_ROLES))],
)
@router.get(
    "/{candidate_id}/documents",
    response_model=List[CandDoc],
    dependencies=[Depends(require_roles(*DOCUMENT_ROLES))],
)
async def list_candidate_documents(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    q: Optional[str] = Query(
        None, description="Поиск по ключу/названию/номеру/заметке"
    ),
    status: Optional[List[str]] = Query(None),
    expiring_in_days: Optional[int] = Query(None, ge=1, le=3650),
):
    db, tenant_id_hint = db_tenant
    tenant_id_str = str(tenant_id_hint)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    # Client in "base" view (accepted handoffs only): hide documents
    if await is_client_tenant(db, tenant_id_str):
        has_pending = await has_pending_handoff_for_client(db, str(candidate_id), tenant_id_str)
        if not has_pending and await client_has_accepted_handoff(db, str(candidate_id), tenant_id_str):
            return []

    cand = await _get_candidate_or_404(db, candidate_id, tenant_id_hint)
    # Align with documents module: pin scope to the candidate's workspace when set,
    # instead of 404 when active ``X-Own-Company-Id`` differs from ``Candidate.own_company_id``.
    effective_own = resolved_document_own_company_id(cand, own_company_id)
    tenant_for_docs = cand.tenant_id

    # Если документы принадлежат другому тенанту, временно меняем контекст RLS
    # чтобы получить доступ к документам кандидата через shared vacancy
    tenant_context_changed = False
    if str(tenant_for_docs) != str(tenant_id_hint):
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_for_docs)},
            )
            tenant_context_changed = True
        except Exception:
            # SQLite и другие диалекты не поддерживают set_config
            pass

    try:
        base_conds = and_(
            Document.tenant_id == str(tenant_for_docs),
            Document.owner_type == "candidate",  # type: ignore[attr-defined]
            Document.owner_id == str(candidate_id),  # type: ignore[attr-defined]
            Document.candidate_id == str(candidate_id),
            Document.deleted_at.is_(None),
        )
        scope = documents_scope_clause(effective_own)
        if scope is not None:
            stmt = (
                select(Document)
                .join(Candidate, Candidate.id == Document.candidate_id)
                .where(and_(base_conds, scope))
                .order_by(Document.created_at.desc())
            )
        else:
            stmt = select(Document).where(base_conds).order_by(Document.created_at.desc())

        rows = (await db.execute(stmt)).scalars().all()
    finally:
        # Восстанавливаем исходный контекст tenant_id
        if tenant_context_changed:
            try:
                await db.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                    {"tenant_id": str(tenant_id_hint)},
                )
            except Exception:
                pass
    items = [CandDoc.from_document(r) for r in rows]

    if q:
        ql = q.strip().lower()
        items = [
            it
            for it in items
            if any(
                ql in (val or "").lower()
                for val in (it.key, it.title, it.number, it.note, it.user_comment)
            )
        ]

    if status:
        st = set(s for s in status if s in STATUSES)
        if st:
            items = [it for it in items if it.status in st]

    if expiring_in_days:
        bound = date.today() + timedelta(days=int(expiring_in_days))
        items = [it for it in items if it.expires_at and it.expires_at <= bound]

    return items


async def _check_document_edit_permission(
    db: AsyncSession,
    tenant_id_str: str,
    candidate_id_str: str,
    is_client: bool,
    *,
    current_user: Optional[UserCtx] = None,
    override_reason: Optional[str] = None,
) -> Optional[dict[str, str]]:
    """Return lock-override audit context when privileged bypass is used; else None."""
    if is_client:
        if not await can_client_edit(db, candidate_id_str, tenant_id_str):
            raise HTTPException(status_code=403, detail="Cannot edit documents: no accepted handoff")
        return None
    locked, lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=tenant_id_str, candidate_id=candidate_id_str
    )
    if not locked:
        return None
    role_l = str(getattr(current_user, "role", "") or "").strip().lower() if current_user else ""
    or_s = str(override_reason or "").strip()
    if role_l in RECRUITMENT_LOCK_OVERRIDE_ROLES and or_s:
        return {"lock_reason": lock_reason or "handoff", "override_reason": or_s}
    raise HTTPException(
        status_code=403,
        detail=f"Recruitment locked ({lock_reason or 'handoff'}): cannot edit documents",
    )


async def _flush_recruitment_lock_override_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    lock_audit_ctx: Optional[dict[str, str]],
    current_user: UserCtx,
    operation: str,
    document_id: Optional[str] = None,
) -> None:
    """Log only after a successful mutation when recruitment lock was bypassed with override_reason."""
    if not lock_audit_ctx:
        return
    payload: Dict[str, Any] = {
        "operation": operation,
        "candidate_id": candidate_id,
        "lock_reason": lock_audit_ctx["lock_reason"],
        "override_reason": lock_audit_ctx["override_reason"],
        "actor_role": str(getattr(current_user, "role", "") or "").strip().lower(),
    }
    if document_id:
        payload["document_id"] = document_id
    try:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.recruitment_lock_write_override,
            entity_type=AuditEntityType.candidate,
            entity_id=candidate_id,
            actor_id=current_user.sub,
            payload=payload,
        )
        await db.commit()
    except Exception:
        await db.rollback()


def _doc_payload_override_reason(payload: Any) -> Optional[str]:
    """Same contract as candidate PATCH: top-level or inside ``meta``."""
    raw = getattr(payload, "override_reason", None)
    meta = getattr(payload, "meta", None) or {}
    if isinstance(meta, dict):
        raw = raw or meta.get("override_reason")
    s = str(raw or "").strip()
    return s or None


# --------- create ---------
@router.post(
    "/candidate/{candidate_id}/documents",
    response_model=CandDoc,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
@router.post(
    "/{candidate_id}/documents",
    response_model=CandDoc,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
async def create_candidate_document(
    candidate_id: UUID,
    payload: CandDocCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id_hint = db_tenant
    tenant_id_str = str(tenant_id_hint)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)
    cand = await _get_candidate_or_404(db, candidate_id, tenant_id_hint)
    ensure_candidate_own_company_scope(cand, own_company_id)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    or_reason = _doc_payload_override_reason(payload)
    lock_audit_ctx = await _check_document_edit_permission(
        db,
        tenant_id_str,
        str(candidate_id),
        client_tenant,
        current_user=current_user,
        override_reason=or_reason,
    )
    status = payload.normalized_status()
    effective_key = (payload.key or payload.doc_type or "").strip()
    if not effective_key:
        raise HTTPException(status_code=422, detail="Document key or doc_type required")

    defaults = get_doc_type_defaults(payload.doc_type or effective_key)
    kind = _kind_or_422(payload.kind, defaults.kind)
    requested_from = _requested_from_or_422(payload.requested_from, defaults.requested_from)
    process_type = _process_type_or_422(payload.process_type, defaults.process_type)
    doc_type = defaults.doc_type

    custom_name = payload.custom_name.strip() if payload.custom_name else None
    if defaults.requires_custom_name:
        custom_name = custom_name or (payload.title or "").strip()
        if not custom_name:
            raise HTTPException(status_code=422, detail="custom_name required for 'other' document")
        if payload.kind is None:
            raise HTTPException(status_code=422, detail="kind required for 'other' document")

    files_list = _dict_files_to_list(payload.files)
    meta_payload: Dict[str, Any] = dict(payload.meta or {})
    meta_payload.pop("override_reason", None)
    if payload.title:
        meta_payload["title"] = payload.title
    if payload.note:
        meta_payload["note"] = payload.note
    if payload.files:
        meta_payload["files"] = payload.files
    if payload.number:
        meta_payload.setdefault("number", payload.number)
    user_comment = _extract_user_comment(payload.user_comment, meta_payload)
    _ensure_comment_requirement(doc_type, user_comment)
    if user_comment:
        meta_payload["user_comment"] = user_comment
    else:
        meta_payload.pop("user_comment", None)
    meta_payload.setdefault("doc_type", doc_type)
    raw_reminder_days = meta_payload.pop("remind_days_before", None)
    try:
        reminder_days = int(raw_reminder_days) if raw_reminder_days is not None else 30
    except (TypeError, ValueError):
        reminder_days = 30

    normalized_workflow = normalize_workflow(process_type, payload.workflow)
    if normalized_workflow is None and process_type in WORKFLOW_DEFINITIONS:
        normalized_workflow = default_workflow(process_type)
    if normalized_workflow:
        meta_payload["workflow"] = normalized_workflow
    elif "workflow" in meta_payload:
        meta_payload.pop("workflow")

    status_enum = DocumentStatus(status)
    auto_status_value = compute_auto_status(
        status_enum,
        process_type=process_type,
        workflow=normalized_workflow,
        has_files=bool(files_list),
        expire_date=_to_date(payload.expires_at),
    )
    verified_at = _utc_aware() if auto_status_value == DocumentStatus.approved else None

    await documents_crud.ensure_document_type(db, str(cand.tenant_id), doc_type)
    doc_oc = resolved_document_own_company_id(cand, own_company_id)
    m = Document(
        id=str(uuid4()),
        tenant_id=str(cand.tenant_id),
        own_company_id=doc_oc,
        owner_type="candidate",
        owner_id=str(candidate_id),
        candidate_id=str(candidate_id),
        doc_type=doc_type,
        custom_name=custom_name,
        kind=kind,
        requested_from=requested_from,
        process_type=process_type,
        number=payload.number,
        filename=None,
        path=None,
        issue_date=payload.issued_at,
        expire_date=payload.expires_at,
        reminder_days_before=reminder_days,
        files=files_list or None,
        meta=meta_payload or None,
        user_comment=user_comment,
        workflow=normalized_workflow or None,
        status=auto_status_value,
        verified_at=verified_at,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    await reminders_service.schedule_document_expiry_reminders(
        db,
        tenant_id=str(cand.tenant_id),
        document=m,
    )
    if auto_status_value == DocumentStatus.requested:
        from backend.app.api.public.intake import _ensure_status_share_token

        _ensure_status_share_token(cand)
        base_url = (settings.frontend_url or "").strip().rstrip("/") or "https://hostflow.cc"
        status_token = getattr(cand, "status_share_token", None) or getattr(cand, "intake_token", None)
        status_url = f"{base_url}/public/status/{status_token}" if status_token else None
        await candidate_notifications.send_document_requested_email_to_candidate(
            db,
            tenant_id=str(cand.tenant_id),
            candidate=cand,
            doc_type=doc_type,
            status_url=status_url,
        )
    await db.commit()
    await _recalc_docs_progress(db, str(cand.tenant_id), str(candidate_id), own_company_id=own_company_id)
    await _flush_recruitment_lock_override_audit(
        db,
        tenant_id=str(cand.tenant_id),
        candidate_id=str(candidate_id),
        lock_audit_ctx=lock_audit_ctx,
        current_user=current_user,
        operation="document_create",
        document_id=str(m.id),
    )
    return CandDoc.from_document(m)


# --------- update ---------
@router.patch(
    "/candidate/{candidate_id}/documents/{doc_id}",
    response_model=CandDoc,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
@router.patch(
    "/{candidate_id}/documents/{doc_id}",
    response_model=CandDoc,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
async def update_candidate_document(
    candidate_id: UUID,
    doc_id: UUID,
    payload: CandDocUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id_hint = db_tenant
    tenant_id_str = str(tenant_id_hint)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)
    cand = await _get_candidate_or_404(db, candidate_id, tenant_id_hint)
    ensure_candidate_own_company_scope(cand, own_company_id)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    or_reason = _doc_payload_override_reason(payload)
    lock_audit_ctx = await _check_document_edit_permission(
        db,
        tenant_id_str,
        str(candidate_id),
        client_tenant,
        current_user=current_user,
        override_reason=or_reason,
    )

    row = await db.execute(
        select(Document).where(
            Document.id == str(doc_id),
            Document.candidate_id == str(candidate_id),
            Document.tenant_id == str(cand.tenant_id),
            Document.deleted_at.is_(None),
        )
    )
    m = row.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_document_own_company_matches(m, cand, own_company_id)

    meta_payload = dict(m.meta) if isinstance(m.meta, dict) else _load_extra(getattr(m, "meta", None))
    meta_payload.setdefault("doc_type", getattr(m, "doc_type", None))

    workflow_before = getattr(m, "workflow", None)
    process_type_before = m.process_type

    doc_type_input = payload.doc_type or payload.key
    if doc_type_input is not None:
        defaults = get_doc_type_defaults(doc_type_input)
        m.doc_type = defaults.doc_type
        await documents_crud.ensure_document_type(db, str(cand.tenant_id), defaults.doc_type)
        if payload.kind is None:
            m.kind = defaults.kind
        if payload.requested_from is None:
            m.requested_from = defaults.requested_from
        if payload.process_type is None:
            m.process_type = defaults.process_type
        meta_payload["doc_type"] = doc_type_input
    else:
        defaults = get_doc_type_defaults(m.doc_type)

    if payload.kind is not None:
        m.kind = _kind_or_422(payload.kind, defaults.kind)
    if payload.requested_from is not None:
        m.requested_from = _requested_from_or_422(payload.requested_from, defaults.requested_from)
    if payload.process_type is not None:
        m.process_type = _process_type_or_422(payload.process_type, defaults.process_type)

    if payload.custom_name is not None:
        custom_value = payload.custom_name.strip() if payload.custom_name else None
        requires_custom = get_doc_type_defaults(m.doc_type).requires_custom_name
        if requires_custom and not custom_value:
            raise HTTPException(status_code=422, detail="custom_name required for 'other' document")
        m.custom_name = custom_value
    elif doc_type_input is not None and get_doc_type_defaults(m.doc_type).requires_custom_name:
        fallback_name = m.custom_name or (payload.title or "").strip()
        if not fallback_name:
            raise HTTPException(status_code=422, detail="custom_name required for 'other' document")

    if payload.issued_at is not None:
        m.issue_date = payload.issued_at
    if payload.expires_at is not None:
        m.expire_date = payload.expires_at

    if payload.company_id is not None:
        m.company_id = str(payload.company_id) if payload.company_id else None
    if payload.owner_id is not None:
        m.owner_id = str(payload.owner_id) if payload.owner_id else None

    if payload.number is not None:
        m.number = payload.number
        meta_payload["number"] = payload.number
    if payload.note is not None:
        meta_payload["note"] = payload.note
    if payload.title is not None:
        meta_payload["title"] = payload.title
    if payload.files is not None:
        meta_payload["files"] = payload.files
        m.files = _dict_files_to_list(payload.files) or None
    if payload.workflow is not None:
        meta_payload["workflow"] = payload.workflow
    if payload.meta is not None:
        meta_payload.update(payload.meta)
    meta_payload.pop("override_reason", None)
    raw_reminder_days = meta_payload.pop("remind_days_before", None)
    if raw_reminder_days is not None:
        try:
            m.reminder_days_before = int(raw_reminder_days)
        except (TypeError, ValueError):
            pass

    user_comment = _extract_user_comment(
        payload.user_comment,
        meta_payload,
        fallback=getattr(m, "user_comment", None),
    )
    _ensure_comment_requirement(m.doc_type, user_comment)
    m.user_comment = user_comment
    if user_comment:
        meta_payload["user_comment"] = user_comment
    else:
        meta_payload.pop("user_comment", None)

    try:
        process_type_before_enum = (
            process_type_before if isinstance(process_type_before, DocumentProcessType) else DocumentProcessType(str(process_type_before))
        )
    except ValueError:
        process_type_before_enum = DocumentProcessType.none
    try:
        process_type_enum = (
            m.process_type if isinstance(m.process_type, DocumentProcessType) else DocumentProcessType(str(m.process_type))
        )
    except ValueError:
        process_type_enum = DocumentProcessType.none
    process_type_changed = process_type_before_enum != process_type_enum

    normalized_workflow = None
    if payload.workflow is not None:
        normalized_workflow = normalize_workflow(
            process_type_enum,
            payload.workflow,
            existing_workflow=workflow_before if not process_type_changed else None,
        )
        if normalized_workflow is None and process_type_enum in WORKFLOW_DEFINITIONS:
            normalized_workflow = default_workflow(process_type_enum)
    elif process_type_changed:
        normalized_workflow = normalize_workflow(process_type_enum, None, existing_workflow=None)
        if normalized_workflow is None and process_type_enum in WORKFLOW_DEFINITIONS:
            normalized_workflow = default_workflow(process_type_enum)
    elif workflow_before is not None:
        normalized_workflow = normalize_workflow(
            process_type_enum,
            workflow_before,
            existing_workflow=workflow_before,
        )

    if normalized_workflow is not None:
        m.workflow = normalized_workflow
    elif payload.workflow is not None or process_type_changed:
        m.workflow = None

    if m.workflow:
        meta_payload["workflow"] = m.workflow
    elif "workflow" in meta_payload:
        meta_payload.pop("workflow")

    has_files = bool(m.files)
    if payload.status is not None:
        status_value = DocumentStatus(payload.normalized_status())
    else:
        current_status = getattr(m, "status", None)
        if isinstance(current_status, DocumentStatus):
            status_value = current_status
        else:
            status_value = DocumentStatus(_normalize_status(str(current_status) if current_status else None))

    auto_status_value = compute_auto_status(
        status_value,
        process_type=process_type_enum,
        workflow=m.workflow,
        has_files=has_files,
        expire_date=_to_date(m.expire_date),
    )
    # Store old status for notification
    old_status = m.status
    
    if payload.status is not None and status_value in (DocumentStatus.rejected, DocumentStatus.expired):
        auto_status_value = status_value
    m.status = auto_status_value

    if payload.verified_at is not None:
        m.verified_at = payload.verified_at
    elif auto_status_value == DocumentStatus.approved and getattr(m, "verified_at", None) is None:
        m.verified_at = _utc_aware()
    
    # Send notification to candidate if status changed
    if old_status != auto_status_value and m.owner_id:
        try:
            from backend.app.api.public.notifications import send_candidate_notification
            from sqlalchemy import select
            cand_result = await db.execute(
                select(Candidate).where(Candidate.id == m.owner_id, Candidate.tenant_id == str(cand.tenant_id))
            )
            candidate = cand_result.scalar_one_or_none()
            if candidate:
                # Get status label
                status_label = (
                    auto_status_value.value if isinstance(auto_status_value, DocumentStatus) else str(auto_status_value)
                )
                old_status_label = (
                    old_status.value if isinstance(old_status, DocumentStatus) else str(old_status)
                )
                await send_candidate_notification(
                    db,
                    candidate,
                    "document.status_changed",
                    "Статус документа изменен",
                    f"Статус вашего документа '{m.doc_type}' изменен на '{status_label}'",
                    entity_type="document",
                    entity_id=str(m.id),
                    payload={
                        "document_type": m.doc_type,
                        "old_status": old_status_label,
                        "new_status": status_label,
                        "document_id": str(m.id),
                    },
                )
        except Exception:
            # Don't fail document update if notification fails
            pass

    if payload.source is not None:
        m.source = payload.source
    if payload.external_id is not None:
        m.external_id = payload.external_id

    m.meta = meta_payload if meta_payload else None
    m.updated_at = _utc_aware()

    if payload.files is None and hasattr(m, "files") and m.files is None and meta_payload.get("files"):
        m.files = _dict_files_to_list(meta_payload["files"]) or None

    await db.commit()
    await db.refresh(m)
    await reminders_service.schedule_document_expiry_reminders(
        db,
        tenant_id=str(cand.tenant_id),
        document=m,
    )
    await db.commit()
    try:
        old_status_value = old_status.value if isinstance(old_status, DocumentStatus) else str(old_status or "")
        new_status_value = auto_status_value.value if isinstance(auto_status_value, DocumentStatus) else str(auto_status_value or "")
        if old_status_value != new_status_value:
            await candidate_tg_notifications.send_candidate_document_status_changed_telegram(
                db,
                tenant_id=str(cand.tenant_id),
                candidate=cand,
                document_type=str(getattr(m, "doc_type", "") or ""),
                old_status=old_status_value,
                new_status=new_status_value,
            )
    except Exception:
        pass
    await _recalc_docs_progress(db, str(cand.tenant_id), str(candidate_id), own_company_id=own_company_id)
    await _flush_recruitment_lock_override_audit(
        db,
        tenant_id=str(cand.tenant_id),
        candidate_id=str(candidate_id),
        lock_audit_ctx=lock_audit_ctx,
        current_user=current_user,
        operation="document_update",
        document_id=str(m.id),
    )
    return CandDoc.from_document(m)


async def apply_template_to_candidate_impl(
    db: AsyncSession,
    tenant_id_str: str,
    candidate_id_str: str,
    *,
    template_id: Optional[str] = None,
    template_code: Optional[str] = None,
    own_company_id: Optional[str] = None,
) -> Optional[AppliedTemplateResponse]:
    """Apply a document template to a candidate. No permission checks. Returns None if candidate or template not found."""
    if not template_id and not template_code:
        return None
    cand_row = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id_str,
            Candidate.tenant_id == tenant_id_str,
            Candidate.deleted_at.is_(None),
        )
    )
    cand = cand_row.scalar_one_or_none()
    if not cand:
        return None
    ensure_candidate_own_company_scope(cand, own_company_id)

    template_query = select(DocumentTemplate).where(DocumentTemplate.tenant_id == tenant_id_str)
    if template_id:
        template_query = template_query.where(DocumentTemplate.id == template_id)
    if template_code:
        template_query = template_query.where(DocumentTemplate.code == template_code)
    template_query = template_query.where(DocumentTemplate.is_active.is_(True)).limit(1)
    template = (await db.execute(template_query)).scalar_one_or_none()
    if not template:
        return None

    template_docs = prepare_template_documents(template.documents or [])
    keep_types = {entry["doc_type"] for entry in template_docs}

    base_existing = and_(
        Document.candidate_id == candidate_id_str,
        Document.tenant_id == str(cand.tenant_id),
        Document.deleted_at.is_(None),
    )
    scope = documents_scope_clause(own_company_id)
    if scope is not None:
        existing_rows = await db.execute(
            select(Document)
            .join(Candidate, Candidate.id == Document.candidate_id)
            .where(and_(base_existing, scope))
        )
    else:
        existing_rows = await db.execute(select(Document).where(base_existing))
    existing_docs = list(existing_rows.scalars())
    existing_by_type: Dict[str, Document] = {}
    for doc in existing_docs:
        existing_by_type.setdefault(doc.doc_type, doc)

    now = _utc_aware()
    touched_docs: List[Document] = []
    for entry in template_docs:
        doc_type = entry["doc_type"]
        defaults = get_doc_type_defaults(doc_type)
        kind = DocumentKind(entry["kind"])
        requested_from = DocumentRequestedFrom(entry["requested_from"])
        process_type = DocumentProcessType(entry["process_type"])
        await documents_crud.ensure_document_type(db, str(cand.tenant_id), defaults.doc_type)
        meta_defaults = dict(entry.get("meta") or {})
        remind_days = entry.get("remind_days_before")
        if remind_days is not None:
            try:
                remind_days = int(remind_days)
            except (TypeError, ValueError):
                remind_days = None

        if defaults.requires_custom_name and not meta_defaults.get("custom_name"):
            meta_defaults.setdefault("custom_name", meta_defaults.get("title"))

        existing = existing_by_type.get(doc_type)
        if existing:
            ro = resolved_document_own_company_id(cand, own_company_id)
            if not str(getattr(existing, "own_company_id", None) or "").strip() and ro:
                existing.own_company_id = ro
            existing.kind = kind
            existing.requested_from = requested_from
            existing.process_type = process_type
            if defaults.requires_custom_name:
                custom_name = meta_defaults.get("custom_name") or meta_defaults.get("title")
                if custom_name:
                    existing.custom_name = custom_name
            else:
                existing.custom_name = None

            current_meta = dict(existing.meta or {})
            current_meta["template_code"] = template.code
            current_meta["template_id"] = template.id
            for key, value in meta_defaults.items():
                current_meta.setdefault(key, value)
            existing.meta = current_meta
            if existing.workflow is None and process_type in WORKFLOW_DEFINITIONS:
                existing.workflow = default_workflow(process_type)

            if remind_days is not None:
                existing.reminder_days_before = remind_days

            status_enum = _coerce_status(existing.status)
            existing.status = compute_auto_status(
                status_enum,
                process_type=process_type,
                workflow=existing.workflow,
                has_files=bool(existing.files),
                expire_date=_to_date(existing.expire_date),
            )

            existing.updated_at = now
            touched_docs.append(existing)
        else:
            custom_name = meta_defaults.get("custom_name") if defaults.requires_custom_name else None
            if defaults.requires_custom_name and not custom_name:
                custom_name = meta_defaults.get("title") or "Other document"

            doc_meta = dict(meta_defaults)
            doc_meta["template_code"] = template.code
            doc_meta["template_id"] = template.id
            doc_meta.setdefault("doc_type", doc_type)

            reminder_days_before = remind_days if remind_days is not None else 30
            workflow_default = default_workflow(process_type) if process_type in WORKFLOW_DEFINITIONS else None
            initial_status = compute_auto_status(
                DocumentStatus.missing,
                process_type=process_type,
                workflow=workflow_default,
                has_files=False,
                expire_date=None,
            )

            await documents_crud.ensure_document_type(db, str(cand.tenant_id), doc_type)
            doc_oc = resolved_document_own_company_id(cand, own_company_id)
            new_doc = Document(
                id=str(uuid4()),
                tenant_id=str(cand.tenant_id),
                own_company_id=doc_oc,
                owner_type="candidate",
                owner_id=candidate_id_str,
                candidate_id=candidate_id_str,
                doc_type=doc_type,
                custom_name=custom_name if defaults.requires_custom_name else None,
                kind=kind,
                requested_from=requested_from,
                process_type=process_type,
                status=initial_status,
                reminder_days_before=reminder_days_before,
                meta=doc_meta,
                files=[],
                workflow=workflow_default,
            )
            db.add(new_doc)
            touched_docs.append(new_doc)

    # Soft-delete or reset documents not in template (except custom "other" docs)
    for doc in existing_docs:
        if doc.doc_type in keep_types or doc.doc_type == "other" or doc.deleted_at is not None:
            continue
        status_enum = _coerce_status(doc.status)
        if status_enum in (DocumentStatus.missing, DocumentStatus.requested) and not (doc.files or doc.path):
            doc.deleted_at = now
            doc.updated_at = now

    await db.flush()
    for doc in touched_docs:
        await reminders_service.schedule_document_expiry_reminders(
            db,
            tenant_id=str(cand.tenant_id),
            document=doc,
        )

    await db.commit()

    base_ref = and_(
        Document.candidate_id == candidate_id_str,
        Document.tenant_id == str(cand.tenant_id),
        Document.deleted_at.is_(None),
    )
    if scope is not None:
        refreshed_rows = await db.execute(
            select(Document)
            .join(Candidate, Candidate.id == Document.candidate_id)
            .where(and_(base_ref, scope))
        )
    else:
        refreshed_rows = await db.execute(select(Document).where(base_ref))
    refreshed_docs = [CandDoc.from_document(doc) for doc in refreshed_rows.scalars()]

    await _recalc_docs_progress(db, str(cand.tenant_id), candidate_id_str, own_company_id=own_company_id)

    return AppliedTemplateResponse(
        template_id=template.id,
        template_code=template.code,
        template_name=template.name,
        documents=refreshed_docs,
    )


@router.post(
    "/candidate/{candidate_id}/documents/apply-template",
    response_model=AppliedTemplateResponse,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
@router.post(
    "/{candidate_id}/documents/apply-template",
    response_model=AppliedTemplateResponse,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
async def apply_document_template(
    candidate_id: UUID,
    payload: ApplyTemplatePayload,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id_hint = db_tenant
    tenant_id_str = str(tenant_id_hint)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    or_reason = _doc_payload_override_reason(payload)
    lock_audit_ctx = await _check_document_edit_permission(
        db,
        tenant_id_str,
        str(candidate_id),
        client_tenant,
        current_user=current_user,
        override_reason=or_reason,
    )

    result = await apply_template_to_candidate_impl(
        db,
        tenant_id_str,
        str(candidate_id),
        template_id=str(payload.template_id) if payload.template_id else None,
        template_code=payload.template_code,
        own_company_id=own_company_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Document template not found")
    await _flush_recruitment_lock_override_audit(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        lock_audit_ctx=lock_audit_ctx,
        current_user=current_user,
        operation="document_apply_template",
        document_id=None,
    )
    return result

# --------- delete ---------
@router.delete(
    "/candidate/{candidate_id}/documents/{doc_id}",
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
@router.delete(
    "/{candidate_id}/documents/{doc_id}",
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
async def delete_candidate_document(
    candidate_id: UUID,
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    override_reason: Optional[str] = Query(
        None,
        description="Privileged bypass when recruitment is handoff-locked (administrator/supervisor/superadmin).",
    ),
):
    db, tenant_id_hint = db_tenant
    tenant_id_str = str(tenant_id_hint)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)
    cand = await _get_candidate_or_404(db, candidate_id, tenant_id_hint)
    ensure_candidate_own_company_scope(cand, own_company_id)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    lock_audit_ctx = await _check_document_edit_permission(
        db,
        tenant_id_str,
        str(candidate_id),
        client_tenant,
        current_user=current_user,
        override_reason=override_reason,
    )

    row = await db.execute(
        select(Document).where(
            Document.id == str(doc_id),
            Document.candidate_id == str(candidate_id),
            Document.tenant_id == str(cand.tenant_id),
            Document.deleted_at.is_(None),
        )
    )
    m = row.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_document_own_company_matches(m, cand, own_company_id)

    await db.execute(
        update(Document)
        .where(Document.id == m.id)
        .values(deleted_at=_utc_aware(), updated_at=_utc_aware())
    )
    await reminders_service.cancel_entity_reminders(
        db,
        tenant_id=str(cand.tenant_id),
        entity_type="document",
        entity_id=str(doc_id),
    )
    await db.commit()
    await _recalc_docs_progress(db, str(cand.tenant_id), str(candidate_id), own_company_id=own_company_id)
    await _flush_recruitment_lock_override_audit(
        db,
        tenant_id=str(cand.tenant_id),
        candidate_id=str(candidate_id),
        lock_audit_ctx=lock_audit_ctx,
        current_user=current_user,
        operation="document_delete",
        document_id=str(doc_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------- upload ---------
@router.post(
    "/candidate/{candidate_id}/documents/upload",
    response_model=CandDoc,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
@router.post(
    "/{candidate_id}/documents/upload",
    response_model=CandDoc,
    dependencies=[Depends(require_roles(*DOCUMENT_MUTATE_ROLES))],
)
async def upload_candidate_document(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    file: UploadFile = File(...),
    key: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    status: str = Form(DocumentStatus.received.value),
    note: Optional[str] = Form(None),
    user_comment: Optional[str] = Form(None),
    override_reason: Optional[str] = Form(
        None,
        description="Privileged bypass when recruitment is handoff-locked (administrator/supervisor/superadmin).",
    ),
):
    if status not in STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    status_normalized = _normalize_status(status)

    db, tenant_id_hint = db_tenant
    tenant_id_str = str(tenant_id_hint)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)
    cand = await _get_candidate_or_404(db, candidate_id, tenant_id_hint)
    ensure_candidate_own_company_scope(cand, own_company_id)

    client_tenant = await is_client_tenant(db, tenant_id_str)
    lock_audit_ctx = await _check_document_edit_permission(
        db,
        tenant_id_str,
        str(candidate_id),
        client_tenant,
        current_user=current_user,
        override_reason=override_reason,
    )

    # 1) файл — пишем через абстракцию object storage (FS или S3/MinIO).
    # Ключ формируется по тому же шаблону, что и раньше, чтобы существующие
    # Document.files[].storage_path не сломались при переезде между бэкендами.
    from backend.app.core.object_storage import get_object_storage, normalize_key

    rel_dir = f"{cand.tenant_id}/candidates/{candidate_id}"
    safe_name = f"{uuid.uuid4().hex}_{(file.filename or 'document').replace('/', '_')}"
    rel_path = normalize_key(f"{rel_dir}/{safe_name}")

    storage = get_object_storage()

    async def _chunks():
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            yield chunk

    saved = await storage.save_stream(
        rel_path,
        _chunks(),
        content_type=file.content_type,
    )
    upload_size = saved.size

    # 2) автоизвлечение — требует локального пути. На FS-бэкенде используем
    #    реальный файл; на S3 автоизвлечение временно отключено (TODO: скачивать
    #    во временный файл до расширенного поддерживаемого пайплайна).
    local_abs = storage.local_path(rel_path)
    if local_abs is not None:
        guessed = auto_fill_from_file(str(local_abs), hinted_key=key)
    else:
        guessed = {}
    g_key = (key or guessed.get("key") or "document").strip()
    g_number = guessed.get("number")
    g_issued = guessed.get("issued_at")
    g_expires = guessed.get("expires_at")

    def _parse(d: Optional[str]) -> Optional[date]:
        if not d:
            return None
        try:
            return date.fromisoformat(d[:10])
        except Exception:
            return None

    # 3) запись
    defaults = get_doc_type_defaults(g_key)
    kind = defaults.kind
    requested_from = defaults.requested_from
    process_type = defaults.process_type
    doc_type = defaults.doc_type

    custom_name = None
    resolved_title = title or guessed.get("title") or (file.filename or g_key)
    if doc_type == "other":
        custom_name = resolved_title

    meta_payload: Dict[str, Any] = {
        "title": resolved_title,
        "number": g_number,
        "note": note,
        "source": "upload",
    }
    normalized_comment = _normalize_user_comment(user_comment)
    _ensure_comment_requirement(doc_type, normalized_comment)
    if normalized_comment:
        meta_payload["user_comment"] = normalized_comment
    meta_payload["doc_type"] = doc_type
    doc_id = str(uuid4())
    download_url = _candidate_document_download_url(str(candidate_id), doc_id)
    files_list = [
        {
            "name": file.filename or safe_name,
            "url": download_url,
            "uploaded_at": datetime.utcnow().isoformat(),
            "source": "upload",
            "storage_path": rel_path.replace("\\", "/"),
            "version": 1,
            "size": upload_size,
            "mime": file.content_type or mimetypes.guess_type(file.filename or safe_name)[0],
            "user_comment": normalized_comment,
        }
    ]
    meta_payload["files"] = {
        "primary": {
            "url": download_url,
            "name": file.filename or safe_name,
            "storage_path": rel_path.replace("\\", "/"),
            "version": 1,
            "mime": file.content_type or mimetypes.guess_type(file.filename or safe_name)[0],
            "uploaded_at": files_list[0]["uploaded_at"],
            "user_comment": normalized_comment,
        }
    }

    await documents_crud.ensure_document_type(db, str(cand.tenant_id), doc_type)
    await ensure_tenant_document_quota(db, tenant_id_str)
    await ensure_tenant_storage_bytes_fits(
        db,
        tenant_id_str,
        previous_doc_attribution_bytes=0,
        next_doc_attribution_bytes=sum_file_entries_bytes(files_list),
    )
    doc_oc = resolved_document_own_company_id(cand, own_company_id)
    obj = Document(
        id=doc_id,
        tenant_id=str(cand.tenant_id),
        own_company_id=doc_oc,
        owner_type="candidate",
        owner_id=str(candidate_id),
        candidate_id=str(candidate_id),
        doc_type=doc_type,
        custom_name=custom_name,
        kind=kind,
        requested_from=requested_from,
        process_type=process_type,
        number=g_number,
        filename=file.filename,
        path=rel_path,
        issue_date=_parse(g_issued),
        expire_date=_parse(g_expires),
        reminder_days_before=60,
        files=files_list,
        meta=meta_payload,
        user_comment=normalized_comment,
        status=DocumentStatus(status_normalized),
        workflow=None,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    await reminders_service.schedule_document_expiry_reminders(
        db,
        tenant_id=str(cand.tenant_id),
        document=obj,
    )
    await db.commit()
    await _recalc_docs_progress(db, str(cand.tenant_id), str(candidate_id), own_company_id=own_company_id)

    await _flush_recruitment_lock_override_audit(
        db,
        tenant_id=str(cand.tenant_id),
        candidate_id=str(candidate_id),
        lock_audit_ctx=lock_audit_ctx,
        current_user=current_user,
        operation="document_upload",
        document_id=str(obj.id),
    )

    return CandDoc.from_document(obj)


# --------- прямой доступ к файлу ---------
@router.get(
    "/candidate/{candidate_id}/documents/{doc_id}/file",
    dependencies=[Depends(require_roles(*DOCUMENT_ROLES))],
)
@router.get(
    "/{candidate_id}/documents/{doc_id}/file",
    dependencies=[Depends(require_roles(*DOCUMENT_ROLES))],
)
async def get_candidate_document_file(
    candidate_id: UUID,
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id_hint = db_tenant
    access_kind = str(db.info.get("security_access_kind") or "").strip() or None
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    await ensure_candidate_access(db, str(tenant_id_hint), str(candidate_id), current_user)
    cand = await _get_candidate_or_404(db, candidate_id, tenant_id_hint)
    ensure_candidate_own_company_scope(cand, own_company_id)
    tenant_for_docs = cand.tenant_id

    # Если документы принадлежат другому тенанту, временно меняем контекст RLS
    tenant_context_changed = False
    if str(tenant_for_docs) != str(tenant_id_hint):
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_for_docs)},
            )
            tenant_context_changed = True
        except Exception:
            pass

    try:
        row = await db.execute(
            select(Document).where(
                Document.id == str(doc_id),
                Document.candidate_id == str(candidate_id),
                Document.tenant_id == str(tenant_for_docs),
                Document.deleted_at.is_(None),
            )
        )
        m = row.scalar_one_or_none()
    finally:
        # Восстанавливаем исходный контекст tenant_id
        if tenant_context_changed:
            try:
                await db.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                    {"tenant_id": str(tenant_id_hint)},
                )
            except Exception:
                pass

    if not m or not m.path:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:candidate_documents:get_file",
            tenant_id=str(tenant_for_docs),
            document_id=str(doc_id),
            access_kind=access_kind,
            actor_id=actor_id,
            candidate_id=str(candidate_id),
            reason="document_or_file_missing",
        )
        raise HTTPException(status_code=404, detail="File not found")
    ensure_document_own_company_matches(m, cand, own_company_id)

    try:
        ref = resolve_document_file_ref(m)
    except FileNotFoundError:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:candidate_documents:get_file",
            tenant_id=str(tenant_for_docs),
            document_id=str(doc_id),
            access_kind=access_kind,
            actor_id=actor_id,
            document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
            candidate_id=str(candidate_id),
            reason="file_not_found",
        )
        raise HTTPException(status_code=404, detail="File not found") from None

    if ref.download_url:
        from fastapi.responses import RedirectResponse

        presigned = url_looks_presigned(ref.download_url)
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
            result="success",
            severity="info",
            source="http:candidate_documents:get_file",
            tenant_id=str(tenant_for_docs),
            document_id=str(doc_id),
            access_kind=access_kind,
            actor_id=actor_id,
            document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
            candidate_id=str(candidate_id),
            has_presigned_url_shape=presigned,
            response_mode="redirect_302",
        )
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_FILE_DOWNLOADED,
            result="success",
            severity="info",
            source="http:candidate_documents:get_file",
            tenant_id=str(tenant_for_docs),
            document_id=str(doc_id),
            access_kind=access_kind,
            actor_id=actor_id,
            document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
            candidate_id=str(candidate_id),
            response_mode="redirect_302",
            has_presigned_url_shape=presigned,
        )
        return RedirectResponse(url=ref.download_url, status_code=302)

    assert ref.local_path is not None  # guarded by resolve_document_file_ref
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_FILE_DOWNLOADED,
        result="success",
        severity="info",
        source="http:candidate_documents:get_file",
        tenant_id=str(tenant_for_docs),
        document_id=str(doc_id),
        access_kind=access_kind,
        actor_id=actor_id,
        document_class=str(m.doc_type) if getattr(m, "doc_type", None) else None,
        candidate_id=str(candidate_id),
        response_mode="file_stream",
    )
    return FileResponse(
        str(ref.local_path),
        media_type=ref.media_type or "application/octet-stream",
        filename=ref.filename,
    )
