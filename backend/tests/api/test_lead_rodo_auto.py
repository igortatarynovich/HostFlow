"""Lead RODO auto-send on ingest (tenant setting lead_rodo_v1).

ADR-031: delivery via Communication Pipeline only (no Lead SMTP).
"""

from __future__ import annotations

import json
import uuid
from typing import Any, List
from unittest.mock import AsyncMock

import pytest

from backend.app.core.settings import settings
from backend.app.db.session import async_session_maker
from backend.app.models.lead import Lead
from backend.app.models.legal_document import LegalDocument
from backend.app.services.lead_rodo import lead_rodo_notice_status_from_normalized, lead_rodo_sent_from_normalized
from backend.app.services.lead_rodo_auto import apply_lead_rodo_on_ingest
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


async def _lead_rodo_block(tenant_id: str, lead_id: str) -> dict[str, Any]:
    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert str(lead.tenant_id) == str(tenant_id)
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw = norm.get("rodo")
        return raw if isinstance(raw, dict) else {}


@pytest.mark.anyio
async def test_auto_on_lead_created_sends_rodo(client, manager_headers, tenant_id, monkeypatch):
    sent: List[Any] = []

    async def _fake_prepare(*_args, **_kwargs):
        sent.append(True)
        return None

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_prepare,
    )

    patch = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"lead_rodo_send_mode": "auto_on_lead_created"},
    )
    assert patch.status_code == 200, patch.text

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await _seed_active_rodo_clause(session, tenant_id)
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_940_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    email = f"auto-rodo-{u}@example.com"
    payload = _meta_payload(
        vacancy_id,
        email=email,
        phone=f"+48195{u[:9]}",
        lead_id=f"lg-auto-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    rodo = await _lead_rodo_block(tenant_id, lead_id)
    assert rodo.get("status") == "sent"
    assert rodo.get("delivery") == "communication_pipeline"
    assert rodo.get("auto_trigger") == "lead_created"
    assert len(sent) == 1


@pytest.mark.anyio
async def test_meta_webhook_replay_does_not_send_rodo_twice(client, manager_headers, tenant_id, monkeypatch):
    sent: List[Any] = []

    async def _fake_prepare(*_args, **_kwargs):
        sent.append(True)
        return None

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_prepare,
    )

    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"lead_rodo_send_mode": "auto_on_lead_created"},
    )

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await _seed_active_rodo_clause(session, tenant_id)
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_941_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    lead_ext = f"lg-replay-{u}"
    payload = _meta_payload(
        vacancy_id,
        email=f"replay-rodo-{u}@example.com",
        phone=f"+48194{u[:9]}",
        lead_id=lead_ext,
        ad_id=str(ad_numeric),
    )
    headers = {**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)}
    first = await client.post("/api/v1/leads/meta", headers=headers, content=json.dumps(payload))
    second = await client.post("/api/v1/leads/meta", headers=headers, content=json.dumps(payload))
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["lead_id"] == second.json()["lead_id"]
    assert len(sent) == 1


@pytest.mark.anyio
async def test_auto_on_lead_created_no_email_sets_pending_channel(
    client, manager_headers, tenant_id, monkeypatch
):
    sent: List[Any] = []

    async def _fake_prepare(*_args, **_kwargs):
        sent.append(True)
        return None

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_prepare,
    )

    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"lead_rodo_send_mode": "auto_on_lead_created"},
    )

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await _seed_active_rodo_clause(session, tenant_id)
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_942_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    payload = _meta_payload(
        vacancy_id,
        email="",
        phone=f"+48193{u[:9]}",
        lead_id=f"lg-noemail-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert lead_rodo_notice_status_from_normalized(lead.normalized) == "pending_channel"
    assert len(sent) == 0


@pytest.mark.anyio
async def test_manual_mode_does_not_auto_send_on_ingest(client, manager_headers, tenant_id, monkeypatch):
    sent: List[Any] = []

    async def _fake_prepare(*_args, **_kwargs):
        sent.append(True)
        return None

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_prepare,
    )

    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={"lead_rodo_send_mode": "manual"},
    )

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await _seed_active_rodo_clause(session, tenant_id)
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_943_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"manual-rodo-{u}@example.com",
        phone=f"+48192{u[:9]}",
        lead_id=f"lg-manual-{u}",
        ad_id=str(ad_numeric),
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers={**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)},
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    lead_id = ingest.json()["lead_id"]

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert not lead_rodo_sent_from_normalized(lead.normalized)
        assert lead_rodo_notice_status_from_normalized(lead.normalized) == "manual_required"
    assert len(sent) == 0


@pytest.mark.anyio
async def test_ingest_rodo_notice_at_source_skips_outbound_send(tenant_id, monkeypatch):
    sent: List[Any] = []

    async def _fake_prepare(*_args, **_kwargs):
        sent.append(True)
        return None

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_prepare,
    )

    async with async_session_maker() as session:
        from backend.app.modules.leads import crud
        from backend.app.services.lead_rodo_settings import persist_lead_rodo_settings

        await persist_lead_rodo_settings(session, tenant_id, send_mode="auto_on_lead_created")
        company_id = await _ensure_company(session, tenant_id)
        lead = await crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=company_id,
            company_id=company_id,
            vacancy_id=None,
            payload={"email": "pub@example.com"},
            normalized={"email": "pub@example.com", "rodo_notice_at_source": True},
            ad_id=None,
            source="public_form",
            external_id=f"pub-{uuid.uuid4().hex[:8]}",
        )
        await apply_lead_rodo_on_ingest(
            session,
            tenant_id=tenant_id,
            lead=lead,
            source="public_form",
            normalized=lead.normalized,
            is_new_lead=True,
        )
        await session.commit()
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        rodo = norm.get("rodo") if isinstance(norm.get("rodo"), dict) else {}

    assert rodo.get("status") == "source_provided"
    assert len(sent) == 0


@pytest.mark.anyio
async def test_unbound_destination_fail_closed_no_smtp(tenant_id, monkeypatch):
    """ADR-031 PR-5: without Sales/Recruitment destination, RODO does not SMTP."""
    from backend.app.services.lead_rodo import send_lead_rodo_email

    monkeypatch.setattr(
        "backend.app.modules.sales.communication.compliance_pipeline"
        ".resolve_lead_uses_sales_compliance_pipeline",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "backend.app.modules.recruitment.communication.compliance_pipeline"
        ".resolve_lead_uses_recruitment_compliance_pipeline",
        AsyncMock(return_value=False),
    )

    async with async_session_maker() as session:
        from backend.app.modules.leads import crud

        await _seed_active_rodo_clause(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        lead = await crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=company_id,
            company_id=company_id,
            vacancy_id=None,
            payload={"email": "unbound@example.com"},
            normalized={"email": "unbound@example.com", "first_name": "Una"},
            ad_id=None,
            source="manual",
            external_id=f"unb-{uuid.uuid4().hex[:8]}",
        )
        ok, msg = await send_lead_rodo_email(
            session,
            tenant_id=tenant_id,
            lead=lead,
        )
        await session.commit()
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        rodo = norm.get("rodo") if isinstance(norm.get("rodo"), dict) else {}

    assert ok is False
    assert "communication_pipeline_required" in msg
    assert rodo.get("status") == "failed"
    assert rodo.get("failure_reason") == "communication_pipeline_required"
