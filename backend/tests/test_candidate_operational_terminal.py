"""Operational terminal guard: stage OR row-level status in PIPELINE_COMPLETED_STAGE_CODES."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.constants.stages import is_candidate_operationally_terminal
from backend.app.db.candidate_operational_sql import sql_candidate_active_operational_pipeline
from backend.app.models.candidate import Candidate
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.user import User
from backend.app.services.candidate_lifecycle import maybe_apply_candidate_operationally_terminal_cleanup


async def _any_user_id_in_tenant(db, tenant_id: str) -> str:
    uid = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert uid is not None, "No seeded user found in tenant"
    return uid


def test_is_candidate_operationally_terminal_status_only_rejected() -> None:
    assert is_candidate_operationally_terminal(stage="new", status="rejected") is True


def test_is_candidate_operationally_terminal_row_not_arbitrary() -> None:
    assert is_candidate_operationally_terminal(stage="new", status="returned_for_revision") is False


def test_sql_candidate_active_operational_pipeline_smoke() -> None:
    expr = sql_candidate_active_operational_pipeline(Candidate.stage, Candidate.status)
    assert expr is not None


@pytest.mark.anyio
async def test_maybe_apply_operationally_terminal_cleanup_cancels_reminder_on_status_only_rejected(
    db,
    candidate_id: str,
    tenant_id: str,
) -> None:
    uid = await _any_user_id_in_tenant(db, tenant_id)
    now = datetime.now(timezone.utc)
    rem = Reminder(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        type="custom",
        related_entity_type="candidate",
        related_entity_id=candidate_id,
        owner_id=uid,
        assigned_to_user_id=uid,
        title="Follow up",
        due_at=now,
        starts_at=None,
        status=ReminderStatus.pending,
        channel="internal",
    )
    db.add(rem)
    cand = await db.get(Candidate, candidate_id)
    assert cand is not None
    old_stage = str(cand.stage or "").strip() or None
    old_status = str(cand.status or "").strip() or None
    cand.status = "rejected"
    await db.commit()

    await maybe_apply_candidate_operationally_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        old_stage=old_stage,
        old_status=old_status,
        new_stage=str(cand.stage or "").strip() or None,
        new_status=str(cand.status or "").strip() or None,
        actor_id=uid,
    )
    await db.commit()

    await db.refresh(rem)
    assert str(rem.status) == ReminderStatus.done
