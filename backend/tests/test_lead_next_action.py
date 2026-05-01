"""Branch coverage for `services/next_action.compute_lead_next_action`.

Structural test for G-8 stage 2.0 (see `docs/specs/operations-loop.md`).
Mirrors the candidate next-action test layout: one test per branch of the
precedence ladder, plus an HTTP smoke test that confirms the endpoint is
mounted and returns the canonical DTO shape.

Precedence ladder under test (highest priority wins):

    1. terminal stage (converted / lost)         → DONE
    2. terminal status (failed / duplicated)     → DONE
    3. status == 'needs_routing'                 → CONTACT
    4. earliest active reminder                  → REMINDER
    5. status == 'new' (raw, unqualified)        → CONTACT
    6. otherwise                                 → IDLE

The handler explicitly orders branches 1→6 — if the test for branch N starts
failing while N-1 still passes, the precedence got reordered or a branch
predicate regressed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import TASKS
from backend.app.models.lead import Lead
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services.next_action import (
    NextActionKind,
    NextActionPriority,
    compute_lead_next_action,
)


pytestmark = pytest.mark.anyio


async def _seed_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str = "processed",
    stage: str | None = "new",
    lead_type: str = "candidate",
) -> str:
    lid = str(uuid.uuid4())
    db.add(
        Lead(
            id=lid,
            tenant_id=tenant_id,
            lead_type=lead_type,
            payload={},
            status=status,
            stage=stage,
        )
    )
    await db.commit()
    return lid


# ---------------------------------------------------------------------------
# Branch 1: terminal stage. The two literals on the LeadStage Literal that
# close the funnel (converted / lost) must both produce kind=DONE so the UI
# renders a calm "Closed" badge instead of nagging the operator.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage_code", ["converted", "lost"])
async def test_terminal_stage_yields_done(
    db: AsyncSession,
    tenant_id: str,
    stage_code: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage=stage_code)

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.entity_type == "lead"
    assert dto.entity_id == lid
    assert dto.kind == NextActionKind.DONE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == f"terminal_stage_{stage_code}"
    assert dto.href is None  # nothing clickable on a closed lead


# ---------------------------------------------------------------------------
# Branch 2: terminal status. `failed` / `duplicated` are pipeline-rejection
# statuses that must NEVER surface a CTA, regardless of stage.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status_code", ["failed", "duplicated"])
async def test_terminal_status_yields_done(
    db: AsyncSession,
    tenant_id: str,
    status_code: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status=status_code, stage="new")

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == f"terminal_status_{status_code}"


# ---------------------------------------------------------------------------
# Branch 3: needs routing. Pipeline is paused waiting for a manual decision.
# This is "act now" with HIGH priority — operator shouldn't have to look
# anywhere else to know what to do.
# ---------------------------------------------------------------------------


async def test_needs_routing_yields_contact_high(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="needs_routing", stage="new")

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "lead_needs_routing"
    assert dto.href == f"/app/leads/{lid}"


# ---------------------------------------------------------------------------
# Branch 4: earliest active reminder.
#
# Two sub-cases:
#   4a) reminder due in the future → kind=REMINDER, priority=NORMAL.
#   4b) reminder already overdue   → kind=REMINDER, priority=CRITICAL.
#
# Cancelled / done reminders MUST NOT count (regression guard for G-1's
# lifecycle cleanup leaking back into the next-action surface).
# ---------------------------------------------------------------------------


async def test_active_future_reminder_yields_reminder_normal(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage="contacted")
    rid = str(uuid.uuid4())
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="leads_no_next_action",
            entity_type="lead",
            entity_id=lid,
            title="Follow up with lead",
            due_at=datetime.now(timezone.utc) + timedelta(days=2),
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "reminder_due"
    assert dto.href == f"{TASKS}?focus={rid}"


async def test_overdue_reminder_yields_reminder_critical(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage="contacted")
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="leads_stuck_stage",
            entity_type="lead",
            entity_id=lid,
            title="Stuck for 9 days",
            due_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status=ReminderStatus.overdue,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "reminder_overdue"


async def test_cancelled_reminder_does_not_count_as_active(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Regression guard for G-1 cleanup leaking back into the surface.

    A `cancelled` reminder must NOT promote the lead out of the IDLE
    branch even if the lead is otherwise quiet.
    """
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage="contacted")
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="leads_no_next_action",
            entity_type="lead",
            entity_id=lid,
            title="Stale",
            due_at=datetime.now(timezone.utc) - timedelta(days=3),
            status=ReminderStatus.cancelled,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "no_signal"


# ---------------------------------------------------------------------------
# Branch 5: status='new'. The lead landed but the auto-pipeline hasn't
# touched it yet; operator should manually qualify.
# ---------------------------------------------------------------------------


async def test_status_new_yields_contact_qualify(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="new", stage="new")

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "lead_unqualified"
    assert dto.href == f"/app/leads/{lid}"


# ---------------------------------------------------------------------------
# Branch 6 (idle): processed lead, active stage, no reminder, no signal.
# Must explicitly say "nothing to do" — empty CTA reads as broken UI.
# ---------------------------------------------------------------------------


async def test_processed_lead_with_no_signal_yields_idle(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage="contacted")

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.IDLE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "no_signal"
    assert dto.href is None


async def test_processed_lead_with_candidate_yields_done(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage="contacted")
    lead = await db.get(Lead, lid)
    assert lead is not None
    lead.candidate_id = candidate_id
    await db.commit()

    dto = await compute_lead_next_action(db, tenant_id=tenant_id, lead_id=lid)

    assert dto.kind == NextActionKind.DONE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "lead_converted_to_candidate"
    assert dto.href is None


# ---------------------------------------------------------------------------
# Defensive paths.
# ---------------------------------------------------------------------------


async def test_unknown_lead_yields_idle_placeholder(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    dto = await compute_lead_next_action(
        db,
        tenant_id=tenant_id,
        lead_id=str(uuid.uuid4()),
    )

    assert dto.entity_type == "lead"
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "lead_not_found"


# ---------------------------------------------------------------------------
# HTTP smoke test — confirms the endpoint is mounted and returns the DTO.
# ---------------------------------------------------------------------------


async def test_endpoint_returns_dto_for_known_lead(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: str,
    manager_headers: Dict[str, str],
) -> None:
    lid = await _seed_lead(db, tenant_id=tenant_id, status="processed", stage="contacted")

    r = await client.get(
        f"/api/v1/leads/{lid}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["entity_type"] == "lead"
    assert body["entity_id"] == lid
    assert body["kind"] in {k.value for k in NextActionKind}
    assert body["priority"] in {p.value for p in NextActionPriority}
    assert isinstance(body["reason_code"], str) and body["reason_code"]
    assert isinstance(body["title"], str) and body["title"]


async def test_endpoint_returns_404_for_unknown_lead(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    r = await client.get(
        f"/api/v1/leads/{uuid.uuid4()}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 404, r.text
