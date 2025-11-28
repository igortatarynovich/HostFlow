from __future__ import annotations

from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_employment import CandidateEmployment


def _normalize_id(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return str(value)


async def list_employments(
    db: AsyncSession,
    tenant_id: str | bytes,
    candidate_id: str | bytes,
) -> Sequence[CandidateEmployment]:
    stmt = (
        select(CandidateEmployment)
        .where(
            CandidateEmployment.tenant_id == _normalize_id(tenant_id),
            CandidateEmployment.candidate_id == _normalize_id(candidate_id),
        )
        .order_by(
            CandidateEmployment.start_date.desc(),
            CandidateEmployment.created_at.desc(),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def count_employments(
    db: AsyncSession,
    tenant_id: str | bytes,
    candidate_id: str | bytes,
) -> int:
    stmt = (
        select(func.count())
        .select_from(CandidateEmployment)
        .where(
            CandidateEmployment.tenant_id == _normalize_id(tenant_id),
            CandidateEmployment.candidate_id == _normalize_id(candidate_id),
        )
    )
    return int((await db.scalar(stmt)) or 0)


async def get_employment(
    db: AsyncSession,
    tenant_id: str | bytes,
    candidate_id: str | bytes,
    employment_id: str | bytes,
) -> CandidateEmployment | None:
    stmt = select(CandidateEmployment).where(
        CandidateEmployment.tenant_id == _normalize_id(tenant_id),
        CandidateEmployment.candidate_id == _normalize_id(candidate_id),
        CandidateEmployment.id == _normalize_id(employment_id),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_employment(
    db: AsyncSession,
    tenant_id: str | bytes,
    candidate_id: str | bytes,
    payload: dict,
) -> CandidateEmployment:
    record = CandidateEmployment(
        tenant_id=_normalize_id(tenant_id),
        candidate_id=_normalize_id(candidate_id),
        **payload,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def update_employment(
    db: AsyncSession,
    record: CandidateEmployment,
    updates: dict,
) -> CandidateEmployment:
    for key, value in updates.items():
        setattr(record, key, value)
    await db.flush()
    await db.refresh(record)
    return record


async def delete_employment(
    db: AsyncSession,
    tenant_id: str | bytes,
    candidate_id: str | bytes,
    employment_id: str | bytes,
) -> bool:
    stmt = (
        delete(CandidateEmployment)
        .where(
            CandidateEmployment.tenant_id == _normalize_id(tenant_id),
            CandidateEmployment.candidate_id == _normalize_id(candidate_id),
            CandidateEmployment.id == _normalize_id(employment_id),
        )
    )
    result = await db.execute(stmt)
    return result.rowcount > 0


__all__ = [
    "CandidateEmployment",
    "list_employments",
    "count_employments",
    "get_employment",
    "create_employment",
    "update_employment",
    "delete_employment",
]
