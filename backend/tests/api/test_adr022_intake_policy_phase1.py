"""ADR-022 Phase 1 — match_or_create + attach policy tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_targeted_advertising_form import ensure_tenant_targeted_advertising_intake_form
from backend.app.intake_platform.constants import SUBMISSIONS_V1_KEY
from backend.app.models import Lead
from backend.app.modules.leads import crud as leads_crud


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr("backend.app.services.intake_form_write_service.ensure_lead_source_limit", _noop)
    monkeypatch.setattr("backend.app.services.intake_form_write_service.count_tenant_lead_sources", _zero)
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


async def _seed(tenant_id: str) -> None:
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_tenant_targeted_advertising_intake_form(session, tenant_id)
        await session.commit()


async def _admin_headers(tenant_id: str) -> dict[str, str]:
    from backend.tests.api.test_intake_forms_settings import _admin_headers as _base

    return await _base(tenant_id)


def _sales_presentation_values(email: str, phone: str) -> dict[str, str | list[str]]:
    prefix = f"{TARGETED_ADVERTISING_PROFILE_CODE}."
    return {
        f"{prefix}need_type": "client_acquisition",
        f"{prefix}primary_outcome": "more_inquiries",
        f"{prefix}contact_full_name": "Jan Kowalski",
        f"{prefix}contact_company_name": "Test Firma",
        f"{prefix}contact_phone": phone,
        f"{prefix}contact_email": email,
    }


async def _create_open_sales_inquiry(tenant_id: str, *, email: str, phone: str) -> Lead:
    async with async_session_maker() as session:
        from backend.app.models.own_company import OwnCompany

        own_company_id = await session.scalar(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own_company_id is not None
        lead = await leads_crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=str(own_company_id),
            company_id=None,
            vacancy_id=None,
            source="meta_ads",
            external_id=f"meta-open-{uuid4().hex[:12]}",
            payload={"email": email, "phone": phone},
            normalized={
                "email": email,
                "phone": phone,
                "entity_profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
                "full_name": "Existing Client",
            },
            lead_type="client",
            lead_target_type="client_lead",
        )
        lead.status = "new"
        lead.stage = "new"
        await session.commit()
        await session.refresh(lead)
        return lead


async def _public_intake_submit(
    client: AsyncClient,
    *,
    slug: str,
    email: str,
    phone: str,
) -> str:
    create_resp = await client.post(
        "/api/v1/public/intake",
        json={
            "contacts": {"email": email, "phone": phone},
            "lead_form_slug": slug,
            "application_kind": "client",
            "source": "public_intake",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    token = create_resp.json()["token"]

    put_resp = await client.put(
        f"/api/v1/public/apply/{token}",
        json={
            "data": {
                "presentation_values": _sales_presentation_values(email, phone),
                "application_kind": "client",
            }
        },
    )
    assert put_resp.status_code == 200, put_resp.text

    submit_resp = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "cookies_accepted": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text
    return token


@pytest.mark.asyncio
async def test_adr022_public_match_or_create_no_match(client: AsyncClient, tenant_id: str) -> None:
    await _seed(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"adr022-{uuid4().hex[:8]}"
    preset = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{TARGETED_ADVERTISING_PROFILE_CODE}/presentation-preset",
        headers=headers,
    )
    assert preset.status_code == 200, preset.text
    create = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "ADR-022 public form",
            "public_slug": slug,
            "entity_profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
            "fields": preset.json()["fields"],
        },
    )
    assert create.status_code == 200, create.text
    assert create.json()["form_definition"]["submission_policy"]["mode"] == "match_or_create"

    email = f"new-{uuid4().hex[:8]}@example.com"
    phone = "+48111222333"
    await _public_intake_submit(client, slug=slug, email=email, phone=phone)

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(Lead).where(Lead.tenant_id == tenant_id, Lead.lead_type == "client")
            )
        ).scalars().all()
        lead = next(
            (row for row in rows if (row.normalized or {}).get("email") == email),
            None,
        )
        assert lead is not None, f"No lead found for email {email}"
        submissions = (lead.normalized or {}).get(SUBMISSIONS_V1_KEY) or []
        assert len(submissions) >= 1
        assert submissions[-1]["effective_submission_policy"]["submission_policy"]["mode"] == "match_or_create"


@pytest.mark.asyncio
async def test_adr022_public_match_or_create_attach(client: AsyncClient, tenant_id: str) -> None:
    await _seed(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"adr022-attach-{uuid4().hex[:8]}"
    email = f"match-{uuid4().hex[:6]}@example.com"
    phone = "+48123456789"

    existing = await _create_open_sales_inquiry(tenant_id, email=email, phone=phone)
    existing_id = str(existing.id)

    preset = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{TARGETED_ADVERTISING_PROFILE_CODE}/presentation-preset",
        headers=headers,
    )
    create = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "ADR-022 attach form",
            "public_slug": slug,
            "entity_profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
            "fields": preset.json()["fields"],
        },
    )
    assert create.status_code == 200, create.text

    before_count = None
    async with async_session_maker() as session:
        before_count = await session.scalar(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id))

    await _public_intake_submit(client, slug=slug, email=email, phone=phone)

    async with async_session_maker() as session:
        after_count = await session.scalar(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id))
        assert after_count == before_count + 1

        refreshed = await leads_crud.get_lead(session, tenant_id=tenant_id, lead_id=existing_id)
        assert refreshed is not None
        submissions = (refreshed.normalized or {}).get(SUBMISSIONS_V1_KEY) or []
        assert len(submissions) >= 1
        assert submissions[-1].get("match_result_v1", {}).get("confidence") == "strong_single"


@pytest.mark.asyncio
async def test_adr022_invite_attach_submission(client: AsyncClient, tenant_id: str, manager_headers: dict) -> None:
    await _seed(tenant_id)
    existing = await _create_open_sales_inquiry(
        tenant_id,
        email=f"invite-{uuid4().hex[:6]}@example.com",
        phone="+48987654321",
    )
    lead_id = str(existing.id)

    invite_resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    token = invite_resp.json()["token"]

    email = existing.normalized.get("email")
    phone = existing.normalized.get("phone")
    await client.put(
        f"/api/v1/public/apply/{token}",
        json={"data": {"presentation_values": _sales_presentation_values(email, phone), "application_kind": "client"}},
    )
    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 200, submit.text

    async with async_session_maker() as session:
        lead_count = await session.scalar(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id))
        refreshed = await leads_crud.get_lead(session, tenant_id=tenant_id, lead_id=lead_id)
        assert refreshed is not None
        submissions = (refreshed.normalized or {}).get(SUBMISSIONS_V1_KEY) or []
        assert len(submissions) >= 1
        assert submissions[-1]["effective_submission_policy"]["submission_policy"]["mode"] == "attach"
        assert submissions[-1]["invite_id"] is not None
        assert lead_count is not None


@pytest.mark.asyncio
async def test_adr022_public_submit_idempotent(client: AsyncClient, tenant_id: str) -> None:
    await _seed(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"adr022-idem-{uuid4().hex[:8]}"
    preset = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{TARGETED_ADVERTISING_PROFILE_CODE}/presentation-preset",
        headers=headers,
    )
    create = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "ADR-022 idempotent submit",
            "public_slug": slug,
            "entity_profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
            "fields": preset.json()["fields"],
        },
    )
    assert create.status_code == 200, create.text

    email = f"idem-{uuid4().hex[:8]}@example.com"
    phone = "+48199888777"
    create_resp = await client.post(
        "/api/v1/public/intake",
        json={
            "contacts": {"email": email, "phone": phone},
            "lead_form_slug": slug,
            "application_kind": "client",
            "source": "public_intake",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    token = create_resp.json()["token"]

    await client.put(
        f"/api/v1/public/apply/{token}",
        json={
            "data": {
                "presentation_values": _sales_presentation_values(email, phone),
                "application_kind": "client",
            }
        },
    )
    submit_payload = {
        "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
        "cookies_accepted": True,
    }
    first = await client.post(f"/api/v1/public/apply/{token}/submit", json=submit_payload)
    second = await client.post(f"/api/v1/public/apply/{token}/submit", json=submit_payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(Lead).where(Lead.tenant_id == tenant_id, Lead.lead_type == "client")
            )
        ).scalars().all()
        lead = next((row for row in rows if (row.normalized or {}).get("email") == email), None)
        assert lead is not None
        submissions = (lead.normalized or {}).get(SUBMISSIONS_V1_KEY) or []
        assert len(submissions) == 1
        assert first.json().get("status") == "submitted"
        assert second.json().get("status") == "submitted"
