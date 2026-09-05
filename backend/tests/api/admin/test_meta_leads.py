import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.core.settings import settings
from backend.app.modules.leads import meta_oauth_service as meta_oauth_service_mod
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import MetaLeadFormMapping
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import DEFAULT_TENANT_ID, _build_token, _init_data, _set_tenant


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
            INSERT INTO companies (id, tenant_id, name, party_entity_type)
            VALUES (:id, :tenant_id, :name, :party_entity_type)
            """
        ),
        {"id": company_id, "tenant_id": tenant_id, "name": "Meta Admin Co", "party_entity_type": "company"},
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


async def _default_own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        row = await session.execute(
            sa.select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


async def _seed_meta_intake_source(
    tenant_id: str,
    *,
    form_id: str,
    page_id: str = "",
    name: str | None = None,
) -> None:
    own_company_id = await _default_own_company_id(tenant_id)
    label = name or f"Meta form {form_id}"
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        profile_id = str(uuid.uuid4())
        session.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                code=f"meta-form-{form_id}"[:64],
                name=label,
                provider="meta",
                channel="paid",
                own_company_id=own_company_id,
                route_intent="candidate_application",
                is_active=True,
            )
        )
        await session.flush()
        session.add(
            IntakeSourceBinding(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                intake_source_profile_id=profile_id,
                provider="meta",
                external_key=f"form_id:{form_id}",
                external_key_secondary=f"page_id:{page_id}" if page_id else "",
                label=label,
                is_active=True,
            )
        )
        await session.commit()


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
                    pull_field_data_from_graph = TRUE,
                    leads_auto_convert_on_fit_v1 = TRUE
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
    assert data.get("leads_auto_convert_on_fit_v1", True) is True

    patch_payload = {
        "auto_create_enabled": False,
        "leads_auto_convert_on_fit_v1": False,
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
    assert patched.get("leads_auto_convert_on_fit_v1") is False
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
    assert created["ad_account_id"] == "123456789"
    assert created["page_id"] == "987654321"

    list_resp = await client.get(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    listed = next(item for item in items if item["id"] == credential_id)
    assert listed["ad_account_id"] == "123456789"
    assert listed["page_id"] == "987654321"

    clear_resp = await client.patch(
        f"/api/v1/settings/leads/credentials/{credential_id}",
        headers=manager_headers,
        json={"ad_account_id": None, "page_id": None},
    )
    assert clear_resp.status_code == 200, clear_resp.text
    cleared = clear_resp.json()
    assert cleared["ad_account_id"] is None
    assert cleared["page_id"] is None

    disable_resp = await client.patch(
        f"/api/v1/settings/leads/credentials/{credential_id}",
        headers=manager_headers,
        json={"status": "disabled", "page_id": "987654321"},
    )
    assert disable_resp.status_code == 200, disable_resp.text
    assert disable_resp.json()["status"] == "disabled"
    assert disable_resp.json()["page_id"] == "987654321"

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


@pytest.mark.anyio
async def test_meta_graph_field_preview_ok(client, manager_headers, monkeypatch):
    from backend.app.modules.leads import pipeline

    async def fake_fetch(lead_id: str, access_token: str):
        assert lead_id == "L1"
        assert access_token == "TOK111"
        return {
            "field_data": [
                {"name": "email", "values": ["a@b.co"]},
                {"name": "Custom_Question", "values": ["x"]},
            ],
            "ad_id": 99,
            "form_id": "FORM1",
        }

    monkeypatch.setattr(pipeline, "fetch_meta_lead_field_data_from_graph", fake_fetch)

    cred = await client.post(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
        json={"label": "gp", "secret": "sec", "page_id": "PAGE99", "access_token": "TOK111"},
    )
    assert cred.status_code == 201, cred.text

    resp = await client.post(
        "/api/v1/settings/leads/meta/graph-field-preview",
        headers=manager_headers,
        json={"leadgen_id": "L1", "page_id": "PAGE99"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["leadgen_id"] == "L1"
    assert data["page_id"] == "PAGE99"
    assert data["form_id"] == "FORM1"
    assert data["ad_id"] == "99"
    assert data["field_names"] == ["custom_question", "email"]


@pytest.mark.anyio
async def test_meta_graph_field_preview_requires_ids(client, manager_headers):
    resp = await client.post(
        "/api/v1/settings/leads/meta/graph-field-preview",
        headers=manager_headers,
        json={},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_meta_graph_field_preview_graph_error(client, manager_headers, monkeypatch):
    from backend.app.modules.leads import pipeline

    async def boom(_lead_id: str, _token: str):
        raise pipeline.GraphAPIError("190", "expired")

    monkeypatch.setattr(pipeline, "fetch_meta_lead_field_data_from_graph", boom)

    cred = await client.post(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
        json={"label": "gx", "secret": "sec", "page_id": "P2", "access_token": "T2"},
    )
    assert cred.status_code == 201, cred.text

    resp = await client.post(
        "/api/v1/settings/leads/meta/graph-field-preview",
        headers=manager_headers,
        json={"leadgen_id": "LX", "page_id": "P2"},
    )
    assert resp.status_code == 502
    detail = resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "meta_graph_error"


@pytest.mark.anyio
async def test_meta_graph_field_preview_by_form_id(client, manager_headers, monkeypatch):
    from backend.app.modules.leads import meta_marketing_graph as graph

    async def fake_form(form_id: str, access_token: str):
        assert form_id == "1074988858916526"
        assert access_token == "TOKFORM"
        return {
            "id": form_id,
            "name": "Metafora TSL C/CE 110",
            "questions": [
                {"key": "email", "label": "Email", "type": "EMAIL"},
                {
                    "key": "основание_для_пребывания_в_польше",
                    "label": "Основание для пребывания в Польше",
                    "type": "CUSTOM",
                },
            ],
        }

    async def fake_latest(form_id: str, access_token: str):
        assert form_id == "1074988858916526"
        return {
            "id": "1010176182055377",
            "form_id": form_id,
            "ad_id": "120252053013860163",
            "field_data": [{"name": "email", "values": ["a@b.co"]}],
        }

    monkeypatch.setattr(graph, "fetch_leadgen_form", fake_form)
    monkeypatch.setattr(graph, "fetch_leadgen_form_latest_lead", fake_latest)

    cred = await client.post(
        "/api/v1/settings/leads/credentials",
        headers=manager_headers,
        json={"label": "gf", "secret": "sec", "page_id": "259905353877064", "access_token": "TOKFORM"},
    )
    assert cred.status_code == 201, cred.text

    resp = await client.post(
        "/api/v1/settings/leads/meta/graph-field-preview",
        headers=manager_headers,
        json={"form_id": "1074988858916526", "page_id": "259905353877064"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["form_id"] == "1074988858916526"
    assert data["leadgen_id"] == "1010176182055377"
    names = data["field_names"]
    assert "email" in names
    assert "основание_для_пребывания_в_польше" in names
    email = next(f for f in data["fields"] if f["name"] == "email")
    assert email["value_preview"] == "a@b.co"


@pytest.mark.anyio
async def test_meta_forms_list_includes_graph_leadgen_forms(
    client, manager_headers, tenant_id, monkeypatch
):
    form_id = f"1{uuid.uuid4().int % 10**15:015d}"
    page_id = "259905353877064"
    await _seed_meta_intake_source(
        tenant_id, form_id=form_id, page_id=page_id, name="Metafora TSL C/CE 110"
    )

    async def _fake_graph(_db, *, tenant_id: str):
        return [
            {
                "form_id": form_id,
                "page_id": page_id,
                "form_name": "Metafora TSL C/CE 110",
                "source": "meta",
            }
        ]

    monkeypatch.setattr(
        "backend.app.acquisition.connect_source_picker.discover_leadgen_forms_from_connected_pages",
        _fake_graph,
    )
    resp = await client.get("/api/v1/settings/leads/meta/forms", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json().get("items") or []
    by_id = {str(x.get("form_id")): x for x in items}
    assert form_id in by_id
    assert by_id[form_id]["form_name"] == "Metafora TSL C/CE 110"


@pytest.mark.anyio
async def test_meta_forms_list_hides_unclaimed_graph_and_disconnected_leftover(
    client, manager_headers, tenant_id, monkeypatch
):
    connected_page = "484113398123847"
    claimed_form = f"8{uuid.uuid4().int % 10**15:015d}"
    unclaimed_graph = f"9{uuid.uuid4().int % 10**15:015d}"
    leftover_form = f"7{uuid.uuid4().int % 10**15:015d}"
    leftover_page = "259905353877064"

    await _seed_meta_intake_source(
        tenant_id, form_id=claimed_form, page_id=connected_page, name="POLTRAKT ENG CE Drivers PL"
    )
    await _seed_meta_intake_source(
        tenant_id, form_id=leftover_form, page_id=leftover_page, name="ENG Warehouse jobs"
    )

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        session.add(
            MetaLeadFormMapping(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                source="meta",
                form_id=leftover_form,
                page_id=leftover_page,
                form_name="ENG Warehouse jobs",
                mapping_rules=[],
            )
        )
        await session.commit()

    async def _fake_graph(_db, *, tenant_id: str):
        return [
            {
                "form_id": claimed_form,
                "page_id": connected_page,
                "form_name": "POLTRAKT ENG CE Drivers PL",
                "source": "meta",
            },
            {
                "form_id": unclaimed_graph,
                "page_id": connected_page,
                "form_name": "Dyspozytor PL",
                "source": "meta",
            },
        ]

    monkeypatch.setattr(
        "backend.app.acquisition.connect_source_picker.discover_leadgen_forms_from_connected_pages",
        _fake_graph,
    )
    resp = await client.get("/api/v1/settings/leads/meta/forms", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    by_id = {str(x.get("form_id")): x for x in (resp.json().get("items") or [])}
    assert claimed_form in by_id
    assert unclaimed_graph not in by_id
    assert leftover_form not in by_id


@pytest.mark.anyio
async def test_meta_self_serve_onboarding_admin(client, manager_headers, tenant_id, monkeypatch):
    monkeypatch.setattr(settings, "meta_leads_app_id", "1102404865044655", raising=False)
    monkeypatch.setattr(settings, "meta_leads_shared_app_secret", "shared-secret-test", raising=False)
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.test.example", raising=False)
    patch_resp = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"webhook_verify_token": "verify-tenant-xyz"},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    resp = await client.get("/api/v1/settings/leads/meta/self-serve-onboarding", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["meta_app_id"] == "1102404865044655"
    assert data["shared_meta_app_secret"] == "shared-secret-test"
    assert data["public_api_base_configured"] is True
    assert data["webhook_verify_token_configured"] is True
    url = data.get("webhook_callback_url") or ""
    assert url.startswith("https://api.test.example/api/v1/leads/meta/webhook")
    assert "verify-tenant-xyz" in url
    assert "pages_read_engagement" in data.get("graph_permission_names", [])


@pytest.mark.anyio
async def test_meta_self_serve_onboarding_supervisor_hides_secret(
    client, manager_headers, supervisor_headers, tenant_id, monkeypatch
):
    monkeypatch.setattr(settings, "meta_leads_shared_app_secret", "shared-secret-test", raising=False)
    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"webhook_verify_token": "v1"},
    )
    resp = await client.get("/api/v1/settings/leads/meta/self-serve-onboarding", headers=supervisor_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json().get("shared_meta_app_secret") is None


@pytest.mark.anyio
async def test_meta_self_serve_onboarding_includes_oauth_flags(client, manager_headers, tenant_id, monkeypatch):
    monkeypatch.setattr(settings, "meta_leads_app_id", "1102404865044655", raising=False)
    monkeypatch.setattr(settings, "meta_leads_shared_app_secret", "sec", raising=False)
    monkeypatch.setattr(settings, "frontend_url", "https://app.test.example", raising=False)
    monkeypatch.setattr(settings, "meta_leads_oauth_redirect_uri", None, raising=False)
    async with async_session_maker() as session:
        await session.execute(
            sa.text("UPDATE tenant_licenses SET plan = 'team' WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
        await session.commit()
    resp = await client.get("/api/v1/settings/leads/meta/self-serve-onboarding", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("oauth_quick_connect_enabled") is True
    assert data.get("meta_oauth_plan_allowed") is True
    assert data.get("meta_oauth_server_ready") is True
    assert "app.test.example/app/settings/integrations/meta" in (data.get("oauth_redirect_uri") or "")


@pytest.mark.anyio
async def test_meta_self_serve_onboarding_oauth_flags_on_trial_plan(
    client, manager_headers, tenant_id, monkeypatch
):
    monkeypatch.setattr(settings, "meta_leads_app_id", "1102404865044655", raising=False)
    monkeypatch.setattr(settings, "meta_leads_shared_app_secret", "sec", raising=False)
    monkeypatch.setattr(settings, "frontend_url", "https://app.test.example", raising=False)
    monkeypatch.setattr(settings, "meta_leads_oauth_redirect_uri", None, raising=False)
    async with async_session_maker() as session:
        await session.execute(
            sa.text("UPDATE tenant_licenses SET plan = 'trial' WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
        await session.commit()
    resp = await client.get("/api/v1/settings/leads/meta/self-serve-onboarding", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("oauth_quick_connect_enabled") is True
    assert data.get("meta_oauth_plan_allowed") is True
    assert data.get("meta_oauth_server_ready") is True


@pytest.mark.anyio
async def test_meta_oauth_start_allowed_on_trial_plan(client, manager_headers, tenant_id, monkeypatch):
    monkeypatch.setattr(settings, "meta_leads_app_id", "1102404865044655", raising=False)
    monkeypatch.setattr(settings, "meta_leads_shared_app_secret", "sec", raising=False)
    monkeypatch.setattr(settings, "frontend_url", "https://app.test.example", raising=False)
    async with async_session_maker() as session:
        await session.execute(
            sa.text("UPDATE tenant_licenses SET plan = 'trial' WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
        await session.commit()
    resp = await client.post("/api/v1/settings/leads/meta/oauth/start", headers=manager_headers)
    assert resp.status_code != 403, resp.text


@pytest.mark.anyio
async def test_meta_oauth_start_403_on_starter_plan(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        await session.execute(
            sa.text("UPDATE tenant_licenses SET plan = 'starter' WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
        await session.commit()
    resp = await client.post("/api/v1/settings/leads/meta/oauth/start", headers=manager_headers)
    assert resp.status_code == 403, resp.text
    assert resp.json().get("detail", {}).get("code") == "plan_meta_leads_oauth"


@pytest.mark.anyio
async def test_meta_oauth_complete_and_finalize_mocked(client, manager_headers, tenant_id, monkeypatch):
    monkeypatch.setattr(settings, "meta_leads_app_id", "app-id-test", raising=False)
    monkeypatch.setattr(settings, "meta_leads_shared_app_secret", "app-secret-test", raising=False)
    monkeypatch.setattr(settings, "frontend_url", "https://app.test.example", raising=False)
    async with async_session_maker() as session:
        await session.execute(
            sa.text("UPDATE tenant_licenses SET plan = 'team' WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
        await session.commit()

    monkeypatch.setattr(
        meta_oauth_service_mod,
        "exchange_code_for_short_lived_user_token",
        AsyncMock(return_value="short_user"),
    )
    monkeypatch.setattr(
        meta_oauth_service_mod,
        "exchange_for_long_lived_user_token",
        AsyncMock(return_value="long_user"),
    )
    monkeypatch.setattr(
        meta_oauth_service_mod,
        "fetch_pages_with_tokens",
        AsyncMock(
            return_value=[
                {"id": "123456789", "name": "Test Page", "access_token": "page-token-xyz"},
            ]
        ),
    )
    monkeypatch.setattr(
        meta_oauth_service_mod,
        "subscribe_page_leadgen",
        AsyncMock(return_value=None),
    )

    st_resp = await client.post("/api/v1/settings/leads/meta/oauth/start", headers=manager_headers)
    assert st_resp.status_code == 200, st_resp.text
    state = st_resp.json()["state"]

    co_resp = await client.post(
        "/api/v1/settings/leads/meta/oauth/complete",
        headers=manager_headers,
        json={"code": "fake-code", "state": state},
    )
    assert co_resp.status_code == 200, co_resp.text
    pending_id = co_resp.json()["pending_id"]
    assert co_resp.json()["pages"] == [{"id": "123456789", "name": "Test Page"}]

    fin_resp = await client.post(
        "/api/v1/settings/leads/meta/oauth/finalize",
        headers=manager_headers,
        json={
            "pending_id": pending_id,
            "page_id": "123456789",
            "label": "OAuth Page",
            "subscribe_leadgen": True,
        },
    )
    assert fin_resp.status_code == 200, fin_resp.text
    body = fin_resp.json()
    assert body.get("subscribed_leadgen") is True
    assert body.get("credential", {}).get("label") == "OAuth Page"


@pytest.mark.anyio
async def test_superadmin_bootstrap_meta_uses_operational_tenant(client, monkeypatch):
    """META_LEADS_OPERATIONAL_TENANT_ID: superadmin on legacy default tenant reads/writes Meta on ops tenant."""
    op_id = str(uuid.uuid4())
    op_name = f"Operational Meta {op_id[:8]}"
    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                INSERT INTO tenants (id, name, slug, api_key, is_active, type, status)
                VALUES (:id, :name, :slug, :key, true, 'agency', 'active')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": op_id,
                "name": op_name,
                "slug": f"op-{op_id[:8]}",
                "key": uuid.uuid4().hex[:32],
            },
        )
        await session.commit()

    monkeypatch.setattr(settings, "meta_leads_operational_tenant_id", op_id, raising=False)

    data = await _init_data()
    sa_token = _build_token(data["admin_id"], data["admin_email"], "superadmin", DEFAULT_TENANT_ID)
    sa_headers = {
        "Authorization": f"Bearer {sa_token}",
        "X-Tenant-Id": DEFAULT_TENANT_ID,
        "X-HostFlow-Elevated-Reason": "integration-test-meta-leads-operational-remap",
        "X-HostFlow-Elevated-Scope": "meta_leads_operational_tenant",
    }

    r = await client.get("/api/v1/settings/leads/meta/self-serve-onboarding", headers=sa_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("meta_leads_context_redirected") is True
    assert body.get("meta_leads_data_tenant_id") == op_id
    assert body.get("meta_leads_data_tenant_name") == op_name

    adm_token = _build_token(data["admin_id"], data["admin_email"], "administrator", DEFAULT_TENANT_ID)
    adm_headers = {"Authorization": f"Bearer {adm_token}", "X-Tenant-Id": DEFAULT_TENANT_ID}
    r2 = await client.get("/api/v1/settings/leads/meta/self-serve-onboarding", headers=adm_headers)
    assert r2.status_code == 200, r2.text
    assert r2.json().get("meta_leads_context_redirected") is False


@pytest.mark.anyio
async def test_meta_lead_form_mapping_crud(client, manager_headers, tenant_id):
    form_id = f"test-form-{uuid.uuid4().hex[:8]}"
    page_id = "484113398123847"

    list_resp = await client.get("/api/v1/settings/leads/meta/forms", headers=manager_headers)
    assert list_resp.status_code == 200, list_resp.text
    assert "tenant_fallback_rules_count" in list_resp.json()

    get_empty = await client.get(
        f"/api/v1/settings/leads/meta/forms/{form_id}/mapping",
        headers=manager_headers,
        params={"page_id": page_id, "source": "meta"},
    )
    assert get_empty.status_code == 200, get_empty.text
    body = get_empty.json()
    assert body["inherits_tenant_fallback"] is True

    put_resp = await client.put(
        f"/api/v1/settings/leads/meta/forms/{form_id}/mapping",
        headers=manager_headers,
        json={
            "page_id": page_id,
            "source": "meta",
            "form_name": "Test Form",
            "mapping_rules": [
                {"source": "phone_number", "target": "phone", "format": "phone"},
            ],
        },
    )
    assert put_resp.status_code == 410, put_resp.text
    detail = put_resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "meta_lead_mapping_writes_retired"
    assert "/app/marketing/sources" in str(detail.get("mapping_path") or "")

    still_empty = await client.get(
        f"/api/v1/settings/leads/meta/forms/{form_id}/mapping",
        headers=manager_headers,
        params={"page_id": page_id, "source": "meta"},
    )
    assert still_empty.status_code == 200, still_empty.text
    assert still_empty.json()["inherits_tenant_fallback"] is True
