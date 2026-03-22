"""Aggregate service order metrics per company (party as client)."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.additional_service import ServiceOrder


async def company_service_order_metrics(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_ids: List[str],
) -> Dict[str, Dict[str, object]]:
    """
    For each company_id with service orders in this tenant:
      - active_orders: count where status not in (completed, cancelled)
      - revenue_completed: sum(total_amount) where status == completed
    """
    if not company_ids:
        return {}

    active_expr = func.count().filter(
        ~ServiceOrder.status.in_(["completed", "cancelled"]),
    )
    revenue_expr = func.coalesce(
        func.sum(ServiceOrder.total_amount).filter(ServiceOrder.status == "completed"),
        0,
    )

    stmt = (
        select(
            ServiceOrder.company_id,
            active_expr.label("active_orders"),
            revenue_expr.label("revenue_completed"),
        )
        .where(
            ServiceOrder.tenant_id == tenant_id,
            ServiceOrder.company_id.isnot(None),
            ServiceOrder.company_id.in_(company_ids),
        )
        .group_by(ServiceOrder.company_id)
    )
    rows = (await db.execute(stmt)).all()
    out: Dict[str, Dict[str, object]] = {}
    for cid, active_n, rev in rows:
        if not cid:
            continue
        sid = str(cid)
        rev_dec = rev if isinstance(rev, Decimal) else Decimal(str(rev or 0))
        out[sid] = {
            "active_orders": int(active_n or 0),
            "revenue_completed": float(rev_dec.quantize(Decimal("0.01"))),
        }
    return out
