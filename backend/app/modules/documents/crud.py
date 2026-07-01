from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Mapping

import sqlalchemy as sa
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
from ...models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.services.document_catalog import (
    DOCUMENT_TYPE_DEFAULTS,
    doc_type_requires_user_comment,
    get_doc_type_defaults,
    normalize_doc_type,
    normalize_kind,
    normalize_process_type,
    normalize_requested_from,
    normalize_status,
)
from backend.app.services.document_workflow import (
    default_workflow,
    normalize_workflow,
    auto_status as compute_auto_status,
)
from backend.app.services.ruleset_versioning import (
    compute_ruleset_diff,
    compute_ruleset_signature,
    normalize_ruleset_payload,
)
from backend.app.services.own_company_doc_scope import documents_scope_clause
from backend.app.services.tenant_quota import (
    ensure_tenant_document_quota,
    ensure_tenant_storage_bytes_fits,
    sum_file_entries_bytes,
)
from backend.app.models import (
    Candidate,
    Document,
    DocumentCheck,
    DocumentRulesetDiff,
    DocumentRulesetUsage,
    DocumentRulesetVersion,
    DocumentType,
)
from .validators import (
    validate_date_range,
)

DEFAULT_REMINDER_DAYS = 30
DOCUMENT_TYPE_DEFINITION_MAP = {
    definition.code: definition for definition in DOCUMENT_TYPE_DEFINITIONS
}
DOCUMENT_TYPE_CODES: tuple[str, ...] = tuple(DOCUMENT_TYPE_DEFINITION_MAP.keys())
DEFAULT_DOCUMENT_TYPE_LABELS: Dict[str, str] = {
    code: definition.name for code, definition in DOCUMENT_TYPE_DEFINITION_MAP.items()
}


def _required_fields_from_schema(schema: Mapping[str, Any]) -> List[str]:
    if not isinstance(schema, Mapping):
        return []
    required = schema.get("required")
    if isinstance(required, (list, tuple)):
        return [str(item) for item in required]
    return []


def _clone_dict(data: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(data, Mapping):
        return {}
    return json.loads(json.dumps(data))


def _tid(value: Any) -> str:
    return str(value)


def _norm_ruleset_oc(own_company_id: Optional[str]) -> Optional[str]:
    s = str(own_company_id or "").strip()
    return s or None


def ruleset_version_scope_where(own_company_id: Optional[str]):
    """Match one ruleset chain: global (NULL) or a specific own_company_id."""
    oc = _norm_ruleset_oc(own_company_id)
    if oc:
        return DocumentRulesetVersion.own_company_id == oc
    return DocumentRulesetVersion.own_company_id.is_(None)


def ruleset_version_same_scope_clause(version_row: DocumentRulesetVersion):
    oc = _norm_ruleset_oc(getattr(version_row, "own_company_id", None))
    if oc is None:
        return DocumentRulesetVersion.own_company_id.is_(None)
    return DocumentRulesetVersion.own_company_id == oc


def ruleset_version_visible_for_scope(
    record: DocumentRulesetVersion, active_oc: Optional[str]
) -> bool:
    row_oc = _norm_ruleset_oc(getattr(record, "own_company_id", None))
    if row_oc is None:
        return True
    return _norm_ruleset_oc(active_oc) == row_oc


def ruleset_versions_share_scope(
    a: DocumentRulesetVersion, b: DocumentRulesetVersion
) -> bool:
    return _norm_ruleset_oc(getattr(a, "own_company_id", None)) == _norm_ruleset_oc(
        getattr(b, "own_company_id", None)
    )


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _normalize_user_comment(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        comment = value.strip()
    else:
        comment = str(value).strip()
    return comment or None


def _normalize_files(files: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not files:
        return []
    normalized: List[Dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        clean = {
            "name": str(item.get("name", "")).strip(),
            "url": item.get("url"),
            "size": item.get("size"),
            "mime": item.get("mime"),
            "uploaded_at": item.get("uploaded_at"),
            "uploaded_by": item.get("uploaded_by"),
            "user_comment": _normalize_user_comment(item.get("user_comment")),
        }
        if not clean["name"] and clean["url"]:
            clean["name"] = clean["url"]
        normalized.append(clean)
    return normalized


async def ensure_document_type(
    session: AsyncSession, tenant_id: str, code: str, name: Optional[str] = None
) -> DocumentType:
    tenant_id_s = _tid(tenant_id)
    canonical = normalize_doc_type(code)
    defaults = get_doc_type_defaults(canonical)
    definition = DOCUMENT_TYPE_DEFINITION_MAP.get(canonical)
    label = name or DEFAULT_DOCUMENT_TYPE_LABELS.get(
        canonical, canonical.replace("_", " ").title()
    )
    title_payload = dict(definition.title) if definition else {"en": label}
    metadata_schema = (
        _clone_dict(definition.metadata_schema)
        if definition
        else _clone_dict(defaults.metadata_schema)
    )
    required_files = (
        _clone_dict(definition.required_files)
        if definition
        else _clone_dict(defaults.required_files)
    )
    expiry_rule = (
        _clone_dict(definition.expiry_rule)
        if definition
        else _clone_dict(defaults.expiry_rule)
    )
    definition_required_meta = (
        _required_fields_from_schema(definition.metadata_schema)
        if definition
        else list(defaults.required_meta)
    )

    stmt = select(DocumentType).where(
        DocumentType.tenant_id == tenant_id_s,
        DocumentType.code == canonical,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        updates: dict[str, Any] = {}
        if label and existing.name != label:
            updates["name"] = label
        if getattr(existing, "kind", None) != defaults.kind:
            updates["kind"] = defaults.kind
        if getattr(existing, "requested_from", None) != defaults.requested_from:
            updates["requested_from"] = defaults.requested_from
        if getattr(existing, "process_type", None) != defaults.process_type:
            updates["process_type"] = defaults.process_type
        if getattr(existing, "default_expire_in_days", None) != defaults.default_expire_in_days:
            updates["default_expire_in_days"] = defaults.default_expire_in_days
        if list(getattr(existing, "aliases", []) or []) != list(defaults.aliases):
            updates["aliases"] = list(defaults.aliases)
        if list(getattr(existing, "required_meta", []) or []) != list(definition_required_meta):
            updates["required_meta"] = list(definition_required_meta)
        if (getattr(existing, "title", None) or {}) != title_payload:
            updates["title"] = title_payload
        if (getattr(existing, "metadata_schema", None) or {}) != metadata_schema:
            updates["metadata_schema"] = metadata_schema
        if (getattr(existing, "required_files", None) or {}) != required_files:
            updates["required_files"] = required_files
        if (getattr(existing, "expiry_rule", None) or {}) != expiry_rule:
            updates["expiry_rule"] = expiry_rule
        if int(getattr(existing, "owner_summary_weight", 0) or 0) != defaults.owner_summary_weight:
            updates["owner_summary_weight"] = defaults.owner_summary_weight
        existing_i18n = getattr(existing, "i18n_key", None)
        desired_i18n = defaults.i18n_key or f"documents.catalog.{canonical}"
        if (existing_i18n or "").strip() != desired_i18n:
            updates["i18n_key"] = desired_i18n
        if bool(getattr(existing, "requires_custom_name", False)) != bool(defaults.requires_custom_name):
            updates["requires_custom_name"] = defaults.requires_custom_name
        if getattr(existing, "duplicate_policy", None) != defaults.duplicate_policy:
            updates["duplicate_policy"] = defaults.duplicate_policy
        if bool(getattr(existing, "orderable", False)) != bool(defaults.orderable):
            updates["orderable"] = defaults.orderable
        if updates:
            updates["updated_at"] = func.now()
            updates["is_active"] = True
            await session.execute(
                update(DocumentType)
                .where(DocumentType.id == existing.id)
                .values(**updates)
            )
            await session.flush()
        return existing

    doc_type = DocumentType(
        tenant_id=tenant_id_s,
        code=canonical,
        name=label,
        kind=defaults.kind,
        requested_from=defaults.requested_from,
        process_type=defaults.process_type,
        default_expire_in_days=defaults.default_expire_in_days,
        aliases=list(defaults.aliases),
        required_meta=list(definition_required_meta),
        title=title_payload,
        metadata_schema=metadata_schema,
        required_files=required_files,
        expiry_rule=expiry_rule,
        owner_summary_weight=defaults.owner_summary_weight,
        i18n_key=defaults.i18n_key or f"documents.catalog.{canonical}",
        requires_custom_name=defaults.requires_custom_name,
        duplicate_policy=defaults.duplicate_policy,
        orderable=defaults.orderable,
        is_active=True,
    )
    session.add(doc_type)
    await session.flush()
    return doc_type


async def list_document_types(
    session: AsyncSession, tenant_id: str
) -> Sequence[DocumentType]:
    tenant_id_s = _tid(tenant_id)

    # Always sync canonical catalog definitions before reading rows so that
    # legacy entries get refreshed (metadata_schema, required_files, etc.).
    for code in DOCUMENT_TYPE_CODES:
        await ensure_document_type(
            session,
            tenant_id_s,
            code,
            DEFAULT_DOCUMENT_TYPE_LABELS.get(code, code),
        )

    stmt = (
        select(DocumentType)
        .where(DocumentType.tenant_id == tenant_id_s, DocumentType.is_active.is_(True))
        .order_by(DocumentType.code.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()

    legacy_codes = [
        row.code
        for row in rows
        if row.code not in DOCUMENT_TYPE_CODES
    ]
    if legacy_codes:
        await session.execute(
            update(DocumentType)
            .where(
                DocumentType.tenant_id == tenant_id_s,
                DocumentType.code.not_in(DOCUMENT_TYPE_CODES),
                DocumentType.is_active.is_(True),
            )
            .values(is_active=False, updated_at=func.now())
        )
        rows = (await session.execute(stmt)).scalars().all()
    return rows


async def create_document(session: AsyncSession, payload: Dict[str, Any]) -> Document:
    tenant_id = _tid(payload["tenant_id"])
    candidate_id = _tid(payload["candidate_id"])
    await ensure_tenant_document_quota(session, tenant_id)

    doc_type = normalize_doc_type(
        payload.get("doc_type")
        or payload.get("type")
        or payload.get("key")
        or ""
    )
    if not doc_type:
        raise ValueError("doc_type is required")

    defaults = get_doc_type_defaults(doc_type)

    kind = normalize_kind(payload.get("kind"), defaults.kind)
    requested_from = normalize_requested_from(payload.get("requested_from"), defaults.requested_from)
    process_type = normalize_process_type(payload.get("process_type"), defaults.process_type)

    custom_name = (payload.get("custom_name") or "").strip() or None
    if defaults.requires_custom_name and not custom_name:
        raise ValueError(f"custom_name is required for doc_type '{doc_type}'")

    number = (payload.get("number") or "").strip() or None
    issue_date: Optional[date] = payload.get("issue_date") or payload.get("issued_at")
    expire_date = _as_date(payload.get("expire_date") or payload.get("expires_at"))
    validate_date_range(issue_date, expire_date)

    ordered_at: Optional[date] = payload.get("ordered_at")
    valid_from: Optional[date] = payload.get("valid_from")

    reminder_days = int(payload.get("reminder_days_before") or DEFAULT_REMINDER_DAYS)

    await ensure_document_type(session, tenant_id, doc_type)

    files_payload = _normalize_files(payload.get("files"))
    await ensure_tenant_storage_bytes_fits(
        session,
        tenant_id,
        previous_doc_attribution_bytes=0,
        next_doc_attribution_bytes=sum_file_entries_bytes(files_payload),
    )

    meta_payload: Dict[str, Any] = {}
    if isinstance(payload.get("meta"), dict):
        meta_payload.update(payload["meta"])
    if isinstance(payload.get("meta_json"), dict):
        meta_payload.update(payload["meta_json"])
    if isinstance(payload.get("extra"), dict):
        meta_payload.update(payload["extra"])
    meta_payload.setdefault("doc_type", doc_type)
    if custom_name:
        meta_payload.setdefault("title", custom_name)

    user_comment = _normalize_user_comment(
        payload.get("user_comment") or meta_payload.get("user_comment")
    )
    if user_comment:
        meta_payload["user_comment"] = user_comment
    else:
        meta_payload.pop("user_comment", None)
    if doc_type_requires_user_comment(doc_type) and not user_comment:
        raise ValueError("user_comment is required for doc_type 'additional_document'")

    workflow_payload = normalize_workflow(process_type, payload.get("workflow"))
    if workflow_payload is None:
        workflow_payload = default_workflow(process_type)

    status_input = payload.get("status")
    status_enum = normalize_status(status_input)
    status_final: DocumentStatus = compute_auto_status(
        status_enum,
        process_type=process_type,
        workflow=workflow_payload,
        has_files=bool(files_payload),
        expire_date=expire_date,
    )

    verified_at = payload.get("verified_at")
    if verified_at is None and status_final == DocumentStatus.approved:
        verified_at = datetime.now(timezone.utc)

    if isinstance(workflow_payload, dict):
        workflow_payload = dict(workflow_payload)
        workflow_payload["auto_status"] = status_final.value

    own_co_raw = payload.get("own_company_id")
    own_co = str(own_co_raw).strip() if own_co_raw else None

    doc = Document(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        own_company_id=own_co or None,
        company_id=_tid(payload.get("company_id")) if payload.get("company_id") else None,
        owner_type="candidate",
        owner_id=_tid(payload.get("owner_id") or candidate_id),
        kind=kind,
        doc_type=doc_type,
        custom_name=custom_name,
        requested_from=requested_from,
        process_type=process_type,
        number=number,
        status=status_final,
        reminder_days_before=reminder_days,
        files=files_payload or None,
        workflow=workflow_payload or None,
        source=payload.get("source"),
        external_id=payload.get("external_id"),
        verified_at=verified_at,
        issue_date=issue_date,
        expire_date=expire_date,
        ordered_at=ordered_at,
        valid_from=valid_from,
        meta=meta_payload or None,
        user_comment=user_comment,
    )
    doc.version = 1

    session.add(doc)
    await session.flush()
    await session.refresh(doc)
    return doc


async def get_document(session: AsyncSession, tenant_id: str, doc_id: str) -> Optional[Document]:
    tenant_id_s = _tid(tenant_id)
    stmt = select(Document).where(
        Document.id == doc_id,
        Document.tenant_id == tenant_id_s,
        Document.deleted_at.is_(None),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_document(
    session: AsyncSession,
    tenant_id: str,
    doc_id: str,
    payload: Dict[str, Any],
) -> Optional[Document]:
    doc = await get_document(session, tenant_id, doc_id)
    if not doc:
        return None

    changes: Dict[str, Any] = {}

    current_defaults = get_doc_type_defaults(doc.doc_type)

    new_doc_type = None
    if payload.get("doc_type") or payload.get("type"):
        new_doc_type = normalize_doc_type(payload.get("doc_type") or payload.get("type"))
        await ensure_document_type(session, doc.tenant_id, new_doc_type)
        doc.doc_type = new_doc_type
        current_defaults = get_doc_type_defaults(new_doc_type)
        changes["doc_type"] = new_doc_type

    if "kind" in payload and payload["kind"] is not None:
        doc.kind = normalize_kind(payload["kind"], current_defaults.kind)
        changes["kind"] = doc.kind
    elif payload.get("doc_type") or payload.get("type"):
        doc.kind = current_defaults.kind
        changes["kind"] = doc.kind

    if "requested_from" in payload and payload["requested_from"] is not None:
        doc.requested_from = normalize_requested_from(payload["requested_from"], current_defaults.requested_from)
        changes["requested_from"] = doc.requested_from
    elif payload.get("doc_type") or payload.get("type"):
        doc.requested_from = current_defaults.requested_from
        changes["requested_from"] = doc.requested_from

    process_type_before = doc.process_type if isinstance(doc.process_type, DocumentProcessType) else current_defaults.process_type
    if "process_type" in payload and payload["process_type"] is not None:
        doc.process_type = normalize_process_type(payload["process_type"], current_defaults.process_type)
    elif payload.get("doc_type") or payload.get("type"):
        doc.process_type = current_defaults.process_type
    process_type_enum = (
        doc.process_type if isinstance(doc.process_type, DocumentProcessType) else normalize_process_type(str(doc.process_type), current_defaults.process_type)
    )
    if doc.process_type != process_type_before:
        changes["process_type"] = doc.process_type

    if "custom_name" in payload:
        custom_name = (payload.get("custom_name") or "").strip() or None
        if current_defaults.requires_custom_name and not custom_name:
            raise ValueError("custom_name is required for doc_type 'other'")
        doc.custom_name = custom_name
        changes["custom_name"] = doc.custom_name

    if "number" in payload:
        doc.number = (payload.get("number") or "").strip() or None
        changes["number"] = doc.number

    if "issue_date" in payload or "issued_at" in payload:
        doc.issue_date = payload.get("issue_date") or payload.get("issued_at")
        changes["issue_date"] = doc.issue_date
    if "expire_date" in payload or "expires_at" in payload:
        doc.expire_date = _as_date(payload.get("expire_date") or payload.get("expires_at"))
        changes["expire_date"] = doc.expire_date
    validate_date_range(doc.issue_date, doc.expire_date)

    if "ordered_at" in payload:
        ordered_value = payload.get("ordered_at")
        doc.ordered_at = ordered_value if isinstance(ordered_value, date) else _as_date(ordered_value)
        changes["ordered_at"] = doc.ordered_at

    if "valid_from" in payload:
        valid_value = payload.get("valid_from")
        doc.valid_from = valid_value if isinstance(valid_value, date) else _as_date(valid_value)
        changes["valid_from"] = doc.valid_from

    if "reminder_days_before" in payload and payload["reminder_days_before"] is not None:
        doc.reminder_days_before = int(payload["reminder_days_before"])
        changes["reminder_days_before"] = doc.reminder_days_before

    if "company_id" in payload:
        doc.company_id = _tid(payload["company_id"]) if payload["company_id"] else None
        changes["company_id"] = doc.company_id
    if "owner_id" in payload:
        doc.owner_id = _tid(payload["owner_id"]) if payload["owner_id"] else None
        changes["owner_id"] = doc.owner_id

    if "files" in payload and payload["files"] is not None:
        files = _normalize_files(payload["files"])
        prev_b = sum_file_entries_bytes(doc.files)
        next_b = sum_file_entries_bytes(files)
        await ensure_tenant_storage_bytes_fits(
            session,
            tenant_id,
            previous_doc_attribution_bytes=prev_b,
            next_doc_attribution_bytes=next_b,
        )
        doc.files = files or None
        changes["files"] = doc.files

    if "user_comment" in payload:
        doc.user_comment = _normalize_user_comment(payload.get("user_comment"))
        changes["user_comment"] = doc.user_comment

    wf_payload: Optional[Dict[str, Any]]
    if "workflow" in payload:
        wf_payload = normalize_workflow(
            process_type_enum,
            payload.get("workflow"),
            existing_workflow=doc.workflow,
        )
    elif process_type_enum != process_type_before:
        wf_payload = normalize_workflow(process_type_enum, doc.workflow, existing_workflow=doc.workflow)
    else:
        wf_payload = doc.workflow if isinstance(doc.workflow, Mapping) else None
    if wf_payload is None:
        wf_payload = default_workflow(process_type_enum)
    if wf_payload is not None:
        wf_payload = dict(wf_payload)
    doc.workflow = wf_payload

    if "source" in payload:
        doc.source = payload.get("source")
        changes["source"] = doc.source
    if "external_id" in payload:
        doc.external_id = payload.get("external_id")
        changes["external_id"] = doc.external_id

    meta_payload = dict(doc.meta or {})
    if "meta" in payload and payload["meta"] is not None:
        meta_payload.update(dict(payload["meta"]))
    if "meta_json" in payload and payload["meta_json"] is not None:
        meta_payload.update(dict(payload["meta_json"]))
    if "extra" in payload and payload["extra"] is not None:
        meta_payload.update(dict(payload["extra"]))
    meta_payload.setdefault("doc_type", doc.doc_type)
    if getattr(doc, "custom_name", None):
        meta_payload.setdefault("title", doc.custom_name)
    if doc.user_comment:
        meta_payload["user_comment"] = doc.user_comment
    else:
        meta_payload.pop("user_comment", None)

    if doc_type_requires_user_comment(doc.doc_type) and not doc.user_comment:
        raise ValueError("user_comment is required for doc_type 'additional_document'")

    doc.meta = meta_payload or None
    changes["meta"] = doc.meta

    status_enum: DocumentStatus
    manual_status_provided = "status" in payload and payload["status"] is not None
    if manual_status_provided:
        status_enum = normalize_status(payload["status"])
    else:
        status_enum = doc.status if isinstance(doc.status, DocumentStatus) else normalize_status(doc.status)

    has_files = bool(doc.files)
    auto_status_value = compute_auto_status(
        status_enum,
        process_type=process_type_enum,
        workflow=doc.workflow,
        has_files=has_files,
        expire_date=_as_date(doc.expire_date),
    )
    if manual_status_provided:
        doc.status = (
            auto_status_value
            if auto_status_value in (DocumentStatus.expired, DocumentStatus.overdue)
            else status_enum
        )
    else:
        doc.status = auto_status_value
    changes["status"] = doc.status

    if isinstance(doc.workflow, dict):
        workflow_snapshot = dict(doc.workflow)
        workflow_snapshot["auto_status"] = doc.status.value
        doc.workflow = workflow_snapshot
        changes["workflow"] = doc.workflow
    else:
        changes["workflow"] = doc.workflow

    if "verified_at" in payload:
        doc.verified_at = payload["verified_at"]
    elif doc.status == DocumentStatus.approved and getattr(doc, "verified_at", None) is None:
        doc.verified_at = datetime.now(timezone.utc)
    changes["verified_at"] = doc.verified_at

    if changes:
        new_version = (int(doc.version) if getattr(doc, "version", None) is not None else 0) + 1
        doc.version = new_version
        doc.updated_at = datetime.now(timezone.utc)
        session.add(doc)
        await session.flush()
        await session.refresh(doc)
    return doc


async def list_candidate_documents(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    *,
    status: Optional[str] = None,
    type_filter: Optional[str] = None,
    include_deleted: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    allowed_tenant_ids: Optional[Iterable[str]] = None,
    active_own_company_id: Optional[str] = None,
) -> List[Document]:
    tenant_ids = {_tid(tenant_id)}
    if allowed_tenant_ids:
        tenant_ids.update({_tid(tid) for tid in allowed_tenant_ids if tid})
    stmt = (
        select(Document)
        .where(
            Document.tenant_id.in_(tenant_ids),
            Document.candidate_id == _tid(candidate_id),
        )
        .order_by(Document.created_at.desc())
    )
    if active_own_company_id:
        scope = documents_scope_clause(active_own_company_id)
        if scope is not None:
            stmt = stmt.join(Candidate, Candidate.id == Document.candidate_id).where(scope)
    if not include_deleted:
        stmt = stmt.where(Document.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Document.status == normalize_status(status))
    if type_filter:
        stmt = stmt.where(Document.doc_type == normalize_doc_type(type_filter))
    if offset:
        stmt = stmt.offset(int(offset))
    if limit:
        stmt = stmt.limit(int(limit))
    return (await session.execute(stmt)).scalars().all()


async def soft_delete_document(
    session: AsyncSession, tenant_id: str, doc_id: str
) -> bool:
    doc = await get_document(session, tenant_id, doc_id)
    if not doc:
        return False
    doc.deleted_at = datetime.utcnow()
    await session.execute(
        update(Document)
        .where(Document.id == doc_id)
        .values(deleted_at=doc.deleted_at, updated_at=func.now())
    )
    await session.flush()
    return True


async def list_document_checks(
    session: AsyncSession, tenant_id: str, document_id: str
) -> List[DocumentCheck]:
    tenant_id_s = _tid(tenant_id)
    stmt = (
        select(DocumentCheck)
        .where(
            DocumentCheck.tenant_id == tenant_id_s,
            DocumentCheck.document_id == _tid(document_id),
        )
        .order_by(DocumentCheck.created_at.desc())
    )
    return (await session.execute(stmt)).scalars().all()


async def create_document_check(
    session: AsyncSession,
    tenant_id: str,
    document_id: str,
    *,
    reviewer_id: Optional[str],
    decision: str,
    reason_code: Optional[str] = None,
    comment: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> DocumentCheck:
    decision_norm = "approved" if decision == "approved" else "rejected"
    check = DocumentCheck(
        tenant_id=_tid(tenant_id),
        document_id=_tid(document_id),
        reviewer_id=_tid(reviewer_id) if reviewer_id else None,
        decision=decision_norm,
        reason_code=reason_code,
        comment=comment,
        payload=dict(payload or {}),
    )
    session.add(check)
    await session.flush()
    await session.refresh(check)
    return check


async def get_last_document_checks_map(
    session: AsyncSession, tenant_id: str, document_ids: Sequence[str]
) -> Dict[str, DocumentCheck]:
    if not document_ids:
        return {}
    tenant_id_s = _tid(tenant_id)
    ids = {str(doc_id) for doc_id in document_ids if doc_id}
    if not ids:
        return {}
    stmt = (
        select(DocumentCheck)
        .where(
            DocumentCheck.tenant_id == tenant_id_s,
            DocumentCheck.document_id.in_(list(ids)),
        )
        .order_by(
            DocumentCheck.document_id.asc(),
            DocumentCheck.created_at.desc(),
        )
    )
    rows = (await session.execute(stmt)).scalars().all()
    latest: Dict[str, DocumentCheck] = {}
    for row in rows:
        if row.document_id not in latest:
            latest[row.document_id] = row
    return latest


async def get_latest_ruleset_version(
    session: AsyncSession,
    tenant_id: str,
    *,
    own_company_id: Optional[str] = None,
    include_inactive: bool = False,
) -> Optional[DocumentRulesetVersion]:
    tenant_id_s = _tid(tenant_id)
    stmt = select(DocumentRulesetVersion).where(
        DocumentRulesetVersion.tenant_id == tenant_id_s,
        ruleset_version_scope_where(own_company_id),
    )
    if not include_inactive:
        stmt = stmt.where(DocumentRulesetVersion.is_active.is_(True))
    stmt = stmt.order_by(DocumentRulesetVersion.version.desc()).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def ruleset_write_scope_own_company_id(
    session: AsyncSession, tenant_id: str, own_company_id: Optional[str]
) -> Optional[str]:
    """
    Mutations that should stay compatible with legacy single-chain tenants: until an
    explicit scoped version row exists for ``own_company_id``, append to the global
    (NULL) chain. Forked chains start with ``POST /ruleset/versions`` (or similar).
    """
    oc = _norm_ruleset_oc(own_company_id)
    if not oc:
        return None
    stmt = (
        select(DocumentRulesetVersion.id)
        .where(
            DocumentRulesetVersion.tenant_id == _tid(tenant_id),
            DocumentRulesetVersion.own_company_id == oc,
        )
        .limit(1)
    )
    if (await session.execute(stmt)).scalar_one_or_none():
        return oc
    return None


async def get_effective_latest_ruleset_version(
    session: AsyncSession,
    tenant_id: str,
    *,
    own_company_id: Optional[str] = None,
    include_inactive: bool = False,
) -> Optional[DocumentRulesetVersion]:
    """
    Prefer latest ruleset for ``own_company_id``; fall back to tenant-global (NULL) chain.
    """
    oc = _norm_ruleset_oc(own_company_id)
    if oc:
        row = await get_latest_ruleset_version(
            session,
            tenant_id,
            own_company_id=oc,
            include_inactive=include_inactive,
        )
        if row:
            return row
    return await get_latest_ruleset_version(
        session,
        tenant_id,
        own_company_id=None,
        include_inactive=include_inactive,
    )


async def list_ruleset_versions(
    session: AsyncSession,
    tenant_id: str,
    *,
    own_company_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[DocumentRulesetVersion]:
    tenant_id_s = _tid(tenant_id)
    stmt = select(DocumentRulesetVersion).where(
        DocumentRulesetVersion.tenant_id == tenant_id_s,
        ruleset_version_scope_where(own_company_id),
    )
    if status == "active":
        stmt = stmt.where(DocumentRulesetVersion.is_active.is_(True))
    elif status == "archived":
        stmt = stmt.where(DocumentRulesetVersion.is_active.is_(False))
    stmt = stmt.order_by(DocumentRulesetVersion.version.desc())
    if offset:
        stmt = stmt.offset(int(offset))
    if limit:
        stmt = stmt.limit(int(limit))
    return (await session.execute(stmt)).scalars().all()


async def create_ruleset_version(
    session: AsyncSession,
    tenant_id: str,
    json_data: Dict[str, Any],
    *,
    created_by: Optional[str] = None,
    comment: Optional[str] = None,
    activate: bool = True,
    origin_version_id: Optional[str] = None,
    rollback_comment: Optional[str] = None,
    own_company_id: Optional[str] = None,
) -> DocumentRulesetVersion:
    tenant_id_s = _tid(tenant_id)
    scope_oc = _norm_ruleset_oc(own_company_id)
    last_version_stmt = (
        select(DocumentRulesetVersion)
        .where(
            DocumentRulesetVersion.tenant_id == tenant_id_s,
            ruleset_version_scope_where(scope_oc),
        )
        .order_by(DocumentRulesetVersion.version.desc())
        .limit(1)
    )
    previous_version = (await session.execute(last_version_stmt)).scalar_one_or_none()
    current_max = int(previous_version.version) if previous_version else 0
    new_version = current_max + 1

    if activate:
        scope_filter = ruleset_version_scope_where(scope_oc)
        await session.execute(
            update(DocumentRulesetVersion)
            .where(
                DocumentRulesetVersion.tenant_id == tenant_id_s,
                DocumentRulesetVersion.is_active.is_(True),
                scope_filter,
            )
            .values(is_active=False)
        )

    payload = normalize_ruleset_payload(json_data)
    signature = compute_ruleset_signature(
        tenant_id=tenant_id_s,
        version=new_version,
        payload=payload,
        comment=comment,
    )
    record = DocumentRulesetVersion(
        tenant_id=tenant_id_s,
        own_company_id=scope_oc,
        version=new_version,
        json_data=payload,
        comment=comment,
        created_by=_tid(created_by) if created_by else None,
        is_active=activate,
        signature=signature,
        origin_version_id=_tid(origin_version_id) if origin_version_id else None,
        rollback_comment=rollback_comment,
    )
    session.add(record)
    await session.flush()
    await session.refresh(record)

    if previous_version:
        previous_payload = normalize_ruleset_payload(previous_version.json_data)
        diff_payload = compute_ruleset_diff(previous_payload, payload)
        diff_entry = DocumentRulesetDiff(
            ruleset_id_from=previous_version.id,
            ruleset_id_to=record.id,
            diff_json=diff_payload,
            computed_with=diff_payload.get("engine"),
        )
        session.add(diff_entry)

    return record


async def ensure_ruleset_seed(
    session: AsyncSession,
    tenant_id: str,
    default_ruleset: Dict[str, Any],
    *,
    created_by: Optional[str] = None,
    comment: Optional[str] = None,
    own_company_id: Optional[str] = None,
) -> DocumentRulesetVersion:
    existing = await get_effective_latest_ruleset_version(
        session, tenant_id, own_company_id=own_company_id
    )
    if existing:
        return existing
    return await create_ruleset_version(
        session,
        tenant_id,
        default_ruleset,
        created_by=created_by,
        comment=comment or "Seed ruleset",
        activate=True,
        own_company_id=None,
    )


async def get_ruleset_version_by_id(
    session: AsyncSession, tenant_id: str, version_id: str
) -> Optional[DocumentRulesetVersion]:
    tenant_id_s = _tid(tenant_id)
    stmt = (
        select(DocumentRulesetVersion)
        .where(
            DocumentRulesetVersion.id == _tid(version_id),
            DocumentRulesetVersion.tenant_id == tenant_id_s,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_previous_ruleset_version(
    session: AsyncSession,
    tenant_id: str,
    version: int,
    *,
    own_company_id: Optional[str] = None,
) -> Optional[DocumentRulesetVersion]:
    tenant_id_s = _tid(tenant_id)
    stmt = (
        select(DocumentRulesetVersion)
        .where(
            DocumentRulesetVersion.tenant_id == tenant_id_s,
            DocumentRulesetVersion.version < int(version),
            ruleset_version_scope_where(own_company_id),
        )
        .order_by(DocumentRulesetVersion.version.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def activate_ruleset_version(
    session: AsyncSession, tenant_id: str, version_id: str
) -> Optional[DocumentRulesetVersion]:
    tenant_id_s = _tid(tenant_id)
    stmt = (
        select(DocumentRulesetVersion)
        .where(
            DocumentRulesetVersion.id == _tid(version_id),
            DocumentRulesetVersion.tenant_id == tenant_id_s,
        )
        .limit(1)
    )
    target = (await session.execute(stmt)).scalar_one_or_none()
    if not target:
        return None
    scope_filter = ruleset_version_same_scope_clause(target)
    await session.execute(
        update(DocumentRulesetVersion)
        .where(
            DocumentRulesetVersion.tenant_id == tenant_id_s,
            scope_filter,
        )
        .values(is_active=False)
    )
    target.is_active = True
    await session.flush()
    await session.refresh(target)
    return target


async def get_ruleset_diff_between(
    session: AsyncSession,
    ruleset_id_from: str,
    ruleset_id_to: str,
) -> Optional[DocumentRulesetDiff]:
    stmt = (
        select(DocumentRulesetDiff)
        .where(
            DocumentRulesetDiff.ruleset_id_from == _tid(ruleset_id_from),
            DocumentRulesetDiff.ruleset_id_to == _tid(ruleset_id_to),
        )
        .order_by(DocumentRulesetDiff.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_latest_diff_for_version(
    session: AsyncSession, ruleset_version_id: str
) -> Optional[DocumentRulesetDiff]:
    stmt = (
        select(DocumentRulesetDiff)
        .where(DocumentRulesetDiff.ruleset_id_to == _tid(ruleset_version_id))
        .order_by(DocumentRulesetDiff.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def log_ruleset_usage(
    session: AsyncSession,
    tenant_id: str,
    ruleset_version_id: str,
    used_in: str,
    *,
    reference_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> DocumentRulesetUsage:
    usage = DocumentRulesetUsage(
        tenant_id=_tid(tenant_id),
        ruleset_version_id=_tid(ruleset_version_id),
        used_in=used_in,
        reference_id=_tid(reference_id) if reference_id else None,
        meta=dict(meta or {}),
    )
    session.add(usage)
    await session.flush()
    await session.refresh(usage)
    return usage


async def list_ruleset_usage(
    session: AsyncSession,
    tenant_id: str,
    *,
    own_company_id: Optional[str] = None,
    used_in: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> List[DocumentRulesetUsage]:
    tenant_id_s = _tid(tenant_id)
    stmt = (
        select(DocumentRulesetUsage)
        .join(
            DocumentRulesetVersion,
            DocumentRulesetVersion.id == DocumentRulesetUsage.ruleset_version_id,
        )
        .where(
            DocumentRulesetUsage.tenant_id == tenant_id_s,
            ruleset_version_scope_where(own_company_id),
        )
    )
    if used_in:
        stmt = stmt.where(DocumentRulesetUsage.used_in == used_in)
    if since:
        stmt = stmt.where(DocumentRulesetUsage.used_at >= since)
    if until:
        stmt = stmt.where(DocumentRulesetUsage.used_at <= until)
    stmt = stmt.order_by(DocumentRulesetUsage.used_at.desc())
    if limit:
        stmt = stmt.limit(int(limit))
    return (await session.execute(stmt)).scalars().all()
