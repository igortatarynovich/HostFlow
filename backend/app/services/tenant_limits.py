from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import TenantLicense, TenantUsage, TenantUsageMetric


@dataclass
class TenantLimits:
    """Сводка лимитов арендатора.

    Значение 0 трактуем как «без ограничения» и не блокируем операции.
    Жёсткая логика интерпретации лимитов живёт в сервисном слое и UI.
    """

    plan: str
    max_recruiters: int
    max_supervisors: int
    max_client_managers: int
    max_viewers: int
    max_storage_gb: int
    max_companies: int
    max_candidates_active: int
    max_vacancies_active: int
    max_documents: int
    max_public_portal_links: int


def _license_to_limits(license_entry: Optional[TenantLicense]) -> TenantLimits:
    """Преобразует ORM-модель лицензии в DTO ограничений.

    Если лицензии нет, считаем, что это базовый бесплатный план без жёстких лимитов (0 = unlimited).
    """

    if not license_entry:
        return TenantLimits(
            plan="free",
            max_recruiters=0,
            max_supervisors=0,
            max_client_managers=0,
            max_viewers=0,
            max_storage_gb=0,
            max_companies=0,
            max_candidates_active=0,
            max_vacancies_active=0,
            max_documents=0,
            max_public_portal_links=0,
        )

    return TenantLimits(
        plan=license_entry.plan or "custom",
        max_recruiters=license_entry.max_recruiters,
        max_supervisors=license_entry.max_supervisors,
        max_client_managers=license_entry.max_client_managers,
        max_viewers=license_entry.max_viewers,
        max_storage_gb=license_entry.max_storage_gb,
        max_companies=license_entry.max_companies,
        max_candidates_active=license_entry.max_candidates_active,
        max_vacancies_active=license_entry.max_vacancies_active,
        max_documents=license_entry.max_documents,
        max_public_portal_links=license_entry.max_public_portal_links,
    )


async def get_tenant_limits(db: AsyncSession, tenant_id: str) -> TenantLimits:
    """Возвращает агрегированные лимиты для арендатора."""

    stmt = select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1)
    result = await db.execute(stmt)
    license_entry = result.scalar_one_or_none()
    return _license_to_limits(license_entry)


def _month_period(today: Optional[date] = None) -> tuple[date, date]:
    """Возвращает период [from, to] для текущего календарного месяца."""

    today = today or date.today()
    start = date(today.year, today.month, 1)
    if today.month == 12:
        end_month = 1
        end_year = today.year + 1
    else:
        end_month = today.month + 1
        end_year = today.year
    end = date(end_year, end_month, 1)
    return start, end


async def get_tenant_usage(
    db: AsyncSession,
    tenant_id: str,
    metric: TenantUsageMetric | str,
    *,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> int:
    """Возвращает значение usage-метрики за период (по умолчанию — текущий месяц)."""

    if period_start is None or period_end is None:
        period_start, period_end = _month_period()

    metric_value = metric.value if isinstance(metric, TenantUsageMetric) else str(metric)

    stmt = (
        select(TenantUsage.value)
        .where(TenantUsage.tenant_id == tenant_id)
        .where(TenantUsage.metric == metric_value)
        .where(TenantUsage.period_start == period_start)
        .where(TenantUsage.period_end == period_end)
        .limit(1)
    )
    result = await db.execute(stmt)
    value = result.scalar_one_or_none()
    return int(value or 0)


async def increment_tenant_usage(
    db: AsyncSession,
    tenant_id: str,
    metric: TenantUsageMetric | str,
    *,
    delta: int = 1,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> TenantUsage:
    """Увеличивает счётчик usage-метрики (по умолчанию — в рамках текущего месяца)."""

    if delta <= 0:
        raise ValueError("delta must be positive")

    if period_start is None or period_end is None:
        period_start, period_end = _month_period()

    metric_value = metric.value if isinstance(metric, TenantUsageMetric) else str(metric)

    stmt = (
        select(TenantUsage)
        .where(TenantUsage.tenant_id == tenant_id)
        .where(TenantUsage.metric == metric_value)
        .where(TenantUsage.period_start == period_start)
        .where(TenantUsage.period_end == period_end)
        .with_for_update()
    )
    result = await db.execute(stmt)
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = TenantUsage(
            tenant_id=tenant_id,
            metric=metric_value,
            period_start=period_start,
            period_end=period_end,
            value=delta,
        )
        db.add(usage)
    else:
        usage.value = int(usage.value or 0) + delta

    await db.flush()
    return usage


async def ensure_usage_limit_not_exceeded(
    db: AsyncSession,
    tenant_id: str,
    metric: TenantUsageMetric | str,
    *,
    limit_per_month: int,
    increment: int = 1,
) -> None:
    """Проверяет месячный лимит по usage-метрике и выбрасывает 402/403 при превышении.

    На данном этапе используется как строительный блок для будущего paywall:
    вызывается перед выполнением «дорогих» операций (OCR, уведомления и т.п.).
    """

    if limit_per_month <= 0:
        # 0 или отрицательное значение — считаем «без ограничения» и ничего не блокируем.
        return

    current_value = await get_tenant_usage(db, tenant_id, metric)
    projected = current_value + max(increment, 0)

    if projected > limit_per_month:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "usage_limit_exceeded",
                "metric": metric.value if isinstance(metric, TenantUsageMetric) else str(metric),
                "limit": limit_per_month,
                "current": current_value,
            },
        )


