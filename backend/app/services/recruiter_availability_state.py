"""Canonical recruiter availability for new-lead / candidate auto-assign (not User.extra)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.recruiter_availability_state import RecruiterAvailabilityStateRow


class RecruiterAvailabilityState(str, Enum):
    available = "available"
    paused = "paused"
    offline = "offline"
    vacation = "vacation"


_STATE_VALUES = frozenset(m.value for m in RecruiterAvailabilityState)


def parse_recruiter_availability_state(raw: str | None) -> RecruiterAvailabilityState:
    s = (raw or "").strip().lower()
    if s in _STATE_VALUES:
        return RecruiterAvailabilityState(s)
    return RecruiterAvailabilityState.available


async def get_recruiter_availability_state(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> RecruiterAvailabilityState:
    tid, uid = str(tenant_id).strip(), str(user_id).strip()
    if not tid or not uid:
        return RecruiterAvailabilityState.available
    row = await db.execute(
        select(RecruiterAvailabilityStateRow.state).where(
            RecruiterAvailabilityStateRow.tenant_id == tid,
            RecruiterAvailabilityStateRow.user_id == uid,
        )
    )
    val = row.scalar_one_or_none()
    if val is None:
        return RecruiterAvailabilityState.available
    return parse_recruiter_availability_state(str(val))


async def get_recruiter_availability_states_for_users(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_ids: Iterable[str],
) -> dict[str, RecruiterAvailabilityState]:
    tid = str(tenant_id).strip()
    ids = sorted({str(u).strip() for u in user_ids if str(u).strip()})
    if not tid or not ids:
        return {}
    rows = await db.execute(
        select(RecruiterAvailabilityStateRow.user_id, RecruiterAvailabilityStateRow.state).where(
            RecruiterAvailabilityStateRow.tenant_id == tid,
            RecruiterAvailabilityStateRow.user_id.in_(ids),
        )
    )
    return {
        str(r[0]): parse_recruiter_availability_state(str(r[1])) for r in rows.all() if r[0]
    }


async def upsert_recruiter_availability_state(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    state: RecruiterAvailabilityState,
) -> RecruiterAvailabilityStateRow:
    tid, uid = str(tenant_id).strip(), str(user_id).strip()
    now = datetime.now(timezone.utc)
    existing = await db.execute(
        select(RecruiterAvailabilityStateRow).where(
            RecruiterAvailabilityStateRow.tenant_id == tid,
            RecruiterAvailabilityStateRow.user_id == uid,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = RecruiterAvailabilityStateRow(
            id=str(uuid.uuid4()),
            tenant_id=tid,
            user_id=uid,
            state=state.value,
            updated_at=now,
        )
        db.add(row)
    else:
        row.state = state.value
        row.updated_at = now
    await db.flush()
    return row
