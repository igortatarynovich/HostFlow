"""Read Employment rows. This module does not open an Employment from handoff."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.hr_employment import Employment

_ACTIVE = "active"


def choose_display_employment(rows: Iterable[Employment]) -> Optional[Employment]:
    """The in-force relationship, otherwise the newest row.

    One backfilled employee has one row, so the choice does not matter there.
    """

    found = list(rows)
    if not found:
        return None
    active = [row for row in found if row.state == _ACTIVE]
    pool = active or found

    def _key(row: Employment) -> datetime:
        created = row.created_at
        if created is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if created.tzinfo is None:
            return created.replace(tzinfo=timezone.utc)
        return created

    return max(pool, key=_key)


async def list_employments(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> list[Employment]:
    res = await db.execute(
        select(Employment)
        .where(
            Employment.tenant_id == tenant_id,
            Employment.employee_id == employee_id,
        )
        .order_by(Employment.created_at.desc())
    )
    return list(res.scalars().all())


async def display_employment(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> Optional[Employment]:
    return choose_display_employment(await list_employments(db, tenant_id, employee_id))


async def display_employments_by_employee(
    db: AsyncSession,
    tenant_id: str,
    employee_ids: Iterable[str],
) -> dict[str, Employment]:
    ids = [str(item) for item in employee_ids if str(item).strip()]
    if not ids:
        return {}
    res = await db.execute(
        select(Employment).where(
            Employment.tenant_id == tenant_id,
            Employment.employee_id.in_(ids),
        )
    )
    grouped: dict[str, list[Employment]] = {}
    for row in res.scalars().all():
        grouped.setdefault(str(row.employee_id), []).append(row)
    return {key: choose_display_employment(value) for key, value in grouped.items() if value}


async def snapshot_for_employee(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> dict | None:
    row = await display_employment(db, tenant_id, employee_id)
    snap = row.candidate_snapshot if row is not None else None
    return snap if isinstance(snap, dict) else None


async def handoff_id_for_employee(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> str | None:
    row = await display_employment(db, tenant_id, employee_id)
    if row is None:
        return None
    text = str(row.handoff_id or "").strip()
    return text or None
