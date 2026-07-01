"""Guard 1: no duplicate UOS \"Call candidate\" after lead conversion when lead shows prior touch."""

from __future__ import annotations

import uuid
from typing import Any, Dict

import pytest
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, Reminder
from backend.app.models.audit import ActivityLog
from backend.app.services.lead_first_contact_continuity import (
    FIRST_CONTACT_SUPPRESSED_ACTION,
    lead_first_contact_suppression_reasons_sync,
)
from backend.app.services import uos_auto_activities
from backend.tests.api.test_leads_meta import _ensure_company


def _lead_ns(**kwargs: Any) -> Any:
    return type("L", (), kwargs)()


@pytest.mark.anyio
async def test_suppression_reasons_intake_info_requested() -> None:
    lead = _lead_ns(
        id=str(uuid.uuid4()),
        stage="new",
        normalized={
            "intake_resolution_v1": {
                "status": "info_requested",
                "last_decision": "request_info",
            }
        },
    )
    r = lead_first_contact_suppression_reasons_sync(lead)
    assert any(x.startswith("intake_resolution:info_requested") for x in r)


@pytest.mark.anyio
async def test_suppression_reasons_intake_qualified() -> None:
    lead = _lead_ns(
        id=str(uuid.uuid4()),
        stage="new",
        normalized={
            "intake_resolution_v1": {
                "status": "qualified",
                "last_decision": "qualify",
            }
        },
    )
    r = lead_first_contact_suppression_reasons_sync(lead)
    assert any(x.startswith("intake_resolution:qualified") for x in r)


@pytest.mark.anyio
async def test_suppression_reasons_lead_stage_contacted() -> None:
    lead = _lead_ns(id=str(uuid.uuid4()), stage="contacted", normalized={})
    r = lead_first_contact_suppression_reasons_sync(lead)
    assert "lead_stage:contacted" in r


@pytest.mark.anyio
async def test_greenfield_lead_no_sync_reasons() -> None:
    lead = _lead_ns(id=str(uuid.uuid4()), stage="new", normalized={})
    assert lead_first_contact_suppression_reasons_sync(lead) == []


@pytest.mark.anyio
async def test_uos_creates_call_reminder_without_lead_context(
    tenant_id: str, bootstrap: Dict[str, str]
) -> None:
    actor_id = bootstrap["admin_id"]
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cid = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cid,
                tenant_id=tenant_id,
                first_name="A",
                last_name="B",
                email=f"uos-base-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                recruiter_id=actor_id,
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        row = await db.execute(select(Candidate).where(Candidate.id == cid))
        cand = row.scalar_one()
        await uos_auto_activities.ensure_candidate_created_call_task(
            db, tenant_id, actor_id, cand, source_lead=None
        )
        await db.commit()

    async with async_session_maker() as db:
        cnt = await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "candidate",
                Reminder.entity_id == cid,
                Reminder.type == "uos_candidate_call",
            )
        )
        assert int(cnt.scalar_one() or 0) >= 1


@pytest.mark.anyio
async def test_uos_skips_when_intake_info_requested_and_writes_marker(
    tenant_id: str, bootstrap: Dict[str, str]
) -> None:
    actor_id = bootstrap["admin_id"]
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cid = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cid,
                tenant_id=tenant_id,
                first_name="C",
                last_name="D",
                email=f"uos-skip-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                recruiter_id=actor_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={
                    "intake_resolution_v1": {
                        "status": "info_requested",
                        "last_decision": "request_info",
                    }
                },
                status="needs_routing",
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        row = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = row.scalar_one()
        row_c = await db.execute(select(Candidate).where(Candidate.id == cid))
        cand = row_c.scalar_one()
        await uos_auto_activities.ensure_candidate_created_call_task(
            db, tenant_id, actor_id, cand, source_lead=lead
        )
        await db.commit()

    async with async_session_maker() as db:
        cnt = await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "candidate",
                Reminder.entity_id == cid,
                Reminder.type == "uos_candidate_call",
            )
        )
        assert int(cnt.scalar_one() or 0) == 0

        log_cnt = await db.execute(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == FIRST_CONTACT_SUPPRESSED_ACTION,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == cid,
            )
        )
        assert int(log_cnt.scalar_one() or 0) >= 1


@pytest.mark.anyio
async def test_uos_skips_when_activity_log_stage_to_contacted(
    tenant_id: str, bootstrap: Dict[str, str]
) -> None:
    actor_id = bootstrap["admin_id"]
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cid = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cid,
                tenant_id=tenant_id,
                first_name="E",
                last_name="F",
                email=f"uos-act-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                recruiter_id=actor_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={},
                status="needs_routing",
                stage="new",
                source="meta",
            )
        )
        db.add(
            ActivityLog(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                action="lead.stage_changed",
                target_type="lead",
                target_id=lead_id,
                payload={"lead_id": lead_id, "from_stage": "new", "to_stage": "contacted"},
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        row = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = row.scalar_one()
        row_c = await db.execute(select(Candidate).where(Candidate.id == cid))
        cand = row_c.scalar_one()
        await uos_auto_activities.ensure_candidate_created_call_task(
            db, tenant_id, actor_id, cand, source_lead=lead
        )
        await db.commit()

    async with async_session_maker() as db:
        cnt = await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "candidate",
                Reminder.entity_id == cid,
                Reminder.type == "uos_candidate_call",
            )
        )
        assert int(cnt.scalar_one() or 0) == 0
