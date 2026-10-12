"""Every persisted Candidate.stage change has one CandidateStageHistory row."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.services.candidate_stage_history_integrity import (
    UNSCOPED_STAGE_ASSIGNMENT_REASON,
    transition_candidate_stage,
)
from backend.tests.conftest import _set_tenant

_APP = Path(__file__).resolve().parents[2] / "app"
_ASSIGNMENT = (
    "cand.stage =",
    "candidate.stage =",
    "session.candidate.stage =",
)
_CORE_STAGE_UPDATE = "values(stage="
_ASSIGNMENT_ALLOWLIST = {
    "services/candidate_stage_history_integrity.py",
}
_CORE_UPDATE_ALLOWLIST = {
    "api/v1/candidates/service.py",
}


def _app_files():
    return [path for path in _APP.rglob("*.py") if "__pycache__" not in path.parts]


def test_stage_assignment_is_only_in_the_transition_helper() -> None:
    offenders: list[str] = []
    for path in _app_files():
        rel = path.relative_to(_APP).as_posix()
        text = path.read_text(encoding="utf-8")
        if rel not in _ASSIGNMENT_ALLOWLIST and any(token in text for token in _ASSIGNMENT):
            offenders.append(rel)
        if rel not in _CORE_UPDATE_ALLOWLIST and _CORE_STAGE_UPDATE in text.replace(" ", ""):
            offenders.append(f"{rel} core-update")
    assert offenders == []


async def _history(tenant_id: str, candidate_id: str) -> list[CandidateStageHistory]:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        rows = (
            await db.execute(
                select(CandidateStageHistory)
                .where(
                    CandidateStageHistory.tenant_id == tenant_id,
                    CandidateStageHistory.candidate_id == candidate_id,
                )
                .order_by(CandidateStageHistory.at)
            )
        ).scalars().all()
        return list(rows)


@pytest.mark.anyio
async def test_direct_assignment_records_exactly_one_history_row(tenant_id: str) -> None:
    cand_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Stage",
                last_name="Integrity",
                email=f"stage-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
            )
        )
        await db.commit()
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        cand.stage = "docs_wait"
        await db.commit()

    rows = await _history(tenant_id, cand_id)
    assert len(rows) == 1
    assert rows[0].from_code == "new"
    assert rows[0].to_code == "docs_wait"
    assert rows[0].reason == UNSCOPED_STAGE_ASSIGNMENT_REASON


@pytest.mark.anyio
async def test_transition_helper_does_not_double_write(tenant_id: str) -> None:
    cand_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Stage",
                last_name="Helper",
                email=f"stage-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
            )
        )
        await db.commit()
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert transition_candidate_stage(
            db,
            cand,
            "contacted",
            actor_id="recruiter-1",
            reason="contact_attempt:answered",
        )
        assert not transition_candidate_stage(
            db,
            cand,
            "contacted",
            actor_id="recruiter-1",
            reason="contact_attempt:answered",
        )
        await db.commit()

    rows = await _history(tenant_id, cand_id)
    assert len(rows) == 1
    assert rows[0].to_code == "contacted"
    assert rows[0].actor == "recruiter-1"
    assert rows[0].reason == "contact_attempt:answered"
    count = 0
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(CandidateStageHistory)
                    .where(CandidateStageHistory.candidate_id == cand_id)
                )
            ).scalar_one()
        )
    assert count == 1
