"""Coverage for `services.recruiter_assignment.record_candidate_reassignment`.

Phase 2.6.G-5 Stage C guard — the helper is the *single* write-point for
``Candidate.recruiter_id`` mutations across HostFlow and is responsible for
appending an audit row to ``candidate_assignee_history`` for every
reassignment. See ``docs/specs/manager-assignment.md`` §2.5 for the table
contract and §4 Stage C for the roll-out plan.

Surface we lock in:

* No-op on unchanged value (``skip_if_unchanged=True`` default).
* Happy path — old recruiter → new recruiter writes both the candidate
  column and a history row with ``from_user_id`` / ``to_user_id``.
* ``write=False`` — history-only path used by ``create_candidate_full`` where
  the INSERT already baked ``recruiter_id`` into the row.
* Unassign (new_recruiter_id=None) — history row with
  ``to_user_id=NULL``.
* ``skip_if_unchanged=False`` — caller can force an audit row even when
  values match (used for initial-assignment audit).
* Reason / actor / actor_kind / note roundtrip.
* Defensive guards — ``candidate=None``, candidate without primary key /
  tenant_id returns ``None`` without raising.
* Reason / actor_kind length clamps (String(32)/(16)).
"""

from __future__ import annotations

import uuid
from typing import Optional

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Candidate,
    CandidateAssigneeHistory,
    Company,
    User,
)
from backend.app.models.user import Role as UserRole
from backend.app.services.recruiter_assignment import record_candidate_reassignment


pytestmark = pytest.mark.anyio


async def _any_company_id(db: AsyncSession, tenant_id: str) -> str:
    cid = await db.scalar(
        select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
    )
    if cid is None:
        cid = str(uuid.uuid4())
        db.add(Company(id=cid, tenant_id=tenant_id, name="Assignee History Test Co"))
        await db.flush()
    return str(cid)


async def _seed_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    role: UserRole = UserRole.recruiter,
) -> str:
    uid = str(uuid.uuid4())
    db.add(
        User(
            id=uid,
            email=f"assignee-{uid[:8]}@hostflow.test",
            password_hash="x",
            role=role,
            tenant_id=tenant_id,
            is_active=True,
            full_name=f"Rec {uid[:8]}",
        )
    )
    await db.flush()
    return uid


async def _seed_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    recruiter_id: Optional[str] = None,
) -> Candidate:
    cid = str(uuid.uuid4())
    company_id = await _any_company_id(db, tenant_id)
    candidate = Candidate(
        id=cid,
        tenant_id=tenant_id,
        company_id=company_id,
        first_name="Hist",
        last_name=f"Test-{cid[:6]}",
        stage="new",
        status="new",
        recruiter_id=recruiter_id,
    )
    db.add(candidate)
    await db.commit()
    return candidate


async def _fetch_history(
    db: AsyncSession, *, tenant_id: str, candidate_id: str
) -> list[CandidateAssigneeHistory]:
    rows = await db.execute(
        select(CandidateAssigneeHistory)
        .where(
            CandidateAssigneeHistory.tenant_id == tenant_id,
            CandidateAssigneeHistory.candidate_id == candidate_id,
        )
        .order_by(CandidateAssigneeHistory.changed_at)
    )
    return list(rows.scalars().all())


async def test_skip_if_unchanged_returns_none_no_history(
    db: AsyncSession, tenant_id: str
) -> None:
    """Helper is a no-op when the target recruiter_id matches the current one.

    Important for idempotency — routing cascades in lead-processing may call
    the helper multiple times with the same value across reroutes / retries;
    the audit trail MUST NOT grow spuriously.
    """
    user_a = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    result = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=user_a,
        reason="manual_single",
    )
    await db.commit()

    assert result is None
    history = await _fetch_history(
        db, tenant_id=tenant_id, candidate_id=candidate.id
    )
    assert history == []


async def test_happy_path_writes_candidate_and_history(
    db: AsyncSession, tenant_id: str
) -> None:
    """Old → new recruiter transition flips ``Candidate.recruiter_id`` AND
    appends one history row with the correct ``from_user_id`` / ``to_user_id``."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    user_b = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    row = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=user_b,
        reason="manual_single",
        actor=user_a,
        note="test handoff",
    )
    await db.commit()

    assert row is not None
    assert candidate.recruiter_id == user_b

    history = await _fetch_history(
        db, tenant_id=tenant_id, candidate_id=candidate.id
    )
    assert len(history) == 1
    hist = history[0]
    assert hist.from_user_id == user_a
    assert hist.to_user_id == user_b
    assert hist.reason == "manual_single"
    assert hist.actor_user_id == user_a
    assert hist.actor_kind == "user"
    assert hist.note == "test handoff"


async def test_write_false_emits_history_without_mutating_candidate(
    db: AsyncSession, tenant_id: str
) -> None:
    """``write=False`` is the INSERT-time path — ``create_candidate_full``
    already set ``recruiter_id`` via the INSERT statement and just needs the
    audit row appended. The helper MUST NOT issue an UPDATE in that mode."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    row = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=user_a,
        reason="candidate_create",
        actor=user_a,
        note="strategy=least_load",
        write=False,
        skip_if_unchanged=False,
    )
    await db.commit()

    assert row is not None
    assert candidate.recruiter_id == user_a

    history = await _fetch_history(
        db, tenant_id=tenant_id, candidate_id=candidate.id
    )
    assert len(history) == 1
    hist = history[0]
    # write=False means we don't know the "old" value pre-INSERT; the helper
    # records ``from == to`` and callers at the INSERT path interpret this
    # as "initial assignment, no prior value".
    assert hist.from_user_id == user_a
    assert hist.to_user_id == user_a
    assert hist.reason == "candidate_create"
    assert hist.note == "strategy=least_load"


async def test_unassign_records_to_user_id_null(
    db: AsyncSession, tenant_id: str
) -> None:
    """Unassigning a candidate (new_recruiter_id=None) must leave a
    forensic trail with ``to_user_id=NULL`` so explainability can show
    «кандидат снят с рекрутера X»."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    row = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=None,
        reason="admin",
        actor=user_a,
    )
    await db.commit()

    assert row is not None
    assert candidate.recruiter_id is None

    history = await _fetch_history(
        db, tenant_id=tenant_id, candidate_id=candidate.id
    )
    assert len(history) == 1
    assert history[0].from_user_id == user_a
    assert history[0].to_user_id is None
    assert history[0].reason == "admin"


async def test_none_candidate_returns_none_without_writing(
    db: AsyncSession, tenant_id: str
) -> None:
    """Defensive guard — callers in lead-processing may pass ``None`` when
    candidate creation has failed; helper MUST short-circuit silently."""
    result = await record_candidate_reassignment(
        db,
        None,  # type: ignore[arg-type]
        new_recruiter_id=str(uuid.uuid4()),
        reason="manual_single",
    )
    assert result is None


async def test_candidate_without_tenant_id_returns_none(
    db: AsyncSession, tenant_id: str
) -> None:
    """Defensive guard — the helper refuses to persist a history row without
    a ``tenant_id`` scope (RLS / multi-tenant safety)."""
    user_a = await _seed_user(db, tenant_id=tenant_id)

    orphan = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=None,  # type: ignore[arg-type]
        company_id=await _any_company_id(db, tenant_id),
        first_name="Orph",
        last_name="An",
        stage="new",
        status="new",
    )

    result = await record_candidate_reassignment(
        db,
        orphan,
        new_recruiter_id=user_a,
        reason="manual_single",
    )

    assert result is None
    assert orphan.recruiter_id is None


async def test_reason_and_actor_kind_are_length_clamped(
    db: AsyncSession, tenant_id: str
) -> None:
    """``reason`` (String(32)) and ``actor_kind`` (String(16)) must never
    overflow the DB column even if a sloppy call-site passes a longer value."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    user_b = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    long_reason = "manual_bulk_with_context_pack_0001_very_long"
    long_actor_kind = "automation_retry_v2"

    row = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=user_b,
        reason=long_reason,
        actor_kind=long_actor_kind,
    )
    await db.commit()

    assert row is not None
    assert len(row.reason) <= 32
    assert row.reason == long_reason[:32]
    assert len(row.actor_kind) <= 16
    assert row.actor_kind == long_actor_kind[:16]


async def test_multiple_reassignments_append_not_update(
    db: AsyncSession, tenant_id: str
) -> None:
    """The audit table is append-only — sequential reassignments produce N
    separate rows ordered by ``changed_at``, each with the correct
    ``from_user_id`` chain."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    user_b = await _seed_user(db, tenant_id=tenant_id)
    user_c = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    await record_candidate_reassignment(
        db, candidate, new_recruiter_id=user_b, reason="manual_single"
    )
    await db.commit()
    await record_candidate_reassignment(
        db, candidate, new_recruiter_id=user_c, reason="admin"
    )
    await db.commit()
    await record_candidate_reassignment(
        db, candidate, new_recruiter_id=None, reason="admin"
    )
    await db.commit()

    history = await _fetch_history(
        db, tenant_id=tenant_id, candidate_id=candidate.id
    )
    assert len(history) == 3
    assert [h.from_user_id for h in history] == [user_a, user_b, user_c]
    assert [h.to_user_id for h in history] == [user_b, user_c, None]
    assert [h.reason for h in history] == ["manual_single", "admin", "admin"]


async def test_empty_string_recruiter_id_normalised_to_none(
    db: AsyncSession, tenant_id: str
) -> None:
    """Some call-sites pass ``""`` meaning «unassign». The normaliser in the
    helper converts empty / whitespace strings to ``None`` so the audit row
    has a clean ``to_user_id=NULL`` (not an empty-string FK which would
    violate the users.id FK)."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(db, tenant_id=tenant_id, recruiter_id=user_a)

    row = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id="   ",
        reason="admin",
    )
    await db.commit()

    assert row is not None
    assert candidate.recruiter_id is None
    assert row.to_user_id is None
