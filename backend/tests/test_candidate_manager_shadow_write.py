"""Phase 2.6.G-5 Stage D — `Candidate.manager` ↔ `Candidate.recruiter_id`
shadow-write invariant coverage.

Spec: ``docs/specs/manager-assignment.md`` §4 Stage D.

The invariant we lock in across the codebase:

* Every write to ``Candidate.recruiter_id`` (canonical column, FK to
  ``users.id``) MUST also write the same value to ``Candidate.manager``
  (legacy column, used by the UI filter ``?manager=`` until Stage F).
* Every call to ``bulk_update_manager`` MUST funnel through
  ``record_candidate_reassignment`` so the two columns stay in lock-step
  AND one ``candidate_assignee_history`` row is appended per candidate.
* The ``?manager=<user>`` list filter MUST match a candidate whose
  ``manager`` IS NULL but whose ``recruiter_id`` equals the filter value
  (transitional behaviour until Stage F swaps the query param to
  ``?recruiter_id=``).

Why each test exists:

* ``test_helper_shadow_writes_manager_on_happy_path`` — proves the helper
  mirrors into both columns on an old→new transition.
* ``test_helper_shadow_writes_manager_on_unassign`` — proves the mirror
  also applies when unassigning (``new_recruiter_id=None``); a drifted
  ``manager`` left behind would keep the candidate visible to the wrong
  filter.
* ``test_helper_self_heals_drifted_manager_on_noop`` — covers the
  ``skip_if_unchanged`` branch where ``recruiter_id`` is already correct
  but ``manager`` drifted (bulk-set-manager written before Stage D);
  helper MUST reconcile without emitting a spurious history row.
* ``test_bulk_update_manager_syncs_recruiter_id_and_history`` — locks
  the refactor of ``bulk_update_manager`` from bare ``UPDATE
  SET manager=…`` to one history-aware helper call per candidate.
* ``test_bulk_update_manager_idempotent_on_same_value`` — calling bulk
  with the already-current value must not grow the audit trail.
* ``test_repo_manager_filter_matches_recruiter_id_only`` — covers the
  OR branch in ``candidates/repo.py`` for legacy rows where
  ``manager`` is NULL but ``recruiter_id`` is set.
"""

from __future__ import annotations

import uuid
from typing import Optional

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.repo import list_candidates
from backend.app.api.v1.candidates.service import bulk_update_manager
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
        db.add(Company(id=cid, tenant_id=tenant_id, name="Shadow Write Test Co"))
        await db.flush()
    return str(cid)


async def _seed_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    role: UserRole = UserRole.employee,
) -> str:
    uid = str(uuid.uuid4())
    db.add(
        User(
            id=uid,
            email=f"shadow-{uid[:8]}@hostflow.test",
            password_hash="x",
            role=role,
            tenant_id=tenant_id,
            is_active=True,
            full_name=f"Shadow {uid[:8]}",
        )
    )
    await db.flush()
    return uid


async def _seed_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    recruiter_id: Optional[str] = None,
    manager: Optional[str] = None,
) -> Candidate:
    cid = str(uuid.uuid4())
    company_id = await _any_company_id(db, tenant_id)
    candidate = Candidate(
        id=cid,
        tenant_id=tenant_id,
        company_id=company_id,
        first_name="Shadow",
        last_name=f"Test-{cid[:6]}",
        stage="new",
        status="new",
        recruiter_id=recruiter_id,
        manager=manager,
    )
    db.add(candidate)
    await db.commit()
    return candidate


async def _count_history(
    db: AsyncSession, *, tenant_id: str, candidate_id: str
) -> int:
    rows = await db.execute(
        select(CandidateAssigneeHistory).where(
            CandidateAssigneeHistory.tenant_id == tenant_id,
            CandidateAssigneeHistory.candidate_id == candidate_id,
        )
    )
    return len(list(rows.scalars().all()))


async def test_helper_shadow_writes_manager_on_happy_path(
    db: AsyncSession, tenant_id: str
) -> None:
    """Reassign A → B MUST flip both columns to B."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    user_b = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=user_a, manager=user_a
    )

    await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=user_b,
        reason="manual_single",
    )
    await db.commit()

    assert candidate.recruiter_id == user_b
    assert candidate.manager == user_b


async def test_helper_shadow_writes_manager_on_unassign(
    db: AsyncSession, tenant_id: str
) -> None:
    """Unassign (recruiter_id→NULL) MUST also clear the legacy manager
    column — otherwise the candidate stays visible to
    ``?manager=<old-user>`` after the system dropped the responsible."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=user_a, manager=user_a
    )

    await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=None,
        reason="admin",
    )
    await db.commit()

    assert candidate.recruiter_id is None
    assert candidate.manager is None


async def test_helper_self_heals_drifted_manager_on_noop(
    db: AsyncSession, tenant_id: str
) -> None:
    """Legacy rows may have ``manager != recruiter_id`` because
    ``bulk_update_manager`` (pre-Stage D) wrote only to ``manager``.

    When the helper is next called with the already-current
    ``recruiter_id`` value (``skip_if_unchanged`` hit), it MUST still
    reconcile ``manager`` to the canonical value. No history row is
    emitted — history tracks reassignments, not drift-repair.
    """
    user_a = await _seed_user(db, tenant_id=tenant_id)
    user_b = await _seed_user(db, tenant_id=tenant_id)
    candidate = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=user_a, manager=user_b
    )

    result = await record_candidate_reassignment(
        db,
        candidate,
        new_recruiter_id=user_a,
        reason="manual_single",
    )
    await db.commit()

    assert result is None
    assert candidate.recruiter_id == user_a
    assert candidate.manager == user_a
    assert (
        await _count_history(db, tenant_id=tenant_id, candidate_id=candidate.id)
    ) == 0


async def test_bulk_update_manager_syncs_recruiter_id_and_history(
    db: AsyncSession, tenant_id: str
) -> None:
    """The bulk endpoint historically wrote only ``Candidate.manager`` in
    a single ``UPDATE`` and left ``recruiter_id`` stale (split-brain bug
    §1.2.1). Stage D funnels every candidate through
    ``record_candidate_reassignment`` — lock that this produces one
    ``manual_bulk`` history row per candidate AND syncs
    ``recruiter_id``."""
    user_a = await _seed_user(db, tenant_id=tenant_id)
    user_b = await _seed_user(db, tenant_id=tenant_id)
    target = await _seed_user(db, tenant_id=tenant_id)

    c1 = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=user_a, manager=user_a
    )
    c2 = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=user_b, manager=user_b
    )

    results = await bulk_update_manager(
        db,
        tenant_id,
        [c1.id, c2.id],
        target,
        actor_id=None,
        acl=None,
    )

    assert all(entry.get("ok") for entry in results)

    await db.refresh(c1)
    await db.refresh(c2)
    assert c1.recruiter_id == target
    assert c1.manager == target
    assert c2.recruiter_id == target
    assert c2.manager == target

    # Exactly one history row per candidate — ``manual_bulk`` reason.
    for cand_id, prior in ((c1.id, user_a), (c2.id, user_b)):
        rows = await db.execute(
            select(CandidateAssigneeHistory).where(
                CandidateAssigneeHistory.candidate_id == cand_id
            )
        )
        rows_list = list(rows.scalars().all())
        assert len(rows_list) == 1
        hist = rows_list[0]
        assert hist.from_user_id == prior
        assert hist.to_user_id == target
        assert hist.reason == "manual_bulk"


async def test_bulk_update_manager_idempotent_on_same_value(
    db: AsyncSession, tenant_id: str
) -> None:
    """Re-running the bulk with the already-current value MUST NOT add a
    second history row — the helper's ``skip_if_unchanged`` default
    protects the audit trail from noise."""
    target = await _seed_user(db, tenant_id=tenant_id)
    c1 = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=target, manager=target
    )

    results = await bulk_update_manager(
        db, tenant_id, [c1.id], target, actor_id=None, acl=None
    )
    assert all(entry.get("ok") for entry in results)

    rows = await db.execute(
        select(CandidateAssigneeHistory).where(
            CandidateAssigneeHistory.candidate_id == c1.id
        )
    )
    assert len(list(rows.scalars().all())) == 0


async def test_repo_manager_filter_matches_recruiter_id_only(
    db: AsyncSession, tenant_id: str
) -> None:
    """``?manager=<user>`` MUST return a candidate whose ``manager`` is
    NULL but whose ``recruiter_id`` equals ``<user>``. This is the
    transitional OR-branch that keeps the UI filter working for rows
    written through ``record_candidate_reassignment`` before
    ``bulk_update_manager`` was refactored to mirror both columns."""
    recruiter = await _seed_user(db, tenant_id=tenant_id)

    # Legacy-written candidate: recruiter_id set by helper, manager NULL
    # (simulates a row from before Stage D shadow-write landed; the
    # self-heal path only fires on subsequent writes).
    c = await _seed_candidate(
        db, tenant_id=tenant_id, recruiter_id=recruiter, manager=None
    )

    rows = await list_candidates(
        db,
        tenant_id,
        filters={"manager": recruiter},
        limit=50,
        offset=0,
    )
    ids = [str(row.id) for row in rows]
    assert c.id in ids
