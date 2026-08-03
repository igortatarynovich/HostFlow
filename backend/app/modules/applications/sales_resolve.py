"""SalesInquiry product resolve helpers (Stage 3 slice 3)."""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.leads import crud
from backend.app.modules.sales.services.sales_inquiry_service import (
    ensure_sales_inquiry_for_transport_lead,
)


def _is_client_sales_lead(lead: Lead) -> bool:
    return str(getattr(lead, "lead_type", "") or "") == "client" and str(
        getattr(lead, "lead_target_type", "") or ""
    ) == "client_lead"


async def resolve_sales_inquiry_and_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    ensure_if_lead: bool = True,
) -> Tuple[SalesInquiry, Lead]:
    """Resolve SalesInquiry + transport Lead by SI id or Lead id (compat).

    Order: Lead id → SalesInquiry by lead_id → SalesInquiry PK → load Lead.
    When ``ensure_if_lead`` and a client Lead has no SI yet, create one (Meta inbox).
    """
    tid = str(tenant_id).strip()
    aid = str(application_id or "").strip()
    if not tid or not aid:
        raise LookupError("application not found")

    lead = await crud.get_lead(db, tenant_id=tid, lead_id=aid)
    inquiry: Optional[SalesInquiry] = None

    if lead is not None and _is_client_sales_lead(lead):
        inquiry = await db.scalar(
            select(SalesInquiry)
            .where(SalesInquiry.tenant_id == tid, SalesInquiry.lead_id == str(lead.id))
            .limit(1)
        )
        if inquiry is None and ensure_if_lead:
            source = str(getattr(lead, "source", None) or "meta").strip() or "meta"
            inquiry = await ensure_sales_inquiry_for_transport_lead(
                db,
                tenant_id=tid,
                lead=lead,
                source=source,
            )
        if inquiry is not None:
            return inquiry, lead

    inquiry = await db.get(SalesInquiry, aid)
    if inquiry is None or str(inquiry.tenant_id) != tid:
        raise LookupError("application not found")

    lead_id = str(inquiry.lead_id or "").strip()
    if not lead_id:
        raise LookupError("application not found")
    lead = await crud.get_lead(db, tenant_id=tid, lead_id=lead_id)
    if lead is None or not _is_client_sales_lead(lead):
        raise LookupError("application not found")
    return inquiry, lead
