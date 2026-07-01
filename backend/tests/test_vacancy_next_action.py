"""Branch coverage for `services/next_action.compute_vacancy_next_action`.

Structural test for G-8 stage 2.1 (see `docs/specs/operations-loop.md`).
Mirrors the lead/candidate next-action test layout: one test per branch of
the precedence ladder, plus an HTTP smoke test that confirms the endpoint
is mounted and returns the canonical DTO shape.

Precedence ladder under test (highest priority wins):

    1. is_archived                                   → DONE
    2. status == 'closed'                            → DONE
    3. earliest active reminder                      → REMINDER
    4. status == 'paused'                            → IDLE (vacancy_paused)
    5. status == 'open' AND zero active recruiters   → CONTACT (vacancy_no_recruiter)
    6. otherwise (open + has recruiter, no reminder) → IDLE (no_signal)

The handler explicitly orders branches 1→6; if a higher-precedence branch
test starts failing while a lower one passes, the precedence got reordered
or a branch predicate regressed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import TASKS
from backend.app.models import Company, User, Vacancy
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.vacancy_recruiter import VacancyRecruiter
from backend.app.services.next_action import (
    NextActionKind,
    NextActionPriority,
    compute_vacancy_next_action,
)


pytestmark = pytest.mark.anyio


async def _any_company_id(db: AsyncSession, tenant_id: str) -> str:
    """Pick an arbitrary company in this tenant to satisfy the FK.

    `Vacancy.company_id` is a non-null FK to `companies.id` with
    `ondelete=RESTRICT`, so we cannot use a random UUID here.
    """
    cid = await db.scalar(
        select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
    )
    if cid is None:
        # Fallback: create a throwaway company. Most test fixtures already
        # seed at least one but this keeps the test resilient if seeds change.
        cid = str(uuid.uuid4())
        db.add(Company(id=cid, tenant_id=tenant_id, name="Vacancy NA Test Co"))
        await db.flush()
    return str(cid)


async def _any_user_id(db: AsyncSession, tenant_id: str) -> str:
    """Pick an arbitrary user in this tenant to satisfy the recruiter FK."""
    uid = await db.scalar(
        select(User.id).where(User.tenant_id == tenant_id).limit(1)
    )
    assert uid is not None, "test fixtures must seed at least one user"
    return str(uid)


async def _seed_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str = "open",
    is_archived: bool = False,
    is_active: bool = True,
) -> str:
    vid = str(uuid.uuid4())
    company_id = await _any_company_id(db, tenant_id)
    db.add(
        Vacancy(
            id=vid,
            tenant_id=tenant_id,
            company_id=company_id,
            title=f"Vacancy {vid[:8]}",
            status=status,
            is_active=is_active,
            is_archived=is_archived,
        )
    )
    await db.commit()
    return vid


async def _attach_recruiter(db: AsyncSession, *, tenant_id: str, vacancy_id: str) -> None:
    """Attach an active recruiter so the `vacancy_no_recruiter` branch
    doesn't fire. We use any user in the tenant — for the next-action
    surface only the `is_active` flag matters."""
    user_id = await _any_user_id(db, tenant_id)
    db.add(
        VacancyRecruiter(
            vacancy_id=vacancy_id,
            user_id=user_id,
            tenant_id=tenant_id,
            is_active=True,
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Branch 1: is_archived. Trumps everything else — even an archived vacancy
# in `status='open'` with reminders should not nag the operator.
# ---------------------------------------------------------------------------


async def test_archived_vacancy_yields_done_archived(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open", is_archived=True)

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.entity_type == "vacancy"
    assert dto.entity_id == vid
    assert dto.kind == NextActionKind.DONE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "terminal_archived"
    assert dto.href is None  # nothing clickable on archived


async def test_archived_trumps_open_with_reminder(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Regression guard for precedence: archived must beat reminder."""
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open", is_archived=True)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="manual",
            entity_type="vacancy",
            entity_id=vid,
            title="Should not surface",
            due_at=datetime.now(timezone.utc) - timedelta(hours=1),
            status=ReminderStatus.overdue,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_archived"


# ---------------------------------------------------------------------------
# Branch 2: status='closed'. Pipeline outcome recorded.
# ---------------------------------------------------------------------------


async def test_closed_status_yields_done(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="closed")

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_status_closed"


# ---------------------------------------------------------------------------
# Branch 3: earliest active reminder. Two sub-cases (future / overdue).
# Cancelled reminders MUST NOT count (regression guard for G-1).
# ---------------------------------------------------------------------------


async def test_active_future_reminder_yields_reminder_normal(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")
    # Attach a recruiter so this test isolates the reminder branch from the
    # `vacancy_no_recruiter` branch — otherwise we'd be testing precedence
    # by accident.
    await _attach_recruiter(db, tenant_id=tenant_id, vacancy_id=vid)
    rid = str(uuid.uuid4())
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="manual",
            entity_type="vacancy",
            entity_id=vid,
            title="Refresh JD",
            due_at=datetime.now(timezone.utc) + timedelta(days=2),
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "reminder_due"
    assert dto.href == f"{TASKS}?focus={rid}"


async def test_overdue_reminder_yields_reminder_critical(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")
    await _attach_recruiter(db, tenant_id=tenant_id, vacancy_id=vid)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="manual",
            entity_type="vacancy",
            entity_id=vid,
            title="Stale JD",
            due_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status=ReminderStatus.overdue,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "reminder_overdue"


async def test_cancelled_reminder_does_not_count_as_active(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Regression guard for G-1 cleanup leaking back into the surface."""
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")
    await _attach_recruiter(db, tenant_id=tenant_id, vacancy_id=vid)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="manual",
            entity_type="vacancy",
            entity_id=vid,
            title="Stale",
            due_at=datetime.now(timezone.utc) - timedelta(days=3),
            status=ReminderStatus.cancelled,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "no_signal"


# ---------------------------------------------------------------------------
# Branch 2 extension (Phase 2.6.D Stage F): `filled` and `cancelled`
# joined `closed` as canonical terminal codes — see `_VACANCY_TERMINAL_
# STATUS_CODES` in `services/next_action.py`. The reason_code is templated
# (`terminal_status_<code>`) so the popover can localise per-code copy.
# ---------------------------------------------------------------------------


async def test_filled_status_yields_done_with_filled_reason(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="filled")

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.DONE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "terminal_status_filled"
    assert dto.href is None


async def test_cancelled_status_yields_done_with_cancelled_reason(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="cancelled")

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.DONE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "terminal_status_cancelled"
    assert dto.href is None


# ---------------------------------------------------------------------------
# Branch 4: status='on_hold' — intentional, render IDLE with a distinct
# reason so the popover can explain "you paused this on purpose".
#
# The legacy `paused` alias must keep firing the same branch until the
# Stage B alembic backfill rewrites stored rows; otherwise an existing
# tenant could wake up to spurious "no recruiter assigned" CTAs on a
# hold they put in place months ago.
# ---------------------------------------------------------------------------


async def test_on_hold_vacancy_yields_idle_with_paused_reason(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="on_hold")
    # Recruiter presence shouldn't matter here — on_hold beats no_recruiter.
    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.IDLE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "vacancy_paused"
    assert dto.href is None


async def test_legacy_paused_alias_still_yields_paused_branch(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Stage F backward-compat: rows the alembic backfill has not yet
    rewritten (`status='paused'`) must continue to fire the on-hold
    branch instead of falling through to `vacancy_no_recruiter`.
    """
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="paused")

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "vacancy_paused"


# ---------------------------------------------------------------------------
# Branch 5: status='open' + zero active recruiters → structural blocker.
# ---------------------------------------------------------------------------


async def test_open_vacancy_without_recruiters_yields_contact_high(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "vacancy_no_recruiter"
    assert dto.href == f"/app/vacancies/{vid}"


async def test_open_vacancy_with_inactive_recruiter_still_yields_no_recruiter(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """`is_active=False` on the link must NOT count as an assignment.

    Lead distribution skips inactive recruiters — the next-action surface
    has to agree, otherwise the badge says "you're fine" while the
    distributor silently drops the vacancy.
    """
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")
    user_id = await _any_user_id(db, tenant_id)
    db.add(
        VacancyRecruiter(
            vacancy_id=vid,
            user_id=user_id,
            tenant_id=tenant_id,
            is_active=False,
        )
    )
    await db.commit()

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.reason_code == "vacancy_no_recruiter"


# ---------------------------------------------------------------------------
# Branch 6 (idle): open + has active recruiter + no reminder → no_signal.
# ---------------------------------------------------------------------------


async def test_open_vacancy_with_recruiter_and_no_reminder_yields_idle(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")
    await _attach_recruiter(db, tenant_id=tenant_id, vacancy_id=vid)

    dto = await compute_vacancy_next_action(db, tenant_id=tenant_id, vacancy_id=vid)

    assert dto.kind == NextActionKind.IDLE
    assert dto.priority == NextActionPriority.IDLE
    assert dto.reason_code == "no_signal"
    assert dto.href is None


# ---------------------------------------------------------------------------
# Defensive paths.
# ---------------------------------------------------------------------------


async def test_unknown_vacancy_yields_idle_placeholder(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    dto = await compute_vacancy_next_action(
        db,
        tenant_id=tenant_id,
        vacancy_id=str(uuid.uuid4()),
    )

    assert dto.entity_type == "vacancy"
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "vacancy_not_found"


# ---------------------------------------------------------------------------
# HTTP smoke test — confirms the endpoint is mounted and returns the DTO.
# ---------------------------------------------------------------------------


async def test_endpoint_returns_dto_for_known_vacancy(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: str,
    manager_headers: Dict[str, str],
) -> None:
    vid = await _seed_vacancy(db, tenant_id=tenant_id, status="open")
    await _attach_recruiter(db, tenant_id=tenant_id, vacancy_id=vid)

    r = await client.get(
        f"/api/v1/vacancies/{vid}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["entity_type"] == "vacancy"
    assert body["entity_id"] == vid
    assert body["kind"] in {k.value for k in NextActionKind}
    assert body["priority"] in {p.value for p in NextActionPriority}
    assert isinstance(body["reason_code"], str) and body["reason_code"]
    assert isinstance(body["title"], str) and body["title"]


async def test_endpoint_returns_404_for_unknown_vacancy(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    r = await client.get(
        f"/api/v1/vacancies/{uuid.uuid4()}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 404, r.text
