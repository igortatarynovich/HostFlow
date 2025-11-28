from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.app.db.deps import get_db_with_tenant
from backend.app.models.service import CandidateService
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/services-summary", tags=["services-summary"])


@router.get("", response_model=Dict[str, Any])
async def services_summary(
    db_tenant=Depends(get_db_with_tenant),
    candidate_id: Optional[UUID] = Query(
        None, description="фильтр по конкретному кандидату"
    ),
    code: Optional[List[str]] = Query(None, description="фильтр по service_code"),
    status: Optional[List[str]] = Query(None, description="фильтр по статусу"),
):
    """
    Сводка по доп-услугам:
      - by_code: количество и сумма по каждому коду услуги
      - by_status: количество по статусам
      - totals: общее количество и сумма
    Все агрегаты построены **только** на CandidateService.
    """
    db: AsyncSession
    db, tenant_id = db_tenant

    conds = [CandidateService.tenant_id == str(tenant_id)]
    if candidate_id:
        conds.append(CandidateService.candidate_id == str(candidate_id))
    if code:
        conds.append(
            CandidateService.service_code.in_([c.strip() for c in code if c.strip()])
        )
    if status:
        conds.append(
            CandidateService.status.in_([s.strip() for s in status if s.strip()])
        )

    base = select(CandidateService).where(and_(*conds)).subquery()

    # totals
    total_cnt_row = await db.execute(select(func.count()).select_from(base))
    total_cnt = total_cnt_row.scalar_one()

    total_sum_row = await db.execute(select(func.coalesce(func.sum(base.c.price), 0)))
    total_sum = float(total_sum_row.scalar_one() or 0)

    # by_code
    by_code_rows = await db.execute(
        select(
            base.c.service_code, func.count(), func.coalesce(func.sum(base.c.price), 0)
        )
        .group_by(base.c.service_code)
        .order_by(base.c.service_code.asc())
    )
    by_code = []
    for code_val, cnt, s in by_code_rows.all():
        by_code.append(
            {
                "service_code": code_val or "",
                "count": int(cnt or 0),
                "sum": float(s or 0),
            }
        )

    # by_status
    by_status_rows = await db.execute(
        select(base.c.status, func.count())
        .group_by(base.c.status)
        .order_by(base.c.status.asc())
    )
    by_status = {(st or ""): int(cnt or 0) for st, cnt in by_status_rows.all()}

    return {
        "totals": {"count": int(total_cnt or 0), "sum": float(total_sum or 0)},
        "by_code": by_code,
        "by_status": by_status,
        "filters": {
            "candidate_id": str(candidate_id) if candidate_id else None,
            "code": code or None,
            "status": status or None,
        },
    }
