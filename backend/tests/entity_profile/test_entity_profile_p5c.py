"""Entity Profile Definition Registry P5C — Lead-first public intake draft session."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.decision_layer import IngestDisposition
from backend.app.entity_profile.public_intake_draft_session import (
    PUBLIC_INTAKE_DRAFT_V1,
    is_public_intake_draft_lead,
)
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


pytestmark = pytest.mark.anyio


async def _seed_form(tenant_id: str) -> str:
    slug = f"p5c-{uuid.uuid4().hex[:10]}"
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                title="P5C test form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()
    return slug


async def _seed_form_with_vacancy(tenant_id: str) -> tuple[str, str]:
    slug = f"p5c-vac-{uuid.uuid4().hex[:10]}"
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_driver_ce_default_profile(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        session.add(
            TenantLeadForm(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                title="P5C vacancy form",
                public_slug=slug,
                is_active=True,
            )
        )
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
    token = create.json()["token"]
    lead_id = create.json()["lead_id"]

    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 200, submit.text
    submitted = submit.json()
    assert submitted["status"] == "submitted"
    assert submitted.get("lead_id") == lead_id

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        assert norm.get("decision_result_v1") or (norm.get(PUBLIC_INTAKE_DRAFT_V1) or {}).get("decision_result_v1")


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

    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 200, submit.text
    submitted = submit.json()
    candidate_id = submitted.get("candidate_id")
    assert candidate_id

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert str(lead.candidate_id) == str(candidate_id)
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        decision = norm.get("decision_result_v1") or (norm.get(PUBLIC_INTAKE_DRAFT_V1) or {}).get("decision_result_v1")
        assert decision is not None
        assert decision.get("disposition") == IngestDisposition.create_candidate.value
        count = await session.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.phone == phone,
                Candidate.deleted_at.is_(None),
            )
        )
        assert int(count or 0) == 1


async def test_p5c_submit_blocked_duplicate_no_new_candidate(client: AsyncClient, tenant_id: str) -> None:
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

    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        existing_id = str(uuid.uuid4())
        session.add(
            Candidate(
                id=existing_id,
                tenant_id=tenant_id,
                company_id=company_id,
                first_name="Existing",
                last_name="Driver",
                phone=phone,
                email=email,
                source="manual",
            )
        )
        await session.commit()

    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 200, submit.text

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        decision = norm.get("decision_result_v1") or (norm.get(PUBLIC_INTAKE_DRAFT_V1) or {}).get("decision_result_v1")
        assert decision is not None
        assert decision.get("disposition") == IngestDisposition.blocked_duplicate.value
        count = await session.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.phone == phone,
                Candidate.deleted_at.is_(None),
            )
        )
        assert int(count or 0) == 1
        if lead.candidate_id:
            assert str(lead.candidate_id) == existing_id
