"""Document Expiry Notifications P4 — scheduled sync job (evaluate + persist only)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_expiry_notifications.constants import DEFAULT_EXPIRING_SOON_DAYS
from backend.app.document_expiry_notifications.event_registry import (
    empty_sync_summary,
    sync_document_expiry_events_with_summary,
)
from backend.app.models.candidate import Candidate
from backend.app.services.document_hub_delivery_contract import list_candidate_documents_via_contract
from backend.app.services.document_runtime_delivery_contract import enrich_documents_via_contract


def _document_status_value(doc: Any) -> str:
    status = getattr(doc, "status", None)
    if status is None:
        return ""
    if hasattr(status, "value"):
        return str(status.value).strip().lower()
    return str(status).strip().lower()


def _document_has_files(doc: Any) -> bool:
    files = getattr(doc, "files", None) or []
    if isinstance(files, list) and len(files) > 0:
        return True
    return bool(getattr(doc, "filename", None) or getattr(doc, "path", None))


def hub_document_to_runtime_snapshot(
    doc: Any,
    *,
    tenant_id: str,
    owner_type: str,
    owner_id: str,
) -> dict[str, Any]:
    """Map a Document Hub instance row into a delivery-contract input snapshot."""
    expire_date = getattr(doc, "expire_date", None)
    expires_on = expire_date.isoformat() if expire_date is not None else None
    doc_type = str(getattr(doc, "doc_type", "") or "").strip()
    return {
        "document_id": str(getattr(doc, "id", "") or "").strip() or None,
        "type": doc_type,
        "document_type_code": doc_type,
        "status": _document_status_value(doc),
        "has_files": _document_has_files(doc),
        "expires_on": expires_on,
        "expire_date": expires_on,
        "tenant_id": str(tenant_id).strip(),
        "owner_type": str(owner_type or "candidate").strip().lower(),
        "owner_id": str(owner_id).strip(),
    }


async def collect_candidate_runtime_snapshots(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    own_company_id: str | None = None,
) -> list[dict[str, Any]]:
    """Load candidate documents via Hub contract and enrich via Runtime delivery contract."""
    docs = await list_candidate_documents_via_contract(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate_id=str(candidate_id).strip(),
        include_deleted=False,
        active_own_company_id=own_company_id,
    )
    raw_snapshots: list[dict[str, Any]] = []
    for doc in docs or []:
        if getattr(doc, "deleted_at", None) is not None:
            continue
        raw_snapshots.append(
            hub_document_to_runtime_snapshot(
                doc,
                tenant_id=tenant_id,
                owner_type="candidate",
                owner_id=str(candidate_id),
            )
        )
    return enrich_documents_via_contract(raw_snapshots)


async def sync_document_expiry_notification_events(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_ids: list[str] | None = None,
    candidate_limit: int = 5000,
    expiring_soon_days: int = DEFAULT_EXPIRING_SOON_DAYS,
) -> dict[str, Any]:
    """
    P4 sync job: Document Runtime Delivery Contract → expiry evaluator → event registry upsert.

    No message dispatch, task creation, or channel adapters.
    """
    scoped_tenant_id = str(tenant_id or "").strip()
    summary = empty_sync_summary(tenant_id=scoped_tenant_id)
    if not scoped_tenant_id:
        return summary

    stmt = (
        select(Candidate.id, Candidate.own_company_id)
        .where(Candidate.tenant_id == scoped_tenant_id)
        .order_by(Candidate.created_at.desc())
        .limit(max(1, int(candidate_limit)))
    )
    normalized_ids = [str(value).strip() for value in (candidate_ids or []) if str(value).strip()]
    if normalized_ids:
        stmt = stmt.where(Candidate.id.in_(normalized_ids))

    candidates = list((await db.execute(stmt)).all())
    summary["evaluated_owners"] = len(candidates)

    for candidate_id, own_company_id in candidates:
        owner_id = str(candidate_id).strip()
        own_company = str(own_company_id).strip() if own_company_id else None
        snapshots = await collect_candidate_runtime_snapshots(
            db,
            tenant_id=scoped_tenant_id,
            candidate_id=owner_id,
            own_company_id=own_company,
        )
        if not snapshots:
            continue

        owner_summary = await sync_document_expiry_events_with_summary(
            db,
            snapshots,
            tenant_id=scoped_tenant_id,
            expiring_soon_days=expiring_soon_days,
        )
        summary["evaluated_documents"] += int(owner_summary.get("evaluated_documents") or 0)
        summary["events_evaluated"] += int(owner_summary.get("events_evaluated") or 0)
        summary["created"] += int(owner_summary.get("created") or 0)
        summary["updated"] += int(owner_summary.get("updated") or 0)
        summary["skipped"] += int(owner_summary.get("skipped") or 0)
        for code, count in (owner_summary.get("event_codes") or {}).items():
            merged = summary.setdefault("event_codes", {})
            merged[str(code)] = int(merged.get(str(code)) or 0) + int(count or 0)

    return summary
