"""SalesInquiry product resolve helpers (Stage 3 slice 3)."""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.leads import crud
from backend.app.modules.sales.services.sales_inquiry_service import (
    SalesInquiryTransportConflictError,
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
            try:
                inquiry = await ensure_sales_inquiry_for_transport_lead(
                    db,
                    tenant_id=tid,
                    lead=lead,
                    source=source,
                )
            except SalesInquiryTransportConflictError as exc:
                raise LookupError("application not found") from exc
        if inquiry is not None:
            return inquiry, lead

    inquiry = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.id == aid, SalesInquiry.tenant_id == tid)
        .limit(1)
    )
    if inquiry is None:
        raise LookupError("application not found")

    lead_id = str(inquiry.lead_id or "").strip()
    if not lead_id:
        raise LookupError("application not found")
    lead = await crud.get_lead(db, tenant_id=tid, lead_id=lead_id)
    if lead is None or not _is_client_sales_lead(lead):
        raise LookupError("application not found")
    return inquiry, lead


async def _ensure_missing_client_sales_inquiries(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
) -> int:
    """Create SI rows for client transport leads that still lack one (Meta inbox).

    Returns how many SalesInquiry rows were created in this call. Callers that
    serve HTTP must commit afterwards — otherwise list returns IDs that GET 404s.
    """
    stmt = (
        select(Lead)
        .outerjoin(
            SalesInquiry,
            and_(
                SalesInquiry.tenant_id == Lead.tenant_id,
                SalesInquiry.lead_id == Lead.id,
            ),
        )
        .where(
            Lead.tenant_id == tenant_id,
            Lead.lead_type == "client",
            Lead.lead_target_type == "client_lead",
            SalesInquiry.id.is_(None),
        )
        .limit(200)
    )
    oc = str(own_company_id or "").strip()
    if oc:
        stmt = stmt.where(Lead.own_company_id == oc)
    rows = (await db.execute(stmt)).scalars().all()
    created = 0
    for lead in rows:
        source = str(getattr(lead, "source", None) or "meta").strip() or "meta"
        try:
            await ensure_sales_inquiry_for_transport_lead(
                db,
                tenant_id=tenant_id,
                lead=lead,
                source=source,
            )
            created += 1
        except SalesInquiryTransportConflictError:
            continue
    return created


async def list_sales_inquiry_pairs(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    limit: int = 200,
    offset: int = 0,
) -> Tuple[list[Tuple[SalesInquiry, Lead]], int]:
    """Inbox page: SalesInquiry ⨝ transport Lead. Product id is the SI row."""
    await _ensure_missing_client_sales_inquiries(
        db, tenant_id=tenant_id, own_company_id=own_company_id
    )

    filters = [
        SalesInquiry.tenant_id == tenant_id,
        Lead.lead_type == "client",
        Lead.lead_target_type == "client_lead",
    ]
    oc = str(own_company_id or "").strip()
    if oc:
        filters.append(Lead.own_company_id == oc)

    base = (
        select(SalesInquiry, Lead)
        .join(Lead, Lead.id == SalesInquiry.lead_id)
        .where(*filters)
    )
    total = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesInquiry)
            .join(Lead, Lead.id == SalesInquiry.lead_id)
            .where(*filters)
        )
        or 0
    )
    page = (
        await db.execute(
            base.order_by(desc(SalesInquiry.updated_at), desc(SalesInquiry.created_at))
            .offset(max(0, int(offset)))
            .limit(max(1, min(int(limit), 200)))
        )
    ).all()
    return [(inquiry, lead) for inquiry, lead in page], total
