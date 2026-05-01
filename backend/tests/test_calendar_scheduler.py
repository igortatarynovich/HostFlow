from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.db.base import Base
from backend.app.models.calendar_integration import (
    CalendarChannel,
    CalendarConnection,
    CalendarSyncCursor,
    CalendarSyncJob,
)
from backend.app.models.tenant import Tenant
from backend.app.services.communications_scheduler import _run_calendar_maintenance_for_tenant


pytestmark = pytest.mark.anyio


async def _ensure_calendar_tables(db) -> None:
    async with db.bind.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    CalendarConnection.__table__,
                    CalendarChannel.__table__,
                    CalendarSyncCursor.__table__,
                    CalendarSyncJob.__table__,
                ],
            )
        )


async def test_calendar_scheduler_queues_renew_and_reconcile(db, tenant_id, monkeypatch):
    await _ensure_calendar_tables(db)
    async def _noop_enqueue(*args, **kwargs):
        return "test-noop"

    monkeypatch.setattr("backend.app.services.communications_scheduler.enqueue_job", _noop_enqueue)

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))).scalar_one()

    connection = CalendarConnection(
        tenant_id=tenant_id,
        user_id=None,
        provider="google",
        account_ref="sched-user@example.test",
        status="active",
        scopes_json=["calendar.read"],
        token_meta_json={"access_token": "tok"},
        last_error=None,
    )
    db.add(connection)
    await db.flush()
    conn_id = str(connection.id)
    now = datetime.now(timezone.utc)

    channel = CalendarChannel(
        tenant_id=tenant_id,
        connection_id=conn_id,
        provider="google",
        resource_id="res-1",
        channel_ref="chan-1",
        expires_at=now + timedelta(minutes=5),
        renew_after=now - timedelta(minutes=1),
        health_state="healthy",
        payload={},
    )
    db.add(channel)
    cursor = CalendarSyncCursor(
        tenant_id=tenant_id,
        connection_id=conn_id,
        provider="google",
        calendar_ref="primary",
        cursor="old-sync",
        cursor_meta_json={},
        last_synced_at=now - timedelta(minutes=60),
    )
    db.add(cursor)
    await db.commit()

    stats = await _run_calendar_maintenance_for_tenant(db, tenant=tenant, now=now)
    assert stats["connections"] >= 1
    assert stats["renew_queued"] >= 1
    assert stats["reconcile_queued"] >= 1
    assert stats["renew_failed"] == 0
    assert stats["reconcile_failed"] == 0

    jobs = (
        await db.execute(
            select(CalendarSyncJob).where(
                CalendarSyncJob.tenant_id == tenant_id,
                CalendarSyncJob.status == "queued",
            )
        )
    ).scalars().all()
    assert any(j.operation == "renew_subscription" for j in jobs)
    assert any(j.operation == "reconcile" for j in jobs)
