"""Intake Resolution MVP §1: manual vacancy confirmation + process bypass."""

import json
import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models import Lead
from backend.app.core.settings import settings
from backend.tests.api.test_leads_meta import (
    _ensure_company,
    _ensure_meta_settings,
    _ensure_vacancy,
    _meta_payload,
    _signature_for_payload,
)


@pytest.mark.anyio
async def test_confirm_vacancy_then_process_assisted(client, manager_headers, tenant_id):
    patch_settings = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"auto_create_enabled": True, "leads_processing_mode_v1": "assisted"},
    )
    assert patch_settings.status_code == 200, patch_settings.text

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    leadgen = f"lg-confirm-{u}"
    ad_numeric = 9_000_000_000 + (uuid.uuid4().int % 99_000_000)
    map_resp = await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "test_vacancy_confirm"},
    )
    assert map_resp.status_code == 201, map_resp.text

    payload = _meta_payload(
        vacancy_id,
        email=f"confirm-{u}@example.com",
        phone=f"+48133{u[:9]}",
        lead_id=leadgen,
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    body = ingest.json()
    assert body["status"] == "needs_routing"
    assert body.get("candidate_id") is None
    lead_id = body["lead_id"]

    detail_before = await client.get(f"/api/v1/leads/{lead_id}", headers=manager_headers)
    assert detail_before.status_code == 200
    row = detail_before.json()
    assert row.get("vacancy_routing_confirmed") is False

    conf = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text
    confirmed = conf.json()
    assert confirmed.get("vacancy_routing_confirmed") is True
    norm = confirmed.get("normalized") or {}
    assert isinstance(norm.get("intake_vacancy_confirm_v1"), dict)
    assert str(norm["intake_vacancy_confirm_v1"].get("vacancy_id")) == str(vacancy_id)

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 200, proc.text
    out = proc.json()
    assert out["status"] == "processed"
    assert out.get("candidate_id") is not None

    async with async_session_maker() as session:
        lead_row = await session.get(Lead, lead_id)
        assert lead_row is not None
        assert lead_row.status == "processed"


@pytest.mark.anyio
async def test_confirm_vacancy_rejects_wrong_source(client, manager_headers, tenant_id):
    """Non-meta/csv_import leads cannot use confirm-vacancy."""
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        lead_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO leads (
                  id, tenant_id, company_id, vacancy_id, source, lead_type, payload, normalized,
                  status, external_id, created_at
                )
                VALUES (
                  :id, :tenant_id, :company_id, NULL, 'manual', 'candidate',
                  CAST(:payload AS jsonb), CAST(:normalized AS jsonb),
                  'needs_routing', :ext, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": lead_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "payload": "{}",
                "normalized": "{}",
                "ext": f"manual-{lead_id[:8]}",
            },
        )
        await session.commit()

    resp = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert resp.status_code == 422
    assert "LEAD_SOURCE_NOT_CONFIRMABLE" in resp.text
