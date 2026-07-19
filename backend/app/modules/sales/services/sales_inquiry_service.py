"""Sales-owned SalesInquiry result creation (Runtime Split R4).

Must not import Recruitment models/services.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.lead import Lead
from backend.app.models.sales_inquiry import INITIAL_SALES_INQUIRY_STATUS, SalesInquiry


class SalesInquiryTransportConflictError(Exception):
    """Transport Lead is already bound to a Recruitment Application."""

    code = "sales_inquiry_transport_conflict"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _existing_link(lead: Lead) -> dict[str, Any]:
    return _record(_record(lead.normalized).get("intake_result_link_v1"))


def _stamp_transport_link(lead: Lead, *, sales_inquiry_id: str) -> None:
    normalized = _record(lead.normalized)
    link = _record(normalized.get("intake_result_link_v1"))
    if link.get("sales_inquiry_id") == sales_inquiry_id:
        return
    if link.get("application_id") or link.get("result_type") == "application":
        raise SalesInquiryTransportConflictError(
            "transport lead already linked to Application",
            details={
                "lead_id": str(lead.id),
                "application_id": link.get("application_id"),
                "sales_inquiry_id": sales_inquiry_id,
            },
        )
    normalized["intake_result_link_v1"] = {
        "result_type": "sales_inquiry",
        "sales_inquiry_id": sales_inquiry_id,
        "linked_at": datetime.now(timezone.utc).isoformat(),
    }
    lead.normalized = normalized
    flag_modified(lead, "normalized")


async def ensure_sales_inquiry_for_transport_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str = "public_intake",
    idempotency_key: Optional[str] = None,
    entity_profile_code: Optional[str] = None,
    intake_source_profile_id: Optional[str] = None,
    form_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> SalesInquiry:
    """Idempotent SalesInquiry creation owned by Sales destination.

    Idempotency: (tenant_id, lead_id) when lead is set; else (tenant_id, idempotency_key).
    """
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    if not tid or not lid:
        raise ValueError("tenant_id and lead.id are required")

    link = _existing_link(lead)
    if link.get("application_id") or link.get("result_type") == "application":
        raise SalesInquiryTransportConflictError(
            "transport lead already linked to Application",
            details={"lead_id": lid, "application_id": link.get("application_id")},
        )

    existing = await db.scalar(
        select(SalesInquiry).where(
            SalesInquiry.tenant_id == tid,
            SalesInquiry.lead_id == lid,
        ).limit(1)
    )
    if existing is not None:
        _stamp_transport_link(lead, sales_inquiry_id=str(existing.id))
        await db.flush()
        return existing

    key = str(idempotency_key or "").strip() or None
    if key:
        by_key = await db.scalar(
            select(SalesInquiry).where(
                SalesInquiry.tenant_id == tid,
                SalesInquiry.idempotency_key == key,
            ).limit(1)
        )
        if by_key is not None:
            if not by_key.lead_id:
                by_key.lead_id = lid
            _stamp_transport_link(lead, sales_inquiry_id=str(by_key.id))
            await db.flush()
            return by_key

    stamps = dict(meta) if isinstance(meta, dict) else {}
    stamps.setdefault(
        "intake_result_v1",
        {
            "route_intent": "sales_inquiry",
            "destination": "sales",
            "handler_id": "sales.inquiry_draft",
            "transport_lead_id": lid,
        },
    )

    row = SalesInquiry(
        tenant_id=tid,
        lead_id=lid,
        status=INITIAL_SALES_INQUIRY_STATUS,
        source=str(source or "public_intake").strip() or "public_intake",
        own_company_id=str(getattr(lead, "own_company_id", None) or "").strip() or None,
        assignee_id=str(getattr(lead, "assigned_to", None) or getattr(lead, "recruiter_id", None) or "").strip()
        or None,
        entity_profile_code=str(entity_profile_code or "").strip() or None,
        intake_source_profile_id=str(intake_source_profile_id or "").strip() or None,
        form_id=str(form_id or "").strip() or None,
        idempotency_key=key,
        meta=stamps,
    )
    db.add(row)
    await db.flush()
    _stamp_transport_link(lead, sales_inquiry_id=str(row.id))
    await db.flush()
    return row
