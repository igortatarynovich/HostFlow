"""GDPR notice delivery: tenant SMTP first, platform mailbox fallback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.communications.prepare_send import deliver_gdpr_notice_email
from backend.app.services.lead_lifecycle_email_policy import PLATFORM_RODO_FROM_EMAIL


@pytest.mark.asyncio
async def test_gdpr_notice_uses_tenant_smtp_when_configured(monkeypatch) -> None:
    cfg = SimpleNamespace(smtp_host="smtp.example.com", from_email="recruiter@danema.pl")
    monkeypatch.setattr(
        "backend.app.services.tenant_email.get_tenant_email_config",
        AsyncMock(return_value=cfg),
    )
    send_tenant = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._default_email_transport",
        send_tenant,
    )
    send_platform = AsyncMock()
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._platform_compliance_email_transport",
        send_platform,
    )

    out = await deliver_gdpr_notice_email(
        SimpleNamespace(),
        tenant_id="t1",
        to="lead@example.com",
        subject="RODO",
        body="Hello",
    )
    assert out["via"] == "tenant_smtp"
    assert out["from_email"] == "recruiter@danema.pl"
    assert out["attempts"][0]["ok"] is True
    send_tenant.assert_awaited_once()
    send_platform.assert_not_awaited()


@pytest.mark.asyncio
async def test_gdpr_notice_falls_back_when_tenant_smtp_fails(monkeypatch) -> None:
    cfg = SimpleNamespace(smtp_host="smtp.example.com", from_email="recruiter@danema.pl")
    monkeypatch.setattr(
        "backend.app.services.tenant_email.get_tenant_email_config",
        AsyncMock(return_value=cfg),
    )
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._default_email_transport",
        AsyncMock(side_effect=ValueError("TENANT_EMAIL_NOT_CONFIGURED")),
    )
    send_platform = AsyncMock()
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._platform_compliance_email_transport",
        send_platform,
    )

    out = await deliver_gdpr_notice_email(
        SimpleNamespace(),
        tenant_id="t1",
        to="lead@example.com",
        subject="RODO",
        body="Hello",
    )
    assert out["via"] == "platform_smtp"
    assert out["from_email"] == PLATFORM_RODO_FROM_EMAIL
    assert out["attempts"][-1]["via"] == "platform_smtp"
    assert out["attempts"][-1]["ok"] is True
    send_platform.assert_awaited_once()


@pytest.mark.asyncio
async def test_gdpr_notice_platform_when_no_tenant_sender(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.tenant_email.get_tenant_email_config",
        AsyncMock(return_value=None),
    )
    send_platform = AsyncMock()
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._platform_compliance_email_transport",
        send_platform,
    )

    out = await deliver_gdpr_notice_email(
        SimpleNamespace(),
        tenant_id="t1",
        to="lead@example.com",
        subject="RODO",
        body="Hello",
    )
    assert out["via"] == "platform_smtp"
    send_platform.assert_awaited_once()


@pytest.mark.asyncio
async def test_gdpr_notice_both_smtp_fail_is_exhausted_not_silent(monkeypatch) -> None:
    from backend.app.communications.send_communication import SendCommunicationError

    cfg = SimpleNamespace(smtp_host="smtp.example.com", from_email="recruiter@danema.pl")
    monkeypatch.setattr(
        "backend.app.services.tenant_email.get_tenant_email_config",
        AsyncMock(return_value=cfg),
    )
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._default_email_transport",
        AsyncMock(side_effect=ValueError("smtp down")),
    )
    monkeypatch.setattr(
        "backend.app.communications.prepare_send._platform_compliance_email_transport",
        AsyncMock(
            side_effect=SendCommunicationError(
                "Platform compliance email failed",
                details={"reason": "system_email_send_failed"},
            )
        ),
    )

    with pytest.raises(SendCommunicationError) as ei:
        await deliver_gdpr_notice_email(
            SimpleNamespace(),
            tenant_id="t1",
            to="lead@example.com",
            subject="RODO",
            body="Hello",
        )
    assert ei.value.details["reason"] == "gdpr_notice_delivery_exhausted"
    attempts = ei.value.details["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["via"] == "tenant_smtp" and attempts[0]["ok"] is False
    assert attempts[1]["via"] == "platform_smtp" and attempts[1]["ok"] is False
