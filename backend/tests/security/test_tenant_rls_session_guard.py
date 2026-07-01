"""Postgres-only: enforced session cannot execute SQL before RLS tenant bind."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.db.deps import bind_tenant_context_to_session
from backend.app.db.session import async_session_maker


@pytest.mark.anyio
async def test_enforced_session_blocks_execute_before_bind() -> None:
    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("RLS tenant guard is enforced on PostgreSQL only")
        session.info["tenant_rls_enforcement"] = True
        with pytest.raises(RuntimeError, match="RLS tenant context"):
            await session.execute(text("SELECT 1"))


@pytest.mark.anyio
async def test_enforced_session_allows_execute_after_bind() -> None:
    from uuid import UUID

    tid = UUID("11111111-1111-1111-1111-111111111111")
    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL only")
        session.info["tenant_rls_enforcement"] = True
        await bind_tenant_context_to_session(session, tid)
        res = await session.execute(text("SELECT 1 AS x"))
        assert res.scalar_one() == 1


@pytest.mark.anyio
async def test_tenant_enforced_session_context_manager() -> None:
    from uuid import UUID

    from backend.app.db.deps import tenant_enforced_session

    tid = UUID("11111111-1111-1111-1111-111111111111")
    async with tenant_enforced_session(tid) as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL only")
        res = await session.execute(text("SELECT current_setting('app.tenant_id', true) AS t"))
        assert (res.scalar_one() or "").strip() == str(tid)
