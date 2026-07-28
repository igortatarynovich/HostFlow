"""ADR-032: accrue SalesBillableItem from recruitment / workforce results.

Sales-owned. Other modules call only through ``contracts`` (delivery facade).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.sales_order import BILLING_TRIGGERS, SalesBillableItem, SalesOrder, SalesOrderLine
from backend.app.models.vacancy import Vacancy

logger = logging.getLogger(__name__)

HIRED_STAGES = frozenset({"hired", "employed"})
TRIGGER_HIRED = "candidate_hired"
TRIGGER_STARTED = "candidate_started_work"
TRIGGER_HEADCOUNT = "headcount_completed"

_V1_AUTO_TRIGGERS = frozenset({TRIGGER_HIRED, TRIGGER_STARTED, TRIGGER_HEADCOUNT})


def _dec(value: object | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


async def _existing_non_void(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_order_line_id: str,
    trigger_code: str,
    source_entity_type: str,
    source_entity_id: str,
) -> Optional[SalesBillableItem]:
    q = await db.execute(
        select(SalesBillableItem).where(
            SalesBillableItem.tenant_id == tenant_id,
            SalesBillableItem.sales_order_line_id == sales_order_line_id,
            SalesBillableItem.trigger_code == trigger_code,
            SalesBillableItem.source_entity_type == source_entity_type,
            SalesBillableItem.source_entity_id == source_entity_id,
            SalesBillableItem.status != "void",
        )
    )
    return q.scalars().first()


async def _load_line_for_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: str,
) -> tuple[Optional[Vacancy], Optional[SalesOrderLine], Optional[SalesOrder]]:
    vac = await db.get(Vacancy, str(vacancy_id).strip())
    if vac is None or str(vac.tenant_id) != tenant_id:
        return None, None, None
    line_id = getattr(vac, "order_line_id", None)
    if not line_id:
        return vac, None, None
    line = await db.get(SalesOrderLine, str(line_id))
    if line is None or str(line.tenant_id) != tenant_id:
        return vac, None, None
    order = await db.get(SalesOrder, line.sales_order_id)
    if order is None or str(order.tenant_id) != tenant_id:
        return vac, line, None
    return vac, line, order


async def _create_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    order: SalesOrder,
    line: SalesOrderLine,
    trigger_code: str,
    amount: Decimal,
    quantity: Decimal,
    source_entity_type: str,
    source_entity_id: str,
    notes: Optional[str] = None,
) -> SalesBillableItem:
    currency = (str(order.currency or "").strip().upper() or "PLN")
    item = SalesBillableItem(
        id=str(uuid4()),
        tenant_id=tenant_id,
        sales_order_id=order.id,
        sales_order_line_id=line.id,
        trigger_code=trigger_code,
        amount=amount,
        currency=currency,
        quantity=quantity,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        status="pending",
        notes=notes,
    )
    db.add(item)
    await db.flush()
    return item


async def _count_hired_on_vacancy(db: AsyncSession, *, tenant_id: str, vacancy_id: str) -> int:
    q = await db.execute(
        select(func.count())
        .select_from(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.vacancy_id == vacancy_id,
            Candidate.stage.in_(tuple(HIRED_STAGES)),
        )
    )
    return int(q.scalar() or 0)


async def _maybe_headcount_completed(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy: Vacancy,
    line: SalesOrderLine,
    order: SalesOrder,
) -> Optional[SalesBillableItem]:
    if str(line.billing_trigger or "").strip() != TRIGGER_HEADCOUNT:
        return None
    needed = int(line.quantity_needed or 0)
    if needed < 1:
        return None
    hired = await _count_hired_on_vacancy(db, tenant_id=tenant_id, vacancy_id=str(vacancy.id))
    if hired < needed:
        return None
    existing = await _existing_non_void(
        db,
        tenant_id=tenant_id,
        sales_order_line_id=line.id,
        trigger_code=TRIGGER_HEADCOUNT,
        source_entity_type="sales_order_line",
        source_entity_id=line.id,
    )
    if existing is not None:
        return existing
    rate = _dec(line.unit_rate)
    amount = rate * Decimal(needed) if rate else Decimal("0")
    return await _create_item(
        db,
        tenant_id=tenant_id,
        order=order,
        line=line,
        trigger_code=TRIGGER_HEADCOUNT,
        amount=amount,
        quantity=Decimal(needed),
        source_entity_type="sales_order_line",
        source_entity_id=line.id,
        notes=f"headcount filled: {hired}/{needed}",
    )


async def accrue_on_candidate_hired(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
) -> Optional[SalesBillableItem]:
    """Create billable when line.billing_trigger is candidate_hired; also evaluate headcount_completed."""
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    vid = str(vacancy_id or "").strip() or None
    if not vid:
        return None
    vac, line, order = await _load_line_for_vacancy(db, tenant_id=tid, vacancy_id=vid)
    if vac is None or line is None or order is None:
        return None

    trigger = str(line.billing_trigger or "").strip()
    if trigger not in BILLING_TRIGGERS or trigger not in _V1_AUTO_TRIGGERS:
        return None

    created: Optional[SalesBillableItem] = None
    if trigger == TRIGGER_HIRED:
        existing = await _existing_non_void(
            db,
            tenant_id=tid,
            sales_order_line_id=line.id,
            trigger_code=TRIGGER_HIRED,
            source_entity_type="candidate",
            source_entity_id=cid,
        )
        if existing is not None:
            return existing
        rate = _dec(line.unit_rate)
        created = await _create_item(
            db,
            tenant_id=tid,
            order=order,
            line=line,
            trigger_code=TRIGGER_HIRED,
            amount=rate,
            quantity=Decimal("1"),
            source_entity_type="candidate",
            source_entity_id=cid,
        )
    elif trigger == TRIGGER_HEADCOUNT:
        created = await _maybe_headcount_completed(
            db, tenant_id=tid, vacancy=vac, line=line, order=order
        )
    return created


async def accrue_on_candidate_started_work(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
) -> Optional[SalesBillableItem]:
    """Create billable when line.billing_trigger is candidate_started_work."""
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    vid = str(vacancy_id or "").strip() or None
    if not vid:
        return None
    vac, line, order = await _load_line_for_vacancy(db, tenant_id=tid, vacancy_id=vid)
    if vac is None or line is None or order is None:
        return None
    if str(line.billing_trigger or "").strip() != TRIGGER_STARTED:
        return None
    existing = await _existing_non_void(
        db,
        tenant_id=tid,
        sales_order_line_id=line.id,
        trigger_code=TRIGGER_STARTED,
        source_entity_type="candidate",
        source_entity_id=cid,
    )
    if existing is not None:
        return existing
    rate = _dec(line.unit_rate)
    return await _create_item(
        db,
        tenant_id=tid,
        order=order,
        line=line,
        trigger_code=TRIGGER_STARTED,
        amount=rate,
        quantity=Decimal("1"),
        source_entity_type="candidate",
        source_entity_id=cid,
    )


async def safe_accrue_on_candidate_hired(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
) -> None:
    """Never raise into recruitment callers."""
    try:
        item = await accrue_on_candidate_hired(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
        )
        if item is not None:
            await db.commit()
    except Exception:
        logger.exception(
            "sales_billable_accrual_hired_failed tenant=%s candidate=%s vacancy=%s",
            tenant_id,
            candidate_id,
            vacancy_id,
        )
        try:
            await db.rollback()
        except Exception:
            pass


async def safe_accrue_on_candidate_started_work(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
) -> None:
    """Never raise into workforce callers."""
    try:
        item = await accrue_on_candidate_started_work(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
        )
        if item is not None:
            await db.commit()
    except Exception:
        logger.exception(
            "sales_billable_accrual_started_failed tenant=%s candidate=%s vacancy=%s",
            tenant_id,
            candidate_id,
            vacancy_id,
        )
        try:
            await db.rollback()
        except Exception:
            pass
