"""Branch coverage for `services/next_action.compute_candidate_next_action`.

This is the structural test for G-8 stage 1a (see
`docs/specs/operations-loop.md`). It exercises every branch of the precedence
ladder so that future contributors can rearrange the algorithm and still see
exactly which case regressed.

We deliberately call the service directly for the branch-coverage matrix
(faster, no HTTP setup, less flake) and add one HTTP smoke test against the
real router to confirm the endpoint is wired up and responds with the
expected DTO shape.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient

from sqlalchemy import select

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.contact_attempt import ContactAttempt
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.user import User
from backend.app.services.next_action import (
    NextActionKind,
    NextActionPriority,
    compute_candidate_next_action,
)


async def _any_user_id_in_tenant(db, tenant_id: str) -> str:
    """Return any existing user id in the tenant.

    The handoff FK to `users.id` is RESTRICT, so the test must reuse a
    seeded user instead of inventing a uuid.
    """
    uid = await db.scalar(
        select(User.id).where(User.tenant_id == tenant_id).limit(1)
    )
    assert uid is not None, "No seeded user found in tenant"
    return uid


# ---------------------------------------------------------------------------
# Branch 5 (default for the conftest candidate fixture).
#
# The shared `candidate_id` fixture creates a candidate in stage="new" with
# zero contact attempts. That maps to "Make first contact" — the most common
# state a recruiter sees on day one of a candidate's life.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_default_candidate_yields_contact_cta(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "no_contact_attempt"
    # Deep-link must point at the candidate detail with the action focus —
    # the frontend keys off `?action=log_contact` to open the contact dialog.
    assert dto.href is not None
    assert candidate_id in dto.href
    assert "log_contact" in dto.href


# ---------------------------------------------------------------------------
# Branches 1-2: terminal states.
#
# Once a candidate is rejected/declined/employed/probation_ok the system
# must NEVER suggest an action. Same for soft-deleted candidates. Both map
# to kind=DONE so the frontend renders a calm "Closed" badge.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "stage_code,expected_reason",
    [
        ("rejected", "terminal_stage_rejected"),
        ("declined", "terminal_stage_declined"),
        ("employed", "terminal_stage_employed"),
        ("probation_ok", "terminal_stage_probation_ok"),
    ],
)
async def test_terminal_stage_yields_done(
    db,
    candidate_id: str,
    tenant_id: str,
    stage_code: str,
    expected_reason: str,
) -> None:
    candidate = await db.get(Candidate, candidate_id)
    assert candidate is not None
    candidate.stage = stage_code
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.DONE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == expected_reason
    # Critical: terminal states intentionally have NO clickable CTA.
    # Rendering a button on a closed candidate would invite mistakes.
    assert dto.href is None


@pytest.mark.anyio
async def test_soft_deleted_candidate_yields_done_deleted(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    candidate = await db.get(Candidate, candidate_id)
    assert candidate is not None
    candidate.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_deleted"
    assert dto.href is None


# ---------------------------------------------------------------------------
# Branch 4: active reminder wins over the contact-attempt branch.
#
# Two sub-cases — overdue (priority CRITICAL) and future-due (priority NORMAL)
# — confirm the priority bucketing logic in `_priority_from_due`.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_overdue_reminder_yields_critical_reminder(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    rid = str(uuid.uuid4())
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="custom",
            entity_type="candidate",
            entity_id=candidate_id,
            title="Call back the candidate",
            due_at=past,
            status=ReminderStatus.overdue,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "reminder_overdue"
    assert dto.title == "Call back the candidate"
    assert dto.due_at is not None
    assert dto.href is not None and rid in dto.href


@pytest.mark.anyio
async def test_future_reminder_yields_normal_priority(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    rid = str(uuid.uuid4())
    future = datetime.now(timezone.utc) + timedelta(days=3)
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="custom",
            entity_type="candidate",
            entity_id=candidate_id,
            title="Schedule interview",
            due_at=future,
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "reminder_due"


@pytest.mark.anyio
async def test_cancelled_reminder_does_not_count_as_active(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    """Regression guard for G-1: a cancelled reminder must not re-surface
    as a pending CTA. If this test starts failing, G-1's lifecycle cleanup
    is leaking back into the next-action surface."""
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="custom",
            entity_type="candidate",
            entity_id=candidate_id,
            title="Stale task",
            due_at=datetime.now(timezone.utc) - timedelta(days=1),
            status=ReminderStatus.cancelled,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    # Falls through reminder branch (cancelled is not active) and lands on
    # the contact-attempt branch since the conftest candidate has none.
    assert dto.kind == NextActionKind.CONTACT


# ---------------------------------------------------------------------------
# Branch 3: pending handoff. Two sub-cases for agency vs client viewer.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_pending_handoff_agency_view_yields_await(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    requester = await _any_user_id_in_tenant(db, tenant_id)
    db.add(
        CandidateHandoff(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            agency_tenant_id=tenant_id,
            client_tenant_id=tenant_id,
            requested_by_user_id=requester,
            status="pending_review",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        is_client_tenant=False,
    )

    assert dto.kind == NextActionKind.HANDOFF_AWAIT
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "handoff_pending_client_decision"


@pytest.mark.anyio
async def test_pending_handoff_client_view_yields_decision(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    requester = await _any_user_id_in_tenant(db, tenant_id)
    db.add(
        CandidateHandoff(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            agency_tenant_id=tenant_id,
            client_tenant_id=tenant_id,
            requested_by_user_id=requester,
            status="pending_review",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        is_client_tenant=True,
    )

    assert dto.kind == NextActionKind.HANDOFF_DECISION
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "handoff_pending_client_decision"
    # Client side gets a clickable CTA — they're the blocker.
    assert dto.href is not None and "focus=handoff" in dto.href


# ---------------------------------------------------------------------------
# Branch 6 (idle): active candidate, past pre-contact stage, no signals.
#
# Logged a contact attempt, advanced past pre-contact stages, no reminders,
# no handoff — the system must explicitly say "nothing to do" rather than
# render an empty card (which operators read as a bug).
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_advanced_candidate_with_contact_logged_yields_idle(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    candidate = await db.get(Candidate, candidate_id)
    assert candidate is not None
    candidate.stage = "docs_got"
    candidate.status = "docs_got"
    db.add(
        ContactAttempt(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            attempt_number=1,
            attempted_at=datetime.now(timezone.utc),
            channel="phone",
            result="answered",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.IDLE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "no_signal"
    assert dto.href is None  # nothing clickable on idle


@pytest.mark.anyio
async def test_pre_contact_stage_with_attempt_logged_yields_idle(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    """Even on a pre-contact stage, if the recruiter logged at least one
    attempt the contact-CTA must NOT fire — the system trusts the log."""
    db.add(
        ContactAttempt(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            attempt_number=1,
            attempted_at=datetime.now(timezone.utc),
            channel="phone",
            result="no_answer",
        )
    )
    await db.commit()

    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "no_signal"


# ---------------------------------------------------------------------------
# Defensive paths.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_unknown_candidate_yields_idle_placeholder(
    db,
    tenant_id: str,
) -> None:
    dto = await compute_candidate_next_action(
        db,
        tenant_id=tenant_id,
        candidate_id=str(uuid.uuid4()),
    )

    # Service never raises — placeholder DTO carries the diagnostic in
    # reason_code so callers can decide whether to 404.
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "candidate_not_found"


# ---------------------------------------------------------------------------
# HTTP smoke test — confirms the endpoint is mounted and returns the DTO.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_endpoint_returns_dto_for_known_candidate(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    r = await client.get(
        f"/api/v1/candidates/{candidate_id}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["entity_type"] == "candidate"
    assert body["entity_id"] == candidate_id
    assert body["kind"] in {k.value for k in NextActionKind}
    assert body["priority"] in {p.value for p in NextActionPriority}
    assert isinstance(body["reason_code"], str) and body["reason_code"]
    assert isinstance(body["title"], str) and body["title"]


@pytest.mark.anyio
async def test_endpoint_returns_404_for_unknown_candidate(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    r = await client.get(
        f"/api/v1/candidates/{uuid.uuid4()}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 404, r.text
