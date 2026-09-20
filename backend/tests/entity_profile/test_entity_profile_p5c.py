"""Entity Profile Definition Registry P5C — Lead-first public intake draft session."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.public_intake_draft_session import is_public_intake_draft_lead
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


pytestmark = pytest.mark.anyio


async def _seed_form(tenant_id: str) -> str:
    slug = f"p5c-{uuid.uuid4().hex[:10]}"
    async with async_session_maker() as session:
        form_id = str(uuid.uuid4())
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="P5C test form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.flush()
        from backend.tests.forms_platform.publish_fixtures import commit_live_publication

        await commit_live_publication(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    return slug


async def _seed_form_with_vacancy(tenant_id: str) -> tuple[str, str]:
    slug = f"p5c-vac-{uuid.uuid4().hex[:10]}"
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_driver_ce_default_profile(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        form_id = str(uuid.uuid4())
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="P5C vacancy form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.flush()
        from backend.tests.forms_platform.publish_fixtures import commit_live_publication

        await commit_live_publication(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    return slug, vacancy_id


def _headers(tenant_id: str) -> dict[str, str]:
    return {"X-Tenant-Id": tenant_id}


async def test_p5c_create_draft_lead_not_candidate(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_form(tenant_id)
    phone_suffix = uuid.uuid4().int % 10**9
    phone = f"{phone_suffix:09d}"
    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"phone_country_code": "+48", "phone": phone}, "lead_form_slug": slug},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("lead_id")
    assert body.get("candidate_id") in (None, "")

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.stage == "intake_draft"
        assert is_public_intake_draft_lead(lead)
        count = await session.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.phone == phone,
                Candidate.deleted_at.is_(None),
            )
        )
        assert int(count or 0) == 0


async def test_p5c_submit_lead_only_without_candidate(client: AsyncClient, tenant_id: str) -> None:
    """Live publication is required to create; leftover ingest dispatch is not FP-3."""
    slug = await _seed_form(tenant_id)
    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone": phone, "email": f"leadonly-{uuid.uuid4().hex[:8]}@example.com"},
            "lead_form_slug": slug,
        },
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    lead_id = create.json()["lead_id"]
    assert lead_id
    assert not create.json().get("candidate_id")

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body.get("form_presentation") is None
    runtime = body.get("form_runtime")
    assert runtime is not None
    assert runtime["contract"] == RUNTIME_MODEL_CONTRACT
    assert body.get("lead_id") == lead_id


async def test_p5c_provider_agnostic_draft_block(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_form(tenant_id)
    for source in ("landing", "meta", "csv"):
        phone_suffix = uuid.uuid4().int % 10**9
        resp = await client.post(
            "/api/v1/public/intake",
            headers=_headers(tenant_id),
            json={
                "contacts": {"phone_country_code": "+48", "phone": f"{phone_suffix:09d}"},
                "lead_form_slug": slug,
                "source": source,
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json().get("lead_id")
        assert not resp.json().get("candidate_id")


async def test_p5c_submit_create_candidate_with_vacancy(client: AsyncClient, tenant_id: str) -> None:
    """Create stays lead-draft; leftover ingest candidate create is not FP-3."""
    slug, vacancy_id = await _seed_form_with_vacancy(tenant_id)
    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    email = f"p5c-create-{uuid.uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone": phone, "email": email},
            "lead_form_slug": slug,
            "vacancy_id": vacancy_id,
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body.get("lead_id")
    assert not body.get("candidate_id")
    token = body["token"]

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    served = get_resp.json()
    assert served.get("form_presentation") is None
    runtime = served.get("form_runtime")
    assert runtime is not None
    assert runtime["contract"] == RUNTIME_MODEL_CONTRACT


async def test_p5c_submit_blocked_duplicate_no_new_candidate(client: AsyncClient, tenant_id: str) -> None:
    """Create stays lead-draft even when a candidate already exists; leftover ingest is not FP-3."""
    slug, vacancy_id = await _seed_form_with_vacancy(tenant_id)
    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    email = f"p5c-dup-{uuid.uuid4().hex[:8]}@example.com"

    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone": phone, "email": email},
            "lead_form_slug": slug,
            "vacancy_id": vacancy_id,
        },
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    lead_id = create.json()["lead_id"]
    assert lead_id
    assert not create.json().get("candidate_id")

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    served = get_resp.json()
    assert served.get("form_presentation") is None
    runtime = served.get("form_runtime")
    assert runtime is not None
    assert runtime["contract"] == RUNTIME_MODEL_CONTRACT
    assert served.get("lead_id") == lead_id
