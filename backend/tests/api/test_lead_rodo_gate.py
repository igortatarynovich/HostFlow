"""Lead-stage RODO gate (P0): process / request_info / contacted blocked until art.14 satisfied."""

from __future__ import annotations

import json
import uuid

import pytest

from backend.app.core.settings import settings
from backend.app.db.session import async_session_maker
from backend.app.models.legal_document import LegalDocument
from backend.tests.api.lead_rodo_test_utils import satisfy_lead_rodo_via_source_for_tests
from backend.tests.api.test_leads_meta import (
    _ensure_company,
    _ensure_meta_settings,
    _ensure_vacancy,
    _meta_payload,
    _signature_for_payload,
)


async def _seed_active_rodo_clause(db, tenant_id: str) -> None:
    doc = LegalDocument(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        type="rodo_clause",
        version_id=f"test-rodo-{uuid.uuid4().hex[:8]}",
        content_url="https://example.com/rodo",
        is_active=True,
    )
    db.add(doc)
    await db.flush()


@pytest.mark.anyio
async def test_process_without_rodo_returns_lead_rodo_required(client, manager_headers, tenant_id):
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
    ad_numeric = 9_900_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "rodo_gate"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"rodo-gate-{u}@example.com",
        phone=f"+48199{u[:9]}",
        lead_id=f"lg-rodo-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    conf = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 422, proc.text
    assert proc.json().get("detail", {}).get("code") == "LEAD_RODO_REQUIRED"


@pytest.mark.anyio
async def test_request_info_without_rodo_returns_lead_rodo_required(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_910_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "x"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"ri-rodo-{u}@example.com",
        phone=f"+48198{u[:9]}",
        lead_id=f"lg-ri-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    ri = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "request_info", "note": "need dl"},
    )
    assert ri.status_code == 422, ri.text
    assert ri.json().get("detail", {}).get("code") == "LEAD_RODO_REQUIRED"


@pytest.mark.anyio
async def test_reject_without_rodo_ok(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_920_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "x"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"rej-rodo-{u}@example.com",
        phone=f"+48197{u[:9]}",
        lead_id=f"lg-rej-rodo-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    dec = await client.post(
        f"/api/v1/leads/{lead_id}/intake-decision",
        headers=manager_headers,
        json={"decision": "reject", "reason_code": "not_interested"},
    )
    assert dec.status_code == 200, dec.text


@pytest.mark.anyio
async def test_send_rodo_and_process_ok(client, manager_headers, tenant_id):
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
        await _seed_active_rodo_clause(session, tenant_id)
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_930_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "send"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"send-rodo-{u}@example.com",
        phone=f"+48196{u[:9]}",
        lead_id=f"lg-send-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    conf = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text

    send = await client.post(f"/api/v1/leads/{lead_id}/compliance/rodo/send", headers=manager_headers)
    assert send.status_code == 200, send.text

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 200, proc.text
    assert proc.json().get("candidate_id")


@pytest.mark.anyio
async def test_source_provided_then_process_ok(client, manager_headers, tenant_id):
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
    ad_numeric = 9_940_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "src"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"src-rodo-{u}@example.com",
        phone=f"+48195{u[:9]}",
        lead_id=f"lg-src-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    conf = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text

    await satisfy_lead_rodo_via_source_for_tests(client, manager_headers, lead_id)

    proc = await client.post(f"/api/v1/leads/{lead_id}/process", headers=manager_headers)
    assert proc.status_code == 200, proc.text
    assert proc.json().get("candidate_id")


@pytest.mark.anyio
async def test_confirm_vacancy_without_rodo_ok(client, manager_headers, tenant_id):
    """Internal routing only — vacancy confirm must not require art.14."""
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_960_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "vac-no-rodo"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"vac-nr-{u}@example.com",
        phone=f"+48193{u[:9]}",
        lead_id=f"lg-vac-nr-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    conf = await client.post(
        f"/api/v1/leads/{lead_id}/confirm-vacancy",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert conf.status_code == 200, conf.text
    body = conf.json()
    assert body.get("vacancy_routing_confirmed") is True
    norm = body.get("normalized") or {}
    rodo = norm.get("rodo") if isinstance(norm, dict) else None
    assert not rodo or not (isinstance(rodo, dict) and rodo.get("status") in ("sent", "satisfied", "source_provided"))
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_950_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id, "note": "st"},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"st-rodo-{u}@example.com",
        phone=f"+48194{u[:9]}",
        lead_id=f"lg-st-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    patch = await client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert patch.status_code == 422, patch.text
    assert patch.json().get("detail", {}).get("code") == "LEAD_RODO_REQUIRED"
