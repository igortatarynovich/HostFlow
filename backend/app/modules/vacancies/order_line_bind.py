"""Bind Vacancy ↔ Sales Order Line (ADR-032)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.sales_order import SalesOrder, SalesOrderLine
from backend.app.models.vacancy import Vacancy


class OrderLineBindError(ValueError):
    def __init__(self, detail: str, *, status_code: int = 422):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


async def resolve_order_line_for_vacancy_bind(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    order_line_id: str,
    exclude_vacancy_id: str | None = None,
) -> tuple[SalesOrderLine, SalesOrder]:
    lid = str(order_line_id or "").strip()
    if not lid:
        raise OrderLineBindError("order_line_id is required")
    line = await db.get(SalesOrderLine, lid)
    if line is None or str(line.tenant_id) != str(tenant_id):
        raise OrderLineBindError("Order line not found", status_code=404)
    order = await db.get(SalesOrder, str(line.sales_order_id))
    if order is None or str(order.tenant_id) != str(tenant_id):
        raise OrderLineBindError("Sales order not found", status_code=404)
    if str(order.company_id) != str(company_id):
        raise OrderLineBindError("Order line company must match vacancy company_id")
    if str(line.status or "").lower() not in {"open", "in_progress"}:
        raise OrderLineBindError("Order line must be open or in_progress")
    if str(order.status or "").lower() not in {"open", "in_progress"}:
        raise OrderLineBindError("Sales order must be open or in_progress")
    stmt = select(Vacancy.id).where(
        Vacancy.tenant_id == tenant_id,
        Vacancy.order_line_id == lid,
    )
    if exclude_vacancy_id:
        stmt = stmt.where(Vacancy.id != str(exclude_vacancy_id))
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise OrderLineBindError(
            "Order line already has a vacancy (1 line = 1 vacancy)",
            status_code=409,
        )
    return line, order
