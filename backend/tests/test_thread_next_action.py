"""Branch coverage for `services/next_action.compute_thread_next_action`.

Structural test for G-8 stage 2.3 (see `docs/specs/operations-loop.md`).
Mirrors the candidate / lead / vacancy / document next-action test layouts:
one test per branch of the precedence ladder, plus an HTTP smoke test
that confirms the endpoint is mounted (asserted via 404 on an unknown
thread, which short-circuits before the channel-feature-access gate).

Precedence ladder under test (highest priority wins):

    1.  is_archived                                 → DONE  (terminal_archived)
    2.  status.lower() == 'deleted'                 → DONE  (terminal_status_deleted)
    3.  status.lower() ∈ {closed, resolved}         → DONE  (terminal_status_*)
    4.  sla_due_at < now                            → CONTACT/CRITICAL (thread_sla_overdue)
    5.  earliest active reminder                    → REMINDER
        (entity_type='communication_thread')
    6.  unread_count > 0                            → CONTACT/HIGH (thread_unread_inbound)
    7.  last_inbound_at > last_outbound_at          → CONTACT/NORMAL (thread_awaiting_reply)
    8.  sla_due_at within next 30 min               → CONTACT/NORMAL (thread_sla_due_soon)
    9.  status.lower() ∈ {snoozed, pending}         → IDLE (thread_<status>)
   10.  fallback                                    → IDLE (no_signal)

Regression guards:

  * G-1: cancelled reminders MUST NOT count as active.
  * Archived MUST trump every other signal (precedence top-of-ladder).
  * Unread inbound MUST trump `awaiting_reply` (otherwise read-only acks
    would suppress the urgent CTA).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import TASKS
from backend.app.models.communication import CommunicationThread
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services.next_action import (
    NextActionKind,
    NextActionPriority,
    compute_thread_next_action,
)


pytestmark = pytest.mark.anyio


async def _seed_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str = "open",
    is_archived: bool = False,
    unread_count: int = 0,
    sla_due_at: Optional[datetime] = None,
    last_inbound_at: Optional[datetime] = None,
    last_outbound_at: Optional[datetime] = None,
    channel: str = "telegram",
) -> str:
    tid = str(uuid.uuid4())
    db.add(
        CommunicationThread(
            id=tid,
            tenant_id=tenant_id,
            channel=channel,
            status=status,
            is_archived=is_archived,
            unread_count=unread_count,
            sla_due_at=sla_due_at,
            last_inbound_at=last_inbound_at,
            last_outbound_at=last_outbound_at,
            priority="normal",
            participants_json={},
            tags_json=[],
            thread_meta={},
        )
    )
    await db.commit()
    return tid


# Reference "now" for the test suite. Anchored to real `datetime.now()`
# rather than a hard-coded date because the reminder branch routes through
# `_priority_from_due`, which compares against real `datetime.now(timezone.utc)`
# (it's not parametrised on `now`). With a fixed historical anchor any
# `_NOW + 1h` future reminder would still be in the past relative to real
# now and would surface as CRITICAL instead of NORMAL. Real-now-anchoring
# keeps the relative deltas honest end-to-end.
_NOW = datetime.now(timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------------------
# Branch 1: archived trumps everything.
# ---------------------------------------------------------------------------


async def test_archived_trumps_unread_and_sla_breach(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Archived MUST be terminal even if unread and SLA-overdue. Otherwise
    a stale archived thread keeps lighting up the operator's inbox."""
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        is_archived=True,
        unread_count=5,
        sla_due_at=_NOW - timedelta(hours=2),  # would be CRITICAL
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.entity_type == "thread"
    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_archived"


# ---------------------------------------------------------------------------
# Branch 2-3: status-driven terminal states.
# ---------------------------------------------------------------------------


async def test_status_deleted_yields_done(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, status="deleted", unread_count=3)

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_status_deleted"


async def test_status_deleted_is_case_insensitive(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, status="DELETED")

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.reason_code == "terminal_status_deleted"


@pytest.mark.parametrize("status", ["closed", "resolved"])
async def test_status_closed_or_resolved_yields_done(
    db: AsyncSession,
    tenant_id: str,
    status: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, status=status)

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == f"terminal_status_{status}"


# ---------------------------------------------------------------------------
# Branch 4: SLA breach.
# ---------------------------------------------------------------------------


async def test_sla_overdue_yields_contact_critical(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        sla_due_at=_NOW - timedelta(minutes=5),
        unread_count=0,  # SLA breach trumps unread anyway
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "thread_sla_overdue"
    assert dto.due_at is not None


# ---------------------------------------------------------------------------
# Branch 5: reminder. Future + overdue + cancelled regression-guard.
# ---------------------------------------------------------------------------


async def test_active_future_reminder_yields_reminder_due(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Future-but-soon reminder → REMINDER kind, `reminder_due` reason.
    Priority is bucketed by `_priority_from_due` (HIGH if within 24h,
    NORMAL otherwise) — we only assert the bucket boundary indirectly via
    the kind/reason here. Far-future deltas would NORMAL; near deltas HIGH."""
    tid = await _seed_thread(db, tenant_id=tenant_id, unread_count=0)
    rid = str(uuid.uuid4())
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="communications_sla_overdue",
            entity_type="communication_thread",
            entity_id=tid,
            title="Follow up on thread",
            due_at=_NOW + timedelta(hours=1),
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.HIGH  # within 24h window
    assert dto.reason_code == "reminder_due"
    assert dto.href == f"{TASKS}?focus={rid}"


async def test_overdue_reminder_yields_reminder_critical(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, unread_count=0)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="communications_sla_overdue",
            entity_type="communication_thread",
            entity_id=tid,
            title="Stale chase",
            due_at=_NOW - timedelta(hours=2),
            status=ReminderStatus.overdue,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "reminder_overdue"


async def test_cancelled_reminder_does_not_count_as_active(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Regression guard for G-1 cleanup leaking back into the surface."""
    tid = await _seed_thread(db, tenant_id=tenant_id, unread_count=0)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="communications_sla_overdue",
            entity_type="communication_thread",
            entity_id=tid,
            title="Stale",
            due_at=_NOW - timedelta(days=3),
            status=ReminderStatus.cancelled,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    # No reminder, no SLA, no unread, no inbound → falls all the way to
    # `no_signal`. The test name guards the cancelled-reminder branch,
    # not the IDLE outcome itself.
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "no_signal"


# ---------------------------------------------------------------------------
# Branch 6: unread inbound (HIGH).
# ---------------------------------------------------------------------------


async def test_unread_count_yields_contact_high(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, unread_count=3)

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "thread_unread_inbound"
    assert "3" in (dto.title or "")


async def test_unread_count_one_uses_singular_title(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, unread_count=1)

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.title == "1 unread message"


async def test_unread_trumps_awaiting_reply(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Unread MUST win over `awaiting_reply` — the latter is a weaker
    "you read it but did not reply" signal."""
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        unread_count=1,
        last_inbound_at=_NOW - timedelta(hours=1),
        last_outbound_at=_NOW - timedelta(hours=2),
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.reason_code == "thread_unread_inbound"


# ---------------------------------------------------------------------------
# Branch 7: read but not replied (NORMAL).
# ---------------------------------------------------------------------------


async def test_inbound_after_outbound_yields_awaiting_reply(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        unread_count=0,
        last_inbound_at=_NOW - timedelta(minutes=10),
        last_outbound_at=_NOW - timedelta(hours=1),
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "thread_awaiting_reply"


async def test_inbound_with_no_outbound_yields_awaiting_reply(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Brand-new thread, inbound only, already marked as read — still
    awaiting reply."""
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        unread_count=0,
        last_inbound_at=_NOW - timedelta(minutes=10),
        last_outbound_at=None,
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.reason_code == "thread_awaiting_reply"


async def test_outbound_after_inbound_does_not_yield_awaiting_reply(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """The ball is in the candidate's court — operator has nothing to do."""
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        unread_count=0,
        last_inbound_at=_NOW - timedelta(hours=2),
        last_outbound_at=_NOW - timedelta(minutes=10),
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "no_signal"


# ---------------------------------------------------------------------------
# Branch 8: SLA due soon (within 30 min, but not yet breached).
# ---------------------------------------------------------------------------


async def test_sla_due_in_15_minutes_yields_due_soon_normal(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        unread_count=0,
        sla_due_at=_NOW + timedelta(minutes=15),
        last_inbound_at=None,  # Skip awaiting_reply branch
        last_outbound_at=None,
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "thread_sla_due_soon"


async def test_sla_due_far_in_future_does_not_yield_due_soon(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """SLA more than the 30-minute window away should not trigger the CTA."""
    tid = await _seed_thread(
        db,
        tenant_id=tenant_id,
        unread_count=0,
        sla_due_at=_NOW + timedelta(hours=4),
        last_inbound_at=None,
        last_outbound_at=None,
    )

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "no_signal"


# ---------------------------------------------------------------------------
# Branch 9: explicit IDLE statuses.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["snoozed", "pending"])
async def test_idle_status_yields_idle_with_dedicated_reason(
    db: AsyncSession,
    tenant_id: str,
    status: str,
) -> None:
    tid = await _seed_thread(db, tenant_id=tenant_id, status=status)

    dto = await compute_thread_next_action(
        db, tenant_id=tenant_id, thread_id=tid, now=_NOW
    )

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == f"thread_{status}"


# ---------------------------------------------------------------------------
# Defensive paths.
# ---------------------------------------------------------------------------


async def test_unknown_thread_yields_idle_placeholder(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    dto = await compute_thread_next_action(
        db,
        tenant_id=tenant_id,
        thread_id=str(uuid.uuid4()),
        now=_NOW,
    )

    assert dto.entity_type == "thread"
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "thread_not_found"


# ---------------------------------------------------------------------------
# HTTP smoke: confirm the endpoint is mounted. We assert via the 404 path
# because the read endpoint applies channel-feature-access gating after
# the existence check, and seeding the comm-feature entitlements per
# channel is heavier than the value of testing through the HTTP layer.
# ---------------------------------------------------------------------------


async def test_endpoint_returns_404_for_unknown_thread(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    r = await client.get(
        f"/api/v1/communications/threads/{uuid.uuid4()}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 404, r.text
