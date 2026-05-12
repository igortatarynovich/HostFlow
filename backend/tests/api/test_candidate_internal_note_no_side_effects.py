"""Internal candidate notes under recruitment lock must not mutate recruitment state or emit lock-override audit.

Canon: ``POST .../candidates/{id}/notes`` with ``visibility=internal`` performs a single SQL INSERT only
(no ``update_candidate_full``, no automation triggers, no SLA/activity hooks in this codebase).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text

from backend.app.db.session import async_session_maker
from backend.app.models.activity import Activity
from backend.app.models.audit import ActivityLog
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.tests.conftest import _set_tenant


async def _count_notes_raw(session, tenant_id: str, candidate_id: str) -> int:
    await _set_tenant(session, tenant_id)
    r = await session.execute(
        text("SELECT COUNT(*) FROM candidate_notes WHERE tenant_id = :tid AND candidate_id = :cid"),
        {"tid": tenant_id, "cid": candidate_id},
    )
    return int(r.scalar_one() or 0)


async def _count_activity_logs(session, tenant_id: str, candidate_id: str) -> int:
    await _set_tenant(session, tenant_id)
    r = await session.execute(
        select(func.count())
        .select_from(ActivityLog)
        .where(ActivityLog.tenant_id == tenant_id, ActivityLog.target_id == candidate_id)
    )
    return int(r.scalar_one() or 0)


async def _count_lock_override_audits(session, tenant_id: str, candidate_id: str) -> int:
    await _set_tenant(session, tenant_id)
    r = await session.execute(
        select(func.count())
        .select_from(ActivityLog)
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_id == candidate_id,
            ActivityLog.action == "recruitment_lock_write_override",
        )
    )
    return int(r.scalar_one() or 0)


async def _count_activities_for_candidate(session, tenant_id: str, candidate_id: str) -> int:
    await _set_tenant(session, tenant_id)
    r = await session.execute(
        select(func.count())
        .select_from(Activity)
        .where(
            Activity.tenant_id == tenant_id,
            Activity.related_entity_type == "candidate",
            Activity.related_entity_id == candidate_id,
        )
    )
    return int(r.scalar_one() or 0)


async def _count_stage_history(session, tenant_id: str, candidate_id: str) -> int:
    await _set_tenant(session, tenant_id)
    r = await session.execute(
        select(func.count())
        .select_from(CandidateStageHistory)
        .where(
            CandidateStageHistory.tenant_id == tenant_id,
            CandidateStageHistory.candidate_id == candidate_id,
        )
    )
    return int(r.scalar_one() or 0)


@pytest.mark.asyncio
async def test_internal_note_under_application_lock_does_not_move_recruitment_or_side_channels(
    client: AsyncClient,
    manager_headers: dict,
    candidate_id: str,
    bootstrap: dict,
) -> None:
    """RecruitmentApplication ``handed_off`` locks agency dossier; internal note stays a plain INSERT."""
    tenant_id = bootstrap["tenant_id"]
    recruiter_id = bootstrap["recruiter_id"]
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            await session.commit()

        before = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
        assert before.status_code == 200, before.text
        stage_before = before.json().get("stage")
        status_before = before.json().get("status")

        async with async_session_maker() as session:
            n_log = await _count_activity_logs(session, tenant_id, candidate_id)
            n_act = await _count_activities_for_candidate(session, tenant_id, candidate_id)
            n_hist = await _count_stage_history(session, tenant_id, candidate_id)
            n_notes = await _count_notes_raw(session, tenant_id, candidate_id)
            n_lock_ov = await _count_lock_override_audits(session, tenant_id, candidate_id)

        note = await client.post(
            f"/api/v1/candidates/{candidate_id}/notes",
            headers=mgr_json,
            json={"text": "internal-only coordination under lock", "visibility": "internal"},
        )
        assert note.status_code == 201, note.text
        assert note.json().get("visibility") == "internal"

        after = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
        assert after.status_code == 200, after.text
        assert after.json().get("stage") == stage_before
        assert after.json().get("status") == status_before

        async with async_session_maker() as session:
            assert await _count_activity_logs(session, tenant_id, candidate_id) == n_log
            assert await _count_activities_for_candidate(session, tenant_id, candidate_id) == n_act
            assert await _count_stage_history(session, tenant_id, candidate_id) == n_hist
            assert await _count_notes_raw(session, tenant_id, candidate_id) == n_notes + 1
            assert await _count_lock_override_audits(session, tenant_id, candidate_id) == n_lock_ov
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(
                text("DELETE FROM recruitment_applications WHERE id = :id"),
                {"id": app_id},
            )
            await session.commit()
