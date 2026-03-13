import json
import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead


async def _set_tenant_business_type(session, tenant_id: str, business_type: str) -> None:
    await session.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings, '{}'::jsonb) || jsonb_build_object('business_type', :business_type)
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id, "business_type": business_type},
    )
    await session.commit()


async def _ensure_vacancy(session, tenant_id: str, company_id: str) -> str:
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
            "title": "Meta Drivers",
            "status": "open",
            "is_active": True,
            "is_archived": False,
        },
    )
    await session.commit()
    return vacancy_id


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
        sa.text(
            """
            INSERT INTO companies (id, tenant_id, name)
            VALUES (:id, :tenant_id, :name)
            """
        ),
        {"id": company_id, "tenant_id": tenant_id, "name": "Meta Logistics"},
    )
    await session.commit()
    return company_id


async def _ensure_meta_settings(session, tenant_id: str, verify_token: str) -> None:
    await session.execute(
        sa.text(
            """
            INSERT INTO meta_lead_settings (tenant_id, auto_create_enabled, mask_pii_in_logs, webhook_verify_token, created_at, updated_at)
            VALUES (:tenant_id, :auto_create_enabled, :mask_pii_in_logs, :verify_token, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (tenant_id)
            DO UPDATE SET webhook_verify_token = :verify_token, updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "tenant_id": tenant_id,
            "verify_token": verify_token,
            "auto_create_enabled": True,
            "mask_pii_in_logs": True,
        },
    )
    await session.commit()


def _meta_payload(
    vacancy_id: str,
    *,
    email: str,
    phone: str,
    lead_id: str = "1234567890",
    preferred_contact: str | None = None,
    preferred_contact_field: str = "preferred_contact",
    country: str | None = None,
    in_poland: bool | None = None,
    in_poland_field: str = "in_poland",
    poland_stay_basis: str | None = None,
    poland_stay_basis_field: str = "poland_stay_basis",
    company_name: str | None = None,
    company_field: str = "company",
) -> dict:
    field_data = [
        {"name": "full_name", "values": ["Meta Lead"]},
        {"name": "email", "values": [email]},
        {"name": "phone_number", "values": [phone]},
        {"name": "vacancy_id", "values": [vacancy_id]},
    ]
    if preferred_contact:
        field_data.append({"name": preferred_contact_field, "values": [preferred_contact]})
    if country:
        field_data.append({"name": "country", "values": [country]})
    if in_poland is not None:
        field_data.append({"name": in_poland_field, "values": ["yes" if in_poland else "no"]})
    if poland_stay_basis:
        field_data.append({"name": poland_stay_basis_field, "values": [poland_stay_basis]})
    if company_name:
        field_data.append({"name": company_field, "values": [company_name]})

    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": lead_id,
                            "ad_id": "987654321",
                            "field_data": field_data,
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.anyio
async def test_meta_lead_processed(client, manager_headers, recruiter_headers, supervisor_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    payload = _meta_payload(
        vacancy_id,
        email="lead@example.com",
        phone="+48123123123",
        preferred_contact="whatsapp",
        preferred_contact_field="preferred_contact_method",
        country="LK",
        poland_stay_basis="karta_pobytu_(residence_card)",
        poland_stay_basis_field="type_of_residence_in_poland",
        company_name="Meta Logistics",
        company_field="Компания - Название",
    )

    response = await client.post(
        "/api/v1/leads/meta",
        headers=manager_headers,
        content=json.dumps(payload),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "processed"
    assert body["candidate_id"] is not None
    assert body["lead_id"] is not None
    assert body["business_type"] == "agency"
    assert body["outcome_entity_type"] == "candidate"
    assert body["outcome_entity_id"] == body["candidate_id"]

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, body["lead_id"])
        assert lead_row is not None
        assert lead_row.status == "processed"
        assert lead_row.company_id == company_id
        normalized = lead_row.normalized or {}
        if isinstance(normalized, str):
            normalized = json.loads(normalized)
        assert normalized.get("preferred_contact") == "whatsapp"
        assert normalized.get("in_poland") is True
        assert normalized.get("poland_stay_basis") == "karta_pobytu"
        assert normalized.get("poland_stay_basis_raw") == "karta_pobytu_(residence_card)"
        candidate = await session.get(Candidate, body["candidate_id"])
        assert candidate is not None
        assert candidate.source == "meta"
        assert candidate.origin is not None
        extra_payload = json.loads(candidate.extra or "{}")
        assert extra_payload.get("preferred_contact") == "whatsapp"
        assert extra_payload.get("in_poland") is True
        assert extra_payload.get("poland_stay_basis") == "karta_pobytu"

    # recruiter receives notifications
    resp_notif = await client.get("/api/v1/notifications", headers=recruiter_headers)
    assert resp_notif.status_code == 200, resp_notif.text
    notif_data = resp_notif.json()
    assert isinstance(notif_data.get("items"), list)
    recruiter_events = {item["event_type"] for item in notif_data["items"]}
    assert "lead.processed" in recruiter_events
    assert "candidate.created" in recruiter_events
    first_id = notif_data["items"][0]["id"]
    resp_mark = await client.post(
        "/api/v1/notifications/read",
        headers=recruiter_headers,
        json={"ids": [first_id]},
    )
    assert resp_mark.status_code == 200
    assert resp_mark.json().get("updated") == 1
    resp_after = await client.get("/api/v1/notifications", headers=recruiter_headers)
    remaining_ids = {item["id"] for item in resp_after.json().get("items", [])}
    assert first_id not in remaining_ids

    # supervisor sees processed lead notification
    resp_sup = await client.get("/api/v1/notifications", headers=supervisor_headers)
    assert resp_sup.status_code == 200
    sup_events = {item["event_type"] for item in resp_sup.json().get("items", [])}
    assert "lead.processed" in sup_events
    resp_sup_mark = await client.post(
        "/api/v1/notifications/read",
        headers=supervisor_headers,
        json={"mark_all": True},
    )
    assert resp_sup_mark.status_code == 200


@pytest.mark.anyio
async def test_meta_lead_duplicate(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

        duplicate_candidate = Candidate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name="Existing",
            last_name="Candidate",
            email="dup@example.com",
            stage="new",
            status="new",
            company_id=company_id,
        )
        session.add(duplicate_candidate)
        await session.commit()
        dup_candidate_id = duplicate_candidate.id

    payload = _meta_payload(vacancy_id, email="dup@example.com", phone="+48111111222", lead_id="dup-lead")

    response = await client.post(
        "/api/v1/leads/meta",
        headers=manager_headers,
        content=json.dumps(payload),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "duplicated"
    assert body["candidate_id"] == dup_candidate_id

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, body["lead_id"])
        assert lead_row is not None
        assert lead_row.status == "duplicated"


@pytest.mark.anyio
async def test_leads_list_endpoint(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    payload = _meta_payload(vacancy_id, email="list@example.com", phone="+48123123000", lead_id="list-lead")
    post_resp = await client.post(
        "/api/v1/leads/meta",
        headers=manager_headers,
        content=json.dumps(payload),
    )
    assert post_resp.status_code == 200, post_resp.text

    resp = await client.get(
        "/api/v1/leads",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data.get("items"), list)
    assert data["total"] >= 1
    lead_id = post_resp.json()["lead_id"]
    assert any(item["id"] == lead_id for item in data["items"])


@pytest.mark.anyio
async def test_services_leads_list_returns_company_outcome(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        await _set_tenant_business_type(session, tenant_id, "services")
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    payload = _meta_payload(vacancy_id, email="services@example.com", phone="+48123450000", lead_id="services-lead")
    post_resp = await client.post(
        "/api/v1/leads/meta",
        headers=manager_headers,
        content=json.dumps(payload),
    )
    assert post_resp.status_code == 200, post_resp.text
    post_body = post_resp.json()
    assert post_body["business_type"] == "services"
    assert post_body["outcome_entity_type"] == "company"
    assert post_body["outcome_entity_id"] == company_id

    resp = await client.get("/api/v1/leads", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    row = next(item for item in data["items"] if item["id"] == post_body["lead_id"])
    assert row["business_type"] == "services"
    assert row["outcome_entity_type"] == "company"
    assert row["outcome_entity_id"] == company_id

    convert_resp = await client.post(
        f"/api/v1/leads/{post_body['lead_id']}/service-order",
        headers=manager_headers,
    )
    assert convert_resp.status_code == 200, convert_resp.text
    order_body = convert_resp.json()
    assert order_body["company_id"] == company_id

    resp_after = await client.get("/api/v1/leads", headers=manager_headers)
    assert resp_after.status_code == 200, resp_after.text
    updated = next(item for item in resp_after.json()["items"] if item["id"] == post_body["lead_id"])
    assert updated["service_order_id"] == order_body["id"]

    invoice_resp = await client.post(
        f"/api/v1/invoices/from-service-order/{order_body['id']}",
        headers=manager_headers,
    )
    assert invoice_resp.status_code == 201, invoice_resp.text
    invoice_body = invoice_resp.json()
    assert invoice_body["service_order_id"] == order_body["id"]
    assert invoice_body["company_id"] == company_id


@pytest.mark.anyio
async def test_meta_webhook_verify_challenge(client, tenant_id):
    token = "hostflow123"
    async with async_session_maker() as session:
        await _ensure_meta_settings(session, tenant_id, token)

    resp = await client.get(
        "/api/v1/leads/meta/webhook",
        params={"hub.mode": "subscribe", "hub.challenge": "challenge-token", "hub.verify_token": token},
    )
    assert resp.status_code == 200, resp.text
    assert resp.text == "challenge-token"


@pytest.mark.anyio
async def test_meta_webhook_idempotent_processing(client, tenant_id):
    token = "hostflow123"
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, token)

    payload = _meta_payload(
        vacancy_id,
        email="webhook-idem@example.com",
        phone="+48900123123",
        lead_id="idem-lead-1",
    )
    url = f"/api/v1/leads/meta/webhook?verify_token={token}"

    first_resp = await client.post(
        url,
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert first_resp.status_code == 200, first_resp.text
    first_body = first_resp.json()
    assert first_body["status"] in {"processed", "duplicated"}
    assert first_body["lead_id"]

    second_resp = await client.post(
        url,
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert second_resp.status_code == 200, second_resp.text
    second_body = second_resp.json()
    assert second_body["lead_id"] == first_body["lead_id"]
    assert second_body["status"] == first_body["status"]
    assert second_body.get("candidate_id") == first_body.get("candidate_id")
