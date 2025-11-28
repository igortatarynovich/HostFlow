import hashlib
import hmac
import json
import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.core.settings import settings


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
        {"id": company_id, "tenant_id": tenant_id, "name": "Meta Admin Co"},
    )
    await session.commit()
    return company_id


async def _ensure_vacancy(session, tenant_id: str, company_id: str) -> str:
    result = await session.execute(
        sa.text(
            """
            SELECT id
            FROM vacancies
            WHERE tenant_id = :tenant AND company_id = :company
            LIMIT 1
            """
        ),
        {"tenant": tenant_id, "company": company_id},
    )
    vacancy_id = result.scalar_one_or_none()
    if vacancy_id:
        return vacancy_id

    vacancy_id = str(uuid.uuid4())
    await session.execute(
        sa.text(
            """
            INSERT INTO vacancies (id, tenant_id, company_id, title, status, is_active, is_archived)
            VALUES (:id, :tenant_id, :company_id, :title, 'open', :is_active, :is_archived)
            """
        ),
        {
            "id": vacancy_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "title": "Meta Admin Vacancy",
            "is_active": True,
            "is_archived": False,
        },
    )
    await session.commit()
    return vacancy_id


def _signed_headers(base_headers: dict, payload: dict, secret: str | None = None) -> dict:
    actual_secret = secret or settings.meta_webhook_secret or ""
    body = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(actual_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers = dict(base_headers)
    headers["Content-Type"] = "application/json"
    headers["X-Hub-Signature-256"] = signature
    return headers


@pytest.mark.anyio
async def test_meta_leads_settings_patch(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                UPDATE meta_lead_settings
                SET
                    auto_create_enabled = TRUE,
                    mask_pii_in_logs = TRUE,
                    pull_field_data_from_graph = TRUE
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        await session.commit()

    resp = await client.get("/api/v1/settings/leads/settings", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_create_enabled"] is True
    assert "pull_field_data_from_graph" in data

    patch_payload = {
        "auto_create_enabled": False,
        "mask_pii_in_logs": False,
        "reroute_after_hours": 12,
        "webhook_url": "https://example.com/meta",
        "webhook_verify_token": "verify-token-123",
        "pull_field_data_from_graph": False,
    }
    patch_resp = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json=patch_payload,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched = patch_resp.json()
    assert patched["auto_create_enabled"] is False
    assert patched["mask_pii_in_logs"] is False
    assert patched["reroute_after_hours"] == 12
    assert patched["webhook_url"] == "https://example.com/meta"
    assert patched["webhook_verify_token"] == "verify-token-123"
    assert patched["pull_field_data_from_graph"] is False


@pytest.mark.anyio
async def test_meta_leads_credentials_flow(client, manager_headers, tenant_id):
    create_payload = {
        "label": "Primary",
        "secret": "initial-secret",
        "ad_account_id": "123456789",
        "page_id": "987654321",
    }
    create_resp = await client.post(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
        json=create_payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    credential_id = created["id"]
    assert created["has_secret"] is True

    list_resp = await client.get(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["id"] == credential_id for item in items)

    rotate_resp = await client.post(
        f"/api/v1/settings/leads/credentials/{credential_id}/rotate",
        headers=manager_headers,
    )
    assert rotate_resp.status_code == 200
    rotated = rotate_resp.json()
    assert rotated["secret"]

    delete_resp = await client.delete(
        f"/api/v1/settings/leads/credentials/{credential_id}",
        headers=manager_headers,
    )
    assert delete_resp.status_code == 204


@pytest.mark.anyio
async def test_meta_leads_mapping_and_reroute(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    credential_secret = f"mapping-secret-{uuid.uuid4().hex[:6]}"
    credential_payload = {
        "label": f"Mapping credential {uuid.uuid4().hex[:4]}",
        "secret": credential_secret,
        "status": "active",
        "page_id": f"{uuid.uuid4().int % 10**9}",
        "ad_account_id": f"acc-{uuid.uuid4().hex[:6]}",
    }
    credential_resp = await client.post(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
        json=credential_payload,
    )
    assert credential_resp.status_code == 201, credential_resp.text

    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": False},
    )

    # create mapping entry
    mapping_resp = await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": 555555, "vacancy_id": vacancy_id, "note": "Seed mapping"},
    )
    assert mapping_resp.status_code == 201, mapping_resp.text
    mapping_body = mapping_resp.json()
    assert mapping_body["ad_id"] == "555555"
    assert mapping_body["vacancy_id"] == vacancy_id

    leadgen_id = f"lead-reroute-{uuid.uuid4().hex[:6]}"

    payload_skeleton = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": leadgen_id,
                            "ad_id": "555555",
                        }
                    }
                ]
            }
        ]
    }

    skeleton_resp = await client.post(
        "/api/v1/leads/meta",
        headers=_signed_headers(manager_headers, payload_skeleton, secret=credential_secret),
        content=json.dumps(payload_skeleton),
    )
    assert skeleton_resp.status_code == 200, skeleton_resp.text
    skeleton_body = skeleton_resp.json()
    assert skeleton_body["status"] == "failed"
    skeleton_error = skeleton_body.get("error") or ""
    assert any(marker in skeleton_error for marker in ("NO_CONTACTS", "GRAPH_"))
    lead_id = skeleton_body["lead_id"]

    payload_enriched = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": leadgen_id,
                            "ad_id": "555555",
                            "field_data": [
                                {"name": "full_name", "values": ["Manual Lead"]},
                                {"name": "email", "values": ["manual@example.com"]},
                                {"name": "phone_number", "values": ["+48123123001"]},
                            ],
                        }
                    }
                ]
            }
        ]
    }

    ingest_resp = await client.post(
        "/api/v1/leads/meta",
        headers=_signed_headers(manager_headers, payload_enriched, secret=credential_secret),
        content=json.dumps(payload_enriched),
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    ingest_body = ingest_resp.json()
    assert ingest_body["lead_id"] == lead_id
    lead_id = ingest_body["lead_id"]
    assert ingest_body["status"] in {"processed", "needs_routing", "duplicated"}

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT id, status, error, normalized->>'phone' AS phone
                FROM leads
                WHERE external_id = :external_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"external_id": leadgen_id},
        )
        db_id, db_status, db_error, db_phone = row.fetchone()
        assert db_id == lead_id
        assert db_status in ("processed", "needs_routing", "duplicated")
        assert db_error in (None, "", "VACANCY_NOT_RESOLVED")
        assert db_phone == "+48123123001"
        count_row = await session.execute(
            sa.text("SELECT COUNT(*) FROM leads WHERE external_id = :external_id"),
            {"external_id": leadgen_id},
        )
        assert count_row.scalar_one() == 1

    reroute_resp = await client.post(
        f"/api/v1/settings/leads/leads/{lead_id}/reroute",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id, "force_process": True},
    )
    assert reroute_resp.status_code == 200, reroute_resp.text
    rerouted = reroute_resp.json()
    assert rerouted["status"] in {"processed", "duplicated"}
    assert rerouted["candidate_id"] is not None

    # cleanup mapping
    delete_map = await client.delete(
        "/api/v1/settings/leads/mapping/555555",
        headers=manager_headers,
    )
    assert delete_map.status_code == 204

    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True},
    )


@pytest.mark.anyio
async def test_meta_leads_retry_endpoint(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": f"retry-lead-{uuid.uuid4().hex[:6]}",
                            "ad_id": "1234567890",
                            "field_data": [
                                {"name": "full_name", "values": ["Retry Tester"]},
                                {"name": "email", "values": ["retry@example.com"]},
                                {"name": "phone_number", "values": ["+48100000000"]},
                                {"name": "vacancy_id", "values": [vacancy_id]},
                            ],
                        }
                    }
                ]
            }
        ]
    }

    ingest_resp = await client.post(
        "/api/v1/leads/meta",
        headers=manager_headers,
        content=json.dumps(payload),
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    lead_payload = ingest_resp.json()
    lead_id = lead_payload["lead_id"]

    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                UPDATE leads
                SET status = 'failed', candidate_id = NULL, error = 'GRAPH_190'
                WHERE id = :lead_id AND tenant_id = :tenant_id
                """
            ),
            {"lead_id": lead_id, "tenant_id": tenant_id},
        )
        await session.commit()

    retry_resp = await client.post(
        "/api/v1/settings/leads/leads/retry",
        headers=manager_headers,
        json={"statuses": ["failed"]},
    )
    assert retry_resp.status_code == 200, retry_resp.text
    retry_body = retry_resp.json()
    assert retry_body["processed"] == 1, retry_body
    assert retry_body["failed"] == 0
    assert retry_body["skipped"] == 0
    assert len(retry_body["items"]) == 1
    item = retry_body["items"][0]
    assert item["lead_id"] == lead_id
    assert item["processed"] is True
    assert item["status_after"] in {"processed", "duplicated"}

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT status, error, candidate_id
                FROM leads
                WHERE id = :lead_id AND tenant_id = :tenant_id
                """
            ),
            {"lead_id": lead_id, "tenant_id": tenant_id},
        )
        status, error, candidate_id = row.fetchone()
        assert status in ("processed", "duplicated")
        assert error in (None, "", "VACANCY_NOT_RESOLVED")
        assert candidate_id is not None


@pytest.mark.anyio
async def test_settings_leads_forbidden_for_recruiter(client, recruiter_headers):
    resp = await client.get("/api/v1/settings/leads/settings", headers=recruiter_headers)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_settings_leads_supervisor_can_read(client, supervisor_headers):
    resp = await client.get("/api/v1/settings/leads/settings", headers=supervisor_headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_settings_leads_mapping_visible_for_supervisor(client, supervisor_headers):
    resp = await client.get("/api/v1/settings/leads/mapping", headers=supervisor_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_settings_leads_forbidden_for_supervisor(client, supervisor_headers):
    resp = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=supervisor_headers,
        json={"auto_create_enabled": False},
    )
    assert resp.status_code == 403
