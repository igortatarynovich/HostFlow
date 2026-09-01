"""Guard 2: lead note / intake context visible on candidate after conversion."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict

import pytest
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models import ActivityLog, Candidate, Lead
from backend.app.modules.leads.lead_candidate_conversion import create_candidate_from_lead_conversion
from backend.app.services.lead_context_carry import (
    CONTEXT_CARRIED_ACTION,
    build_lead_continuity_snapshot,
)
from backend.tests.api.test_leads_meta import _ensure_company


def _extra_dict(candidate: Candidate) -> dict[str, Any]:
    raw = candidate.extra
    if isinstance(raw, dict):
        return raw
    return json.loads(raw or "{}")


@pytest.mark.anyio
async def test_build_lead_continuity_snapshot_includes_note_and_intake() -> None:
    lead = type(
        "L",
        (),
        {
            "id": "lead-1",
            "note": "Called — interested in CE role",
            "stage": "contacted",
            "normalized": {
                "intake_resolution_v1": {
                    "status": "qualified",
                    "last_decision": "qualify",
                    "summary": "Good fit",
                }
            },
        },
    )()
    snap = build_lead_continuity_snapshot(lead)
    assert snap["source_lead_id"] == "lead-1"
    assert snap["lead_note"] == "Called — interested in CE role"
    assert snap["intake_resolution_v1"]["status"] == "qualified"
    assert "lead_note" in snap["carried_fields"]
    assert "intake_resolution_v1" in snap["carried_fields"]


@pytest.mark.anyio
async def test_build_lead_continuity_snapshot_includes_call_result() -> None:
    lead = type(
        "L",
        (),
        {
            "id": "lead-call",
            "note": "",
            "stage": "contacted",
            "normalized": {
                "call_result_v1": {
                    "result": "interested",
                    "note": "CE 5 years, callback tomorrow",
                    "at": "2026-09-01T10:00:00+00:00",
                },
                "call_results_v1": [
                    {"result": "no_answer", "at": "2026-09-01T09:00:00+00:00"},
                    {
                        "result": "interested",
                        "note": "CE 5 years, callback tomorrow",
                        "at": "2026-09-01T10:00:00+00:00",
                    },
                ],
            },
        },
    )()
    snap = build_lead_continuity_snapshot(lead)
    assert snap["call_result_v1"]["result"] == "interested"
    assert snap["call_result_v1"]["note"] == "CE 5 years, callback tomorrow"
    assert "call_result_v1" in snap["carried_fields"]
    assert len(snap["call_results_v1"]) == 2
    assert "call_results_v1" in snap["carried_fields"]


@pytest.mark.anyio
async def test_conversion_carries_lead_note_to_candidate(
    tenant_id: str,
    bootstrap: Dict[str, str],
) -> None:
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            company_id=company_id,
            payload={},
            normalized={
                "intake_resolution_v1": {
                    "status": "qualified",
                    "last_decision": "qualify",
                },
                "note": "Lead-side note: already spoke on WhatsApp",
            },
            status="new",
            stage="contacted",
            source="meta",
            external_id=f"ctx-carry-{uuid.uuid4().hex[:10]}",
        )
        db.add(lead)
        await db.commit()

    async with async_session_maker() as db:
        row = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = row.scalar_one()
        candidate = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={
                "first_name": "Carry",
                "last_name": "Test",
                "email": f"carry-{uuid.uuid4().hex[:8]}@example.com",
                "company_id": str(lead.company_id),
            },
            source_channel="meta",
            duplicate_match_level="none",
            conversion_reason="lead_processing",
        )
        await db.commit()
        cid = str(candidate.id)

    async with async_session_maker() as db:
        row = await db.execute(select(Candidate).where(Candidate.id == cid))
        cand = row.scalar_one()
        extra = _extra_dict(cand)
        continuity = extra.get("lead_continuity_v1") or {}
        assert extra.get("source_lead_id") == lead_id
        assert continuity.get("lead_note") == "Lead-side note: already spoke on WhatsApp"
        assert continuity.get("intake_resolution_v1", {}).get("status") == "qualified"
        assert "[From lead]" in str(cand.note or "")
        assert "WhatsApp" in str(cand.note or "")

        log_cnt = await db.execute(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == CONTEXT_CARRIED_ACTION,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == cid,
            )
        )
        assert int(log_cnt.scalar_one() or 0) >= 1


@pytest.mark.anyio
async def test_conversion_context_carry_is_idempotent(
    tenant_id: str,
    bootstrap: Dict[str, str],
) -> None:
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            company_id=company_id,
            payload={},
            normalized={"note": "Once only"},
            status="new",
            stage="new",
            source="meta",
            external_id=f"ctx-idemp-{uuid.uuid4().hex[:10]}",
        )
        db.add(lead)
        await db.commit()

    async with async_session_maker() as db:
        row = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = row.scalar_one()
        payload = {
            "first_name": "Idemp",
            "last_name": "Carry",
            "email": f"idemp-{uuid.uuid4().hex[:8]}@example.com",
            "company_id": str(lead.company_id),
        }
        first = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload=payload,
            source_channel="meta",
            duplicate_match_level="none",
            conversion_reason="lead_processing",
        )
        lead.candidate_id = str(first.id)
        await db.commit()
        cid = str(first.id)

    async with async_session_maker() as db:
        row = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = row.scalar_one()
        await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload=payload,
            source_channel="meta",
            duplicate_match_level="none",
            conversion_reason="lead_processing",
        )
        await db.commit()

    async with async_session_maker() as db:
        log_cnt = await db.execute(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == CONTEXT_CARRIED_ACTION,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == cid,
            )
        )
        assert int(log_cnt.scalar_one() or 0) == 1


@pytest.mark.anyio
async def test_greenfield_lead_carries_source_link_only(
    tenant_id: str,
    bootstrap: Dict[str, str],
) -> None:
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            lead_type="candidate",
            company_id=company_id,
            payload={},
            normalized={},
            status="new",
            stage="new",
            source="meta",
            external_id=f"ctx-link-{uuid.uuid4().hex[:10]}",
        )
        db.add(lead)
        await db.commit()

    async with async_session_maker() as db:
        row = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = row.scalar_one()
        candidate = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={
                "first_name": "Link",
                "last_name": "Only",
                "email": f"link-{uuid.uuid4().hex[:8]}@example.com",
                "company_id": str(lead.company_id),
            },
            source_channel="meta",
            duplicate_match_level="none",
            conversion_reason="lead_processing",
        )
        await db.commit()
        cid = str(candidate.id)

    async with async_session_maker() as db:
        row = await db.execute(select(Candidate).where(Candidate.id == cid))
        cand = row.scalar_one()
        extra = _extra_dict(cand)
        continuity = extra.get("lead_continuity_v1") or {}
        assert extra.get("source_lead_id") == lead_id
        assert continuity.get("link_only") is True
        assert continuity.get("carried_fields") == []


@pytest.mark.anyio
async def test_duplicate_attach_carries_context_without_uos_call(
    tenant_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """Guard 5 (§7.5): attach_existing links lead to active dossier — context carried, no UOS."""
    from backend.app.models import Reminder
    from backend.app.modules.leads.duplicate_decision import apply_lead_duplicate_decision
    from backend.app.services.lead_first_contact_continuity import FIRST_CONTACT_SUPPRESSED_ACTION

    actor_id = bootstrap["admin_id"]
    lead_id = str(uuid.uuid4())
    attach_note = "Second application — same driver"
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cid = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cid,
                tenant_id=tenant_id,
                first_name="Existing",
                last_name="Driver",
                email=f"dup-attach-{uuid.uuid4().hex[:8]}@example.com",
                stage="ready_for_hr",
                status="ready_for_hr",
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
                    "duplicate_match_v1": {
                        "level": "exact",
                        "suggested_candidate_id": cid,
                        "reasons": ["email"],
                    },
                    "note": attach_note,
                },
                status="duplicate_review",
                stage="new",
                source="meta",
                external_id=f"dup-attach-{uuid.uuid4().hex[:10]}",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        await apply_lead_duplicate_decision(
            db,
            tenant_id=tenant_id,
            lead_id=lead_id,
            actor_id=actor_id,
            decision="attach_existing",
            note="confirmed same person",
        )

    async with async_session_maker() as db:
        lead_row = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one()
        assert str(lead_row.candidate_id or "") == cid
        assert lead_row.status == "duplicated"

        cand = (await db.execute(select(Candidate).where(Candidate.id == cid))).scalar_one()
        extra = _extra_dict(cand)
        assert extra.get("source_lead_id") == lead_id
        continuity = extra.get("lead_continuity_v1") or {}
        assert continuity.get("lead_note") == attach_note

        uos_cnt = await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "candidate",
                Reminder.entity_id == cid,
                Reminder.type == "uos_candidate_call",
            )
        )
        assert int(uos_cnt.scalar_one() or 0) == 0

        ctx_cnt = await db.execute(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == CONTEXT_CARRIED_ACTION,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == cid,
            )
        )
        assert int(ctx_cnt.scalar_one() or 0) >= 1

        suppressed_cnt = await db.execute(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == FIRST_CONTACT_SUPPRESSED_ACTION,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == cid,
            )
        )
        assert int(suppressed_cnt.scalar_one() or 0) == 0
