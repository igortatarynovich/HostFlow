"""Stage Sales Intake 1 — Meta lead → questionnaire invite → submit → convert-client."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_targeted_advertising_form import ensure_tenant_targeted_advertising_intake_form
from backend.app.models import Lead
from backend.app.modules.leads import crud as leads_crud


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _ensure_questionnaire_invite_table() -> None:
    from backend.app.db.base import Base
    from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
    from backend.app.db.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[LeadQuestionnaireInvite.__table__],
                checkfirst=True,
            )
        )


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


async def _seed_sales_profile(tenant_id: str) -> None:
    async with async_session_maker() as session:
        from backend.app.models.tenant import Tenant
        from sqlalchemy.orm.attributes import flag_modified

        tenant = await session.get(Tenant, str(tenant_id))
        if tenant is not None:
            settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
            settings["business_type"] = "services"
            tenant.settings = settings
            flag_modified(tenant, "settings")
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_tenant_targeted_advertising_intake_form(session, tenant_id)
        await session.commit()


async def _create_meta_client_lead(tenant_id: str) -> Lead:
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
            external_id=f"meta-test-{uuid4().hex[:12]}",
            payload={"full_name": "Jan Kowalski", "email": "jan@example.com"},
            normalized={
                "full_name": "Jan Kowalski",
                "email": "jan@example.com",
                "phone": "+48123456789",
                "company_name": "Test Firma",
            },
            lead_type="client",
            lead_target_type="client_lead",
        )
        lead.status = "new"
        lead.stage = "new"
        await session.commit()
        await session.refresh(lead)
        return lead


def _sales_presentation_values() -> dict[str, str | list[str]]:
    prefix = "service_sales.targeted_advertising."
    return {
        f"{prefix}need_type": "client_acquisition",
        f"{prefix}primary_outcome": "more_inquiries",
        f"{prefix}promotion_subject": "service",
        f"{prefix}industry": "transport",
        f"{prefix}client_geo_scope": "poland",
        f"{prefix}conversion_destination": "whatsapp",
        f"{prefix}offer_ready": "ready",
        f"{prefix}marketing_materials": ["photos", "logo"],
        f"{prefix}prior_ads_experience": "no",
        f"{prefix}monthly_ad_budget": "2000_5000",
        f"{prefix}start_timeline": "two_weeks",
        f"{prefix}decision_maker": "owner",
        f"{prefix}contact_full_name": "Jan Kowalski",
        f"{prefix}contact_company_name": "Test Firma",
        f"{prefix}contact_phone": "+48123456789",
        f"{prefix}contact_email": "jan@example.com",
    }


@pytest.mark.asyncio
async def test_meta_lead_questionnaire_invite_submit_convert_client(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    await _seed_sales_profile(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    invite_resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    token = invite_resp.json()["token"]
    assert token

    async with async_session_maker() as session:
        sent_lead = await leads_crud.get_lead(session, tenant_id=tenant_id, lead_id=lead_id)
        assert sent_lead is not None
        assert sent_lead.stage == "waiting_for_response"
        assert (sent_lead.normalized or {}).get("sales_questionnaire_status") == "sent"
        from backend.app.modules.applications.mappers import lead_to_sales_inquiry

        app_row = lead_to_sales_inquiry(sent_lead)
        assert app_row.status == "waiting"

    get_resp = await client.get(f"/api/v1/public/apply/{token}")
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body.get("form_presentation", {}).get("entity_profile_code") == TARGETED_ADVERTISING_PROFILE_CODE

    put_resp = await client.put(
        f"/api/v1/public/apply/{token}",
        json={"data": {"presentation_values": _sales_presentation_values(), "application_kind": "client"}},
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

    async with async_session_maker() as session:
        refreshed = await leads_crud.get_lead(session, tenant_id=tenant_id, lead_id=lead_id)
        assert refreshed is not None
        normalized = refreshed.normalized or {}
        assert normalized.get("sales_questionnaire_status") == "submitted"
        assert refreshed.stage == "questionnaire_submitted"
        assert isinstance(normalized.get("sales_questionnaire"), dict)
        assert normalized["sales_questionnaire"].get("need_type") == "client_acquisition"

        from backend.app.models.user_notification import UserNotification
        from backend.app.modules.applications.mappers import lead_to_sales_inquiry

        app_row = lead_to_sales_inquiry(refreshed)
        assert app_row.status == "questionnaire_submitted"

        notifs = [
            row
            for row in (
                await session.execute(
                    select(UserNotification).where(
                        UserNotification.tenant_id == tenant_id,
                        UserNotification.event_type == "intake.questionnaire.submitted",
                    )
                )
            ).scalars().all()
            if (row.payload or {}).get("lead_id") == lead_id
        ]
        assert len(notifs) == 1

        lead_count = await session.scalar(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id))
        assert lead_count is not None and lead_count >= 1

    # Lead convert-client is a compatibility facade over convert_sales_inquiry_mapping
    # (Review SoT + Flights provenance). Seed readiness before product convert.
    from backend.tests.api._sales_convert_readiness import ensure_product_convert_readiness

    async with async_session_maker() as session:
        await ensure_product_convert_readiness(session, tenant_id=tenant_id, lead_id=lead_id)

    convert_resp = await client.post(f"/api/v1/leads/{lead_id}/convert-client", headers=manager_headers)
    assert convert_resp.status_code == 200, convert_resp.text
    converted = convert_resp.json()
    assert converted.get("converted_client_id")


@pytest.mark.asyncio
async def test_questionnaire_invite_mark_sent_false_does_not_create_draft(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    await _seed_sales_profile(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    missing = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": False},
    )
    assert missing.status_code == 404, missing.text

    invite_resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    first_token = invite_resp.json()["token"]

    reuse = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": False},
    )
    assert reuse.status_code == 200, reuse.text
    assert reuse.json()["token"] == first_token
    assert reuse.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_constructor_b2b_form_questionnaire_invite_flow(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.models.intake_routing import IntakeSourceProfile
    from backend.tests.api.test_intake_forms_settings import _admin_headers

    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()

    admin_headers = await _admin_headers(tenant_id)
    slug = f"b2b-{uuid4().hex[:8]}"
    preset_resp = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{TARGETED_ADVERTISING_PROFILE_CODE}/presentation-preset",
        headers=admin_headers,
    )
    assert preset_resp.status_code == 200, preset_resp.text
    preset_fields = preset_resp.json()["fields"]
    assert len(preset_fields) >= 10

    create_resp = await client.post(
        "/api/v1/settings/intake-forms",
        headers=admin_headers,
        json={
            "title": "Ankieta B2B — konstruktor",
            "public_slug": slug,
            "entity_profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
            "fields": preset_fields,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    assert created["intake_source_profile"]["route_intent"] == "sales_inquiry"
    assert created["intake_source_profile"]["entity_profile_code"] == TARGETED_ADVERTISING_PROFILE_CODE
    expected_presentation = f"{TARGETED_ADVERTISING_PROFILE_CODE}.form.{slug}"
    assert created["intake_source_profile"]["presentation_code"] == expected_presentation

    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    form_id = str(created.get("form", {}).get("id") or created.get("id") or "")
    invite_resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True, **({"lead_form_id": form_id} if form_id else {})},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    token = invite_resp.json()["token"]
    assert token

    # Operator CRM headers must not hijack public apply (logged-in tester / leftover tenant).
    foreign_headers = {"X-Tenant-Id": "00000000-0000-0000-0000-000000000000"}
    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=foreign_headers)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body.get("form_presentation", {}).get("entity_profile_code") == TARGETED_ADVERTISING_PROFILE_CODE
    assert body.get("form_presentation", {}).get("presentation_code") == expected_presentation

    put_resp = await client.put(
        f"/api/v1/public/apply/{token}",
        headers=foreign_headers,
        json={"data": {"presentation_values": _sales_presentation_values(), "application_kind": "client"}},
    )
    assert put_resp.status_code == 200, put_resp.text

    submit_resp = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=foreign_headers,
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "cookies_accepted": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text
    assert submit_resp.json().get("status") == "submitted"

    async with async_session_maker() as session:
        intake_profile = await session.scalar(
            select(IntakeSourceProfile).where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.public_slug == slug,
            )
        )
        assert intake_profile is not None
        assert intake_profile.form_type == "sales_questionnaire"
        assert intake_profile.lead_target_type == "client_lead"
        refreshed = await leads_crud.get_lead(session, tenant_id=tenant_id, lead_id=lead_id)
        assert refreshed is not None
        assert (refreshed.normalized or {}).get("sales_questionnaire_status") == "submitted"
