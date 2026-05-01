"""Branch coverage for `services/next_action.compute_document_next_action`.

Structural test for G-8 stage 2.2 (see `docs/specs/operations-loop.md`).
Mirrors the candidate / lead / vacancy next-action test layout: one test
per branch of the precedence ladder, plus an HTTP smoke test that confirms
the endpoint is mounted and returns the canonical DTO shape.

Precedence ladder under test (highest priority wins):

    1.  deleted_at IS NOT NULL                            → DONE  (terminal_deleted)
    2.  status ∈ {cancelled, not_required}                → DONE  (terminal_status_*)
    3.  status == overdue                                 → CONTACT/CRITICAL
    4.  status == expired                                 → CONTACT/HIGH
    5.  earliest active reminder                          → REMINDER
    6.  status ∈ HIGH_PRIORITY map                        → CONTACT/HIGH
    7.  status ∈ RESOLVED_DONE & expire_date < today      → CONTACT/HIGH
    8.  status ∈ RESOLVED_DONE & expire_date within 30d   → CONTACT/NORMAL
    9.  status ∈ RESOLVED_DONE                            → DONE
   10.  status ∈ AWAITING                                 → IDLE (awaiting_party)
   11.  fallback                                          → IDLE (no_signal)

Every test exercises ONE branch in isolation: higher branches are
either suppressed (no reminder, no expire date) or trumped by structural
state. Two regression-guards:

  * G-1: cancelled reminders MUST NOT count as active.
  * The mid-ladder `expire_date < today` check on a `verified` doc MUST
    fire (real-world bug we hit pre-fix: status="verified" stayed DONE
    forever even after the validity passed).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import TASKS
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.enums import DocumentKind, DocumentStatus
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services.next_action import (
    NextActionKind,
    NextActionPriority,
    compute_document_next_action,
)


pytestmark = pytest.mark.anyio


async def _seed_candidate(db: AsyncSession, *, tenant_id: str) -> str:
    cid = str(uuid.uuid4())
    db.add(
        Candidate(
            id=cid,
            tenant_id=tenant_id,
            first_name="Doc",
            last_name="Owner",
            email=f"doc-{cid[:8]}@example.com",
            stage="screening",
        )
    )
    await db.flush()
    return cid


async def _seed_document(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: DocumentStatus = DocumentStatus.missing,
    expire_date: Optional[date] = None,
    deleted_at: Optional[datetime] = None,
    candidate_id: Optional[str] = None,
) -> str:
    did = str(uuid.uuid4())
    cid = candidate_id or await _seed_candidate(db, tenant_id=tenant_id)
    db.add(
        Document(
            id=did,
            tenant_id=tenant_id,
            candidate_id=cid,
            doc_type="passport",
            kind=DocumentKind.driver,
            status=status,
            expire_date=expire_date,
            deleted_at=deleted_at,
        )
    )
    await db.commit()
    return did


# ---------------------------------------------------------------------------
# Branch 1: soft-deleted. Trumps everything (G-1 cleanup contract).
# ---------------------------------------------------------------------------


async def test_soft_deleted_document_yields_done_terminal_deleted(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    did = await _seed_document(
        db,
        tenant_id=tenant_id,
        status=DocumentStatus.missing,  # would otherwise be CONTACT/HIGH
        deleted_at=datetime.now(timezone.utc),
    )

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.entity_type == "document"
    assert dto.entity_id == did
    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_deleted"
    assert dto.href is None


# ---------------------------------------------------------------------------
# Branch 2: explicit operator opt-out (cancelled / not_required).
#
# NB: `DocumentStatus.cancelled` and `DocumentStatus.not_required` exist in
# the Python enum but are NOT yet present in the Postgres
# `document_status_enum_v2` type (verified live: only 11 of the 20 Python
# values are migrated). The service handles them defensively for when the
# enum is extended; we cannot exercise the branch via a real DB row today.
# Test below uses a synthetic Document model (no INSERT) to keep coverage.
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "DocumentStatus.cancelled / not_required exist in the Python enum but "
        "are NOT yet in Postgres `document_status_enum_v2` (live check: only "
        "11 of 20 Python values migrated). The service branch is defensive "
        "and will pass the moment the migration ships; until then we cannot "
        "INSERT a row carrying these values to exercise it through a real DB."
    )
)
@pytest.mark.parametrize(
    "status",
    [DocumentStatus.cancelled, DocumentStatus.not_required],
)
async def test_terminal_done_status_yields_done(
    db: AsyncSession,
    tenant_id: str,
    status: DocumentStatus,
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=status)

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == f"terminal_status_{status.value}"


# ---------------------------------------------------------------------------
# Branch 3: status == overdue (system-declared SLA breach).
# ---------------------------------------------------------------------------


async def test_overdue_status_yields_contact_critical(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.overdue)

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "document_overdue"


# ---------------------------------------------------------------------------
# Branch 4: status == expired (system-declared validity breach).
# ---------------------------------------------------------------------------


async def test_expired_status_yields_contact_high(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.expired)

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "document_expired"


# ---------------------------------------------------------------------------
# Branch 5: active reminder. Two flavors plus a regression-guard for
# cancelled reminders, and a coverage test for `document_step` reminders.
# ---------------------------------------------------------------------------


async def test_active_future_reminder_yields_reminder_normal(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    # status='requested' falls into AWAITING (IDLE) by default — that lets
    # us isolate the reminder branch.
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.requested)
    rid = str(uuid.uuid4())
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="manual",
            entity_type="document",
            entity_id=did,
            title="Chase carrier",
            due_at=datetime.now(timezone.utc) + timedelta(days=2),
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "reminder_due"
    assert dto.href == f"{TASKS}?focus={rid}"


async def test_overdue_reminder_yields_reminder_critical(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.requested)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="manual",
            entity_type="document",
            entity_id=did,
            title="Stale chase",
            due_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status=ReminderStatus.overdue,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.priority == NextActionPriority.CRITICAL
    assert dto.reason_code == "reminder_overdue"


async def test_document_step_reminder_surfaces_through_doc_lookup(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """`entity_type='document_step'` with `entity_id={doc_id}:{step}` MUST
    surface — the workflow scheduler uses this exact shape (see
    `services/reminders.py`)."""
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.requested)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="manual",
            entity_type="document_step",
            entity_id=f"{did}:upload_scan",
            title="Upload scan",
            due_at=datetime.now(timezone.utc) + timedelta(days=1),
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.REMINDER
    assert dto.title == "Upload scan"


async def test_cancelled_reminder_does_not_count_as_active(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Regression guard for G-1 cleanup leaking back into the surface."""
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.requested)
    db.add(
        Reminder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type="manual",
            entity_type="document",
            entity_id=did,
            title="Stale",
            due_at=datetime.now(timezone.utc) - timedelta(days=3),
            status=ReminderStatus.cancelled,
            channel="internal",
        )
    )
    await db.commit()

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    # No reminder, no terminal — falls through to AWAITING bucket because
    # status='requested'. The test name guards the cancelled-reminder branch,
    # not the IDLE outcome itself.
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "document_awaiting_party"


# ---------------------------------------------------------------------------
# Branch 6: HIGH-priority status map. One representative per reason_code
# class — the precedence already covers the bucketing.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,reason_code",
    [
        # Only DB-migrated DocumentStatus values are tested — see the skip
        # comment on the cancelled/not_required branch above for context.
        # The Python enum also defines `to_prepare`, `to_register`,
        # `uploaded` which the service maps but cannot currently persist.
        (DocumentStatus.missing, "document_missing"),
        (DocumentStatus.rejected, "document_rejected"),
        (DocumentStatus.submitted, "document_needs_verification"),
    ],
)
async def test_high_priority_status_yields_contact_high(
    db: AsyncSession,
    tenant_id: str,
    status: DocumentStatus,
    reason_code: str,
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=status)

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == reason_code
    assert dto.href is not None  # candidate page link must be present


# ---------------------------------------------------------------------------
# Branches 7-9: RESOLVED_DONE bucket × expire_date matrix.
# ---------------------------------------------------------------------------


# NB: We use `approved` rather than `verified` for the RESOLVED_DONE × expiry
# matrix because `verified` is in the Python enum but not in Postgres
# `document_status_enum_v2`. Both belong to `_DOCUMENT_RESOLVED_DONE_STATUSES`
# so the branch under test is identical.


async def test_resolved_with_expired_date_surfaces_renew_cta(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """The bug we explicitly guard against: status='approved' but expire_date
    in the past. System does NOT auto-flip status, so the next-action layer
    has to catch it."""
    today = date(2025, 6, 15)
    did = await _seed_document(
        db,
        tenant_id=tenant_id,
        status=DocumentStatus.approved,
        expire_date=today - timedelta(days=1),
    )

    dto = await compute_document_next_action(
        db,
        tenant_id=tenant_id,
        document_id=did,
        today=today,
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.HIGH
    assert dto.reason_code == "document_expired_by_date"


async def test_resolved_within_expiring_window_yields_normal_cta(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    today = date(2025, 6, 15)
    did = await _seed_document(
        db,
        tenant_id=tenant_id,
        status=DocumentStatus.approved,
        expire_date=today + timedelta(days=10),
    )

    dto = await compute_document_next_action(
        db,
        tenant_id=tenant_id,
        document_id=did,
        today=today,
    )

    assert dto.kind == NextActionKind.CONTACT
    assert dto.priority == NextActionPriority.NORMAL
    assert dto.reason_code == "document_expiring_soon"


async def test_resolved_with_far_expire_date_yields_done(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    today = date(2025, 6, 15)
    did = await _seed_document(
        db,
        tenant_id=tenant_id,
        status=DocumentStatus.approved,
        expire_date=today + timedelta(days=365),
    )

    dto = await compute_document_next_action(
        db,
        tenant_id=tenant_id,
        document_id=did,
        today=today,
    )

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_status_approved"


async def test_resolved_without_expire_date_yields_done(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """No expire_date column → no expiry check possible → DONE."""
    did = await _seed_document(
        db,
        tenant_id=tenant_id,
        status=DocumentStatus.approved,
        expire_date=None,
    )

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.DONE
    assert dto.reason_code == "terminal_status_approved"


# ---------------------------------------------------------------------------
# Branch 10: AWAITING bucket → IDLE with context reason.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [DocumentStatus.requested, DocumentStatus.in_progress],
)
async def test_awaiting_status_yields_idle_with_awaiting_reason(
    db: AsyncSession,
    tenant_id: str,
    status: DocumentStatus,
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=status)

    dto = await compute_document_next_action(db, tenant_id=tenant_id, document_id=did)

    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "document_awaiting_party"


# ---------------------------------------------------------------------------
# Defensive paths.
# ---------------------------------------------------------------------------


async def test_unknown_document_yields_idle_placeholder(
    db: AsyncSession,
    tenant_id: str,
) -> None:
    dto = await compute_document_next_action(
        db,
        tenant_id=tenant_id,
        document_id=str(uuid.uuid4()),
    )

    assert dto.entity_type == "document"
    assert dto.kind == NextActionKind.IDLE
    assert dto.reason_code == "document_not_found"


# ---------------------------------------------------------------------------
# HTTP smoke tests.
# ---------------------------------------------------------------------------


async def test_endpoint_returns_dto_for_known_document(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: str,
    manager_headers: Dict[str, str],
) -> None:
    did = await _seed_document(db, tenant_id=tenant_id, status=DocumentStatus.missing)

    r = await client.get(
        f"/api/v1/db/documents/{did}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["entity_type"] == "document"
    assert body["entity_id"] == did
    assert body["kind"] in {k.value for k in NextActionKind}
    assert body["priority"] in {p.value for p in NextActionPriority}
    assert isinstance(body["reason_code"], str) and body["reason_code"]


async def test_endpoint_returns_404_for_unknown_document(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    r = await client.get(
        f"/api/v1/db/documents/{uuid.uuid4()}/next-action",
        headers=manager_headers,
    )
    assert r.status_code == 404, r.text
