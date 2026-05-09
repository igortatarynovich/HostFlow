from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

# Phase 2.1 (ADR-012, 2026-05-09): legacy ``Reminder`` / planner-event
# tables are absorbed into ``activities``; tests now seed via
# ``Activity`` directly. Reminder-style rows = ``starts_at IS NULL``;
# planner-style rows = ``starts_at IS NOT NULL``. ``ReminderStatus``
# constants are kept because their string values match what the
# service layer enforces.
from backend.app.models.activity import Activity, ActivityStatus
from backend.app.models.lead import Lead
from backend.app.models.reminder import ReminderStatus
from backend.app.models.user_notification import UserNotification
from backend.app.models.user import User
from backend.app.services.lead_lifecycle import (
    maybe_apply_lead_silence_cleanup,
    maybe_apply_lead_terminal_cleanup,
    sweep_converted_lead_operational_noise,
)
from backend.app.services.reminder_tasks import list_reminders
from backend.app.services.user_notifications import list_notifications


@pytest.mark.anyio
async def test_terminal_lead_transition_cleans_operational_signals(
    db,
    tenant_id: str,
) -> None:
    manager_id = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert manager_id is not None
    lead_id = str(uuid.uuid4())
    db.add(
        Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            payload={},
            status="processed",
            stage="contacted",
        )
    )
    planner_start = datetime.now(timezone.utc) + timedelta(days=1)
    db.add(
        Activity(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="custom",
            related_entity_type="lead",
            related_entity_id=lead_id,
            title="Follow up lead",
            due_at=datetime.now(timezone.utc) + timedelta(hours=2),
            starts_at=None,
            status=ReminderStatus.pending,
            channel="internal",
            assigned_to_user_id=manager_id,
        )
    )
    db.add(
        UserNotification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=manager_id,
            event_type="lead_no_next_action",
            entity_type="lead",
            entity_id=lead_id,
            payload={},
            is_read=False,
            channel="in_app",
        )
    )
    db.add(
        Activity(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title="Call lead",
            type="task",
            status=ActivityStatus.planned,
            priority="normal",
            starts_at=planner_start,
            due_at=planner_start + timedelta(hours=1),
            assigned_to_user_id=manager_id,
            related_entity_type="lead",
            related_entity_id=lead_id,
            metadata_={"planner": {"kind": "task"}},
        )
    )
    await db.commit()

    cleanup = await maybe_apply_lead_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        old_stage="contacted",
        new_stage="lost",
        old_status="processed",
        new_status="processed",
        actor_id=manager_id,
    )
    await db.commit()

    assert cleanup is not None
    assert cleanup.reminders_cancelled == 1
    assert cleanup.notifications_marked_read == 1
    assert cleanup.planner_events_cancelled == 1

    reminder = await db.scalar(
        select(Activity).where(
            Activity.tenant_id == tenant_id,
            Activity.related_entity_type == "lead",
            Activity.related_entity_id == lead_id,
            Activity.starts_at.is_(None),
        )
    )
    assert reminder is not None
    assert reminder.status == ActivityStatus.done

    notif = await db.scalar(
        select(UserNotification).where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == manager_id,
            UserNotification.entity_type == "lead",
            UserNotification.entity_id == lead_id,
        )
    )
    assert notif is not None
    assert notif.is_read is True


@pytest.mark.anyio
async def test_list_surfaces_hide_terminal_lead_entities_by_default(
    db,
    tenant_id: str,
) -> None:
    manager_id = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert manager_id is not None
    lead_id = str(uuid.uuid4())
    db.add(
        Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            payload={},
            status="failed",
            stage="new",
        )
    )
    db.add(
        Activity(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="custom",
            related_entity_type="lead",
            related_entity_id=lead_id,
            title="Stale lead task",
            due_at=datetime.now(timezone.utc) + timedelta(hours=1),
            starts_at=None,
            status=ReminderStatus.pending,
            channel="internal",
            assigned_to_user_id=manager_id,
        )
    )
    db.add(
        UserNotification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=manager_id,
            event_type="lead_stuck_stage",
            entity_type="lead",
            entity_id=lead_id,
            payload={},
            is_read=False,
            channel="in_app",
        )
    )
    await db.commit()

    reminders_hidden = await list_reminders(
        db,
        tenant_id=tenant_id,
        assignee_id=manager_id,
        include_completed_entities=False,
    )
    assert all(not (r.entity_type == "lead" and r.entity_id == lead_id) for r in reminders_hidden)

    reminders_all = await list_reminders(
        db,
        tenant_id=tenant_id,
        assignee_id=manager_id,
        include_completed_entities=True,
    )
    assert any(r.entity_type == "lead" and r.entity_id == lead_id for r in reminders_all)

    notifications_hidden = await list_notifications(
        db,
        tenant_id=tenant_id,
        user_id=manager_id,
        include_read=False,
        include_completed_entities=False,
    )
    assert all(not (n.entity_type == "lead" and n.entity_id == lead_id) for n in notifications_hidden)


@pytest.mark.anyio
async def test_list_surfaces_hide_lead_with_created_candidate(
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    manager_id = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert manager_id is not None
    lead_id = str(uuid.uuid4())
    db.add(
        Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            payload={},
            status="processed",
            stage="contacted",
            candidate_id=candidate_id,
        )
    )
    db.add(
        Activity(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="custom",
            related_entity_type="lead",
            related_entity_id=lead_id,
            title="Should be hidden",
            due_at=datetime.now(timezone.utc) + timedelta(hours=2),
            starts_at=None,
            status=ReminderStatus.pending,
            channel="internal",
            assigned_to_user_id=manager_id,
        )
    )
    await db.commit()

    reminders_hidden = await list_reminders(
        db,
        tenant_id=tenant_id,
        assignee_id=manager_id,
        include_completed_entities=False,
    )
    assert all(not (r.entity_type == "lead" and r.entity_id == lead_id) for r in reminders_hidden)


@pytest.mark.anyio
async def test_candidate_link_transition_cleans_operational_signals(
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    manager_id = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert manager_id is not None
    lead_id = str(uuid.uuid4())
    db.add(
        Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            payload={},
            status="processed",
            stage="contacted",
        )
    )
    db.add(
        Activity(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="custom",
            related_entity_type="lead",
            related_entity_id=lead_id,
            title="Follow up lead",
            due_at=datetime.now(timezone.utc) + timedelta(hours=2),
            starts_at=None,
            status=ReminderStatus.pending,
            channel="internal",
            assigned_to_user_id=manager_id,
        )
    )
    db.add(
        UserNotification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=manager_id,
            event_type="lead_no_next_action",
            entity_type="lead",
            entity_id=lead_id,
            payload={},
            is_read=False,
            channel="in_app",
        )
    )
    await db.commit()

    cleanup = await maybe_apply_lead_silence_cleanup(
        db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        old_stage="contacted",
        new_stage="contacted",
        old_status="processed",
        new_status="processed",
        old_candidate_id=None,
        new_candidate_id=candidate_id,
        actor_id=manager_id,
    )
    await db.commit()

    assert cleanup is not None
    assert cleanup.reminders_cancelled == 1
    assert cleanup.notifications_marked_read == 1


@pytest.mark.anyio
async def test_sweep_converted_lead_cleans_stale_lead_reminders(
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    """Backstop when conversion cleanup was missed: lead already has candidate_id but lead reminders remain."""
    manager_id = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert manager_id is not None
    lead_id = str(uuid.uuid4())
    db.add(
        Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            payload={},
            status="processed",
            stage="contacted",
            candidate_id=candidate_id,
        )
    )
    db.add(
        Activity(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="custom",
            related_entity_type="lead",
            related_entity_id=lead_id,
            title="Stale lead task",
            due_at=datetime.now(timezone.utc) + timedelta(hours=2),
            starts_at=None,
            status=ReminderStatus.pending,
            channel="internal",
            assigned_to_user_id=manager_id,
        )
    )
    await db.commit()

    stats = await sweep_converted_lead_operational_noise(
        db,
        tenant_id=tenant_id,
        limit=50,
        actor_id=str(manager_id),
    )
    await db.commit()

    assert stats["leads_processed"] >= 1
    assert stats["reminders_cancelled"] >= 1

    reminder = await db.scalar(
        select(Activity).where(
            Activity.tenant_id == tenant_id,
            Activity.related_entity_type == "lead",
            Activity.related_entity_id == lead_id,
            Activity.starts_at.is_(None),
        )
    )
    assert reminder is not None
    assert reminder.status == ActivityStatus.done
