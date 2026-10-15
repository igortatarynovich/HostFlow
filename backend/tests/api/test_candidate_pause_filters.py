"""Pause is a list query, not a page filter.

Active pause = extra.candidate_ops.pause.resume_on is a date.
Overdue = that date is before today (UTC) and the candidate is still paused.
Clearing the pause leaves the pipeline stage untouched.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend.app.api.v1.candidates.repo import list_candidates
from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate

STAGE = "docs_got"


def _pause_extra(resume_on: str) -> str:
    return json.dumps(
        {
            "candidate_ops": {
                "pause": {
                    "reason": "waiting for documents",
                    "comment": "",
                    "paused_at": datetime.now(timezone.utc).isoformat(),
                    "resume_on": resume_on,
                    "paused_by": "operator",
                }
            }
        }
    )


async def _set_tenant(session, tenant_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
        {"tenant_id": tenant_id},
    )


@pytest.mark.anyio
async def test_pause_filters_find_overdue_then_clear_without_changing_stage() -> None:
    tenant = str(uuid.uuid4())
    today = datetime.now(timezone.utc).date()
    future = (today + timedelta(days=20)).isoformat()
    past = (today - timedelta(days=3)).isoformat()
    paused_future_id = str(uuid.uuid4())
    paused_past_id = str(uuid.uuid4())
    active_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _set_tenant(session, tenant)
        session.add_all(
            [
                Candidate(
                    id=paused_future_id,
                    tenant_id=tenant,
                    first_name="Future",
                    last_name="Pause",
                    stage=STAGE,
                    extra=_pause_extra(future),
                ),
                Candidate(
                    id=paused_past_id,
                    tenant_id=tenant,
                    first_name="Overdue",
                    last_name="Pause",
                    stage=STAGE,
                    extra=_pause_extra(past),
                ),
                Candidate(
                    id=active_id,
                    tenant_id=tenant,
                    first_name="Working",
                    last_name="Candidate",
                    stage=STAGE,
                    extra="{}",
                ),
            ]
        )
        await session.commit()

    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant)
            paused = await list_candidates(session, tenant, {"paused": "yes"}, limit=20)
            overdue = await list_candidates(session, tenant, {"resume_overdue": True}, limit=20)
            before = await list_candidates(
                session, tenant, {"resume_before": past}, limit=20
            )
            not_paused = await list_candidates(session, tenant, {"paused": "no"}, limit=20)

        paused_ids = {row.id for row in paused}
        overdue_ids = {row.id for row in overdue}
        before_ids = {row.id for row in before}
        not_paused_ids = {row.id for row in not_paused}

        assert paused_future_id in paused_ids
        assert paused_past_id in paused_ids
        assert active_id not in paused_ids
        assert overdue_ids == {paused_past_id}
        assert before_ids == {paused_past_id}
        assert active_id in not_paused_ids
        assert paused_past_id not in not_paused_ids

        async with async_session_maker() as session:
            await _set_tenant(session, tenant)
            row = await session.get(Candidate, paused_past_id)
            assert row is not None
            extra = json.loads(row.extra or "{}")
            extra["candidate_ops"]["pause"] = None
            row.extra = json.dumps(extra)
            await session.commit()

        async with async_session_maker() as session:
            await _set_tenant(session, tenant)
            paused_after = await list_candidates(session, tenant, {"paused": "yes"}, limit=20)
            overdue_after = await list_candidates(
                session, tenant, {"resume_overdue": True}, limit=20
            )
            stored = await session.get(Candidate, paused_past_id)

        assert paused_past_id not in {row.id for row in paused_after}
        assert paused_past_id not in {row.id for row in overdue_after}
        assert stored is not None
        assert stored.stage == STAGE
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant)
            await session.execute(
                text("DELETE FROM candidates WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant},
            )
            await session.commit()
