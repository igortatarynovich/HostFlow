"""Delivery facade for Sales Order billable accrual (ADR-032).

Other modules may import **only** this module from ``sales_orders`` for accrual.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.sales_orders.accrual import (
    HIRED_STAGES,
    safe_accrue_on_candidate_hired,
    safe_accrue_on_candidate_started_work,
)

__all__ = [
    "HIRED_STAGES",
    "notify_candidate_hired",
    "notify_candidate_started_work",
]


async def notify_candidate_hired(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
    stage_code: Optional[str] = None,
) -> None:
    """Call after candidate stage lands in hired/employed (idempotent, never raises)."""
    stage = str(stage_code or "").strip().lower()
    if stage and stage not in HIRED_STAGES:
        return
    await safe_accrue_on_candidate_hired(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
    )


async def notify_candidate_started_work(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
) -> None:
    """Call when workforce employee flips onboarding → active (idempotent, never raises)."""
    await safe_accrue_on_candidate_started_work(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
    )
