from __future__ import annotations

import csv
import io
import json
import logging
import os
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path as PathLib
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.security.document_events import (
    emit_document_security_event_v1,
    url_looks_presigned,
)
from backend.app.security.export_events import (
    clip_export_filter_scope,
    emit_export_security_event_v1,
)
from backend.app.security.event_taxonomy import (
    EVENT_DOCUMENT_FILE_ACCESS_REQUESTED,
    EVENT_DOCUMENT_FILE_DOWNLOADED,
    EVENT_DOCUMENT_METADATA_READ,
    EVENT_DOCUMENT_SIGNED_URL_DENIED,
    EVENT_DOCUMENT_SIGNED_URL_GENERATED,
    EVENT_EXPORT_DENIED,
    EVENT_EXPORT_DOWNLOADED,
    EVENT_EXPORT_GENERATED,
    EVENT_EXPORT_REQUESTED,
)
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.user import User
from ...models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from ...models.reminder import Reminder, ReminderStatus
from backend.app.services import reminders as reminders_service
from backend.app.services.document_catalog import (
    get_doc_type_defaults,
    normalize_doc_type,
    normalize_status,
)
from backend.app.services.document_orders import (
    ORDERABLE_CODES,
    find_documents_by_type,
    has_ready_document,
    missing_base_requirements,
)
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import (
    compute_ruleset_diff,
    normalize_ruleset_payload,
)
from backend.app.services.document_workflow import STATUS_ORDER, default_workflow
from .ocr_pipeline import OcrPipeline
from .owner_summary import compute_owner_summary
from .rules_engine import compute_candidate_checklist
from .storage_mock import presign_upload
from .storage import (
    ensure_document_files,
    file_entry_media_type,
    get_uploads_root,
    register_document_upload,
    resolve_file_path,
    sanitize_filename,
    select_file_entry,
)
from backend.app.services.document_files import resolve_document_file
from backend.app.services.own_company_doc_scope import (
    ensure_document_own_company_matches,
    tenant_documents_own_company_clause,
)
from backend.app.services.tenant_visibility import get_tenant_visibility

from .crud import (
    create_document,
    create_document_check,
    create_ruleset_version,
    ensure_ruleset_seed,
    activate_ruleset_version,
    get_document,
    get_effective_latest_ruleset_version,
    get_latest_diff_for_version,
    get_last_document_checks_map,
    get_previous_ruleset_version,
    get_ruleset_diff_between,
    get_ruleset_version_by_id,
    list_candidate_documents,
    list_document_checks,
    list_document_types,
    list_ruleset_versions,
    list_ruleset_usage,
    log_ruleset_usage,
    ruleset_version_visible_for_scope,
    ruleset_versions_share_scope,
    ruleset_write_scope_own_company_id,
    soft_delete_document,
    update_document,
)
from .schemas_db import (
    DocumentCheckOut,
    DocumentCreateIn,
    DocumentOut,
    DocumentReminderOut,
    DocumentTypeOut,
    DocumentUpdateIn,
    DocumentWithChecksOut,
    RulesetDiffOut,
    RulesetUsageOut,
    RulesetUsageResponse,
    RulesetVersionOut,
)
from .candidate_document_owner_access import (
    CandidateDocsContext,
    candidate_visible_for_tenant_documents,
)
from .document_access_resolver import DocumentAccessContext, DocumentAccessResolver
from .document_visibility_and_locks import (
    DOCUMENT_VIEWER_CHANNELS,
    document_visible_to_viewer,
    viewer_readable_scopes,
)
from .validators import validate_meta

router = APIRouter(prefix="/db", tags=["documents"])
logger = logging.getLogger(__name__)


def _db_access_kind(session: AsyncSession) -> Optional[str]:
    raw = session.info.get("security_access_kind")
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


async def _candidate_documents_export_access(
    session: AsyncSession,
    tenant_id: UUID,
    candidate_id: UUID,
    *,
    workspace_own_company_header: Optional[str],
    viewer_channel: str,
    export_type: str,
    source: str,
) -> tuple[DocumentAccessContext, Optional[str]]:
    """Resolve read access for candidate document exports; emit ``export.denied`` on HTTP errors."""
    access_kind = _db_access_kind(session)
    try:
        ctx = await _candidate_documents_read_access(
            session,
            str(tenant_id),
            candidate_id,
            workspace_own_company_header=workspace_own_company_header,
            viewer_channel=viewer_channel,
        )
        return ctx, access_kind
    except HTTPException as exc:
        emit_export_security_event_v1(
            event_type=EVENT_EXPORT_DENIED,
            result="denied",
            severity="low",
            source=source,
            tenant_id=str(tenant_id),
            access_kind=access_kind,
            entity_type="candidate",
            entity_id=str(candidate_id),
            export_type=export_type,
            filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
            reason=f"http_{exc.status_code}",
            export_scope="single_candidate",
            contains_class3=True,
            bulk_operation=False,
        )
        raise


def resolve_document_viewer_channel(
    x_document_viewer_channel: Optional[str] = Header(
        None,
        alias="X-Document-Viewer-Channel",
        description=(
            "Viewer channel for document read visibility (recruitment|hr|transport|finance). "
            "Defaults to recruitment."
        ),
    ),
) -> str:
    if x_document_viewer_channel is None or not str(x_document_viewer_channel).strip():
        return "recruitment"
    ch = str(x_document_viewer_channel).strip().lower()
    if ch not in DOCUMENT_VIEWER_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail="Invalid X-Document-Viewer-Channel",
        )
    return ch


def document_access_trace_response_enabled() -> bool:
    """When true, JSON responses may include ``document_access_trace`` (dev/CI only)."""
    return os.environ.get("HOSTFLOW_DOCUMENT_ACCESS_DEBUG", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _log_document_access_visibility(
    *,
    surface: str,
    candidate_id: UUID,
    viewer_channel: str,
    db_fetch_total: int,
    db_visible: int,
    response_items: int,
    synthetics_returned: int,
) -> None:
    """DEBUG-only: why rows disappeared for a viewer channel (no policy graph)."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    scopes = ",".join(sorted(viewer_readable_scopes(viewer_channel)))
    logger.debug(
        "[document_access_visibility] surface=%s candidate=%s viewer=%s readable_scopes=[%s] "
        "db_fetch_total=%s db_visible=%s filtered_out=%s response_items=%s synthetics_in_response=%s",
        surface,
        candidate_id,
        viewer_channel,
        scopes,
        db_fetch_total,
        db_visible,
        max(0, db_fetch_total - db_visible),
        response_items,
        synthetics_returned,
    )

# G-8 stage 2.2: per-document "what to do next" CTA. Mounted as a sub-router
# so the implementation lives in a small, single-purpose file. Must be
# included BEFORE the inline `@router.get("/documents/{document_id}")`
# below — Starlette matches in registration order and the bare
# `/documents/{document_id}` would otherwise swallow
# `/documents/{document_id}/next-action` and force FastAPI to validate the
# literal string `next-action` as a UUID.
from backend.app.modules.documents import next_action_api as _next_action_api  # noqa: E402

router.include_router(_next_action_api.router)

StatusFilter = Optional[str]

_META_DIR = PathLib(__file__).resolve().parent / "meta_schemas"
_OCR_PIPELINE = OcrPipeline()


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
        return {"history": raw}
    return {}


def _load_meta_schema_for(code: str) -> Dict[str, Any]:
    raw = (code or "").strip()
    if not raw:
        return {}
    names = [raw]
    canonical = normalize_doc_type(raw)
    if canonical not in names:
        names.append(canonical)
    candidates = [
        _META_DIR / f"{name}.json"
        for name in names
    ]
    candidates.extend(_META_DIR / f"{name}.schema.json" for name in names)
    candidates.extend(_META_DIR / f"{name}.meta.json" for name in names)
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
    return {}


def _owner_context_or_400(
    owner_context: Optional[str],
    candidate_id: UUID,
    defaults: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base: Dict[str, Any] = dict(defaults or {})
    base.setdefault("candidate_id", str(candidate_id))
    if not owner_context:
        return base
    try:
        parsed = json.loads(owner_context)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=f"Invalid owner_context: {exc}")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="owner_context must be an object")
    merged = dict(base)
    for key, value in parsed.items():
        if key == "documents" and isinstance(merged.get("documents"), dict) and isinstance(value, dict):
            merged["documents"] = {**merged["documents"], **value}
        else:
            merged[key] = value
    merged.setdefault("candidate_id", str(candidate_id))
    return merged


def _candidate_owner_context_defaults(candidate: Candidate, candidate_id: UUID) -> Dict[str, Any]:
    try:
        extra = candidate._get_extra()
    except Exception:
        extra = getattr(candidate, "extra", {}) or {}
    try:
        personal = candidate._get_personal_data()
    except Exception:
        personal = getattr(candidate, "personal_data", {}) or {}

    extra = extra if isinstance(extra, dict) else {}
    personal = personal if isinstance(personal, dict) else {}
    docs_raw = extra.get("documents")
    docs_ctx = {
        key: bool(value)
        for key, value in (docs_raw.items() if isinstance(docs_raw, dict) else [])
        if isinstance(value, bool)
    }
    ctx: Dict[str, Any] = {
        "candidate_id": str(candidate_id),
        "citizenship": extra.get("citizenship") or personal.get("citizenship"),
        "residency_status": extra.get("poland_stay_basis") or personal.get("residency_status"),
        "has_adr": extra.get("has_adr"),
        "documents": docs_ctx,
    }
    return {k: v for k, v in ctx.items() if v is not None}


def _checklist_sources_for(doc_type: str, checklist: Dict[str, Any]) -> List[str]:
    debug = checklist.get("debug") or {}
    sources: List[str] = []
    if doc_type in (debug.get("added_by_vacancy") or []):
        sources.append("vacancy")
    if doc_type in (debug.get("added_by_category") or []):
        sources.append("category")
    if doc_type in (debug.get("added_by_overrides") or []):
        sources.append("override")
    if not sources:
        sources.append("default")
    return sources


def _fill_checklist_defaults(checklist: Dict[str, Any], ruleset: Dict[str, Any]) -> Dict[str, Any]:
    defaults = (ruleset.get("candidate") or {}).get("defaults") or {}
    if not checklist.get("requiredTypes"):
        checklist["requiredTypes"] = list(defaults.get("requiredTypes") or [])
    if not checklist.get("optionalTypes"):
        checklist["optionalTypes"] = list(defaults.get("optionalTypes") or [])
    return checklist


def _build_synthetic_documents(
    tenant_id: str,
    candidate_id: UUID,
    checklist: Dict[str, Any],
    existing_docs: Sequence[Dict[str, Any]],
) -> List[DocumentOut]:
    required_types = checklist.get("requiredTypes") or []
    existing_types = {
        normalize_doc_type(doc.get("type_code") or doc.get("doc_type") or "")
        for doc in existing_docs
    }
    now_ts = datetime.now(timezone.utc)
    synthetic_docs: List[DocumentOut] = []
    for raw_type in required_types:
        doc_type = normalize_doc_type(raw_type)
        if not doc_type or doc_type in existing_types:
            continue
        defaults = get_doc_type_defaults(doc_type)
        workflow_default = default_workflow(defaults.process_type) or {}
        meta_payload = {
            "synthetic": True,
            "required": True,
            "doc_type": doc_type,
            "checklist_sources": _checklist_sources_for(doc_type, checklist),
        }
        synthetic_docs.append(
            DocumentOut(
                id=f"synthetic::{doc_type}::{candidate_id}",
                tenant_id=tenant_id,
                candidate_id=str(candidate_id),
                company_id=None,
                kind=defaults.kind.value,
                doc_type=doc_type,
                type=doc_type,
                type_code=doc_type,
                custom_name=None,
                title=None,
                owner_type="candidate",
                owner_id=str(candidate_id),
                requested_from=defaults.requested_from.value,
                process_type=defaults.process_type.value,
                number=None,
                status=DocumentStatus.missing.value,
                reminder_days_before=30,
                files=[],
                workflow=workflow_default,
                source=None,
                external_id=None,
                verified_at=None,
                issue_date=None,
                expire_date=None,
                issued_at=None,
                expires_at=None,
                meta=meta_payload.copy(),
                extra=meta_payload.copy(),
                meta_json=meta_payload.copy(),
                created_at=now_ts,
                updated_at=now_ts,
                reminders=[],
                version=None,
                last_check=None,
                responsible_user_id=None,
                responsible_name=None,
            )
        )
    return synthetic_docs


async def _ensure_auto_ordered_documents(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    checklist: Dict[str, Any],
    existing_docs: Sequence[Document],
) -> bool:
    """
    Legacy helper previously auto-created work_permit/driver_certificate entries when the
    checklist was complete. Manual ordering (CTA + POST /documents/order) supersedes that
    flow, so we keep the hook but skip auto-creation to avoid resurrecting deleted orders.
    """

    return False


def _compute_readiness_state(
    status_value: str,
    *,
    has_files: bool,
    ordered_at: Optional[date],
    valid_from: Optional[date],
) -> str:
    normalized = status_value.lower()
    if normalized in {"approved", "received", "delivered", "completed", "verified"}:
        return "ready"
    if normalized in {"rejected", "expired", "invalid", "overdue"}:
        return "problem"
    if ordered_at:
        return "ordered"
    if normalized in {"in_progress", "submitted"}:
        return "in_progress"
    if has_files or valid_from:
        return "awaiting_review"
    if normalized in {"requested", "missing"}:
        return "requested"
    return "pending"


def _as_date(value: Optional[datetime | date]) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    return value


async def _load_reminders(
    session: AsyncSession, tenant_id: str, document_id: str
) -> List[DocumentReminderOut]:
    reminder_list: List[DocumentReminderOut] = []

    expiry_stmt = (
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "document",
            Reminder.entity_id == document_id,
        )
        .order_by(Reminder.due_at.asc())
    )
    expiry_rows = (await session.execute(expiry_stmt)).scalars().all()
    for row in expiry_rows:
        payload = row.payload or {}
        offset_days = int(payload.get("offset_days") or 0)
        reminder_list.append(
            DocumentReminderOut(
                due_at=row.due_at,
                message=row.message or "",
                offset_days=offset_days,
                status=row.status or ReminderStatus.pending,
                kind="expiry",
            )
        )
    step_stmt = (
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "document_step",
            Reminder.entity_id.like(f"{document_id}:%"),
        )
        .order_by(Reminder.due_at.asc())
    )
    step_rows = (await session.execute(step_stmt)).scalars().all()
    for row in step_rows:
        payload = row.payload or {}
        step_code = None
        entity_id = row.entity_id or ""
        if ":" in entity_id:
            _, step_code = entity_id.split(":", 1)
        step_code = payload.get("step_code") or step_code
        reminder_list.append(
            DocumentReminderOut(
                due_at=row.due_at,
                message=row.message or "",
                offset_days=int(payload.get("offset_days") or 0),
                status=row.status or ReminderStatus.pending,
                step_code=step_code,
                kind="workflow_step",
            )
        )
    return reminder_list


def _check_to_out(check) -> DocumentCheckOut:
    return DocumentCheckOut(
        id=str(getattr(check, "id")),
        document_id=str(getattr(check, "document_id")),
        reviewer_id=getattr(check, "reviewer_id", None),
        decision=str(getattr(check, "decision")),
        reason_code=getattr(check, "reason_code", None),
        comment=getattr(check, "comment", None),
        payload=getattr(check, "payload", None),
        created_at=getattr(check, "created_at"),
    )

async def _batch_candidate_recruiter_labels(
    session: AsyncSession,
    tenant_id: str,
    candidate_ids: list[str],
) -> dict[str, tuple[str | None, str | None]]:
    """Map candidate_id -> (recruiter_user_id, recruiter_display_name) for registry columns."""
    if not candidate_ids:
        return {}
    uniq = list(dict.fromkeys([c for c in candidate_ids if c]))
    if not uniq:
        return {}
    stmt = select(Candidate.id, Candidate.recruiter_id).where(
        Candidate.tenant_id == tenant_id,
        Candidate.id.in_(uniq),
    )
    rows = (await session.execute(stmt)).all()
    rid_by_cand: dict[str, str | None] = {
        str(r[0]): (str(r[1]) if r[1] else None) for r in rows
    }
    recruiter_ids = {rid for rid in rid_by_cand.values() if rid}
    name_by_uid: dict[str, str] = {}
    if recruiter_ids:
        ustmt = select(User.id, User.email, User.full_name).where(User.id.in_(recruiter_ids))
        for uid, email, full_name in (await session.execute(ustmt)).all():
            label = (full_name or "").strip() or (email or "").strip() or str(uid)
            name_by_uid[str(uid)] = label
    out: dict[str, tuple[str | None, str | None]] = {}
    for cid in uniq:
        rid = rid_by_cand.get(cid)
        if not rid:
            out[cid] = (None, None)
        else:
            out[cid] = (rid, name_by_uid.get(rid))
    return out


def _ruleset_to_out(record) -> RulesetVersionOut:
    ruleset_payload = normalize_ruleset_payload(getattr(record, "json_data", None))
    return RulesetVersionOut(
        id=str(getattr(record, "id")),
        tenant_id=str(getattr(record, "tenant_id")),
        own_company_id=getattr(record, "own_company_id", None),
        version=int(getattr(record, "version")),
        ruleset=ruleset_payload,
        comment=getattr(record, "comment", None),
        created_by=getattr(record, "created_by", None),
        created_at=getattr(record, "created_at"),
        is_active=bool(getattr(record, "is_active", True)),
        signature=str(getattr(record, "signature", "") or ""),
        origin_version_id=getattr(record, "origin_version_id", None),
        rollback_comment=getattr(record, "rollback_comment", None),
    )


async def _document_to_out(
    session: AsyncSession,
    doc,
    *,
    last_check=None,
    responsible_user_id: str | None = None,
    responsible_name: str | None = None,
) -> DocumentOut:
    await ensure_document_files(session, doc)
    reminders = await _load_reminders(session, doc.tenant_id, doc.id)
    files = list(doc.files or [])
    meta_payload = dict(getattr(doc, "meta", {}) or {})
    workflow_payload = getattr(doc, "workflow", {}) or {}
    extra_payload = dict(meta_payload)
    title = meta_payload.get("title") or getattr(doc, "custom_name", None)
    kind_value = (
        doc.kind.value
        if hasattr(doc, "kind") and isinstance(doc.kind, DocumentKind)
        else str(doc.kind or DocumentKind.driver.value)
    )
    requested_from_value = (
        doc.requested_from.value
        if hasattr(doc, "requested_from") and isinstance(doc.requested_from, DocumentRequestedFrom)
        else str(doc.requested_from or DocumentRequestedFrom.driver.value)
    )
    process_type_value = (
        doc.process_type.value
        if hasattr(doc, "process_type") and isinstance(doc.process_type, DocumentProcessType)
        else str(doc.process_type or DocumentProcessType.none.value)
    )
    status_value = (
        doc.status.value
        if hasattr(doc, "status") and isinstance(doc.status, DocumentStatus)
        else str(doc.status)
    )
    last_check_out = _check_to_out(last_check) if last_check else None
    ordered_at = _as_date(getattr(doc, "ordered_at", None))
    valid_from = _as_date(getattr(doc, "valid_from", None))
    has_files = bool(files)
    try:
        status_rank = STATUS_ORDER[DocumentStatus(status_value)]
    except Exception:
        status_rank = 0
    readiness_state = _compute_readiness_state(
        status_value,
        has_files=has_files,
        ordered_at=ordered_at,
        valid_from=valid_from,
    )
    raw_type = str(doc.doc_type or "").strip()
    canonical_type = normalize_doc_type(raw_type)
    if raw_type and canonical_type != raw_type:
        meta_payload.setdefault("legacy_doc_type", raw_type)
        extra_payload.setdefault("legacy_doc_type", raw_type)
    return DocumentOut(
        id=str(doc.id),
        tenant_id=str(doc.tenant_id),
        candidate_id=str(doc.candidate_id),
        company_id=str(doc.company_id) if getattr(doc, "company_id", None) else None,
        own_company_id=str(getattr(doc, "own_company_id", None))
        if getattr(doc, "own_company_id", None) is not None
        else None,
        kind=kind_value,
        doc_type=canonical_type,
        type=canonical_type,
        type_code=canonical_type,
        custom_name=getattr(doc, "custom_name", None) or title,
        title=title,
        owner_type=str(doc.owner_type or "candidate"),
        owner_id=str(doc.owner_id or doc.candidate_id),
        number=doc.number,
        status=status_value,
        reminder_days_before=doc.reminder_days_before or 30,
        files=files,
        workflow=workflow_payload if isinstance(workflow_payload, dict) else {},
        source=doc.source,
        external_id=doc.external_id,
        verified_at=doc.verified_at,
        issue_date=_as_date(getattr(doc, "issue_date", None)),
        expire_date=_as_date(getattr(doc, "expire_date", None)),
        issued_at=_as_date(getattr(doc, "issue_date", None)),
        expires_at=_as_date(getattr(doc, "expire_date", None)),
        ordered_at=ordered_at,
        valid_from=valid_from,
        has_files=has_files,
        readiness_state=readiness_state,
        status_rank=status_rank,
        requested_from=requested_from_value,
        process_type=process_type_value,
        meta=meta_payload,
        extra=extra_payload,
        meta_json=meta_payload,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        reminders=reminders,
        version=getattr(doc, "version", None),
        last_check=last_check_out,
        responsible_user_id=responsible_user_id,
        responsible_name=responsible_name,
    )


async def _document_to_out_with_responsible(
    session: AsyncSession,
    tenant_id_for_candidate_lookup: str,
    doc,
    *,
    last_check=None,
) -> DocumentOut:
    """Attach recruiter (candidate owner) display for single-document responses."""
    m = await _batch_candidate_recruiter_labels(
        session, tenant_id_for_candidate_lookup, [str(doc.candidate_id)]
    )
    rid, rname = m.get(str(doc.candidate_id), (None, None))
    return await _document_to_out(
        session, doc, last_check=last_check, responsible_user_id=rid, responsible_name=rname
    )


async def _candidate_documents_read_access(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: UUID,
    *,
    workspace_own_company_header: Optional[str],
    viewer_channel: str = "recruitment",
) -> DocumentAccessContext:
    """ADR-014: one read-path resolver call for list / checklist / export / summary."""
    return await DocumentAccessResolver.resolve_for_candidate_documents(
        session,
        str(tenant_id),
        candidate_id,
        workspace_own_company_header=workspace_own_company_header,
        viewer_channel=viewer_channel,
    )


async def _candidate_documents_mutation_access(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: UUID,
    *,
    workspace_own_company_header: Optional[str],
    viewer_channel: str = "recruitment",
) -> DocumentAccessContext:
    """ADR-014: mutation-oriented resolver call (same contract as read; not the read helper)."""
    return await DocumentAccessResolver.resolve_for_candidate_document_mutations(
        session,
        str(tenant_id),
        candidate_id,
        workspace_own_company_header=workspace_own_company_header,
        viewer_channel=viewer_channel,
    )


async def _maybe_ensure_doc_own_company(
    session: AsyncSession,
    doc: Document,
    candidate_row: Optional[Candidate],
    active_own_company_id: Optional[str],
) -> None:
    cand = candidate_row
    if not cand and doc.candidate_id:
        cand = (
            await session.execute(
                select(Candidate).where(
                    Candidate.id == doc.candidate_id,
                    Candidate.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
    if cand:
        ensure_document_own_company_matches(doc, cand, active_own_company_id)


async def _fetch_document_with_visibility(
    session: AsyncSession,
    tenant_id: str,
    document_id: str,
) -> tuple[Optional[Document], str, Optional[Candidate]]:
    """Load document + candidate row without own-company slice enforcement."""
    visibility = get_tenant_visibility(session, tenant_id)
    doc = await get_document(session, tenant_id, document_id)
    if doc:
        candidate_row = (
            await session.execute(
                select(Candidate).where(
                    Candidate.id == doc.candidate_id,
                    Candidate.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return doc, str(getattr(doc, "tenant_id", tenant_id)), candidate_row

    doc = (
        await session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not doc:
        return None, tenant_id, None

    candidate_row = (
        await session.execute(
            select(Candidate).where(
                Candidate.id == doc.candidate_id,
                Candidate.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not candidate_row:
        return None, tenant_id, None
    if not candidate_visible_for_tenant_documents(candidate_row, tenant_id, visibility):
        return None, tenant_id, None
    return doc, str(getattr(doc, "tenant_id", tenant_id)), candidate_row


async def _get_document_with_access(
    session: AsyncSession,
    tenant_id: str,
    document_id: str,
    *,
    active_own_company_id: Optional[str] = None,
    viewer_channel: str = "recruitment",
) -> tuple[Optional[Document], str, Optional[Candidate]]:
    doc, doc_tenant_id, candidate_row = await _fetch_document_with_visibility(
        session, tenant_id, document_id
    )
    if doc:
        await _maybe_ensure_doc_own_company(session, doc, candidate_row, active_own_company_id)
        if not document_visible_to_viewer(getattr(doc, "doc_type", None), viewer_channel):
            return None, doc_tenant_id, candidate_row
    return doc, doc_tenant_id, candidate_row


async def _get_document_with_mutation_access(
    session: AsyncSession,
    tenant_id: str,
    document_id: str,
    *,
    workspace_own_company_header: Optional[str],
    enforce_destructive_process_lock: bool = False,
    viewer_channel: str = "recruitment",
) -> tuple[Optional[Document], str, Optional[Candidate], Optional[DocumentAccessContext]]:
    """ADR-014: resolver + resolved workspace slice before mutating a document row."""
    doc, doc_tenant_id, candidate_row = await _fetch_document_with_visibility(
        session, tenant_id, document_id
    )
    if not doc:
        return None, tenant_id, None, None
    doc_access: Optional[DocumentAccessContext] = None
    if doc.candidate_id:
        cid = UUID(str(doc.candidate_id))
        if enforce_destructive_process_lock:
            doc_access = await DocumentAccessResolver.resolve_for_candidate_destructive_document_mutations(
                session,
                tenant_id,
                cid,
                workspace_own_company_header=workspace_own_company_header,
                viewer_channel=viewer_channel,
            )
        else:
            doc_access = await _candidate_documents_mutation_access(
                session,
                tenant_id,
                cid,
                workspace_own_company_header=workspace_own_company_header,
                viewer_channel=viewer_channel,
            )
        ensure_document_own_company_matches(
            doc,
            doc_access.candidate_context.candidate,
            doc_access.resolved_workspace_own_company_id,
        )
        candidate_row = doc_access.candidate_context.candidate
        if doc_access.viewer_channel != "recruitment":
            raise HTTPException(
                status_code=403,
                detail="Document mutations require recruitment viewer channel",
            )
    else:
        await _maybe_ensure_doc_own_company(
            session, doc, candidate_row, workspace_own_company_header
        )
    return doc, doc_tenant_id, candidate_row, doc_access


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return ""


def _iso(value: Any) -> Optional[str]:
    try:
        if hasattr(value, "isoformat"):
            return value.isoformat()
    except Exception:
        return None
    return str(value) if value is not None else None


def _profile_from_context(cand_ctx: CandidateDocsContext) -> Dict[str, Any]:
    candidate = cand_ctx.candidate
    contacts = {}
    personal = {}
    extra = {}
    try:
        contacts = candidate._get_contacts()
    except Exception:
        contacts = getattr(candidate, "contacts", {}) or {}
    try:
        personal = candidate._get_personal_data()
    except Exception:
        personal = getattr(candidate, "personal_data", {}) or {}
    try:
        extra = candidate._get_extra()
    except Exception:
        extra = getattr(candidate, "extra", {}) or {}

    status_reason = getattr(candidate, "status_reason", None) or []
    if isinstance(status_reason, str):
        try:
            parsed = json.loads(status_reason)
            if isinstance(parsed, list):
                status_reason = parsed
        except Exception:
            status_reason = [status_reason]
    if not isinstance(status_reason, list):
        status_reason = []

    languages = getattr(candidate, "languages", None) or personal.get("languages") or extra.get("languages")
    if isinstance(languages, (list, tuple, set)):
        languages = ", ".join(str(x) for x in languages if str(x).strip())

    return {
        "tenant_id": cand_ctx.owner_tenant_id,
        "candidate_id": str(candidate.id),
        "short_id": getattr(candidate, "short_id", None),
        "first_name": getattr(candidate, "first_name", None),
        "last_name": getattr(candidate, "last_name", None),
        "email": contacts.get("email") or getattr(candidate, "email", None),
        "phone_country_code": contacts.get("phone_country_code") or getattr(candidate, "phone_country_code", None),
        "phone": contacts.get("phone") or getattr(candidate, "phone", None),
        "stage": getattr(candidate, "stage", None),
        "status": getattr(candidate, "status", None) or getattr(candidate, "stage", None),
        "status_reason": ", ".join(str(x) for x in status_reason if str(x).strip()),
        "manager_id": cand_ctx.manager_raw or getattr(candidate, "manager", None),
        "manager_name": cand_ctx.manager_name or cand_ctx.manager_raw or getattr(candidate, "manager", None),
        "recruiter_id": cand_ctx.recruiter_id,
        "recruiter_name": cand_ctx.recruiter_name or cand_ctx.recruiter_short or cand_ctx.recruiter_id,
        "company_id": getattr(candidate, "company_id", None),
        "company_name": cand_ctx.company_name,
        "vacancy_id": getattr(candidate, "vacancy_id", None),
        "vacancy_title": cand_ctx.vacancy_title,
        "languages": languages,
        "country_code": personal.get("country_code") or getattr(candidate, "country_code", None),
        "city": personal.get("city") or getattr(candidate, "city", None),
        "address": personal.get("address") or getattr(candidate, "address", None),
        "birth_date": _iso(getattr(candidate, "birth_date", None)) or personal.get("birth_date"),
        "note": getattr(candidate, "note", None),
        "source": getattr(candidate, "source", None),
        "origin": _safe_json(getattr(candidate, "origin", None)),
        "contacts_json": _safe_json(contacts),
        "personal_data_json": _safe_json(personal),
        "extra_json": _safe_json(extra),
        "docs_progress_json": _safe_json(getattr(candidate, "docs_progress", None)),
        "created_at": _iso(getattr(candidate, "created_at", None)),
        "updated_at": _iso(getattr(candidate, "updated_at", None)),
        "downloaded_at": datetime.utcnow().isoformat() + "Z",
    }


def _add_document_file_to_zip(
    doc: Document,
    archive: zipfile.ZipFile,
    index: int,
    used_names: set[str],
) -> Optional[str]:
    try:
        path, _, original_name = resolve_document_file(doc)
    except FileNotFoundError:
        return None
    base_label = sanitize_filename(
        (getattr(doc, "custom_name", None) or getattr(doc, "title", None) or getattr(doc, "doc_type", None) or f"document_{index}")
    ) or f"document_{index}"
    number = getattr(doc, "number", None)
    stem_parts = [f"{index:02d}", base_label]
    if number:
        stem_parts.append(str(number))
    stem = "_".join(part for part in stem_parts if part)
    ext = PathLib(original_name).suffix
    candidate_name = f"{stem}{ext}" if ext else stem
    unique_name = candidate_name
    counter = 1
    while unique_name in used_names:
        counter += 1
        unique_name = f"{stem}_{counter}{ext}" if ext else f"{stem}_{counter}"
    used_names.add(unique_name)
    with path.open("rb") as fh:
        archive.writestr(unique_name, fh.read())
    return unique_name


async def _list_documents_for_candidate(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: UUID,
    *,
    status: StatusFilter,
    doc_type: Optional[str],
    include_deleted: bool,
    include_last_check: bool,
    owner_context: Optional[str],
    owner_context_defaults: Optional[Dict[str, Any]],
    fill_missing: bool,
    limit: Optional[int],
    offset: Optional[int],
    owner_tenant_id: Optional[str] = None,
    allowed_tenant_ids: Optional[set[str]] = None,
    active_own_company_id: Optional[str] = None,
    viewer_channel: str = "recruitment",
) -> List[DocumentOut]:
    doc_tenant_id = owner_tenant_id or tenant_id
    tenants_scope = set(allowed_tenant_ids or {doc_tenant_id, tenant_id})
    raw_docs = await list_candidate_documents(
        session,
        doc_tenant_id,
        str(candidate_id),
        status=status,
        type_filter=doc_type,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
        allowed_tenant_ids=tenants_scope,
        active_own_company_id=active_own_company_id,
    )
    last_db_fetch_total = len(raw_docs)
    docs = [
        d
        for d in raw_docs
        if document_visible_to_viewer(getattr(d, "doc_type", None), viewer_channel)
    ]
    last_db_visible = len(docs)
    last_checks: Dict[str, Any] = {}
    if include_last_check:
        last_checks = await get_last_document_checks_map(
            session,
            doc_tenant_id,
            [str(doc.id) for doc in docs],
        )
    cand_labels = await _batch_candidate_recruiter_labels(
        session, doc_tenant_id, [str(d.candidate_id) for d in docs]
    )
    result: List[DocumentOut] = []
    for doc in docs:
        last_check = last_checks.get(str(doc.id)) if include_last_check else None
        rid, rname = cand_labels.get(str(doc.candidate_id), (None, None))
        result.append(
            await _document_to_out(
                session, doc, last_check=last_check, responsible_user_id=rid, responsible_name=rname
            )
        )

    if fill_missing:
        ctx = _owner_context_or_400(owner_context, candidate_id, owner_context_defaults)
        ruleset_version = await ensure_ruleset_seed(
            session,
            doc_tenant_id,
            load_default_ruleset(),
            own_company_id=active_own_company_id,
        )
        await session.commit()
        ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
        checklist = compute_candidate_checklist(ctx, ruleset_payload)
        auto_docs = await list_candidate_documents(
            session,
            doc_tenant_id,
            str(candidate_id),
            include_deleted=False,
            allowed_tenant_ids=tenants_scope,
            active_own_company_id=active_own_company_id,
        )
        auto_created = await _ensure_auto_ordered_documents(
            session,
            doc_tenant_id,
            str(candidate_id),
            checklist,
            auto_docs,
        )
        if auto_created:
            await session.commit()
            raw_docs = await list_candidate_documents(
                session,
                doc_tenant_id,
                str(candidate_id),
                status=status,
                type_filter=doc_type,
                include_deleted=include_deleted,
                limit=limit,
                offset=offset,
                allowed_tenant_ids=tenants_scope,
                active_own_company_id=active_own_company_id,
            )
            last_db_fetch_total = len(raw_docs)
            docs = [
                d
                for d in raw_docs
                if document_visible_to_viewer(getattr(d, "doc_type", None), viewer_channel)
            ]
            last_db_visible = len(docs)
            if include_last_check:
                last_checks = await get_last_document_checks_map(
                    session,
                    doc_tenant_id,
                    [str(doc.id) for doc in docs],
                )
            cand_labels = await _batch_candidate_recruiter_labels(
                session, doc_tenant_id, [str(d.candidate_id) for d in docs]
            )
            result = []
            for doc in docs:
                last_check = last_checks.get(str(doc.id)) if include_last_check else None
                rid, rname = cand_labels.get(str(doc.candidate_id), (None, None))
                result.append(
                    await _document_to_out(
                        session, doc, last_check=last_check, responsible_user_id=rid, responsible_name=rname
                    )
                )

        serialized = [item.model_dump() for item in result]
        synthetic_docs = _build_synthetic_documents(
            tenant_id, candidate_id, checklist, serialized
        )
        result.extend(
            d
            for d in synthetic_docs
            if document_visible_to_viewer(d.doc_type, viewer_channel)
        )
    synth_returned = sum(
        1 for r in result if str(getattr(r, "id", "")).startswith("synthetic::")
    )
    _log_document_access_visibility(
        surface="candidate_documents_list",
        candidate_id=candidate_id,
        viewer_channel=viewer_channel,
        db_fetch_total=last_db_fetch_total,
        db_visible=last_db_visible,
        response_items=len(result),
        synthetics_returned=synth_returned,
    )
    return result


@router.get("/health")
async def health():
    return {"ok": True, "module": "documents"}


@router.get("/document-types", response_model=List[DocumentTypeOut])
async def api_list_document_types(
    db_dep=Depends(get_db_with_tenant),
) -> List[DocumentTypeOut]:
    session, tenant_id = db_dep
    rows = await list_document_types(session, str(tenant_id))
    result: List[DocumentTypeOut] = []
    for row in rows:
        meta_schema = getattr(row, "metadata_schema", None) or _load_meta_schema_for(
            getattr(row, "code", "")
        )
        required_files = getattr(row, "required_files", None) or {}
        expiry_rule = getattr(row, "expiry_rule", None) or {}
        duplicate_policy = getattr(row, "duplicate_policy", None)
        result.append(
            DocumentTypeOut(
                id=str(row.id),
                code=row.code,
                name=row.name,
                description=row.description,
                kind=getattr(row.kind, "value", row.kind)
                if getattr(row, "kind", None)
                else None,
                requested_from=getattr(row.requested_from, "value", row.requested_from)
                if getattr(row, "requested_from", None)
                else None,
                process_type=getattr(row.process_type, "value", row.process_type)
                if getattr(row, "process_type", None)
                else None,
                default_expire_in_days=getattr(row, "default_expire_in_days", None),
                valid_days=getattr(row, "default_expire_in_days", None),
                aliases=list(getattr(row, "aliases", []) or []),
                required_meta=list(getattr(row, "required_meta", []) or []),
                owner_summary_weight=int(getattr(row, "owner_summary_weight", 0) or 0),
                i18n_key=getattr(row, "i18n_key", None),
                requires_custom_name=bool(getattr(row, "requires_custom_name", False)),
                required=getattr(row, "is_active", True) or None,
                meta_schema=meta_schema or None,
                title=getattr(row, "title", None) or {},
                required_files=required_files,
                expiry_rule=expiry_rule,
                duplicate_policy=duplicate_policy.value
                if hasattr(duplicate_policy, "value")
                else duplicate_policy,
                orderable=bool(getattr(row, "orderable", False)),
            )
        )
    return result


@router.post("/document-types/{code}/validate-meta")
async def api_validate_document_meta(
    code: str,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    schema = _load_meta_schema_for(code)
    if not schema:
        raise HTTPException(status_code=404, detail="Meta schema not found")
    errors = validate_meta(payload or {}, schema)
    return {"valid": not errors, "errors": errors}


@router.get("/document-types/{code}/meta-schema")
async def api_get_document_type_meta_schema(code: str) -> Dict[str, Any]:
    return _load_meta_schema_for(code) or {}


@router.get("/document-types/{code}/schema")
async def api_get_document_type_schema(code: str) -> Dict[str, Any]:
    return _load_meta_schema_for(code) or {}


@router.get(
    "/documents",
    response_model=List[DocumentOut],
)
async def api_list_documents_legacy(
    candidate_id: Optional[UUID] = Query(
        None, description="Candidate identifier. If omitted, returns tenant-wide documents."
    ),
    status: StatusFilter = Query(None, description="Filter by status"),
    doc_type: Optional[str] = Query(None, alias="type"),
    include_deleted: bool = Query(False),
    include_last_check: bool = Query(
        True, description="Attach last reviewer decision metadata"
    ),
    owner_context: Optional[str] = Query(
        None, description="Optional JSON object with candidate/vacancy context"
    ),
    fill_missing: bool = Query(
        True,
        description="Include synthetic entries for required checklist items that are missing",
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=500, description="Limit number of documents returned"
    ),
    offset: Optional[int] = Query(
        None, ge=0, description="Offset (for pagination)"
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> List[DocumentOut]:
    session, tenant_id = db_dep
    if candidate_id is None:
        stmt = (
            select(Document)
            .where(Document.tenant_id == str(tenant_id))
            .order_by(Document.updated_at.desc())
        )
        scope_t = tenant_documents_own_company_clause(own_company_id)
        if scope_t is not None:
            stmt = stmt.where(scope_t)
        if not include_deleted:
            stmt = stmt.where(Document.deleted_at.is_(None))
        if status:
            try:
                status_enum = normalize_status(status)
            except ValueError as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=422, detail=str(exc))
            stmt = stmt.where(Document.status == status_enum)
        if doc_type:
            stmt = stmt.where(Document.doc_type == normalize_doc_type(doc_type))
        if offset:
            stmt = stmt.offset(int(offset))
        if limit:
            stmt = stmt.limit(int(limit))
        docs = (await session.execute(stmt)).scalars().all()
        docs = [
            d
            for d in docs
            if document_visible_to_viewer(getattr(d, "doc_type", None), viewer_channel)
        ]
        if not docs:
            return []
        last_checks: Dict[str, Any] = {}
        if include_last_check:
            last_checks = await get_last_document_checks_map(
                session, str(tenant_id), [str(doc.id) for doc in docs]
            )
        cand_labels = await _batch_candidate_recruiter_labels(
            session, str(tenant_id), [str(d.candidate_id) for d in docs]
        )
        result: List[DocumentOut] = []
        for doc in docs:
            last_check = last_checks.get(str(doc.id)) if include_last_check else None
            rid, rname = cand_labels.get(str(doc.candidate_id), (None, None))
            result.append(
                await _document_to_out(
                    session, doc, last_check=last_check, responsible_user_id=rid, responsible_name=rname
                )
            )
        return result

    doc_access = await _candidate_documents_read_access(
        session,
        str(tenant_id),
        candidate_id,
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    return await _list_documents_for_candidate(
        session,
        str(tenant_id),
        candidate_id,
        status=status,
        doc_type=doc_type,
        include_deleted=include_deleted,
        include_last_check=include_last_check,
        owner_context=owner_context,
        owner_context_defaults=_candidate_owner_context_defaults(cand_ctx.candidate, candidate_id),
        fill_missing=fill_missing,
        limit=limit,
        offset=offset,
        owner_tenant_id=cand_ctx.owner_tenant_id,
        allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
        active_own_company_id=own_for_docs,
        viewer_channel=viewer_channel,
    )


@router.get(
    "/candidate/{candidate_id}/documents",
    response_model=List[DocumentOut],
)
async def api_list_candidate_documents(
    candidate_id: UUID = Path(...),
    status: StatusFilter = Query(None, description="Filter by status"),
    doc_type: Optional[str] = Query(None, alias="type"),
    include_deleted: bool = Query(False),
    include_last_check: bool = Query(
        True, description="Attach last reviewer decision metadata"
    ),
    owner_context: Optional[str] = Query(
        None, description="Optional JSON object with candidate/vacancy context"
    ),
    fill_missing: bool = Query(
        True,
        description="Include synthetic entries for required checklist items that are missing",
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=500, description="Limit number of documents returned"
    ),
    offset: Optional[int] = Query(
        None, ge=0, description="Offset (for pagination)"
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> List[DocumentOut]:
    session, tenant_id = db_dep
    doc_access = await _candidate_documents_read_access(
        session,
        str(tenant_id),
        candidate_id,
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    return await _list_documents_for_candidate(
        session,
        str(tenant_id),
        candidate_id,
        status=status,
        doc_type=doc_type,
        include_deleted=include_deleted,
        include_last_check=include_last_check,
        owner_context=owner_context,
        owner_context_defaults=_candidate_owner_context_defaults(cand_ctx.candidate, candidate_id),
        fill_missing=fill_missing,
        limit=limit,
        offset=offset,
        owner_tenant_id=cand_ctx.owner_tenant_id,
        allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
        active_own_company_id=own_for_docs,
        viewer_channel=viewer_channel,
    )


@router.post(
    "/candidate/{candidate_id}/documents",
    response_model=DocumentOut,
    status_code=201,
)
async def api_create_candidate_document(
    candidate_id: UUID,
    payload: DocumentCreateIn,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
    current_user: UserCtx = Depends(get_current_user),
) -> DocumentOut:
    session, tenant_id = db_dep
    from backend.app.services.candidate_operational_write import ensure_candidate_operational_write_allowed

    await ensure_candidate_operational_write_allowed(
        session,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        role=str(getattr(current_user, "role", "") or ""),
    )
    logger.info(f"[create_doc] Received request for candidate {candidate_id}, parsed payload: {payload.model_dump()}")
    doc_access = await _candidate_documents_mutation_access(
        session,
        str(tenant_id),
        candidate_id,
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
    )
    cand_ctx = doc_access.candidate_context
    if doc_access.viewer_channel != "recruitment":
        raise HTTPException(
            status_code=403,
            detail="Document mutations require recruitment viewer channel",
        )
    try:
        doc_type = payload.effective_doc_type()
    except ValueError as exc:
        payload_dump = payload.model_dump()
        logger.error(
            f"[create_doc] effective_doc_type failed: {exc}, "
            f"payload keys: {list(payload_dump.keys())}, "
            f"doc_type: {payload_dump.get('doc_type')}, "
            f"type: {payload_dump.get('type')}, "
            f"key: {payload_dump.get('key')}, "
            f"meta: {payload_dump.get('meta')}"
        )
        raise HTTPException(status_code=422, detail=str(exc)) from None

    data = payload.model_dump(by_alias=True, exclude_unset=True)
    data["tenant_id"] = cand_ctx.owner_tenant_id
    data["candidate_id"] = str(candidate_id)
    data["doc_type"] = doc_type
    data.pop("type", None)
    data.pop("key", None)
    meta_json_payload = data.pop("meta_json", None)
    if meta_json_payload is not None and "meta" not in data:
        data["meta"] = meta_json_payload
    owner_id = data.get("owner_id") or str(candidate_id)
    data["owner_id"] = owner_id
    data["own_company_id"] = doc_access.resolved_workspace_own_company_id

    try:
        doc = await create_document(session, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    await reminders_service.schedule_document_expiry_reminders(
        session, cand_ctx.owner_tenant_id, doc
    )
    await session.commit()
    await session.refresh(doc)
    return await _document_to_out_with_responsible(session, cand_ctx.owner_tenant_id, doc)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentWithChecksOut,
)
async def api_get_document(
    document_id: UUID,
    include_checks: bool = Query(False),
    include_last_check: bool = Query(True),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> DocumentWithChecksOut:
    session, tenant_id = db_dep
    access_kind = _db_access_kind(session)
    doc, doc_tenant_id, _ = await _get_document_with_access(
        session,
        str(tenant_id),
        str(document_id),
        active_own_company_id=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_METADATA_READ,
            result="denied",
            severity="low",
            source="http:documents_router:get_document",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            reason="document_not_found_or_invisible",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    checks: List[Any] = []
    last_check = None
    if include_checks:
        checks = await list_document_checks(
            session, doc_tenant_id, str(document_id)
        )
        last_check = checks[0] if checks else None
    elif include_last_check:
        last_map = await get_last_document_checks_map(
            session, doc_tenant_id, [str(document_id)]
        )
        last_check = last_map.get(str(document_id))

    out = await _document_to_out_with_responsible(session, doc_tenant_id, doc, last_check=last_check)
    if include_checks:
        checks_payload = [_check_to_out(item) for item in checks]
    else:
        checks_payload = []
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_METADATA_READ,
        result="success",
        severity="info",
        source="http:documents_router:get_document",
        tenant_id=str(doc_tenant_id),
        document_id=str(document_id),
        access_kind=access_kind,
        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
        candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
    )
    return DocumentWithChecksOut(**out.model_dump(), checks=checks_payload)


@router.patch(
    "/documents/{document_id}",
    response_model=DocumentOut,
)
async def api_patch_document(
    document_id: UUID,
    payload: DocumentUpdateIn,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> DocumentOut:
    session, tenant_id = db_dep
    doc, doc_tenant_id, _, _ = await _get_document_with_mutation_access(
        session,
        str(tenant_id),
        str(document_id),
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    update_data = payload.model_dump(by_alias=True, exclude_unset=True)
    meta_json_payload = update_data.pop("meta_json", None)
    if meta_json_payload is not None and "meta" not in update_data:
        update_data["meta"] = meta_json_payload
    try:
        doc = await update_document(
            session,
            doc_tenant_id,
            str(document_id),
            update_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await reminders_service.schedule_document_expiry_reminders(
        session, doc_tenant_id, doc
    )
    await session.commit()
    await session.refresh(doc)
    return await _document_to_out_with_responsible(session, doc_tenant_id, doc)


@router.delete("/documents/{document_id}", status_code=204)
async def api_delete_document(
    document_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> Response:
    session, tenant_id = db_dep
    doc, doc_tenant_id, _, _ = await _get_document_with_mutation_access(
        session,
        str(tenant_id),
        str(document_id),
        workspace_own_company_header=own_company_id,
        enforce_destructive_process_lock=True,
        viewer_channel=viewer_channel,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    deleted = await soft_delete_document(session, doc_tenant_id, str(document_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    await reminders_service.cancel_entity_reminders(
        session,
        tenant_id=doc_tenant_id,
        entity_type="document",
        entity_id=str(document_id),
    )
    await reminders_service.cancel_document_step_reminders(
        session,
        tenant_id=doc_tenant_id,
        document_id=str(document_id),
    )
    await session.commit()
    return Response(status_code=204)


@router.post("/documents/{document_id}/presign-upload")
async def api_presign_upload(
    document_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> dict[str, Any]:
    session, tenant_id = db_dep
    access_kind = _db_access_kind(session)
    doc, doc_tenant_id, _, _ = await _get_document_with_mutation_access(
        session,
        str(tenant_id),
        str(document_id),
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:presign_upload",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            reason="document_not_found",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    out = presign_upload(str(document_id))
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
        result="success",
        severity="info",
        source="http:documents_router:presign_upload",
        tenant_id=str(doc_tenant_id),
        document_id=str(document_id),
        access_kind=access_kind,
        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
        candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
        upload_presign=True,
    )
    return out


@router.get("/documents/{document_id}/file-url")
async def api_get_document_file_url(
    document_id: UUID,
    version: Optional[int] = Query(None),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> dict[str, Any]:
    session, tenant_id = db_dep
    access_kind = _db_access_kind(session)
    doc, doc_tenant_id, _ = await _get_document_with_access(
        session,
        str(tenant_id),
        str(document_id),
        active_own_company_id=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:get_file_url",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            reason="document_not_found_or_invisible",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    files = await ensure_document_files(session, doc)
    entry = select_file_entry(files, version=version)
    if not entry:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:get_file_url",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="file_entry_not_found",
            file_version=version,
        )
        raise HTTPException(status_code=404, detail="File not found")
    try:
        path = resolve_file_path(entry)
    except ValueError as exc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:get_file_url",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="invalid_file_entry",
            file_version=entry.get("version") if isinstance(entry.get("version"), int) else None,
        )
        raise HTTPException(status_code=404, detail="File not found") from exc
    if not path.exists():
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:get_file_url",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="file_not_on_disk",
            file_version=entry.get("version") if isinstance(entry.get("version"), int) else None,
        )
        raise HTTPException(status_code=404, detail="File not found")
    url = entry.get("url") or doc.path
    if not url:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:get_file_url",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="url_not_configured",
            file_version=entry.get("version") if isinstance(entry.get("version"), int) else None,
        )
        raise HTTPException(status_code=404, detail="File not found")
    presigned_shape = url_looks_presigned(str(url))
    fv = entry.get("version")
    file_version = int(fv) if isinstance(fv, int) else None
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_FILE_ACCESS_REQUESTED,
        result="success",
        severity="info",
        source="http:documents_router:get_file_url",
        tenant_id=str(doc_tenant_id),
        document_id=str(document_id),
        access_kind=access_kind,
        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
        candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
        file_version=file_version,
        has_presigned_url_shape=presigned_shape,
    )
    if presigned_shape:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
            result="success",
            severity="info",
            source="http:documents_router:get_file_url",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            file_version=file_version,
            has_presigned_url_shape=True,
        )
    return {
        "url": url,
        "expires_at": None,
        "version": entry.get("version"),
        "uploaded_at": entry.get("uploaded_at"),
    }


@router.get("/documents/{document_id}/file")
async def api_download_document_file(
    document_id: UUID,
    version: Optional[int] = Query(None),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> FileResponse:
    session, tenant_id = db_dep
    access_kind = _db_access_kind(session)
    doc, doc_tenant_id, _ = await _get_document_with_access(
        session,
        str(tenant_id),
        str(document_id),
        active_own_company_id=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:download_file",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            reason="document_not_found_or_invisible",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    files = await ensure_document_files(session, doc)
    entry = select_file_entry(files, version=version)
    if not entry:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:download_file",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="file_entry_not_found",
            file_version=version,
        )
        raise HTTPException(status_code=404, detail="File not found")
    try:
        path = resolve_file_path(entry)
    except ValueError as exc:
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:download_file",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="invalid_file_entry",
            file_version=entry.get("version") if isinstance(entry.get("version"), int) else None,
        )
        raise HTTPException(status_code=404, detail="File not found") from exc
    if not path.exists():
        emit_document_security_event_v1(
            event_type=EVENT_DOCUMENT_SIGNED_URL_DENIED,
            result="denied",
            severity="low",
            source="http:documents_router:download_file",
            tenant_id=str(doc_tenant_id),
            document_id=str(document_id),
            access_kind=access_kind,
            document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
            candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
            reason="file_not_on_disk",
            file_version=entry.get("version") if isinstance(entry.get("version"), int) else None,
        )
        raise HTTPException(status_code=404, detail="File not found")
    media_type = file_entry_media_type(entry)
    filename = entry.get("name") or path.name
    response = FileResponse(
        path,
        media_type=media_type,
        filename=filename,
    )
    version_value = entry.get("version")
    if version_value is not None:
        response.headers["X-Document-Version"] = str(version_value)
    fv = entry.get("version")
    file_version = int(fv) if isinstance(fv, int) else None
    emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_FILE_DOWNLOADED,
        result="success",
        severity="info",
        source="http:documents_router:download_file",
        tenant_id=str(doc_tenant_id),
        document_id=str(document_id),
        access_kind=access_kind,
        document_class=str(doc.doc_type) if getattr(doc, "doc_type", None) else None,
        candidate_id=str(doc.candidate_id) if doc.candidate_id else None,
        file_version=file_version,
        response_mode="file_stream",
    )
    return response


@router.get("/documents/{document_id}/checks", response_model=List[DocumentCheckOut])
async def api_list_document_checks(
    document_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> List[DocumentCheckOut]:
    session, tenant_id = db_dep
    doc, doc_tenant_id, _ = await _get_document_with_access(
        session,
        str(tenant_id),
        str(document_id),
        active_own_company_id=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    checks = await list_document_checks(session, doc_tenant_id, str(document_id))
    return [_check_to_out(item) for item in checks]


@router.post("/documents/{document_id}/check", response_model=DocumentOut)
async def api_check_document(
    document_id: UUID,
    body: Dict[str, Any],
    current_user: UserCtx = Depends(get_current_user),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> DocumentOut:
    session, tenant_id = db_dep
    doc, doc_tenant_id, _, _ = await _get_document_with_mutation_access(
        session,
        str(tenant_id),
        str(document_id),
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    decision = (body.get("decision") or "").strip().lower()
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="decision must be approved|rejected")
    status_value = (
        DocumentStatus.approved.value if decision == "approved" else DocumentStatus.rejected.value
    )
    update_payload = {
        "status": status_value,
    }
    meta_update = body.get("meta") or body.get("meta_json")
    if isinstance(meta_update, dict):
        update_payload["meta"] = meta_update
    doc = await update_document(
        session,
        doc_tenant_id,
        str(document_id),
        update_payload,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    reviewer_id = body.get("reviewer_id") or getattr(current_user, "sub", None)
    payload = body.get("payload") or body.get("meta_json") or {}
    check = await create_document_check(
        session,
        doc_tenant_id,
        str(document_id),
        reviewer_id=reviewer_id,
        decision=decision,
        reason_code=body.get("reason_code"),
        comment=body.get("comment"),
        payload=payload if isinstance(payload, dict) else {},
    )
    await reminders_service.schedule_document_expiry_reminders(
        session, doc_tenant_id, doc
    )
    await session.commit()
    await session.refresh(doc)
    return await _document_to_out_with_responsible(session, doc_tenant_id, doc, last_check=check)


async def fetch_candidate_documents_summary_response(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: UUID,
    owner_context: Optional[str] = None,
    *,
    active_own_company_id: Optional[str] = None,
    viewer_channel: str = "recruitment",
) -> Dict[str, Any]:
    """Same payload as GET /candidate/{id}/documents/summary (work-panel bundle, tests, etc.)."""
    doc_access = await _candidate_documents_read_access(
        session,
        tenant_id,
        candidate_id,
        workspace_own_company_header=active_own_company_id,
        viewer_channel=viewer_channel,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    ctx = _owner_context_or_400(
        owner_context,
        candidate_id,
        _candidate_owner_context_defaults(cand_ctx.candidate, candidate_id),
    )
    docs = await list_candidate_documents(
        session,
        cand_ctx.owner_tenant_id,
        str(candidate_id),
        include_deleted=False,
        allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
        active_own_company_id=own_for_docs,
    )
    ruleset_version = None
    ruleset_payload: Dict[str, Any]
    try:
        ruleset_version = await ensure_ruleset_seed(
            session,
            cand_ctx.owner_tenant_id,
            load_default_ruleset(),
            own_company_id=own_for_docs,
        )
        await session.commit()
        ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    except Exception as exc:  # pragma: no cover - defensive for legacy DBs
        await session.rollback()
        logger.warning(
            "[documents] ruleset seed failed tenant=%s candidate=%s: %s",
            tenant_id,
            candidate_id,
            exc,
        )
        ruleset_version = None
        ruleset_payload = load_default_ruleset()
    doc_ids = [str(doc.id) for doc in docs]
    last_checks = await get_last_document_checks_map(
        session, cand_ctx.owner_tenant_id, doc_ids
    )
    resp_pair = await _batch_candidate_recruiter_labels(
        session, cand_ctx.owner_tenant_id, [str(candidate_id)]
    )
    rid, rname = resp_pair.get(str(candidate_id), (None, None))
    serialized_docs_full: List[Dict[str, Any]] = []
    for doc in docs:
        last_check = last_checks.get(str(doc.id))
        serialized_docs_full.append(
            (
                await _document_to_out(
                    session, doc, last_check=last_check, responsible_user_id=rid, responsible_name=rname
                )
            ).model_dump()
        )

    def _serialized_visible(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            d
            for d in rows
            if document_visible_to_viewer(
                d.get("doc_type") or d.get("type_code") or d.get("type"),
                viewer_channel,
            )
        ]

    serialized_visible = _serialized_visible(serialized_docs_full)
    summary = compute_owner_summary(ctx, ruleset_payload, serialized_visible)
    from backend.app.services.document_hub_delivery_contract import (
        evaluate_document_hub_requirements_via_contract,
        merge_document_hub_requirements_into_summary_via_contract,
    )

    hub_requirements = await evaluate_document_hub_requirements_via_contract(
        session,
        tenant_id=cand_ctx.owner_tenant_id,
        candidate=cand_ctx.candidate,
    )
    summary = merge_document_hub_requirements_into_summary_via_contract(summary, hub_requirements)
    checklist = _fill_checklist_defaults(summary.get("checklist") or {}, ruleset_payload)
    summary["checklist"] = checklist
    auto_created = await _ensure_auto_ordered_documents(
        session,
        cand_ctx.owner_tenant_id,
        str(candidate_id),
        checklist,
        docs,
    )
    if auto_created:
        await session.commit()
        docs = await list_candidate_documents(
            session,
            cand_ctx.owner_tenant_id,
            str(candidate_id),
            include_deleted=False,
            allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
            active_own_company_id=own_for_docs,
        )
        last_checks = await get_last_document_checks_map(
            session,
            cand_ctx.owner_tenant_id,
            [str(doc.id) for doc in docs],
        )
        serialized_docs_full = [
            (
                await _document_to_out(
                    session,
                    doc,
                    last_check=last_checks.get(str(doc.id)),
                    responsible_user_id=rid,
                    responsible_name=rname,
                )
            ).model_dump()
            for doc in docs
        ]
        serialized_visible = _serialized_visible(serialized_docs_full)
        summary = compute_owner_summary(ctx, ruleset_payload, serialized_visible)
        summary = merge_document_hub_requirements_into_summary_via_contract(summary, hub_requirements)
        checklist = _fill_checklist_defaults(summary.get("checklist") or {}, ruleset_payload)
        summary["checklist"] = checklist
    synthetic_models = _build_synthetic_documents(
        cand_ctx.owner_tenant_id, candidate_id, checklist, serialized_docs_full
    )
    synthetic_docs = [
        doc.model_dump()
        for doc in synthetic_models
        if document_visible_to_viewer(doc.doc_type, viewer_channel)
    ]
    physical_total = len(docs)
    physical_visible = len(serialized_visible)
    synth_built = len(synthetic_models)
    synth_vis = len(synthetic_docs)
    _log_document_access_visibility(
        surface="candidate_documents_summary",
        candidate_id=candidate_id,
        viewer_channel=viewer_channel,
        db_fetch_total=physical_total,
        db_visible=physical_visible,
        response_items=len(serialized_visible) + len(synthetic_docs),
        synthetics_returned=synth_vis,
    )
    out: Dict[str, Any] = {
        "candidate_id": str(candidate_id),
        "summary": summary,
        "documents": serialized_visible + synthetic_docs,
        "ruleset_version": (
            _ruleset_to_out(ruleset_version).model_dump()
            if ruleset_version is not None
            else {
                "id": None,
                "version": 0,
                "is_active": True,
                "comment": "fallback-default",
                "created_at": datetime.now(timezone.utc),
                "documents": [],
            }
        ),
        "checklist": checklist,
    }
    if hub_requirements and hub_requirements.get("applied"):
        out["requirement_engine"] = hub_requirements
        out["source_layer"] = hub_requirements.get("source_layer")
    if document_access_trace_response_enabled():
        out["document_access_trace"] = {
            "surface": "candidate_documents_summary",
            "viewer_channel": viewer_channel,
            "viewer_readable_scopes": sorted(doc_access.viewer_readable_scopes),
            "physical_documents_total": physical_total,
            "physical_documents_visible_to_viewer": physical_visible,
            "physical_documents_filtered_out": max(0, physical_total - physical_visible),
            "synthetic_candidates_built": synth_built,
            "synthetic_documents_returned": synth_vis,
            "synthetic_documents_filtered_out": max(0, synth_built - synth_vis),
        }
    return out


@router.get(
    "/candidate/{candidate_id}/documents/summary",
)
async def api_candidate_documents_summary(
    candidate_id: UUID,
    owner_context: Optional[str] = Query(
        None,
        description="Optional JSON string with candidate/vacancy context",
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> Dict[str, Any]:
    session, tenant_id = db_dep
    return await fetch_candidate_documents_summary_response(
        session,
        str(tenant_id),
        candidate_id,
        owner_context,
        active_own_company_id=own_company_id,
        viewer_channel=viewer_channel,
    )


@router.get("/candidate/{candidate_id}/checklist")
async def api_candidate_checklist(
    candidate_id: UUID,
    owner_context: Optional[str] = Query(
        None,
        description="Optional JSON string with candidate/vacancy context",
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> Dict[str, Any]:
    session, tenant_id = db_dep
    doc_access = await _candidate_documents_read_access(
        session,
        str(tenant_id),
        candidate_id,
        workspace_own_company_header=own_company_id,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    ctx = _owner_context_or_400(
        owner_context,
        candidate_id,
        _candidate_owner_context_defaults(cand_ctx.candidate, candidate_id),
    )
    ruleset_version = await ensure_ruleset_seed(
        session,
        cand_ctx.owner_tenant_id,
        load_default_ruleset(),
        own_company_id=own_for_docs,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    checklist = _fill_checklist_defaults(compute_candidate_checklist(ctx, ruleset_payload), ruleset_payload)
    from backend.app.services.document_hub_delivery_contract import (
        evaluate_document_hub_requirements_via_contract,
    )

    hub_requirements = await evaluate_document_hub_requirements_via_contract(
        session,
        tenant_id=cand_ctx.owner_tenant_id,
        candidate=cand_ctx.candidate,
    )
    if hub_requirements and hub_requirements.get("applied"):
        required_codes = [
            str(row.get("document_type_code") or "")
            for row in hub_requirements.get("required_documents") or []
            if isinstance(row, dict) and row.get("document_type_code")
        ]
        checklist["requiredTypes"] = required_codes
        checklist["source_layer"] = hub_requirements.get("source_layer")
    await log_ruleset_usage(
        session,
        cand_ctx.owner_tenant_id,
        str(ruleset_version.id),
        used_in="checklist",
        reference_id=str(candidate_id),
        meta={"context_keys": sorted(ctx.keys())[:10]},
    )
    await session.commit()
    response: Dict[str, Any] = {
        "candidate_id": str(candidate_id),
        "context": ctx,
        "checklist": checklist,
        "ruleset_version": _ruleset_to_out(ruleset_version).model_dump(),
    }
    if hub_requirements and hub_requirements.get("applied"):
        response["requirement_engine"] = hub_requirements
        response["source_layer"] = hub_requirements.get("source_layer")
    return response


@router.get("/candidate/{candidate_id}/documents/export.json")
async def api_export_documents_json(
    candidate_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> Dict[str, Any]:
    session, tenant_id = db_dep
    _source = "http:documents_router:export_documents_json"
    _export_type = "candidate_documents_json"
    doc_access, access_kind = await _candidate_documents_export_access(
        session,
        tenant_id,
        candidate_id,
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
        export_type=_export_type,
        source=_source,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    raw_docs = await list_candidate_documents(
        session,
        cand_ctx.owner_tenant_id,
        str(candidate_id),
        include_deleted=False,
        allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
        active_own_company_id=own_for_docs,
    )
    physical_total = len(raw_docs)
    docs = [
        d
        for d in raw_docs
        if document_visible_to_viewer(getattr(d, "doc_type", None), viewer_channel)
    ]
    physical_visible = len(docs)
    last_checks = await get_last_document_checks_map(
        session,
        cand_ctx.owner_tenant_id,
        [str(doc.id) for doc in docs],
    )
    resp_pair = await _batch_candidate_recruiter_labels(
        session, cand_ctx.owner_tenant_id, [str(candidate_id)]
    )
    rid, rname = resp_pair.get(str(candidate_id), (None, None))
    serialized = [
        (
            await _document_to_out(
                session,
                doc,
                last_check=last_checks.get(str(doc.id)),
                responsible_user_id=rid,
                responsible_name=rname,
            )
        ).model_dump()
        for doc in docs
    ]
    _log_document_access_visibility(
        surface="candidate_documents_export_json",
        candidate_id=candidate_id,
        viewer_channel=viewer_channel,
        db_fetch_total=physical_total,
        db_visible=physical_visible,
        response_items=len(serialized),
        synthetics_returned=0,
    )
    out: Dict[str, Any] = {
        "candidate_id": str(candidate_id),
        "documents": serialized,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(serialized),
    }
    if document_access_trace_response_enabled():
        out["document_access_trace"] = {
            "surface": "candidate_documents_export_json",
            "viewer_channel": viewer_channel,
            "viewer_readable_scopes": sorted(doc_access.viewer_readable_scopes),
            "physical_documents_total": physical_total,
            "physical_documents_visible_to_viewer": physical_visible,
            "physical_documents_filtered_out": max(0, physical_total - physical_visible),
        }
    row_count = len(serialized)
    byte_size = len(json.dumps(out, default=str).encode("utf-8"))
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_REQUESTED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
    )
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_GENERATED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        row_count=row_count,
        byte_size=byte_size,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
        response_mode="inline_json",
    )
    return out


@router.get("/candidate/{candidate_id}/documents/export.csv")
async def api_export_documents_csv(
    candidate_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> StreamingResponse:
    session, tenant_id = db_dep
    _source = "http:documents_router:export_documents_csv"
    _export_type = "candidate_documents_csv"
    doc_access, access_kind = await _candidate_documents_export_access(
        session,
        tenant_id,
        candidate_id,
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
        export_type=_export_type,
        source=_source,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    docs = await list_candidate_documents(
        session,
        cand_ctx.owner_tenant_id,
        str(candidate_id),
        include_deleted=False,
        allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
        active_own_company_id=own_for_docs,
    )
    docs = [
        d
        for d in docs
        if document_visible_to_viewer(getattr(d, "doc_type", None), viewer_channel)
    ]
    last_checks = await get_last_document_checks_map(
        session,
        cand_ctx.owner_tenant_id,
        [str(doc.id) for doc in docs],
    )
    output = io.StringIO()
    fieldnames = [
        "id",
        "type",
        "number",
        "status",
        "issued_at",
        "expires_at",
        "verified_at",
        "version",
        "last_check_decision",
        "last_check_reviewer",
        "last_check_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for doc in docs:
        check = last_checks.get(str(doc.id))
        writer.writerow(
            {
                "id": str(doc.id),
                "type": doc.doc_type,
                "number": doc.number or "",
                "status": doc.status,
                "issued_at": doc.issue_date.isoformat() if doc.issue_date else "",
                "expires_at": doc.expire_date.isoformat() if doc.expire_date else "",
                "verified_at": doc.verified_at.isoformat() if doc.verified_at else "",
                "version": getattr(doc, "version", ""),
                "last_check_decision": getattr(check, "decision", "") if check else "",
                "last_check_reviewer": getattr(check, "reviewer_id", "") if check else "",
                "last_check_at": check.created_at.isoformat() if check else "",
            }
        )
    output.seek(0)
    row_count = len(docs)
    byte_size = len(output.getvalue().encode("utf-8"))
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_REQUESTED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
    )
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_GENERATED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        row_count=row_count,
        byte_size=byte_size,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
        response_mode="attachment_stream",
    )
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_DOWNLOADED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        row_count=row_count,
        byte_size=byte_size,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
        response_mode="attachment_stream",
    )
    filename = f"candidate_{candidate_id}_documents.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/candidate/{candidate_id}/export.zip")
async def api_export_candidate_bundle(
    candidate_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> StreamingResponse:
    session, tenant_id = db_dep
    _source = "http:documents_router:export_candidate_bundle_zip"
    _export_type = "candidate_documents_bundle_zip"
    doc_access, access_kind = await _candidate_documents_export_access(
        session,
        tenant_id,
        candidate_id,
        workspace_own_company_header=own_company_id,
        viewer_channel=viewer_channel,
        export_type=_export_type,
        source=_source,
    )
    cand_ctx = doc_access.candidate_context
    own_for_docs = doc_access.resolved_workspace_own_company_id
    docs = await list_candidate_documents(
        session,
        cand_ctx.owner_tenant_id,
        str(candidate_id),
        include_deleted=False,
        allowed_tenant_ids=cand_ctx.allowed_tenant_ids,
        active_own_company_id=own_for_docs,
    )
    docs = [
        d
        for d in docs
        if document_visible_to_viewer(getattr(d, "doc_type", None), viewer_channel)
    ]
    last_checks = await get_last_document_checks_map(
        session, cand_ctx.owner_tenant_id, [str(doc.id) for doc in docs]
    )

    buf = io.BytesIO()
    profile = _profile_from_context(cand_ctx)
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        profile_csv = io.StringIO()
        profile_writer = csv.DictWriter(profile_csv, fieldnames=list(profile.keys()))
        profile_writer.writeheader()
        profile_writer.writerow(profile)
        zf.writestr("candidate_profile.csv", profile_csv.getvalue())

        doc_fields = [
            "id",
            "type",
            "number",
            "status",
            "issued_at",
            "expires_at",
            "ordered_at",
            "verified_at",
            "version",
            "last_check_decision",
            "last_check_reviewer",
            "last_check_at",
            "file_name",
        ]
        docs_csv = io.StringIO()
        docs_writer = csv.DictWriter(docs_csv, fieldnames=doc_fields)
        docs_writer.writeheader()
        used_names: set[str] = set()
        for idx, doc in enumerate(docs, start=1):
            check = last_checks.get(str(doc.id))
            file_name = _add_document_file_to_zip(doc, zf, idx, used_names)
            docs_writer.writerow(
                {
                    "id": str(doc.id),
                    "type": getattr(doc, "doc_type", None),
                    "number": getattr(doc, "number", "") or "",
                    "status": getattr(doc, "status", "") or "",
                    "issued_at": _iso(getattr(doc, "issue_date", None)) or "",
                    "expires_at": _iso(getattr(doc, "expire_date", None)) or "",
                    "ordered_at": _iso(getattr(doc, "ordered_at", None)) or "",
                    "verified_at": _iso(getattr(doc, "verified_at", None)) or "",
                    "version": getattr(doc, "version", "") or "",
                    "last_check_decision": getattr(check, "decision", "") if check else "",
                    "last_check_reviewer": getattr(check, "reviewer_id", "") if check else "",
                    "last_check_at": _iso(getattr(check, "created_at", None)) if check else "",
                    "file_name": file_name or "",
                }
            )
        zf.writestr("documents.csv", docs_csv.getvalue())

    buf.seek(0)
    row_count = len(docs)
    byte_size = len(buf.getvalue())
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_REQUESTED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
    )
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_GENERATED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        row_count=row_count,
        byte_size=byte_size,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
        response_mode="attachment_stream",
    )
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_DOWNLOADED,
        result="success",
        severity="info",
        source=_source,
        tenant_id=str(cand_ctx.owner_tenant_id),
        access_kind=access_kind,
        entity_type="candidate",
        entity_id=str(candidate_id),
        export_type=_export_type,
        row_count=row_count,
        byte_size=byte_size,
        filter_scope=clip_export_filter_scope(f"vc={viewer_channel}"),
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
        response_mode="attachment_stream",
    )
    filename = f"candidate_{candidate_id}_bundle.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/{document_id}/extract")
async def api_extract_document(
    document_id: UUID,
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> Dict[str, Any]:
    session, tenant_id = db_dep
    doc, _, _ = await _get_document_with_access(
        session,
        str(tenant_id),
        str(document_id),
        active_own_company_id=own_company_id,
        viewer_channel=viewer_channel,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    files = await ensure_document_files(session, doc)
    entry = select_file_entry(files)
    if not entry:
        raise HTTPException(status_code=404, detail="Document file not found")
    try:
        path = resolve_file_path(entry)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    schema = _load_meta_schema_for(str(doc.doc_type)) or {}
    try:
        with path.open("rb") as fh:
            file_bytes = fh.read()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read file: {exc}")
    try:
        result = _OCR_PIPELINE.run(file_bytes, str(doc.doc_type), schema)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {exc}")
    return result


@router.post("/mock-upload")
async def api_mock_upload(
    key: str = Form(..., description="Storage key obtained from presign"),
    file: UploadFile = File(...),
    current_user: UserCtx = Depends(get_current_user),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
    viewer_channel: str = Depends(resolve_document_viewer_channel),
) -> Dict[str, Any]:
    session, tenant_id = db_dep
    segments = [seg for seg in key.strip().split("/") if seg]
    if len(segments) < 2 or segments[0] != "documents":
        raise HTTPException(
            status_code=400,
            detail="key must follow 'documents/{document_id}/...'",
        )
    document_id = segments[1]
    doc, _, _, _ = await _get_document_with_mutation_access(
        session,
        str(tenant_id),
        document_id,
        workspace_own_company_header=own_company_id,
        enforce_destructive_process_lock=True,
        viewer_channel=viewer_channel,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    uploads_root = get_uploads_root()
    target_dir = uploads_root / "documents" / document_id
    target_dir.mkdir(parents=True, exist_ok=True)

    original_name = sanitize_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_name = f"{timestamp}_{original_name or 'document.bin'}"
    target_path = target_dir / stored_name

    content = await file.read()
    try:
        with target_path.open("wb") as fh:
            fh.write(content)
    finally:
        await file.close()

    rel_path = target_path.relative_to(uploads_root).as_posix()
    entry = await register_document_upload(
        document_id=document_id,
        rel_path=rel_path,
        original_name=file.filename or stored_name,
        size=len(content),
        mime=file.content_type,
        uploaded_by=getattr(current_user, "sub", None),
    )
    if not entry:
        raise HTTPException(
            status_code=404, detail="Document not found during register"
        )

    return {
        "ok": True,
        "stored_as": entry.get("storage_path") or rel_path,
        "url": entry.get("url"),
        "version": entry.get("version"),
    }


@router.get("/ruleset", response_model=RulesetVersionOut)
async def api_get_ruleset(
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetVersionOut:
    session, tenant_id = db_dep
    ruleset_version = await get_effective_latest_ruleset_version(
        session, str(tenant_id), own_company_id=own_company_id
    )
    if not ruleset_version:
        ruleset_version = await ensure_ruleset_seed(
            session,
            str(tenant_id),
            load_default_ruleset(),
            own_company_id=own_company_id,
        )
    await session.commit()
    return _ruleset_to_out(ruleset_version)


@router.get("/ruleset/versions", response_model=List[RulesetVersionOut])
async def api_list_ruleset_versions_route(
    status: Optional[str] = Query(
        None, description="Filter by status: active | archived"
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=200, description="Optional limit (<=200)"
    ),
    offset: Optional[int] = Query(
        None, ge=0, description="Optional offset for pagination"
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> List[RulesetVersionOut]:
    session, tenant_id = db_dep
    status_norm = None
    if status:
        status_lower = status.lower()
        if status_lower in {"active", "archived"}:
            status_norm = status_lower
        elif status_lower not in {"all", "any"}:
            raise HTTPException(status_code=400, detail="Invalid status filter")
    list_scope = await ruleset_write_scope_own_company_id(
        session, str(tenant_id), own_company_id
    )
    rows = await list_ruleset_versions(
        session,
        str(tenant_id),
        own_company_id=list_scope,
        status=status_norm,
        limit=limit,
        offset=offset,
    )
    return [_ruleset_to_out(row) for row in rows]


@router.get("/ruleset/versions/{version_id}", response_model=RulesetVersionOut)
async def api_get_ruleset_version(
    version_id: str = Path(..., description="Ruleset version identifier"),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetVersionOut:
    session, tenant_id = db_dep
    record = await get_ruleset_version_by_id(session, str(tenant_id), version_id)
    if not record or not ruleset_version_visible_for_scope(record, own_company_id):
        raise HTTPException(status_code=404, detail="Ruleset version not found")
    return _ruleset_to_out(record)


@router.post(
    "/ruleset/versions",
    response_model=RulesetVersionOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def api_create_ruleset_version(
    payload: Dict[str, Any] = Body(...),
    current_user: UserCtx = Depends(get_current_user),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetVersionOut:
    session, tenant_id = db_dep
    ruleset_data = payload.get("ruleset") or payload.get("json_data")
    if not isinstance(ruleset_data, dict):
        raise HTTPException(status_code=400, detail="ruleset must be an object")
    comment = payload.get("comment")
    activate = bool(payload.get("activate", False))
    origin_version_id = payload.get("origin_version_id")
    new_version = await create_ruleset_version(
        session,
        str(tenant_id),
        ruleset_data,
        created_by=getattr(current_user, "sub", None),
        comment=comment,
        activate=activate,
        origin_version_id=origin_version_id,
        own_company_id=own_company_id,
    )
    await session.commit()
    return _ruleset_to_out(new_version)


@router.post(
    "/ruleset/versions/{version_id}/activate",
    response_model=RulesetVersionOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def api_activate_ruleset_version(
    version_id: str = Path(..., description="Ruleset version identifier"),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetVersionOut:
    session, tenant_id = db_dep
    pre = await get_ruleset_version_by_id(session, str(tenant_id), version_id)
    if not pre or not ruleset_version_visible_for_scope(pre, own_company_id):
        raise HTTPException(status_code=404, detail="Ruleset version not found")
    record = await activate_ruleset_version(session, str(tenant_id), version_id)
    if not record:
        raise HTTPException(status_code=404, detail="Ruleset version not found")
    await session.commit()
    return _ruleset_to_out(record)


@router.post(
    "/ruleset/versions/{version_id}/rollback",
    response_model=RulesetVersionOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def api_rollback_ruleset_version(
    version_id: str = Path(..., description="Ruleset version identifier"),
    payload: Dict[str, Any] = Body(...),
    current_user: UserCtx = Depends(get_current_user),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetVersionOut:
    session, tenant_id = db_dep
    target = await get_ruleset_version_by_id(session, str(tenant_id), version_id)
    if not target or not ruleset_version_visible_for_scope(target, own_company_id):
        raise HTTPException(status_code=404, detail="Ruleset version not found")
    rollback_comment = str(payload.get("comment") or payload.get("rollback_comment") or "").strip()
    if len(rollback_comment) < 3:
        raise HTTPException(
            status_code=400, detail="Rollback comment must be at least 3 characters"
        )
    new_comment = payload.get("new_comment") or f"Rollback to version {target.version}"
    new_version = await create_ruleset_version(
        session,
        str(tenant_id),
        normalize_ruleset_payload(target.json_data),
        created_by=getattr(current_user, "sub", None),
        comment=new_comment,
        activate=True,
        origin_version_id=str(target.id),
        rollback_comment=rollback_comment,
        own_company_id=getattr(target, "own_company_id", None),
    )
    await session.commit()
    return _ruleset_to_out(new_version)


@router.get(
    "/ruleset/versions/{version_id}/diff",
    response_model=RulesetDiffOut,
)
async def api_get_ruleset_diff(
    version_id: str = Path(..., description="Ruleset version identifier"),
    compare_to: Optional[str] = Query(
        None,
        description="Optional version id to compare against; defaults to previous version",
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetDiffOut:
    session, tenant_id = db_dep
    target = await get_ruleset_version_by_id(session, str(tenant_id), version_id)
    if not target or not ruleset_version_visible_for_scope(target, own_company_id):
        raise HTTPException(status_code=404, detail="Ruleset version not found")
    compare_id = compare_to
    diff_row = None
    if compare_to:
        other = await get_ruleset_version_by_id(session, str(tenant_id), compare_to)
        if not other or not ruleset_version_visible_for_scope(other, own_company_id):
            raise HTTPException(
                status_code=404, detail="Compare ruleset version not found"
            )
        if not ruleset_versions_share_scope(target, other):
            raise HTTPException(
                status_code=400,
                detail="Compare ruleset version is not in the same workspace scope",
            )
        diff_row = await get_ruleset_diff_between(session, compare_to, version_id)
    else:
        diff_row = await get_latest_diff_for_version(session, version_id)
        if diff_row:
            compare_id = diff_row.ruleset_id_from
    diff_payload: Dict[str, Any]
    computed_with: Optional[str] = None
    created_at: Optional[datetime] = None
    if diff_row:
        diff_payload = dict(diff_row.diff_json or {})
        computed_with = diff_row.computed_with
        created_at = diff_row.created_at
        compare_id = compare_id or diff_row.ruleset_id_from
    else:
        if not compare_id:
            prev_version = await get_previous_ruleset_version(
                session,
                str(tenant_id),
                target.version,
                own_company_id=getattr(target, "own_company_id", None),
            )
            if prev_version:
                compare_id = str(prev_version.id)
                previous_payload = normalize_ruleset_payload(prev_version.json_data)
            else:
                previous_payload = {}
        else:
            compare_version = await get_ruleset_version_by_id(
                session, str(tenant_id), compare_id
            )
            if not compare_version or not ruleset_version_visible_for_scope(
                compare_version, own_company_id
            ):
                raise HTTPException(
                    status_code=404, detail="Compare ruleset version not found"
                )
            if not ruleset_versions_share_scope(target, compare_version):
                raise HTTPException(
                    status_code=400,
                    detail="Compare ruleset version is not in the same workspace scope",
                )
            previous_payload = normalize_ruleset_payload(compare_version.json_data)

        current_payload = normalize_ruleset_payload(target.json_data)
        diff_payload = compute_ruleset_diff(previous_payload, current_payload)
        computed_with = diff_payload.get("engine")
        created_at = datetime.utcnow()

    return RulesetDiffOut(
        version_id=str(target.id),
        compare_to=str(compare_id) if compare_id else None,
        diff=diff_payload,
        computed_with=computed_with,
        created_at=created_at,
    )


@router.get(
    "/ruleset/usage",
    response_model=RulesetUsageResponse,
    dependencies=[Depends(require_roles(Role.supervisor, Role.administrator))],
)
async def api_list_ruleset_usage(
    used_in: Optional[str] = Query(
        None, description="Filter by usage scope (compliance/report/checklist/...)"
    ),
    since: Optional[datetime] = Query(
        None, description="Filter usage recorded after this timestamp (ISO8601)"
    ),
    until: Optional[datetime] = Query(
        None, description="Filter usage recorded before this timestamp (ISO8601)"
    ),
    limit: Optional[int] = Query(
        100, ge=1, le=500, description="Limit number of usage records (default 100)"
    ),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetUsageResponse:
    session, tenant_id = db_dep
    usage_scope = await ruleset_write_scope_own_company_id(
        session, str(tenant_id), own_company_id
    )
    rows = await list_ruleset_usage(
        session,
        str(tenant_id),
        own_company_id=usage_scope,
        used_in=used_in,
        since=since,
        until=until,
        limit=limit,
    )
    summary: Dict[str, int] = {}
    items: List[RulesetUsageOut] = []
    for row in rows:
        summary[row.used_in] = summary.get(row.used_in, 0) + 1
        items.append(
            RulesetUsageOut(
                id=str(row.id),
                ruleset_version_id=str(row.ruleset_version_id),
                used_in=row.used_in,
                reference_id=getattr(row, "reference_id", None),
                used_at=row.used_at,
                meta=dict(getattr(row, "meta", {}) or {}),
            )
        )
    return RulesetUsageResponse(items=items, summary=summary)


@router.patch(
    "/ruleset",
    response_model=RulesetVersionOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def api_update_ruleset(
    payload: Dict[str, Any] = Body(...),
    current_user: UserCtx = Depends(get_current_user),
    db_dep=Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> RulesetVersionOut:
    session, tenant_id = db_dep
    ruleset_data = payload.get("ruleset") or payload.get("json_data")
    if not isinstance(ruleset_data, dict):
        raise HTTPException(status_code=400, detail="ruleset must be an object")
    comment = payload.get("comment")
    write_scope = await ruleset_write_scope_own_company_id(
        session, str(tenant_id), own_company_id
    )
    new_version = await create_ruleset_version(
        session,
        str(tenant_id),
        ruleset_data,
        created_by=getattr(current_user, "sub", None),
        comment=comment,
        activate=True,
        own_company_id=write_scope,
    )
    await session.commit()
    return _ruleset_to_out(new_version)
