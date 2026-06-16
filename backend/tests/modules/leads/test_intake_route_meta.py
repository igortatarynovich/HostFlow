"""Meta intake route: form → OwnCompany → lead_target_type → ingest outcome."""

from __future__ import annotations

import json
import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models import Lead, OwnCompany
from backend.app.modules.outcome_rules.reference import OutcomeRuleType
from backend.app.modules.leads import crud
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
        {"id": company_id, "tenant_id": tenant_id, "name": "Route Test Co"},
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


async def _set_agency_business_type(session, tenant_id: str) -> None:
    await session.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb) || jsonb_build_object('business_type', 'agency')
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    await session.commit()


def _meta_payload_with_form(
    *,
    form_id: str,
    email: str,
    phone: str,
    lead_id: str,
    vacancy_id: str | None = None,
) -> dict:
    field_data = [
        {"name": "full_name", "values": ["B2B Lead"]},
        {"name": "email", "values": [email]},
        {"name": "phone_number", "values": [phone]},
    ]
    if vacancy_id:
        field_data.append({"name": "vacancy_id", "values": [vacancy_id]})
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": lead_id,
                            "form_id": form_id,
                            "field_data": field_data,
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.anyio
async def test_intake_route_client_lead_on_agency_profile_skips_candidate(client, manager_headers, tenant_id):
    form_id = f"form-b2b-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        await _set_agency_business_type(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        services_oc = await _ensure_own_company(
            session, tenant_id, business_type="services", name="Work Host Services"
        )
        await crud.upsert_meta_form_route(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            own_company_id=services_oc,
            lead_target_type="client_lead",
        )
        await session.commit()

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload_with_form(
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
    assert body["outcome_entity_type"] == "company"

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.lead_target_type == "client_lead"
        assert lead.lead_type == "client"
        assert str(lead.own_company_id) == services_oc
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        routing = norm.get("intake_routing_v1") or {}
        assert routing.get("matched") is True
        assert routing.get("route_intent") == "sales_inquiry"
        route_block = norm.get("intake_route_v1") or {}
        assert route_block.get("matched") is True
        assert route_block.get("lead_target_type") == "client_lead"
        outcome = norm.get("outcome_resolution_v1") or {}
        assert [item.get("code") for item in outcome.get("actions", [])] == [
            OutcomeRuleType.none.value
        ]


@pytest.mark.anyio
async def test_intake_route_candidate_on_agency_profile_creates_candidate(
    client, manager_headers, tenant_id
):
    form_id = f"form-driver-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        await _set_agency_business_type(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        agency_oc = await _ensure_own_company(
            session, tenant_id, business_type="agency", name="Work Host Agency"
        )
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
        await crud.upsert_meta_form_route(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            own_company_id=agency_oc,
            lead_target_type="candidate",
        )
        await session.commit()

    suffix = uuid.uuid4().hex[:8]
    payload = _meta_payload_with_form(
        form_id=form_id,
        email=f"driver-{suffix}@example.com",
        phone=f"+4866{suffix[:7]}",
        lead_id=f"lg-driver-{suffix}",
        vacancy_id=vacancy_id,
    )
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "automatic"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    response = await post_meta_lead(client, manager_headers, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "processed"
    assert body["candidate_id"] is not None
    assert body["outcome_entity_type"] == "candidate"

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.lead_target_type == "candidate"
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        outcome = norm.get("outcome_resolution_v1") or {}
        assert [item.get("code") for item in outcome.get("actions", [])] == [
            OutcomeRuleType.create_candidate.value
        ]


@pytest.mark.anyio
async def test_meta_form_route_api_roundtrip(client, manager_headers, tenant_id):
    form_id = f"form-api-{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        oc_id = await _ensure_own_company(session, tenant_id, business_type="services", name="API Services OC")

    put_resp = await client.put(
        f"/api/v1/settings/leads/meta/forms/{form_id}/route",
        headers=manager_headers,
        json={
            "own_company_id": oc_id,
            "lead_target_type": "client_lead",
            "pipeline_preset": "services",
            "is_active": True,
        },
    )
    assert put_resp.status_code == 200, put_resp.text
    put_body = put_resp.json()
    assert put_body["form_id"] == form_id
    assert put_body["lead_target_type"] == "client_lead"
    assert put_body["own_company_id"] == oc_id

    get_resp = await client.get(
        f"/api/v1/settings/leads/meta/forms/{form_id}/route",
        headers=manager_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["lead_target_type"] == "client_lead"
