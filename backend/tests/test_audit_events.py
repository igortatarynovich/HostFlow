"""Tests for audit event logging (Phase 1: upgrade spec)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models.audit import ActivityLog
from backend.app.services.audit import log_audit_event

from backend.tests.conftest import DEFAULT_TENANT_ID


@pytest_asyncio.fixture
async def db_session():
    """Session for audit tests."""
    from backend.app.db.session import async_session_maker
    from backend.tests.conftest import _init_data, _set_tenant
    await _init_data()
    async with async_session_maker() as session:
        await _set_tenant(session, DEFAULT_TENANT_ID)
        yield session


@pytest.mark.asyncio
async def test_log_audit_event_writes_to_activity_log(db_session: AsyncSession) -> None:
    """log_audit_event should write to activity_log with correct columns."""
    tenant_id = DEFAULT_TENANT_ID
    await log_audit_event(
        db_session,
        tenant_id=tenant_id,
        event_type=AuditEventType.handoff_requested,
        entity_type=AuditEntityType.handoff,
        entity_id="handoff-123",
        actor_id="user-456",
        payload={"client_company_id": "company-789"},
    )
    await db_session.commit()

    result = await db_session.execute(
        select(ActivityLog)
        .where(ActivityLog.tenant_id == tenant_id)
        .where(ActivityLog.action == "handoff_requested")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.target_type == "handoff"
    assert row.target_id == "handoff-123"
    assert row.actor_id == "user-456"
    assert row.payload.get("client_company_id") == "company-789"


@pytest.mark.asyncio
async def test_log_audit_event_rodo_sent(db_session: AsyncSession) -> None:
    """log_audit_event for rodo_sent."""
    tenant_id = DEFAULT_TENANT_ID
    await log_audit_event(
        db_session,
        tenant_id=tenant_id,
        event_type=AuditEventType.rodo_sent,
        entity_type=AuditEntityType.rodo_notification,
        entity_id="rodo-notif-1",
        actor_id="user-1",
        payload={"candidate_id": "cand-1", "channel": "email"},
    )
    await db_session.commit()

    result = await db_session.execute(
        select(ActivityLog)
        .where(ActivityLog.tenant_id == tenant_id)
        .where(ActivityLog.action == "rodo_sent")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.target_type == "rodo_notification"
    assert row.payload.get("channel") == "email"


@pytest.mark.asyncio
async def test_log_audit_event_contact_attempt(db_session: AsyncSession) -> None:
    """log_audit_event for contact_attempt_logged."""
    tenant_id = DEFAULT_TENANT_ID
    await log_audit_event(
        db_session,
        tenant_id=tenant_id,
        event_type=AuditEventType.contact_attempt_logged,
        entity_type=AuditEntityType.contact_attempt,
        entity_id="attempt-1",
        actor_id="user-1",
        payload={"candidate_id": "cand-1", "attempt_number": 1, "result": "no_answer"},
    )
    await db_session.commit()

    result = await db_session.execute(
        select(ActivityLog)
        .where(ActivityLog.action == "contact_attempt_logged")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.target_type == "contact_attempt"
    assert row.payload.get("attempt_number") == 1
