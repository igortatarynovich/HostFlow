"""Ingest replay (Meta webhook / CSV) must not patch Candidate when recruitment is locked."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.modules.leads import service as leads_service
from backend.tests.conftest import _init_data, _set_tenant


@pytest.mark.asyncio
async def test_processed_lead_replay_skips_candidate_when_recruitment_locked() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    recruiter_id = data["recruiter_id"]
    candidate_id = data["candidate_id"]
    company_id = data["company_id"]
    external_id = f"ingest-lock-{uuid.uuid4().hex}"
    app_id = str(uuid.uuid4())
    lead_id = str(uuid.uuid4())

    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            cand = await session.get(Candidate, candidate_id)
            assert cand is not None
            cand.extra = json.dumps({"preferred_contact": "before"}, ensure_ascii=False)
            await session.flush()

            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    status="handed_off",
                    recruiter_id=recruiter_id,
                )
            )
            session.add(
                Lead(
                    id=lead_id,
                    tenant_id=tenant_id,
                    lead_type="candidate",
                    company_id=company_id,
                    payload={},
                    normalized={"email": "ingest-lock@test.local"},
                    status="processed",
                    source="meta",
                    external_id=external_id,
                    candidate_id=candidate_id,
                )
            )
            await session.commit()

        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await leads_service.process_normalized_lead(
                session,
                tenant_id=tenant_id,
                payload={"id": external_id},
                normalized={
                    "email": "ingest-lock@test.local",
                    "leads_processing_mode_v1": "assisted",
                    "preferred_contact": "after-webhook",
                },
                source="meta",
                external_id=external_id,
            )
            await session.commit()

        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            cand2 = await session.get(Candidate, candidate_id)
            assert cand2 is not None
            extra = cand2._get_extra()
            assert extra.get("preferred_contact") == "before"
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(text("DELETE FROM leads WHERE id = :lid"), {"lid": lead_id})
            await session.execute(
                text("DELETE FROM recruitment_applications WHERE id = :aid"), {"aid": app_id}
            )
            await session.commit()
