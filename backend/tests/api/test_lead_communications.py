"""Lead operational communication emails (separate from RODO).

C5: Lead-scoped autosends without a Sales/Recruitment destination remain
fail-closed (``communication_pipeline_required``). ADR-031 PR-4 auto-binds
Pipeline when destination is known.
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
from backend.app.services.lead_communications import (
    COMMUNICATION_NORMALIZED_KEY,
    EVENT_APPLICATION_RECEIVED,
    EVENT_MOVING_FORWARD,
    communication_event_sent,
)
from backend.tests.api.test_leads_meta import (
    _ensure_company,
    _ensure_meta_settings,
    _ensure_vacancy,
    _meta_payload,
    _signature_for_payload,
)


async def _enable_communication_flags(client, manager_headers, **flags: bool) -> None:
    body: dict[str, Any] = {
        "lead_communication_enabled": True,
        "send_application_received": True,
        "send_rejection_notice": True,
        "send_moving_forward_notice": True,
    }
    body.update(flags)
    res = await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json=body,
    )
    assert res.status_code == 200, res.text


async def _comm_block(tenant_id: str, lead_id: str) -> dict[str, Any]:
    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert str(lead.tenant_id) == str(tenant_id)
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw = norm.get(COMMUNICATION_NORMALIZED_KEY)
        return raw if isinstance(raw, dict) else {}


@pytest.mark.anyio
async def test_application_received_skipped_without_destination_pipeline(
    tenant_id, monkeypatch
):
    """C5: without Sales/Recruitment destination resolve, ops stay fail-closed."""
    sent: List[dict[str, Any]] = []

    async def _fake_send(*_args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_send,
    )
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

    from types import SimpleNamespace

    from backend.app.services.lead_communications import maybe_send_lead_communication

    cfg = type(
        "Cfg",
        (),
        {
            "enabled": True,
            "send_application_received": True,
            "send_rejection_notice": True,
            "send_moving_forward_notice": True,
            "application_received_subject": None,
            "application_received_body": None,
            "rejection_notice_subject": None,
            "rejection_notice_body": None,
            "moving_forward_subject": None,
            "moving_forward_body": None,
            "application_received_template_id": None,
            "rejection_notice_template_id": None,
            "moving_forward_template_id": None,
        },
    )()
    monkeypatch.setattr(
        "backend.app.services.lead_communications.get_lead_communication_settings",
        AsyncMock(return_value=cfg),
    )
    monkeypatch.setattr("backend.app.services.lead_communications.log_audit_event", AsyncMock())
    monkeypatch.setattr("backend.app.services.lead_communications.flag_modified", lambda *_a, **_k: None)

    lead = SimpleNamespace(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        normalized={"email": "c5-skip@example.com", "first_name": "Skip"},
    )
    db = AsyncMock()
    db.flush = AsyncMock()
    ok = await maybe_send_lead_communication(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        event_type=EVENT_APPLICATION_RECEIVED,
        cfg=cfg,
    )
    assert ok is False
    assert len(sent) == 0
    block = (lead.normalized or {}).get(COMMUNICATION_NORMALIZED_KEY) or {}
    rec = block.get(EVENT_APPLICATION_RECEIVED) or {}
    assert rec.get("status") == "skipped"
    assert rec.get("failure_reason") == "communication_pipeline_required"


@pytest.mark.anyio
async def test_replay_does_not_reach_transport_without_pipeline(
    client, manager_headers, tenant_id, monkeypatch
):
    sent: List[dict[str, Any]] = []

    async def _fake_send(*_args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_send,
    )
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
    await _enable_communication_flags(client, manager_headers)

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_951_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"comm-replay-{u}@example.com",
        phone=f"+48190{u[:9]}",
        lead_id=f"lg-comm-replay-{u}",
        ad_id=str(ad_numeric),
    )
    headers = {**manager_headers, "X-Hub-Signature-256": _signature_for_payload(payload)}
    first = await client.post("/api/v1/leads/meta", headers=headers, content=json.dumps(payload))
    second = await client.post("/api/v1/leads/meta", headers=headers, content=json.dumps(payload))
    assert first.status_code == 200 and second.status_code == 200
    assert len(sent) == 0


@pytest.mark.anyio
async def test_no_email_still_skips_pipeline_first(tenant_id, monkeypatch):
    """Without destination pipeline resolve, C5 skips before the no-email channel check."""
    from types import SimpleNamespace

    sent: List[dict[str, Any]] = []

    async def _fake_send(*_args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_send,
    )
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

    from backend.app.services.lead_communications import maybe_send_lead_communication

    cfg = type(
        "Cfg",
        (),
        {
            "enabled": True,
            "send_application_received": True,
            "send_rejection_notice": True,
            "send_moving_forward_notice": True,
            "application_received_subject": None,
            "application_received_body": None,
            "rejection_notice_subject": None,
            "rejection_notice_body": None,
            "moving_forward_subject": None,
            "moving_forward_body": None,
            "application_received_template_id": None,
            "rejection_notice_template_id": None,
            "moving_forward_template_id": None,
        },
    )()
    monkeypatch.setattr(
        "backend.app.services.lead_communications.get_lead_communication_settings",
        AsyncMock(return_value=cfg),
    )
    monkeypatch.setattr("backend.app.services.lead_communications.log_audit_event", AsyncMock())
    monkeypatch.setattr("backend.app.services.lead_communications.flag_modified", lambda *_a, **_k: None)

    lead = SimpleNamespace(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        normalized={"first_name": "NoMail"},
    )
    db = AsyncMock()
    db.flush = AsyncMock()
    ok = await maybe_send_lead_communication(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        event_type=EVENT_APPLICATION_RECEIVED,
        cfg=cfg,
    )
    assert ok is False
    assert len(sent) == 0
    block = (lead.normalized or {}).get(COMMUNICATION_NORMALIZED_KEY) or {}
    rec = block.get(EVENT_APPLICATION_RECEIVED) or {}
    assert rec.get("status") == "skipped"
    assert rec.get("failure_reason") == "communication_pipeline_required"


@pytest.mark.anyio
async def test_disabled_tenant_setting_does_not_send(client, manager_headers, tenant_id, monkeypatch):
    sent: List[dict[str, Any]] = []

    async def _fake_send(*_args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_send,
    )
    await client.patch(
        "/api/v1/settings/leads/settings",
        headers=manager_headers,
        json={
            "lead_communication_enabled": False,
            "send_application_received": True,
            "lead_rodo_send_mode": "manual",
        },
    )

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_953_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"comm-off-{u}@example.com",
        phone=f"+48188{u[:9]}",
        lead_id=f"lg-comm-off-{u}",
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
        assert not communication_event_sent(lead.normalized, EVENT_APPLICATION_RECEIVED)
    assert len(sent) == 0


@pytest.mark.anyio
async def test_reject_skips_without_pipeline(client, manager_headers, tenant_id, monkeypatch):
    sent: List[dict[str, Any]] = []

    async def _fake_send(*_args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_send,
    )
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
    await _enable_communication_flags(client, manager_headers, send_application_received=False)

    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        await _ensure_meta_settings(session, tenant_id, str(settings.meta_webhook_secret or "test-secret"))
        await session.commit()

    u = uuid.uuid4().hex[:12]
    ad_numeric = 9_954_000_000 + (uuid.uuid4().int % 99_000_000)
    await client.post(
        "/api/v1/settings/leads/mapping",
        headers=manager_headers,
        json={"ad_id": ad_numeric, "vacancy_id": vacancy_id},
    )
    payload = _meta_payload(
        vacancy_id,
        email=f"comm-rej-{u}@example.com",
        phone=f"+48187{u[:9]}",
        lead_id=f"lg-comm-rej-{u}",
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
    block = await _comm_block(tenant_id, lead_id)
    assert block.get("lead_rejected", {}).get("status") == "skipped"
    assert len(sent) == 0


@pytest.mark.anyio
async def test_moving_forward_skipped_without_destination_pipeline(tenant_id, monkeypatch):
    """C5 / ADR-031 PR-5: moving_forward stays fail-closed without destination."""
    sent: List[dict[str, Any]] = []

    async def _fake_send(*_args, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(
        "backend.app.communications.prepare_send.prepare_and_send_communication",
        _fake_send,
    )
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

    from types import SimpleNamespace

    from backend.app.services.lead_communications import maybe_send_lead_communication

    cfg = type(
        "Cfg",
        (),
        {
            "enabled": True,
            "send_application_received": False,
            "send_rejection_notice": False,
            "send_moving_forward_notice": True,
            "application_received_subject": None,
            "application_received_body": None,
            "rejection_notice_subject": None,
            "rejection_notice_body": None,
            "moving_forward_subject": None,
            "moving_forward_body": None,
            "application_received_template_id": None,
            "rejection_notice_template_id": None,
            "moving_forward_template_id": None,
        },
    )()
    monkeypatch.setattr(
        "backend.app.services.lead_communications.get_lead_communication_settings",
        AsyncMock(return_value=cfg),
    )
    monkeypatch.setattr("backend.app.services.lead_communications.log_audit_event", AsyncMock())
    monkeypatch.setattr("backend.app.services.lead_communications.flag_modified", lambda *_a, **_k: None)

    lead = SimpleNamespace(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        normalized={"email": "mv-skip@example.com", "first_name": "Move"},
    )
    db = AsyncMock()
    db.flush = AsyncMock()
    ok = await maybe_send_lead_communication(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        event_type=EVENT_MOVING_FORWARD,
        cfg=cfg,
    )
    assert ok is False
    assert len(sent) == 0
    block = (lead.normalized or {}).get(COMMUNICATION_NORMALIZED_KEY) or {}
    rec = block.get(EVENT_MOVING_FORWARD) or {}
    assert rec.get("status") == "skipped"
    assert rec.get("failure_reason") == "communication_pipeline_required"
