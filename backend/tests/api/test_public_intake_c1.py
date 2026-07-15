"""C1 — Form Constructor public form → Lead-first (ADR-013)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.tests.api.test_public_intake import _headers, _seed_active_lead_form


@pytest.mark.asyncio
async def test_c1_lead_form_create_ignores_existing_candidate(client: AsyncClient, tenant_id: str) -> None:
    """Form-bound POST /public/intake must return Lead draft even when Candidate exists by contact."""
    slug = await _seed_active_lead_form(tenant_id, prefix="c1")
    phone = f"7{uuid.uuid4().int % 10**8:08d}"
    cand_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        session.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Legacy",
                last_name="Dossier",
                phone=phone,
                phone_country_code="+48",
                intake_status="draft",
                stage="docs_wait",
            )
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": phone},
            "lead_form_slug": slug,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("lead_id")
    assert body.get("candidate_id") in (None, "")

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.stage == "intake_draft"
        assert str(lead.source or "") == "public_intake"
        cnt = await session.execute(
            select(func.count()).select_from(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.stage == "intake_draft",
            )
        )
        assert int(cnt.scalar_one() or 0) >= 1
