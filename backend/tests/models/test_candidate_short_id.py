from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate


async def _set_tenant(session, tenant_id: str) -> None:
    try:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
    except Exception:
        pass


@pytest.mark.anyio
async def test_assign_short_id_ignores_non_digits_and_scopes_per_tenant() -> None:
    tenant = str(uuid.uuid4())
    other_tenant = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _set_tenant(session, tenant)
        session.add(
            Candidate(
                id=str(uuid.uuid4()),
                tenant_id=tenant,
                first_name="Existing",
                last_name="Candidate",
                short_id="CND000123",
            )
        )
        session.add(
            Candidate(
                id=str(uuid.uuid4()),
                tenant_id=tenant,
                first_name="Junk",
                last_name="Value",
                short_id="TMP",
            )
        )
        await session.flush()

        await _set_tenant(session, other_tenant)
        session.add(
            Candidate(
                id=str(uuid.uuid4()),
                tenant_id=other_tenant,
                first_name="Other",
                last_name="Tenant",
                short_id="CND999999",
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant)
        candidate = Candidate(
            tenant_id=tenant,
            first_name="New",
            last_name="Candidate",
        )
        session.add(candidate)
        await session.flush()
        assigned = candidate.short_id
        assert assigned == "CND000124"
        await session.rollback()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant)
        await session.execute(
            text("DELETE FROM candidates WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant},
        )
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, other_tenant)
        await session.execute(
            text("DELETE FROM candidates WHERE tenant_id = :tenant_id"),
            {"tenant_id": other_tenant},
        )
        await session.commit()
