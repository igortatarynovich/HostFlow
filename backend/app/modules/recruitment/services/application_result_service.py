"""Recruitment-owned Application result creation (Runtime Split R4).

Must not import Sales models/services.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.lead import Lead
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_lead_intent,
)


class ApplicationTransportConflictError(Exception):
    """Transport Lead is already bound to a SalesInquiry."""

    code = "application_transport_conflict"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _existing_link(lead: Lead) -> dict[str, Any]:
    return _record(_record(lead.normalized).get("intake_result_link_v1"))


def _ensure_pool_intent_if_needed(lead: Lead) -> None:
    """Allow Application creation for public intake without vacancy (pool intent)."""
    if getattr(lead, "vacancy_id", None):
        return
    if getattr(lead, "funnel_id", None):
        return
    normalized = _record(lead.normalized)
    if normalized.get("recruitment_pool_intent_v1") is True:
        return
    normalized["recruitment_pool_intent_v1"] = True
    lead.normalized = normalized
    flag_modified(lead, "normalized")


def _stamp_transport_link(lead: Lead, *, application_id: str) -> None:
    normalized = _record(lead.normalized)
    link = _record(normalized.get("intake_result_link_v1"))
    if link.get("application_id") == application_id:
        return
    if link.get("sales_inquiry_id") or link.get("result_type") == "sales_inquiry":
        raise ApplicationTransportConflictError(
            "transport lead already linked to SalesInquiry",
            details={
                "lead_id": str(lead.id),
                "sales_inquiry_id": link.get("sales_inquiry_id"),
                "application_id": application_id,
            },
        )
    normalized["intake_result_link_v1"] = {
        "result_type": "application",
        "application_id": application_id,
        "linked_at": datetime.now(timezone.utc).isoformat(),
    }
    lead.normalized = normalized
    flag_modified(lead, "normalized")


async def ensure_application_result_for_transport_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    candidate_id: str,
    source: str = "public_intake",
    idempotency_key: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> Optional[RecruitmentApplication]:
    """Create/return Recruitment Application as destination result (idempotent on lead)."""
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    cid = str(candidate_id or "").strip()
    if not tid or not lid or not cid:
        return None

    link = _existing_link(lead)
    if link.get("sales_inquiry_id") or link.get("result_type") == "sales_inquiry":
        raise ApplicationTransportConflictError(
            "transport lead already linked to SalesInquiry",
            details={"lead_id": lid, "sales_inquiry_id": link.get("sales_inquiry_id")},
        )

    _ensure_pool_intent_if_needed(lead)

    stamps = dict(meta) if isinstance(meta, dict) else {}
    stamps.setdefault(
        "intake_result_v1",
        {
            "route_intent": "candidate_application",
            "destination": "recruitment",
            "handler_id": "recruitment.lead_draft",
            "transport_lead_id": lid,
            "idempotency_key": str(idempotency_key or "").strip() or None,
        },
    )

    app = await ensure_recruitment_application_for_lead_intent(
        db,
        tenant_id=tid,
        candidate_id=cid,
        lead=lead,
        lead_id=lid,
        source=str(source or "public_intake").strip() or "public_intake",
        meta=stamps,
    )
    if app is None:
        return None
    _stamp_transport_link(lead, application_id=str(app.id))
    await db.flush()
    return app
