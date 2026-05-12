"""Unit/integration tests for ``is_recruitment_recruiter_write_locked_by_handoff`` (PR-3.1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.company import Company
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.models.user import User
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    is_recruitment_recruiter_write_locked_by_handoff,
)
from tests.conftest import DEFAULT_TENANT_ID


async def _set_tenant_ctx(db, tenant_id: str) -> None:
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
    except Exception:
        pass


async def _any_user_id(db, tenant_id: str) -> str:
    row = await db.execute(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    uid = row.scalar_one_or_none()
    assert uid, "bootstrap user required"
    return str(uid)


@pytest.mark.asyncio
async def test_guard_override_roles_contract() -> None:
    assert RECRUITMENT_LOCK_OVERRIDE_ROLES == frozenset({"administrator", "supervisor", "superadmin"})


@pytest.mark.asyncio
async def test_lock_when_application_status_handed_off() -> None:
    cand_id = str(uuid.uuid4())
    app_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        await _set_tenant_ctx(db, DEFAULT_TENANT_ID)
        uid = await _any_user_id(db, DEFAULT_TENANT_ID)
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=DEFAULT_TENANT_ID,
                first_name="G",
                last_name="Handoff",
            )
        )
        db.add(
            RecruitmentApplication(
                id=app_id,
                tenant_id=DEFAULT_TENANT_ID,
                candidate_id=cand_id,
                status="handed_off",
                recruiter_id=uid,
            )
        )
        await db.commit()

        try:
            locked, reason = await is_recruitment_recruiter_write_locked_by_handoff(
                db, agency_tenant_id=DEFAULT_TENANT_ID, candidate_id=cand_id
            )
            assert locked is True
            assert reason == "application_handed_off"
        finally:
            await _set_tenant_ctx(db, DEFAULT_TENANT_ID)
            await db.execute(text("DELETE FROM recruitment_applications WHERE id = :id"), {"id": app_id})
            await db.execute(text("DELETE FROM candidates WHERE id = :id"), {"id": cand_id})
            await db.commit()


@pytest.mark.asyncio
async def test_lock_pending_review_accepted_locked_at_unlock_returned() -> None:
    cand_id = str(uuid.uuid4())
    hid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with async_session_maker() as db:
        await _set_tenant_ctx(db, DEFAULT_TENANT_ID)
        uid = await _any_user_id(db, DEFAULT_TENANT_ID)
        company_id = (
            await db.execute(
                select(Company.id).where(Company.tenant_id == DEFAULT_TENANT_ID).limit(1)
            )
        ).scalar_one_or_none()
        assert company_id, "need a company row for handoff FK check"
        company_id_str = str(company_id)

        db.add(
            Candidate(
                id=cand_id,
                tenant_id=DEFAULT_TENANT_ID,
                first_name="G",
                last_name="Lock",
            )
        )
        await db.flush()

        for status in ("pending_review", "accepted"):
            db.add(
                CandidateHandoff(
                    id=str(uuid.uuid4()),
                    candidate_id=cand_id,
                    agency_tenant_id=DEFAULT_TENANT_ID,
                    client_company_id=company_id_str,
                    client_tenant_id=None,
                    requested_by_user_id=uid,
                    requested_at=now,
                    status=status,
                    destination="internal_hr",
                    handoff_type="internal_hr",
                )
            )
            await db.flush()
            locked, reason = await is_recruitment_recruiter_write_locked_by_handoff(
                db, agency_tenant_id=DEFAULT_TENANT_ID, candidate_id=cand_id
            )
            assert locked is True, status
            assert reason == "active_handoff"
            await db.execute(
                text("DELETE FROM candidate_handoffs WHERE candidate_id = :cid"),
                {"cid": cand_id},
            )
            await db.flush()

        # locked_at set, non-terminal custom status (not in returned/rejected)
        db.add(
            CandidateHandoff(
                id=hid,
                candidate_id=cand_id,
                agency_tenant_id=DEFAULT_TENANT_ID,
                client_company_id=company_id_str,
                client_tenant_id=None,
                requested_by_user_id=uid,
                requested_at=now,
                status="draft_sync",
                destination="internal_hr",
                handoff_type="internal_hr",
                locked_at=now,
            )
        )
        await db.commit()
        try:
            locked, reason = await is_recruitment_recruiter_write_locked_by_handoff(
                db, agency_tenant_id=DEFAULT_TENANT_ID, candidate_id=cand_id
            )
            assert locked is True
            assert reason == "active_handoff"

            await db.execute(
                text(
                    "UPDATE candidate_handoffs SET status = 'returned', locked_at = NULL WHERE id = :id"
                ),
                {"id": hid},
            )
            await db.commit()
            locked2, _ = await is_recruitment_recruiter_write_locked_by_handoff(
                db, agency_tenant_id=DEFAULT_TENANT_ID, candidate_id=cand_id
            )
            assert locked2 is False
        finally:
            await _set_tenant_ctx(db, DEFAULT_TENANT_ID)
            await db.execute(text("DELETE FROM candidate_handoffs WHERE candidate_id = :cid"), {"cid": cand_id})
            await db.execute(text("DELETE FROM candidates WHERE id = :id"), {"id": cand_id})
            await db.commit()

