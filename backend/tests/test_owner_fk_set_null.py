"""Coverage for Phase 2.6.G-5 Stage E — owner FK ON DELETE SET NULL.

Spec: ``docs/specs/manager-assignment.md`` §4 Stage E. Alembic:
``backend/alembic/versions/202604190002_owner_fk_set_null.py``.

Purpose
-------

Before Stage E five owner/assignee columns stored a user UUID as a plain
``VARCHAR(36)`` without referential integrity:

1. ``reminders.assignee_id``
2. ``communication_planner_events.assignee_id``
3. ``communication_threads.assignee_id``
4. ``document_policies.owner_user_id``
5. ``candidate_profiles.owner_user_id``

Hard-deleting the referenced user left these columns pointing at a ghost
UUID that eventually surfaced as a broken assignee chip in ``/app/tasks``,
``/app/calendar``, the bell panel, or the documents / profile admin
views. Stage E adds ``FOREIGN KEY (…) REFERENCES users(id) ON DELETE SET
NULL`` to each of the five columns.

These tests *do not* re-verify the FK exists in the schema (that is the
job of the Alembic round-trip run by ``pytest_sessionstart`` and the DB
introspection step in the developer workflow). Instead, they pin down the
**observable behaviour** that every call-site depends on: when the owner
user goes away, the column MUST become NULL — never stay orphaned,
never cascade-delete the parent row.

Each test is self-contained (fresh tenant-scoped user + owner entity) so
a delete on the test user does not touch seed data.
"""

from __future__ import annotations

import uuid

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    CandidateProfile,
    CommunicationThread,
    DocumentPolicy,
    Reminder,
    User,
)
from backend.app.models.communication import CommunicationPlannerEvent
from backend.app.models.document_policy import DocumentPolicyScope, RequirementLevel
from backend.app.models.enums import RequirementType
from backend.app.models.user import Role as UserRole


pytestmark = pytest.mark.anyio


async def _seed_user(db: AsyncSession, *, tenant_id: str) -> str:
    """Create a fresh user that has no cross-references except the one under test."""
    uid = str(uuid.uuid4())
    db.add(
        User(
            id=uid,
            email=f"fk-setnull-{uid[:8]}@hostflow.test",
            password_hash="x",
            role=UserRole.recruiter,
            tenant_id=tenant_id,
            is_active=True,
            full_name=f"FK SetNull {uid[:8]}",
        )
    )
    await db.flush()
    return uid


async def _hard_delete_user(db: AsyncSession, user_id: str) -> None:
    """Hard-delete the user to trigger the ON DELETE SET NULL side-effect.

    Using ``DELETE`` (not ``UPDATE … is_active = false``) is important —
    only a hard delete fires the FK trigger that Stage E relies on.
    """
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


async def test_reminder_assignee_set_null_on_user_delete(
    db: AsyncSession, tenant_id: str
) -> None:
    """Reminder.assignee_id → NULL when the assignee user is hard-deleted.

    Regression guard for the "ghost reminder in /app/tasks" UX bug that
    motivated Stage E (``docs/specs/manager-assignment.md`` §4 Stage E,
    rationale paragraph).
    """
    user_id = await _seed_user(db, tenant_id=tenant_id)
    reminder_id = str(uuid.uuid4())
    db.add(
        Reminder(
            id=reminder_id,
            tenant_id=tenant_id,
            type="followup",
            entity_type="candidate",
            entity_id=str(uuid.uuid4()),
            title="Stage E orphan guard",
            assignee_id=user_id,
            due_at=datetime.now(timezone.utc) + timedelta(days=1),
            status="pending",
        )
    )
    await db.commit()

    await _hard_delete_user(db, user_id)

    row = await db.scalar(select(Reminder).where(Reminder.id == reminder_id))
    assert row is not None, "Reminder row must NOT cascade-delete with user"
    assert row.assignee_id is None, "assignee_id must be NULLed on user delete"


async def test_planner_event_assignee_set_null_on_user_delete(
    db: AsyncSession, tenant_id: str
) -> None:
    """CommunicationPlannerEvent.assignee_id → NULL on user hard-delete.

    Mirrors the reminder contract — calendar blocks created for a deleted
    user stay as "Unassigned" rather than breaking the calendar view.
    """
    user_id = await _seed_user(db, tenant_id=tenant_id)
    event_id = str(uuid.uuid4())
    start_at = datetime.now(timezone.utc) + timedelta(days=2)
    db.add(
        CommunicationPlannerEvent(
            id=event_id,
            tenant_id=tenant_id,
            title="Stage E planner orphan guard",
            kind="task",
            status="planned",
            priority="normal",
            start_at=start_at,
            end_at=start_at + timedelta(minutes=30),
            assignee_id=user_id,
            source="manual",
        )
    )
    await db.commit()

    await _hard_delete_user(db, user_id)

    row = await db.scalar(
        select(CommunicationPlannerEvent).where(
            CommunicationPlannerEvent.id == event_id
        )
    )
    assert row is not None
    assert row.assignee_id is None


async def test_thread_assignee_set_null_on_user_delete(
    db: AsyncSession, tenant_id: str
) -> None:
    """CommunicationThread.assignee_id → NULL on user hard-delete.

    Keeps inbox threads visible (and re-assignable) after the original
    owner is removed from the tenant.
    """
    user_id = await _seed_user(db, tenant_id=tenant_id)
    thread_id = str(uuid.uuid4())
    db.add(
        CommunicationThread(
            id=thread_id,
            tenant_id=tenant_id,
            channel="email",
            subject="Stage E thread orphan guard",
            status="open",
            assignee_id=user_id,
        )
    )
    await db.commit()

    await _hard_delete_user(db, user_id)

    row = await db.scalar(
        select(CommunicationThread).where(CommunicationThread.id == thread_id)
    )
    assert row is not None
    assert row.assignee_id is None


async def test_document_policy_owner_set_null_on_user_delete(
    db: AsyncSession, tenant_id: str
) -> None:
    """DocumentPolicy.owner_user_id → NULL on user hard-delete.

    Document policies outlive individual users (policies are a
    tenant-level object); when the designated owner is gone, the policy
    reverts to "no owner" rather than dangling on a ghost ID.
    """
    user_id = await _seed_user(db, tenant_id=tenant_id)
    policy_id = str(uuid.uuid4())
    db.add(
        DocumentPolicy(
            id=policy_id,
            tenant_id=tenant_id,
            scope=DocumentPolicyScope.TENANT,
            requirement_code=RequirementType.ID_EVIDENCE,
            required_level=RequirementLevel.OPTIONAL,
            gates=[],
            owner_user_id=user_id,
        )
    )
    await db.commit()

    await _hard_delete_user(db, user_id)

    row = await db.scalar(
        select(DocumentPolicy).where(DocumentPolicy.id == policy_id)
    )
    assert row is not None
    assert row.owner_user_id is None


async def test_candidate_profile_owner_set_null_on_user_delete(
    db: AsyncSession, tenant_id: str
) -> None:
    """CandidateProfile.owner_user_id → NULL on user hard-delete.

    Profile definitions must survive owner-user removal — they are
    referenced by vacancies and candidate pipelines.
    """
    user_id = await _seed_user(db, tenant_id=tenant_id)
    profile_id = str(uuid.uuid4())
    db.add(
        CandidateProfile(
            id=profile_id,
            tenant_id=tenant_id,
            code=f"fk-setnull-{profile_id[:6]}",
            name="Stage E profile orphan guard",
            owner_user_id=user_id,
            config={},
        )
    )
    await db.commit()

    await _hard_delete_user(db, user_id)

    row = await db.scalar(
        select(CandidateProfile).where(CandidateProfile.id == profile_id)
    )
    assert row is not None
    assert row.owner_user_id is None
