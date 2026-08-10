from __future__ import annotations

import enum
import logging
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from pydantic import AliasChoices, ConfigDict  # type: ignore
    PYDANTIC_V2 = True
except Exception:  # pragma: no cover - pydantic<2 fallback
    AliasChoices = None  # type: ignore[assignment]
    ConfigDict = None  # type: ignore[assignment]
    PYDANTIC_V2 = False
    from pydantic import root_validator  # type: ignore
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.core.settings import settings
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.document_template import DocumentTemplate
from backend.app.models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.services.document_catalog import (
    doc_type_requires_user_comment,
    get_doc_type_defaults,
    normalize_doc_type,
    normalize_kind,
    normalize_process_type,
    normalize_requested_from,
    normalize_status,
    prepare_template_documents,
)
from backend.app.services.document_orders import (
    ORDERABLE_CODES,
    default_order_date,
    find_documents_by_type,
    missing_base_requirements,
)
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.services.document_workflow import (
    WORKFLOW_DEFINITIONS,
    auto_status as compute_auto_status,
    default_workflow,
    normalize_workflow,
    STATUS_ORDER,
)
from backend.app.observability.metrics import refresh_documents_overdue_metrics
from backend.app.services import candidate_notifications
from backend.app.services import candidate_telegram_notifications as candidate_tg_notifications
from backend.app.services import reminders as reminders_service
from backend.app.services.audit import log_activity
from backend.app.modules.documents import crud as documents_crud
from backend.app.services.tenant_quota import (
    ensure_tenant_document_quota,
    ensure_tenant_storage_bytes_fits,
    sum_file_entries_bytes,
)

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger("backend.app.api.documents")


def _resolved_document_own_company_id(cand: Candidate, active_own_company_id: Optional[str]) -> Optional[str]:
    c = str(getattr(cand, "own_company_id", None) or "").strip()
    if c:
        return c
    a = str(active_own_company_id or "").strip()
    return a or None


def _ensure_candidate_own_company_scope(cand: Candidate, own_company_id: Optional[str]) -> None:
    if not own_company_id:
        return
    c = str(getattr(cand, "own_company_id", None) or "").strip()
    if c and c != str(own_company_id).strip():
        raise HTTPException(status_code=404, detail="Candidate not found")


def _documents_scope_clause(own_company_id: Optional[str]):
    if not own_company_id:
        return None
    oc = str(own_company_id).strip()
    return or_(
        Document.own_company_id == oc,
        and_(Document.own_company_id.is_(None), Candidate.own_company_id == oc),
        and_(Document.own_company_id.is_(None), Candidate.own_company_id.is_(None)),
    )


def _ensure_document_own_company_matches(
    doc: Document,
    cand: Candidate,
    active_own_company_id: Optional[str],
) -> None:
    if not active_own_company_id:
        return
    oc = str(active_own_company_id).strip()
    doc_oc = str(getattr(doc, "own_company_id", None) or "").strip()
    cand_oc = str(getattr(cand, "own_company_id", None) or "").strip()
    effective = doc_oc or cand_oc
    if not effective:
        return
    if effective != oc:
        raise HTTPException(status_code=404, detail="Document not found")


async def _candidate_for_document_scope(
    db: AsyncSession, tenant_id: UUID, candidate_id: str
) -> Optional[Candidate]:
    return await db.scalar(
        select(Candidate).where(
            Candidate.id == str(candidate_id),
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
        )
    )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


READY_STATUSES = {
    DocumentStatus.received.value,
    DocumentStatus.delivered.value,
    DocumentStatus.approved.value,
    DocumentStatus.completed.value,
}
PROBLEM_STATUSES = {
    DocumentStatus.rejected.value,
    DocumentStatus.expired.value,
    DocumentStatus.overdue.value,
}
IN_PROGRESS_STATUSES = {
    DocumentStatus.in_progress.value,
    DocumentStatus.submitted.value,
}


def _normalize_user_comment(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    comment = value.strip()
    return comment or None


def _ensure_user_comment_requirement(doc_type: str, comment: Optional[str]) -> None:
    if doc_type_requires_user_comment(doc_type) and not comment:
        raise HTTPException(
            status_code=422,
            detail="user_comment required for doc_type 'additional_document'",
        )


def _extract_first(values: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for key in keys:
        if key in values:
            return values[key]
    return None


ALIAS_MAP_IN = {
    "doc_type": ("doc_type", "type", "key"),
    "issue_date": ("issue_date", "issued_at"),
    "expire_date": ("expire_date", "expires_at"),
    "valid_from": ("valid_from", "effective_from", "effective_date"),
    "meta": ("meta", "extra", "meta_json"),
}

ALIAS_MAP_PATCH = {
    "doc_type": ("doc_type", "type", "key"),
    "issue_date": ("issue_date", "issued_at"),
    "expire_date": ("expire_date", "expires_at"),
    "valid_from": ("valid_from", "effective_from", "effective_date"),
    "meta": ("meta", "extra", "meta_json"),
}


if PYDANTIC_V2:

    class DocumentFile(BaseModel):
        model_config = ConfigDict(extra="ignore")

        name: str
        url: Optional[str] = None
        size: Optional[int] = None
        mime: Optional[str] = None
        uploaded_at: Optional[datetime] = None
        uploaded_by: Optional[str] = None
        version: Optional[int] = None
        user_comment: Optional[str] = None


    class DocumentIn(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        candidate_id: UUID
        doc_type: str = Field(
            ..., min_length=1, validation_alias=AliasChoices("doc_type", "type", "key")
        )
        kind: Optional[str] = None
        custom_name: Optional[str] = None
        status: Optional[str] = DocumentStatus.missing.value
        issue_date: Optional[date] = Field(
            default=None, validation_alias=AliasChoices("issue_date", "issued_at")
        )
        expire_date: Optional[date] = Field(
            default=None, validation_alias=AliasChoices("expire_date", "expires_at")
        )
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = Field(
            default=None, validation_alias=AliasChoices("valid_from", "effective_from", "effective_date")
        )
        reminder_days_before: int = 30
        company_id: Optional[UUID] = None
        owner_id: Optional[UUID] = None
        requested_from: Optional[str] = None
        process_type: Optional[str] = None
        workflow: Optional[Dict[str, Any]] = Field(default=None)
        files: List["DocumentFile"] = Field(default_factory=list)
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        meta: Dict[str, Any] = Field(
            default_factory=dict, validation_alias=AliasChoices("meta", "extra", "meta_json")
        )
        number: Optional[str] = None
        user_comment: Optional[str] = None


    class DocumentOut(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        id: str
        tenant_id: str
        candidate_id: str
        company_id: Optional[str] = None
        kind: str
        doc_type: str
        type: str
        type_code: str
        custom_name: Optional[str] = None
        owner_type: str
        owner_id: Optional[str] = None
        requested_from: str
        process_type: str
        number: Optional[str] = None
        status: str
        reminder_days_before: int
        files: List[DocumentFile] = Field(default_factory=list)
        workflow: Dict[str, Any] = Field(default_factory=dict)
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        issue_date: Optional[date] = None
        expire_date: Optional[date] = None
        issued_at: Optional[date] = None
        expires_at: Optional[date] = None
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = None
        user_comment: Optional[str] = None
        has_files: bool = False
        readiness_state: str = Field(default="pending")
        status_rank: int = 0
        extra: Dict[str, Any]
        meta: Dict[str, Any]
        meta_json: Dict[str, Any]
        created_at: datetime
        updated_at: datetime

else:

    class DocumentFile(BaseModel):
        class Config:
            extra = "ignore"

        name: str
        url: Optional[str] = None
        size: Optional[int] = None
        mime: Optional[str] = None
        uploaded_at: Optional[datetime] = None
        uploaded_by: Optional[str] = None
        version: Optional[int] = None
        user_comment: Optional[str] = None


    class DocumentIn(BaseModel):
        class Config:
            allow_population_by_field_name = True

        candidate_id: UUID
        doc_type: str = Field(..., min_length=1)
        kind: Optional[str] = None
        custom_name: Optional[str] = None
        status: Optional[str] = DocumentStatus.missing.value
        issue_date: Optional[date] = Field(default=None)
        expire_date: Optional[date] = Field(default=None)
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = Field(default=None)
        reminder_days_before: int = 30
        company_id: Optional[UUID] = None
        owner_id: Optional[UUID] = None
        requested_from: Optional[str] = None
        process_type: Optional[str] = None
        workflow: Optional[Dict[str, Any]] = Field(default=None)
        files: List["DocumentFile"] = Field(default_factory=list)
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        meta: Dict[str, Any] = Field(default_factory=dict)
        number: Optional[str] = None
        user_comment: Optional[str] = None

        @root_validator(pre=True)
        def _apply_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
            data = dict(values or {})
            for target, aliases in ALIAS_MAP_IN.items():
                if target in data and data[target] is not None:
                    continue
                alias_value = _extract_first(data, aliases)
                if alias_value is not None:
                    data.setdefault(target, alias_value)
            return data


    class DocumentOut(BaseModel):
        class Config:
            allow_population_by_field_name = True

        id: str
        tenant_id: str
        candidate_id: str
        company_id: Optional[str] = None
        kind: str
        doc_type: str
        type: str
        type_code: str
        custom_name: Optional[str] = None
        owner_type: str
        owner_id: Optional[str] = None
        requested_from: str
        process_type: str
        number: Optional[str] = None
        status: str
        reminder_days_before: int
        files: List["DocumentFile"] = Field(default_factory=list)
        workflow: Dict[str, Any] = Field(default_factory=dict)
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        issue_date: Optional[date] = None
        expire_date: Optional[date] = None
        issued_at: Optional[date] = None
        expires_at: Optional[date] = None
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = None
        user_comment: Optional[str] = None
        has_files: bool = False
        readiness_state: str = Field(default="pending")
        status_rank: int = 0
        extra: Dict[str, Any]
        meta: Dict[str, Any]
        meta_json: Dict[str, Any]
        created_at: datetime
        updated_at: datetime
    process_type: str
    number: Optional[str] = None
    status: str
    reminder_days_before: int
    files: List[DocumentFile] = Field(default_factory=list)
    workflow: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    external_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    issue_date: Optional[date] = None
    expire_date: Optional[date] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    ordered_at: Optional[date] = None
    valid_from: Optional[date] = None
    has_files: bool = False
    readiness_state: str = Field(default="pending")
    status_rank: int = 0
    extra: Dict[str, Any]
    meta: Dict[str, Any]
    meta_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TemplateDocument(BaseModel):
    doc_type: str
    kind: str
    requested_from: str
    process_type: str
    required: bool = True
    meta: Dict[str, Any] = Field(default_factory=dict)
    remind_days_before: Optional[int] = None


class DocumentTemplateOut(BaseModel):
    id: str
    code: str
    name: str
    is_active: bool
    created_by: Optional[str] = None
    documents: List[TemplateDocument]
    created_at: datetime
    updated_at: datetime


class DocumentOrderPayload(BaseModel):
    candidate_id: UUID
    doc_type: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("doc_type", "type", "key") if PYDANTIC_V2 else None,
    )
    ordered_at: Optional[date] = None
    requested_from: Optional[date] = None
    owner_context: Optional[Dict[str, Any]] = None

    if not PYDANTIC_V2:

        @root_validator(pre=True)
        def _assign_doc_type(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[misc]
            data = dict(values or {})
            selected = data.get("doc_type")
            if not selected:
                for alias in ("type", "key"):
                    alias_value = data.get(alias)
                    if alias_value:
                        data["doc_type"] = alias_value
                        break
            return data


def _parse_meta(raw: Any) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, (str, bytes, bytearray)):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return dict(parsed)
        except Exception:
            return {}
    return {}


def _enum_to_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return value.value
    return str(value)


def _status_rank(status_value: str) -> int:
    try:
        enum_value = DocumentStatus(status_value)
    except ValueError:
        return STATUS_ORDER.get(DocumentStatus.requested, 1)
    return STATUS_ORDER.get(enum_value, 0)


def _readiness_state(
    status_value: str,
    *,
    ordered_at: Optional[date],
    has_files: bool,
) -> str:
    status_lower = status_value.lower()
    if status_lower in READY_STATUSES:
        return "ready"
    if status_lower in PROBLEM_STATUSES:
        return "problem"
    if status_lower in IN_PROGRESS_STATUSES:
        return "in_progress"
    if has_files:
        return "awaiting_review"
    if ordered_at:
        return "ordered"
    if status_lower == DocumentStatus.requested.value:
        return "requested"
    return "pending"


def _owner_context_from_payload(
    raw_ctx: Optional[Dict[str, Any]],
    candidate_id: UUID,
) -> Dict[str, Any]:
    if raw_ctx is None:
        return {"candidate_id": str(candidate_id)}
    if not isinstance(raw_ctx, dict):
        raise HTTPException(status_code=422, detail="owner_context must be an object")
    ctx = dict(raw_ctx)
    ctx.setdefault("candidate_id", str(candidate_id))
    return ctx


def _has_requested_from_metadata(documents: Iterable[Document]) -> bool:
    for doc in documents:
        meta = getattr(doc, "meta", None) or {}
        if not isinstance(meta, dict):
            continue
        if meta.get("requested_from_date") or meta.get("requested_from"):
            return True
    return False


def _mark_workflow_ordered(doc: Document, ordered_at: date) -> None:
    workflow = getattr(doc, "workflow", None)
    if not isinstance(workflow, dict):
        return
    steps = workflow.get("steps")
    if not isinstance(steps, list):
        return
    ordered_iso = ordered_at.isoformat()
    changed = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        code = str(step.get("code") or "").lower()
        if code == "ordered":
            if step.get("status") != "done":
                step["status"] = "done"
            step.setdefault("ordered_at", ordered_iso)
            step.setdefault("completed_at", ordered_iso)
            changed = True
            break
    if not changed:
        return
    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("status") != "done":
            workflow["current_step"] = step.get("code")
            workflow["completed"] = False
            break
    else:
        workflow["current_step"] = None
        workflow["completed"] = True
    doc.workflow = dict(workflow)


def _normalize_due_at_value(value: Any) -> Optional[str]:
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    text = str(value).strip()
    return text or None


def _workflow_due_at_map(workflow: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {}
    if not workflow or not isinstance(workflow, dict):
        return result
    steps = workflow.get("steps")
    if not isinstance(steps, list):
        return result
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("code") or "").strip()
        if not code:
            continue
        due_at = entry.get("due_at")
        result[code] = _normalize_due_at_value(due_at)
    return result


def _collect_due_at_changes(
    before: Optional[Dict[str, Any]],
    after: Optional[Dict[str, Any]],
) -> List[Dict[str, Optional[str]]]:
    before_map = _workflow_due_at_map(before)
    after_map = _workflow_due_at_map(after)
    changes: List[Dict[str, Optional[str]]] = []
    for step_code in sorted(set(before_map) | set(after_map)):
        prev = before_map.get(step_code)
        new = after_map.get(step_code)
        if prev == new:
            continue
        changes.append({"step_code": step_code, "before": prev, "after": new})
    return changes


def _files_from_row(row: Document, meta: Dict[str, Any]) -> List[DocumentFile]:
    files: List[DocumentFile] = []
    raw_files = getattr(row, "files", None)
    if isinstance(raw_files, list):
        for item in raw_files:
            if isinstance(item, dict):
                files.append(DocumentFile(**{**item}))
    else:
        meta_files = meta.get("files")
        if isinstance(meta_files, dict):
            for key, value in meta_files.items():
                if isinstance(value, dict):
                    files.append(DocumentFile(name=key, **value))
                else:
                    files.append(DocumentFile(name=key, url=str(value)))
    return files


def _row_to_out(d: Document) -> DocumentOut:
    meta = _parse_meta(getattr(d, "meta", None))
    files = _files_from_row(d, meta)
    number = getattr(d, "number", None) or meta.get("number")
    workflow = getattr(d, "workflow", None) or meta.get("workflow") or {}
    status_value = _enum_to_str(getattr(d, "status", None)) or DocumentStatus.missing.value
    kind_value = _enum_to_str(getattr(d, "kind", None)) or DocumentKind.driver.value
    requested_from_value = _enum_to_str(getattr(d, "requested_from", None)) or DocumentRequestedFrom.driver.value
    process_type_value = _enum_to_str(getattr(d, "process_type", None)) or DocumentProcessType.none.value
    issue_date = getattr(d, "issue_date", None)
    expire_date = getattr(d, "expire_date", None)
    ordered_at = getattr(d, "ordered_at", None)
    valid_from = getattr(d, "valid_from", None)
    has_files = bool(files)
    status_rank = _status_rank(status_value)
    readiness_state = _readiness_state(
        status_value,
        ordered_at=ordered_at,
        has_files=has_files,
    )
    canonical_type = normalize_doc_type(getattr(d, "doc_type", None) or getattr(d, "type", ""))
    display_type = meta.get("submitted_doc_type") or canonical_type
    user_comment = getattr(d, "user_comment", None) or meta.get("user_comment")
    return DocumentOut(
        id=d.id,
        tenant_id=d.tenant_id,
        candidate_id=d.candidate_id or "",
        company_id=getattr(d, "company_id", None),
        kind=kind_value,
        doc_type=canonical_type,
        type=display_type,
        type_code=canonical_type,
        custom_name=getattr(d, "custom_name", None),
        owner_type=getattr(d, "owner_type", "candidate") or "candidate",
        owner_id=getattr(d, "owner_id", None) or (d.candidate_id or ""),
        requested_from=requested_from_value,
        process_type=process_type_value,
        number=number,
        status=status_value,
        reminder_days_before=d.reminder_days_before or 30,
        files=files,
        workflow=workflow if isinstance(workflow, dict) else {},
        source=getattr(d, "source", None) or meta.get("source"),
        external_id=getattr(d, "external_id", None) or meta.get("external_id"),
        verified_at=getattr(d, "verified_at", None),
        issue_date=issue_date,
        expire_date=expire_date,
        issued_at=issue_date,
        expires_at=expire_date,
        ordered_at=ordered_at,
        valid_from=valid_from,
        user_comment=user_comment,
        has_files=has_files,
        readiness_state=readiness_state,
        status_rank=status_rank,
        extra=meta,
        meta=meta,
        meta_json=meta,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _template_to_out(t: DocumentTemplate) -> DocumentTemplateOut:
    documents_payload = prepare_template_documents(t.documents or [])
    documents = [
        TemplateDocument(
            doc_type=entry["doc_type"],
            kind=entry["kind"],
            requested_from=entry["requested_from"],
            process_type=entry["process_type"],
            required=bool(entry.get("required", True)),
            meta=dict(entry.get("meta") or {}),
            remind_days_before=entry.get("remind_days_before"),
        )
        for entry in documents_payload
    ]
    return DocumentTemplateOut(
        id=t.id,
        code=t.code,
        name=t.name,
        is_active=bool(t.is_active),
        created_by=getattr(t, "created_by", None),
        documents=documents,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("", response_model=List[DocumentOut])
@router.get("/", response_model=List[DocumentOut])
async def list_documents(
    candidate_id: Optional[UUID] = Query(None),
    key: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None, alias="type"),
    kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    ordered: Optional[bool] = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> List[DocumentOut]:
    db, tenant_id = db_tenant
    stmt = select(Document).where(
        Document.tenant_id == str(tenant_id),
        Document.deleted_at.is_(None),
    )
    if active_own_company_id:
        stmt = stmt.join(Candidate, Document.candidate_id == Candidate.id)
        scope = _documents_scope_clause(active_own_company_id)
        if scope is not None:
            stmt = stmt.where(scope)
    if candidate_id:
        stmt = stmt.where(Document.candidate_id == str(candidate_id))
    current_type = doc_type or key
    if current_type:
        stmt = stmt.where(Document.doc_type == normalize_doc_type(current_type))
    if kind:
        try:
            kind_enum = DocumentKind(kind)
        except ValueError as exc:  # noqa: F841
            raise HTTPException(status_code=422, detail="Invalid kind filter")
        stmt = stmt.where(Document.kind == kind_enum)
    if status:
        normalized_status = _status_or_422(status)
        stmt = stmt.where(Document.status == normalized_status)
    if ordered is not None:
        if ordered:
            stmt = stmt.where(Document.ordered_at.isnot(None))
        else:
            stmt = stmt.where(Document.ordered_at.is_(None))
    res = await db.execute(stmt.order_by(Document.created_at.desc()))
    rows = res.scalars().all()
    return [_row_to_out(r) for r in rows]


@router.post(
    "/order",
    response_model=DocumentOut,
    status_code=201,
    dependencies=[Depends(require_trust_write())],
)
async def order_document(
    payload: DocumentOrderPayload,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> DocumentOut:
    db, tenant_id = db_tenant
    candidate = await db.scalar(
        select(Candidate).where(
            Candidate.id == str(payload.candidate_id),
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
        )
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    _ensure_candidate_own_company_scope(candidate, active_own_company_id)

    doc_type = normalize_doc_type(payload.doc_type)
    defaults = get_doc_type_defaults(doc_type)
    if doc_type not in ORDERABLE_CODES or not defaults.orderable:
        raise HTTPException(status_code=422, detail="doc_type is not orderable")

    if doc_type == "work_permit" and payload.requested_from is None:
        raise HTTPException(
            status_code=422,
            detail="requested_from is required for work_permit orders",
        )

    ordered_at = default_order_date(payload.ordered_at)
    owner_context = _owner_context_from_payload(payload.owner_context, payload.candidate_id)

    ruleset_version = await documents_crud.ensure_ruleset_seed(
        db,
        str(tenant_id),
        load_default_ruleset(),
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    checklist = compute_candidate_checklist(owner_context, ruleset_payload)

    existing_docs = await documents_crud.list_candidate_documents(
        db,
        str(tenant_id),
        str(payload.candidate_id),
    )
    active_docs = [doc for doc in existing_docs if getattr(doc, "deleted_at", None) is None]

    missing = missing_base_requirements(checklist, active_docs)
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "checklist_incomplete",
                "missing_types": missing,
            },
        )

    same_type_docs = find_documents_by_type(active_docs, doc_type)
    if same_type_docs:
        raise HTTPException(
            status_code=409,
            detail={"code": "document_exists", "doc_type": doc_type},
        )

    work_permits = find_documents_by_type(active_docs, "work_permit")
    if doc_type == "driver_certificate":
        if not work_permits:
            raise HTTPException(
                status_code=409,
                detail={"code": "work_permit_required"},
            )
        if not _has_requested_from_metadata(work_permits):
            raise HTTPException(
                status_code=409,
                detail={"code": "requested_from_missing"},
            )

    meta_payload: Dict[str, Any] = {}
    if payload.requested_from is not None:
        iso_value = payload.requested_from.isoformat()
        meta_payload["requested_from_date"] = iso_value
        meta_payload.setdefault("requested_from", iso_value)

    create_payload: Dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "candidate_id": str(payload.candidate_id),
        "doc_type": doc_type,
        "status": DocumentStatus.requested.value,
        "ordered_at": ordered_at,
        "owner_id": str(payload.candidate_id),
    }
    resolved_oc = _resolved_document_own_company_id(candidate, active_own_company_id)
    if resolved_oc:
        create_payload["own_company_id"] = resolved_oc
    if meta_payload:
        create_payload["meta"] = meta_payload

    try:
        doc = await documents_crud.create_document(db, create_payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _mark_workflow_ordered(doc, ordered_at)
    await reminders_service.schedule_document_expiry_reminders(db, str(tenant_id), doc)
    from backend.app.api.public.intake import _ensure_status_share_token

    _ensure_status_share_token(candidate)
    base_url = (settings.frontend_url or "").strip().rstrip("/") or "https://hostflow.cc"
    status_token = getattr(candidate, "status_share_token", None) or getattr(candidate, "intake_token", None)
    status_url = f"{base_url}/public/status/{status_token}" if status_token else None
    await candidate_notifications.send_document_requested_email_to_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
        doc_type=doc_type,
        status_url=status_url,
    )
    await db.commit()
    await db.refresh(doc)
    return _row_to_out(doc)


@router.post(
    "/",
    response_model=DocumentOut,
    dependencies=[Depends(require_trust_write())],
)
async def create_document(
    payload: DocumentIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> DocumentOut:
    db, tenant_id = db_tenant
    candidate = await _candidate_for_document_scope(db, tenant_id, str(payload.candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    _ensure_candidate_own_company_scope(candidate, active_own_company_id)
    resolved_oc = _resolved_document_own_company_id(candidate, active_own_company_id)

    defaults = get_doc_type_defaults(payload.doc_type)
    doc_type = defaults.doc_type
    kind = _kind_or_422(payload.kind, defaults.kind)
    requested_from = _requested_from_or_422(payload.requested_from, defaults.requested_from)
    process_type = _process_type_or_422(payload.process_type, defaults.process_type)
    status = _status_or_422(payload.status)

    custom_name = payload.custom_name.strip() if payload.custom_name else None

    if defaults.requires_custom_name and not custom_name:
        raise HTTPException(
            status_code=422, detail="custom_name required for doc_type 'other'"
        )
    if defaults.requires_custom_name and payload.kind is None:
        raise HTTPException(status_code=422, detail="kind required for doc_type 'other'")

    meta_payload = dict(payload.meta or {})
    if payload.number:
        meta_payload.setdefault("number", payload.number)
    user_comment = _normalize_user_comment(payload.user_comment)
    _ensure_user_comment_requirement(doc_type, user_comment)
    if user_comment:
        meta_payload.setdefault("user_comment", user_comment)
    else:
        meta_payload.pop("user_comment", None)

    files_payload = [f.model_dump() for f in payload.files]
    normalized_workflow = normalize_workflow(process_type, payload.workflow)
    if normalized_workflow is None and process_type in WORKFLOW_DEFINITIONS:
        normalized_workflow = default_workflow(process_type)

    status_final = compute_auto_status(
        status,
        process_type=process_type,
        workflow=normalized_workflow,
        has_files=bool(files_payload),
        expire_date=payload.expire_date,
    )

    await documents_crud.ensure_document_type(db, str(tenant_id), doc_type)
    await ensure_tenant_document_quota(db, str(tenant_id))
    await ensure_tenant_storage_bytes_fits(
        db,
        str(tenant_id),
        previous_doc_attribution_bytes=0,
        next_doc_attribution_bytes=sum_file_entries_bytes(files_payload),
    )
    obj = Document(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        candidate_id=str(payload.candidate_id),
        own_company_id=resolved_oc,
        company_id=str(payload.company_id) if payload.company_id else None,
        owner_type="candidate",
        owner_id=str(payload.owner_id or payload.candidate_id),
        kind=kind,
        doc_type=doc_type,
        custom_name=custom_name,
        status=status_final,
        issue_date=payload.issue_date,
        expire_date=payload.expire_date,
        ordered_at=payload.ordered_at,
        valid_from=payload.valid_from,
        reminder_days_before=payload.reminder_days_before or 30,
        requested_from=requested_from,
        process_type=process_type,
        workflow=normalized_workflow or None,
        files=files_payload,
        source=payload.source,
        external_id=payload.external_id,
        verified_at=payload.verified_at
        if payload.verified_at is not None
        else (_now_utc() if status_final == DocumentStatus.approved else None),
        meta=meta_payload or None,
        number=payload.number,
        user_comment=user_comment,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    await reminders_service.schedule_document_expiry_reminders(db, str(tenant_id), obj)
    await db.commit()
    await db.refresh(obj)
    await refresh_documents_overdue_metrics(db, str(tenant_id))
    return _row_to_out(obj)


if PYDANTIC_V2:

    class DocumentPatch(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        doc_type: Optional[str] = Field(
            default=None, validation_alias=AliasChoices("doc_type", "type", "key")
        )
        kind: Optional[str] = None
        custom_name: Optional[str] = None
        number: Optional[str] = None
        status: Optional[str] = None
        issue_date: Optional[date] = Field(
            default=None, validation_alias=AliasChoices("issue_date", "issued_at")
        )
        expire_date: Optional[date] = Field(
            default=None, validation_alias=AliasChoices("expire_date", "expires_at")
        )
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = Field(
            default=None, validation_alias=AliasChoices("valid_from", "effective_from", "effective_date")
        )
        reminder_days_before: Optional[int] = None
        company_id: Optional[UUID] = None
        owner_id: Optional[UUID] = None
        requested_from: Optional[str] = None
        process_type: Optional[str] = None
        workflow: Optional[Dict[str, Any]] = None
        files: Optional[List[DocumentFile]] = None
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        meta: Optional[Dict[str, Any]] = Field(
            default=None, validation_alias=AliasChoices("meta", "extra", "meta_json")
        )
        user_comment: Optional[str] = None

else:

    class DocumentPatch(BaseModel):
        class Config:
            allow_population_by_field_name = True

        doc_type: Optional[str] = Field(default=None)
        kind: Optional[str] = None
        custom_name: Optional[str] = None
        number: Optional[str] = None
        status: Optional[str] = None
        issue_date: Optional[date] = Field(default=None)
        expire_date: Optional[date] = Field(default=None)
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = Field(default=None)
        reminder_days_before: Optional[int] = None
        company_id: Optional[UUID] = None
        owner_id: Optional[UUID] = None
        requested_from: Optional[str] = None
        process_type: Optional[str] = None
        workflow: Optional[Dict[str, Any]] = None
        files: Optional[List[DocumentFile]] = None
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        meta: Optional[Dict[str, Any]] = Field(default=None)
        user_comment: Optional[str] = None

        @root_validator(pre=True)
        def _apply_patch_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
            data = dict(values or {})
            for target, aliases in ALIAS_MAP_PATCH.items():
                if target in data and data[target] is not None:
                    continue
                alias_value = _extract_first(data, aliases)
                if alias_value is not None:
                    data.setdefault(target, alias_value)
            return data


@router.patch(
    "/{doc_id}",
    response_model=DocumentOut,
    dependencies=[Depends(require_trust_write())],
)
async def update_document(
    doc_id: UUID,
    payload: DocumentPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> DocumentOut:
    db, tenant_id = db_tenant
    res = await db.execute(
        select(Document).where(
            Document.id == str(doc_id),
            Document.tenant_id == str(tenant_id),
            Document.deleted_at.is_(None),
        )
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    cand = await _candidate_for_document_scope(db, tenant_id, str(obj.candidate_id))
    if not cand:
        raise HTTPException(status_code=404, detail="Document not found")
    _ensure_document_own_company_matches(obj, cand, active_own_company_id)
    old_status_value = _enum_to_str(getattr(obj, "status", None))

    defaults = get_doc_type_defaults(obj.doc_type)
    process_type_before = obj.process_type
    workflow_before = getattr(obj, "workflow", None)
    due_at_changes: List[Dict[str, Optional[str]]] = []

    custom_name_update = None
    if payload.custom_name is not None:
        custom_name_update = payload.custom_name.strip() or None

    if payload.doc_type is not None:
        defaults = get_doc_type_defaults(payload.doc_type)
        obj.doc_type = defaults.doc_type
        await documents_crud.ensure_document_type(db, str(tenant_id), defaults.doc_type)
        if payload.kind is None:
            obj.kind = defaults.kind
        if payload.requested_from is None:
            obj.requested_from = defaults.requested_from
        if payload.process_type is None:
            obj.process_type = defaults.process_type

    if payload.kind is not None:
        obj.kind = _kind_or_422(payload.kind, defaults.kind)
    if custom_name_update is not None:
        obj.custom_name = custom_name_update
    if payload.number is not None:
        obj.number = payload.number
    if payload.company_id is not None:
        obj.company_id = str(payload.company_id) if payload.company_id else None
    if payload.owner_id is not None:
        obj.owner_id = str(payload.owner_id) if payload.owner_id else None
    if payload.issue_date is not None:
        obj.issue_date = payload.issue_date
    if payload.expire_date is not None:
        obj.expire_date = payload.expire_date
    if "ordered_at" in payload.model_fields_set:
        obj.ordered_at = payload.ordered_at
    if "valid_from" in payload.model_fields_set:
        obj.valid_from = payload.valid_from
    if payload.reminder_days_before is not None:
        obj.reminder_days_before = payload.reminder_days_before
    if payload.requested_from is not None:
        obj.requested_from = _requested_from_or_422(payload.requested_from, defaults.requested_from)
    if payload.process_type is not None:
        obj.process_type = _process_type_or_422(payload.process_type, defaults.process_type)
    if payload.source is not None:
        obj.source = payload.source
    if payload.external_id is not None:
        obj.external_id = payload.external_id

    if defaults.requires_custom_name and not obj.custom_name:
        raise HTTPException(status_code=422, detail="custom_name required for doc_type 'other'")

    if hasattr(payload, "user_comment") and payload.user_comment is not None:
        obj.user_comment = _normalize_user_comment(payload.user_comment)
    _ensure_user_comment_requirement(obj.doc_type, obj.user_comment)

    try:
        process_type_before_enum = (
            process_type_before
            if isinstance(process_type_before, DocumentProcessType)
            else DocumentProcessType(str(process_type_before))
        )
    except ValueError:
        process_type_before_enum = DocumentProcessType.none

    try:
        process_type_enum = (
            obj.process_type
            if isinstance(obj.process_type, DocumentProcessType)
            else DocumentProcessType(str(obj.process_type))
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
        normalized_workflow = normalize_workflow(
            process_type_enum,
            None,
            existing_workflow=None,
        )
        if normalized_workflow is None and process_type_enum in WORKFLOW_DEFINITIONS:
            normalized_workflow = default_workflow(process_type_enum)
    elif workflow_before is not None:
        normalized_workflow = normalize_workflow(
            process_type_enum,
            workflow_before,
            existing_workflow=workflow_before,
        )

    if normalized_workflow is not None:
        obj.workflow = normalized_workflow
    elif payload.workflow is not None:
        obj.workflow = None
    elif process_type_changed:
        obj.workflow = None
    else:
        obj.workflow = workflow_before

    workflow_after = obj.workflow
    if payload.workflow is not None or process_type_changed:
        due_at_changes = _collect_due_at_changes(workflow_before, workflow_after)

    if payload.files is not None:
        obj.files = [f.model_dump() for f in payload.files]

    has_files = bool(obj.files)

    if payload.status is not None:
        status_value = _status_or_422(payload.status)
    else:
        current_status = getattr(obj, "status", None)
        if isinstance(current_status, DocumentStatus):
            status_value = current_status
        else:
            status_value = _status_or_422(current_status)

    auto_status_value = compute_auto_status(
        status_value,
        process_type=process_type_enum,
        workflow=obj.workflow or normalized_workflow,
        has_files=has_files,
        expire_date=obj.expire_date,
    )
    if payload.status is not None and status_value in (DocumentStatus.rejected, DocumentStatus.expired):
        auto_status_value = status_value

    obj.status = auto_status_value

    if payload.verified_at is not None:
        obj.verified_at = payload.verified_at
    elif auto_status_value == DocumentStatus.approved and obj.verified_at is None:
        obj.verified_at = _now_utc()

    current_meta = dict(obj.meta or {})
    meta_changed = False
    if payload.meta is not None:
        current_meta = dict(payload.meta or {})
        meta_changed = True
    if payload.number is not None:
        if payload.number:
            current_meta["number"] = payload.number
        else:
            if "number" in current_meta:
                current_meta.pop("number", None)
        meta_changed = True
    previous_comment = current_meta.get("user_comment")
    if obj.user_comment:
        if previous_comment != obj.user_comment:
            meta_changed = True
        current_meta["user_comment"] = obj.user_comment
    else:
        if previous_comment is not None:
            current_meta.pop("user_comment", None)
            meta_changed = True
    if meta_changed:
        obj.meta = current_meta if current_meta else None

    obj.updated_at = _now_utc()
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    if due_at_changes:
        await log_activity(
            db,
            tenant_id=str(tenant_id),
            action="document.workflow.due_at_changed",
            target_type="document",
            target_id=str(doc_id),
            payload={"changes": due_at_changes},
        )
        await db.commit()
        await db.refresh(obj)
    await reminders_service.schedule_document_expiry_reminders(db, str(tenant_id), obj)
    await db.commit()
    await db.refresh(obj)
    try:
        new_status_value = _enum_to_str(getattr(obj, "status", None))
        if new_status_value and old_status_value != new_status_value and getattr(obj, "candidate_id", None):
            candidate = await db.get(Candidate, str(obj.candidate_id))
            if candidate and str(getattr(candidate, "tenant_id", "")) == str(tenant_id):
                await candidate_tg_notifications.send_candidate_document_status_changed_telegram(
                    db,
                    tenant_id=str(tenant_id),
                    candidate=candidate,
                    document_type=str(getattr(obj, "doc_type", "") or ""),
                    old_status=old_status_value,
                    new_status=new_status_value,
                )
    except Exception:
        logger.exception(
            "documents.update_document telegram notification failed tenant=%s doc=%s",
            str(tenant_id),
            str(doc_id),
        )
    await refresh_documents_overdue_metrics(db, str(tenant_id))
    return _row_to_out(obj)


@router.delete(
    "/{doc_id}",
    status_code=200,
    dependencies=[Depends(require_trust_write())],
)
async def delete_document(
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> Dict[str, Any]:
    db, tenant_id = db_tenant
    res = await db.execute(
        select(Document).where(
            Document.id == str(doc_id),
            Document.tenant_id == str(tenant_id),
            Document.deleted_at.is_(None),
        )
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    cand = await _candidate_for_document_scope(db, tenant_id, str(obj.candidate_id))
    if not cand:
        raise HTTPException(status_code=404, detail="Document not found")
    _ensure_document_own_company_matches(obj, cand, active_own_company_id)

    now = _now_utc()
    await db.execute(
        update(Document)
        .where(Document.id == obj.id)
        .values(deleted_at=now, updated_at=now)
    )
    await reminders_service.cancel_entity_reminders(
        db,
        tenant_id=str(tenant_id),
        entity_type="document",
        entity_id=str(obj.id),
    )
    await reminders_service.cancel_document_step_reminders(
        db,
        tenant_id=str(tenant_id),
        document_id=str(obj.id),
    )
    await db.commit()
    return {"ok": True, "id": str(obj.id)}


class ExpiringDoc(BaseModel):
    document: DocumentOut
    days_left: int


@router.get("/expiring", response_model=List[ExpiringDoc])
async def list_expiring(
    within_days: int = Query(30, ge=1, le=365),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> List[ExpiringDoc]:
    db, tenant_id = db_tenant
    today = date.today()
    limit_date = today + timedelta(days=within_days)

    stmt = select(Document).where(
        Document.tenant_id == str(tenant_id),
        Document.deleted_at.is_(None),
        Document.expires_at.is_not(None),
        Document.expires_at <= limit_date,
    )
    if active_own_company_id:
        stmt = stmt.join(Candidate, Document.candidate_id == Candidate.id)
        scope = _documents_scope_clause(active_own_company_id)
        if scope is not None:
            stmt = stmt.where(scope)

    res = await db.execute(stmt)
    rows = res.scalars().all()
    out: List[ExpiringDoc] = []
    for r in rows:
        if not r.expires_at:
            continue
        exp = r.expires_at
        exp_date = exp.date() if isinstance(exp, datetime) else exp
        days_left = (exp_date - today).days
        out.append(ExpiringDoc(document=_row_to_out(r), days_left=days_left))
    return out

@router.get("/templates", response_model=List[DocumentTemplateOut])
async def list_document_templates(
    include_inactive: bool = Query(False),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> List[DocumentTemplateOut]:
    db, tenant_id = db_tenant
    stmt = select(DocumentTemplate).where(DocumentTemplate.tenant_id == str(tenant_id))
    if not include_inactive:
        stmt = stmt.where(DocumentTemplate.is_active.is_(True))
    stmt = stmt.order_by(DocumentTemplate.name.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_template_to_out(row) for row in rows]


@router.get("/templates/{template_id}", response_model=DocumentTemplateOut)
async def get_document_template(
    template_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> DocumentTemplateOut:
    db, tenant_id = db_tenant
    res = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.id == str(template_id),
            DocumentTemplate.tenant_id == str(tenant_id),
        )
    )
    template = res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Document template not found")
    return _template_to_out(template)


@router.get(
    "/{doc_id}",
    response_model=DocumentOut,
    dependencies=[Depends(require_trust_write())],
)
async def get_document_detail(
    doc_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> DocumentOut:
    db, tenant_id = db_tenant
    res = await db.execute(
        select(Document).where(
            Document.id == str(doc_id),
            Document.tenant_id == str(tenant_id),
            Document.deleted_at.is_(None),
        )
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    cand = await _candidate_for_document_scope(db, tenant_id, str(obj.candidate_id))
    if not cand:
        raise HTTPException(status_code=404, detail="Document not found")
    _ensure_document_own_company_matches(obj, cand, active_own_company_id)
    return _row_to_out(obj)


def _status_or_422(value: Optional[str]) -> DocumentStatus:
    try:
        return normalize_status(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _kind_or_422(value: Optional[str], fallback: DocumentKind) -> DocumentKind:
    try:
        return normalize_kind(value, fallback)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _requested_from_or_422(
    value: Optional[str], fallback: DocumentRequestedFrom
) -> DocumentRequestedFrom:
    try:
        return normalize_requested_from(value, fallback)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _process_type_or_422(
    value: Optional[str], fallback: DocumentProcessType
) -> DocumentProcessType:
    try:
        return normalize_process_type(value, fallback)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
