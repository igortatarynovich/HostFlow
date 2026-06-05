"""PR-4: Meta ingest → IntakeRouter integration tests."""

from __future__ import annotations

import json
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import func, select, text

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing import crud as intake_crud
from backend.tests.modules.leads.conftest import post_meta_lead


async def _ensure_company(session, tenant_id: str) -> str:
    result = await session.execute(
        sa.text("SELECT id FROM companies WHERE tenant_id = :tenant LIMIT 1"),
        {"tenant": tenant_id},
    )
    company_id = result.scalar_one_or_none()
    if company_id:
        return company_id
    company_id = str(uuid.uuid4())
    await session.execute(
        sa.text("INSERT INTO companies (id, tenant_id, name) VALUES (:id, :tenant_id, :name)"),
        {"id": company_id, "tenant_id": tenant_id, "name": "PR4 Test Co"},
    )
    await session.commit()
    return company_id


async def _ensure_own_company(session, tenant_id: str, *, business_type: str, name: str) -> str:
    oc_id = str(uuid.uuid4())
    extra = json.dumps({"business_type": business_type})
    await session.execute(
        sa.text(
            """
            INSERT INTO own_companies (id, tenant_id, name, extra, is_archived, created_at, updated_at)
            VALUES (:id, :tenant_id, :name, :extra, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {"id": oc_id, "tenant_id": tenant_id, "name": name, "extra": extra},
    )
    await session.commit()
    return oc_id


async def _set_tenant_business_type(session, tenant_id: str, business_type: str) -> None:
    await session.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb)
                || jsonb_build_object('business_type', (:business_type)::text)
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id, "business_type": business_type},
    )
    await session.commit()


async def _set_legacy_fallback_business_type(session, tenant_id: str, business_type: str) -> None:
    """Set business_type for legacy IntakeRouter fallback (operating Company.extra wins over tenant.settings)."""
    await session.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb)
                || jsonb_build_object('business_type', (:business_type)::text)
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id, "business_type": business_type},
    )
    result = await session.execute(
        sa.text(
            """
            UPDATE companies
            SET extra = COALESCE(extra::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                    'company_role', 'operating',
                    'business_type', (:business_type)::text,
                    'company_type', (:business_type)::text
                )
            WHERE tenant_id = :tenant_id
              AND COALESCE(is_archived, false) = false
              AND LOWER(COALESCE(extra::jsonb->>'company_role', '')) = 'operating'
            """
        ),
        {"tenant_id": tenant_id, "business_type": business_type},
    )
    if result.rowcount == 0:
        company_id = await _ensure_company(session, tenant_id)
        await session.execute(
            sa.text(
                """
                UPDATE companies
                SET extra = COALESCE(extra::jsonb, '{}'::jsonb)
                    || jsonb_build_object(
                        'company_role', 'operating',
                        'business_type', (:business_type)::text,
                        'company_type', (:business_type)::text
                    )
                WHERE id = :id
                """
            ),
            {"id": company_id, "business_type": business_type},
        )
    await session.commit()


async def _set_tenant_default_profile(session, tenant_id: str, profile_id: str) -> None:
    await session.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                    'intake_routing_v1',
                    jsonb_build_object('default_profile_id', (:profile_id)::text)
                )
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id, "profile_id": profile_id},
    )
    await session.commit()


async def _seed_intake_binding(
    session,
    *,
    tenant_id: str,
    own_company_id: str,
    form_id: str,
    route_intent: str,
    binding_active: bool = True,
    profile_active: bool = True,
) -> str:
    profile = await intake_crud.create_profile(
        session,
        tenant_id=tenant_id,
        code=f"meta-{form_id}",
        name=f"Meta {form_id}",
        own_company_id=own_company_id,
        provider="meta",
        channel="paid",
        route_intent=route_intent,
        pipeline_preset="service_sales" if route_intent == RouteIntent.sales_inquiry.value else "lead_pipeline",
        is_active=profile_active,
    )
    await intake_crud.create_binding(
        session,
        tenant_id=tenant_id,
        intake_source_profile_id=profile.id,
        provider="meta",
        external_key=f"form_id:{form_id}",
        is_active=binding_active,
    )
    await session.commit()
    return profile.id


def _meta_payload(
    *,
    form_id: str | None,
    email: str,
    phone: str,
    lead_id: str,
    vacancy_id: str | None = None,
) -> dict:
    field_data = [
        {"name": "full_name", "values": ["Test Lead"]},
        {"name": "email", "values": [email]},
        {"name": "phone_number", "values": [phone]},
    ]
    if vacancy_id:
        field_data.append({"name": "vacancy_id", "values": [vacancy_id]})
    value: dict = {
        "leadgen_id": lead_id,
        "field_data": field_data,
    }
    if form_id:
        value["form_id"] = form_id
    return {"entry": [{"changes": [{"value": value}]}]}


async def _candidate_count(session, tenant_id: str) -> int:
    return int(
        (
            await session.execute(
                select(func.count()).select_from(Candidate).where(Candidate.tenant_id == tenant_id)
            )
        ).scalar_one()
    )


@pytest.mark.anyio
async def test_meta_driver_form_creates_lead_and_candidate(client, manager_headers, tenant_id):
    form_id = f"form-driver-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        await _set_tenant_business_type(session, tenant_id, "agency")
        company_id = await _ensure_company(session, tenant_id)
        agency_oc = await _ensure_own_company(session, tenant_id, business_type="agency", name="Agency OC")
        vacancy_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO vacancies (id, tenant_id, company_id, title, status, is_active, is_archived)
                VALUES (:id, :tenant_id, :company_id, :title, :status, :is_active, :is_archived)
                """
            ),
            {
                "id": vacancy_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "title": "Driver vacancy",
                "status": "open",
                "is_active": True,
                "is_archived": False,
            },
        )
        await _seed_intake_binding(
            session,
            tenant_id=tenant_id,
            own_company_id=agency_oc,
            form_id=form_id,
            route_intent=RouteIntent.candidate_application.value,
        )

    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "automatic"},
    )

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"driver-{suffix}@example.com",
                phone=f"+4866{suffix[:7]}",
                lead_id=f"lg-driver-{suffix}",
                vacancy_id=vacancy_id,
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_id"] is not None

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("matched") is True
        assert routing.get("route_intent") == RouteIntent.candidate_application.value


@pytest.mark.anyio
async def test_meta_b2b_form_lead_only_no_candidate(client, manager_headers, tenant_id):
    form_id = f"form-b2b-{uuid.uuid4().hex[:8]}"
    services_oc: str | None = None
    before = 0
    async with async_session_maker() as session:
        await _set_tenant_business_type(session, tenant_id, "agency")
        services_oc = await _ensure_own_company(
            session, tenant_id, business_type="services", name="Services OC"
        )
        before = await _candidate_count(session, tenant_id)
        await _seed_intake_binding(
            session,
            tenant_id=tenant_id,
            own_company_id=services_oc,
            form_id=form_id,
            route_intent=RouteIntent.sales_inquiry.value,
        )

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"b2b-{suffix}@example.com",
                phone=f"+4855{suffix[:7]}",
                lead_id=f"lg-b2b-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "processed"
    assert body["candidate_id"] is None

    async with async_session_maker() as session:
        after = await _candidate_count(session, tenant_id)
        assert after == before
        lead = await session.get(Lead, body["lead_id"])
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("matched") is True
        assert routing.get("route_intent") == RouteIntent.sales_inquiry.value
        assert routing.get("pipeline_preset") == "service_sales"
        assert services_oc is not None
        assert str(lead.own_company_id) == services_oc


@pytest.mark.anyio
async def test_missing_binding_uses_tenant_default(client, manager_headers, tenant_id):
    form_id = f"form-default-{uuid.uuid4().hex[:8]}"
    default_profile_id: str | None = None
    async with async_session_maker() as session:
        oc_id = await _ensure_own_company(session, tenant_id, business_type="agency", name="Default OC")
        default_profile = await intake_crud.create_profile(
            session,
            tenant_id=tenant_id,
            code=f"tenant-default-{uuid.uuid4().hex[:8]}",
            name="Tenant default",
            own_company_id=oc_id,
            provider="meta",
            route_intent=RouteIntent.candidate_application.value,
        )
        default_profile_id = default_profile.id
        await _set_tenant_default_profile(session, tenant_id, default_profile.id)

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"default-{suffix}@example.com",
                phone=f"+4877{suffix[:7]}",
                lead_id=f"lg-default-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("matched") is True
        assert routing.get("intake_source_profile_id") == default_profile_id
        assert "tenant_default_profile" in routing.get("warnings", [])


@pytest.mark.anyio
async def test_missing_form_id_failed_review(client, manager_headers, tenant_id):
    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=None,
                email=f"noform-{suffix}@example.com",
                phone=f"+4888{suffix[:7]}",
                lead_id=f"lg-noform-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_id"] is None
    assert body["status"] == "needs_routing"

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("failed") is True
        assert "meta_missing_form_id" in routing.get("warnings", [])


@pytest.mark.anyio
async def test_legacy_fallback_agency_candidate_application(client, manager_headers, tenant_id):
    form_id = f"form-fallback-agency-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        await _set_legacy_fallback_business_type(session, tenant_id, "agency")

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"fb-agency-{suffix}@example.com",
                phone=f"+4899{suffix[:7]}",
                lead_id=f"lg-fb-agency-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text

    async with async_session_maker() as session:
        lead = await session.get(Lead, response.json()["lead_id"])
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("fallback") is True
        assert routing.get("route_intent") == RouteIntent.candidate_application.value


@pytest.mark.anyio
async def test_legacy_fallback_services_sales_inquiry(client, manager_headers, tenant_id):
    form_id = f"form-fallback-services-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        await _set_legacy_fallback_business_type(session, tenant_id, "services")

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"fb-services-{suffix}@example.com",
                phone=f"+4811{suffix[:7]}",
                lead_id=f"lg-fb-services-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_id"] is None

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("fallback") is True
        assert routing.get("route_intent") == RouteIntent.sales_inquiry.value


@pytest.mark.anyio
async def test_b2b_on_agency_tenant_never_creates_candidate(client, manager_headers, tenant_id):
    """Hard guard: B2B Meta ad must not create Candidate even on agency tenant profile."""
    form_id = f"form-b2b-guard-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        await _set_tenant_business_type(session, tenant_id, "agency")
        services_oc = await _ensure_own_company(
            session, tenant_id, business_type="services", name="WHI Services"
        )
        before = await _candidate_count(session, tenant_id)
        await _seed_intake_binding(
            session,
            tenant_id=tenant_id,
            own_company_id=services_oc,
            form_id=form_id,
            route_intent=RouteIntent.sales_inquiry.value,
        )

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"b2b-guard-{suffix}@example.com",
                phone=f"+4822{suffix[:7]}",
                lead_id=f"lg-b2b-guard-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_id"] is None, "B2B Meta ad must never create Candidate"

    async with async_session_maker() as session:
        after = await _candidate_count(session, tenant_id)
        assert after == before


@pytest.mark.anyio
async def test_inactive_binding_ignored_uses_default(client, manager_headers, tenant_id):
    form_id = f"form-inactive-{uuid.uuid4().hex[:8]}"
    default_profile_id: str | None = None
    async with async_session_maker() as session:
        oc_id = await _ensure_own_company(session, tenant_id, business_type="services", name="Inactive OC")
        await _seed_intake_binding(
            session,
            tenant_id=tenant_id,
            own_company_id=oc_id,
            form_id=form_id,
            route_intent=RouteIntent.sales_inquiry.value,
            binding_active=False,
        )
        default_profile = await intake_crud.create_profile(
            session,
            tenant_id=tenant_id,
            code=f"default-inactive-{uuid.uuid4().hex[:8]}",
            name="Fallback default",
            own_company_id=oc_id,
            provider="meta",
            route_intent=RouteIntent.sales_inquiry.value,
        )
        default_profile_id = default_profile.id
        await _set_tenant_default_profile(session, tenant_id, default_profile.id)

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload(
                form_id=form_id,
                email=f"inactive-{suffix}@example.com",
                phone=f"+4833{suffix[:7]}",
                lead_id=f"lg-inactive-{suffix}",
            )
    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text

    async with async_session_maker() as session:
        lead = await session.get(Lead, response.json()["lead_id"])
        routing = (lead.normalized or {}).get("intake_routing_v1") or {}
        assert routing.get("intake_source_profile_id") == default_profile_id
        assert response.json()["candidate_id"] is None
