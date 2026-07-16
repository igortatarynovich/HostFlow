"""Questionnaire invite email send (B-1 email slice)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.communication_delivery import CommunicationDelivery
from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
from backend.tests.api.test_sales_targeted_advertising_intake import (
    _create_meta_client_lead,
    _seed_sales_profile,
)


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr("backend.app.services.intake_form_write_service.ensure_lead_source_limit", _noop)
    monkeypatch.setattr("backend.app.services.intake_form_write_service.count_tenant_lead_sources", _zero)
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


async def _seed_smtp(tenant_id: str) -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.models import TenantEmailConfig

    async with async_session_maker() as db:
        existing = await db.scalar(
            select(TenantEmailConfig).where(TenantEmailConfig.tenant_id == str(tenant_id)).limit(1)
        )
        if existing:
            existing.smtp_host = "smtp.example.test"
            existing.from_email = "sales@example.test"
            existing.is_active = True
        else:
            db.add(
                TenantEmailConfig(
                    tenant_id=str(tenant_id),
                    smtp_host="smtp.example.test",
                    smtp_port=587,
                    from_email="sales@example.test",
                    from_name="Sales",
                    use_tls=True,
                    is_active=True,
                )
            )
        await db.commit()


@pytest.mark.asyncio
async def test_questionnaire_email_preview_and_send_reuses_invite(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.db.session import async_session_maker

    await _seed_sales_profile(tenant_id)
    await _seed_smtp(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    async with async_session_maker() as db:
        row = await db.get(type(lead), lead.id)
        assert row is not None
        normalized = dict(row.normalized or {})
        normalized["email"] = "client@example.test"
        normalized["full_name"] = "Jan Kowalski"
        row.normalized = normalized
        await db.commit()

    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "backend.app.services.communication_deliveries.questionnaire_email.send_email_for_tenant",
        send_mock,
    )

    preview = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "pl"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["subject"] == "Kilka pytań dotyczących współpracy"
    assert "lang=pl" in body["questionnaire_url"]
    assert "{{" not in body["body"]
    assert "Jan Kowalski" in body["body"]
    assert body["recipient_email"] == "client@example.test"
    token = body["invite"]["token"]
    assert body["invite"]["status"] == "not_sent"

    send = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "pl",
            "recipient_email": "client@example.test",
            "subject": body["subject"],
            "body": body["body"],
        },
    )
    assert send.status_code == 200, send.text
    sent = send.json()
    assert sent["status"] == "sent"
    assert sent["invite"]["token"] == token
    assert sent["invite"]["status"] == "sent"
    send_mock.assert_awaited_once()

    async with async_session_maker() as db:
        row = await db.get(type(lead), lead.id)
        assert row is not None
        assert row.stage == "waiting_for_response"
        assert (row.normalized or {}).get("sales_questionnaire_status") == "sent"
        from backend.app.modules.applications.mappers import lead_to_sales_inquiry

        assert lead_to_sales_inquiry(row).status == "waiting"

    # Second send reuses the same invite token.
    preview2 = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "en"},
    )
    assert preview2.status_code == 200, preview2.text
    assert preview2.json()["invite"]["token"] == token
    assert "lang=en" in preview2.json()["questionnaire_url"]
    assert preview2.json()["subject"] == "A few questions about your request"

    send2 = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "en",
            "recipient_email": "client@example.test",
            "subject": preview2.json()["subject"],
            "body": preview2.json()["body"],
        },
    )
    assert send2.status_code == 200, send2.text
    assert send2.json()["invite"]["token"] == token

    async with async_session_maker() as db:
        invites = (
            await db.execute(
                select(LeadQuestionnaireInvite).where(LeadQuestionnaireInvite.lead_id == lead_id)
            )
        ).scalars().all()
        assert len(invites) == 1
        deliveries = (
            await db.execute(
                select(CommunicationDelivery).where(
                    CommunicationDelivery.entity_id == lead_id,
                    CommunicationDelivery.channel == "email",
                )
            )
        ).scalars().all()
        assert len(deliveries) >= 2


@pytest.mark.asyncio
async def test_questionnaire_email_requires_smtp(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.models import TenantEmailConfig

    await _seed_sales_profile(tenant_id)
    # Ensure no active SMTP row from other tests sharing this tenant.
    async with async_session_maker() as db:
        rows = (
            await db.execute(select(TenantEmailConfig).where(TenantEmailConfig.tenant_id == str(tenant_id)))
        ).scalars().all()
        for row in rows:
            row.is_active = False
            row.smtp_host = None
        await db.commit()

    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    monkeypatch.setattr(
        "backend.app.services.communication_deliveries.questionnaire_email.send_email_for_tenant",
        AsyncMock(side_effect=ValueError("TENANT_EMAIL_NOT_CONFIGURED")),
    )

    preview = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "ru", "recipient_email": "x@example.test"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["email_configured"] is False
    assert preview.json()["subject"] == "Несколько вопросов по вашему обращению"

    send = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "ru",
            "recipient_email": "x@example.test",
            "subject": preview.json()["subject"],
            "body": preview.json()["body"],
        },
    )
    assert send.status_code == 422, send.text
    assert send.json()["detail"]["code"] == "email_not_configured"

    async with async_session_maker() as db:
        invite = await db.scalar(
            select(LeadQuestionnaireInvite).where(LeadQuestionnaireInvite.lead_id == lead_id).limit(1)
        )
        assert invite is not None
        assert invite.status == "not_sent"


@pytest.mark.asyncio
async def test_questionnaire_email_signature_uses_sender_not_client_company(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.models import User
    from backend.app.models.own_company import OwnCompany

    await _seed_sales_profile(tenant_id)
    await _seed_smtp(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    async with async_session_maker() as db:
        own = await db.scalar(
            select(OwnCompany)
            .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own is not None
        own.name = "Focus Personnel"
        admin = await db.scalar(
            select(User).where(func.lower(User.email) == "biuro@work-host.com").limit(1)
        )
        assert admin is not None
        admin.full_name = "Игорь Татаринович"
        extra = dict(admin.extra or {})
        profile = dict(extra.get("profile") or {})
        profile["signature"] = {
            "first_name": "Igor",
            "last_name": "Tatarynovich",
            "position": "Founder & CEO",
            "phone": "+48 504 004 622",
            "email": "info@hostflow.cc",
            "company": "Focus Personnel",
            "website": "focuspersonnel.pl",
            "show_phone": True,
            "show_email": True,
            "show_website": True,
        }
        extra["profile"] = profile
        admin.extra = extra
        flag_modified(admin, "extra")
        row = await db.get(type(lead), lead.id)
        assert row is not None
        normalized = dict(row.normalized or {})
        normalized["email"] = "client@example.test"
        normalized["full_name"] = "Jan Kowalski"
        normalized["company_name"] = "paks transport"
        row.normalized = normalized
        await db.commit()

    preview = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "en"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["subject"] == "A few questions about your request"
    assert "Kind regards," in body["body"]
    assert "Igor Tatarynovich" in body["body"]
    assert "Founder & CEO" in body["body"]
    assert "Игорь" not in body["body"]
    assert "Focus Personnel" in body["body"]
    assert "paks transport" not in body["body"].lower()
    assert "🌐 focuspersonnel.pl" in body["body"] or "↗ focuspersonnel.pl" in body["body"]
    assert "✉ info@hostflow.cc" in body["body"]
    assert "📞 +48 504 004 622" in body["body"] or "☎ +48 504 004 622" in body["body"]
    assert body["body"].rstrip().endswith("logo_hf.svg")
    assert "lang=en" in body["questionnaire_url"]


@pytest.mark.asyncio
async def test_questionnaire_email_send_ignores_stale_client_signature(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.models import User
    from backend.app.models.own_company import OwnCompany

    await _seed_sales_profile(tenant_id)
    await _seed_smtp(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    async with async_session_maker() as db:
        own = await db.scalar(
            select(OwnCompany)
            .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own is not None
        own.name = "Focus Personnel"
        admin = await db.scalar(
            select(User).where(func.lower(User.email) == "biuro@work-host.com").limit(1)
        )
        assert admin is not None
        extra = dict(admin.extra or {})
        profile = dict(extra.get("profile") or {})
        profile["signature"] = {
            "first_name": "Igor",
            "last_name": "Tatarynovich",
            "position": "Founder & CEO",
            "phone": "+48 504 004 622",
            "email": "info@hostflow.cc",
            "company": "Focus Personnel",
            "website": "focuspersonnel.pl",
            "show_phone": True,
            "show_email": True,
            "show_website": True,
        }
        extra["profile"] = profile
        admin.extra = extra
        flag_modified(admin, "extra")
        row = await db.get(type(lead), lead.id)
        assert row is not None
        normalized = dict(row.normalized or {})
        normalized["email"] = "client@example.test"
        normalized["full_name"] = "Jan Kowalski"
        row.normalized = normalized
        await db.commit()

    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "backend.app.services.communication_deliveries.questionnaire_email.send_email_for_tenant",
        send_mock,
    )

    preview = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "pl"},
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()["body"]
    stale_body = preview_body.replace("Z poważaniem,", "Pozdrawiam,")

    send = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "pl",
            "recipient_email": "client@example.test",
            "subject": preview.json()["subject"],
            "body": stale_body,
        },
    )
    assert send.status_code == 200, send.text
    send_mock.assert_awaited_once()
    sent_kwargs = send_mock.await_args.kwargs
    sent_body = sent_kwargs["body"]
    assert "Z poważaniem," in sent_body
    assert "Pozdrawiam," not in sent_body
    assert sent_body.rstrip().endswith("logo_hf.svg")
    html_body = sent_kwargs.get("html_body") or ""
    assert "Z poważaniem" in html_body
    assert 'width="180"' in html_body
    assert "#2e7070" in html_body
    assert "Pozdrawiam" not in html_body


@pytest.mark.asyncio
async def test_questionnaire_email_mints_new_invite_after_submitted(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.db.session import async_session_maker

    await _seed_sales_profile(tenant_id)
    await _seed_smtp(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    async with async_session_maker() as db:
        row = await db.get(type(lead), lead.id)
        assert row is not None
        normalized = dict(row.normalized or {})
        normalized["email"] = "client@example.test"
        normalized["full_name"] = "Jan Kowalski"
        row.normalized = normalized
        await db.commit()

    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "backend.app.services.communication_deliveries.questionnaire_email.send_email_for_tenant",
        send_mock,
    )

    preview = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "pl"},
    )
    assert preview.status_code == 200, preview.text
    first_token = preview.json()["invite"]["token"]

    send = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "pl",
            "recipient_email": "client@example.test",
            "subject": preview.json()["subject"],
            "body": preview.json()["body"],
        },
    )
    assert send.status_code == 200, send.text

    async with async_session_maker() as db:
        invite = await db.scalar(
            select(LeadQuestionnaireInvite)
            .where(LeadQuestionnaireInvite.lead_id == lead_id)
            .limit(1)
        )
        assert invite is not None
        invite.status = "submitted"
        invite.submitted_at = invite.sent_at
        row = await db.get(type(lead), lead.id)
        assert row is not None
        normalized = dict(row.normalized or {})
        normalized["sales_questionnaire_status"] = "submitted"
        normalized["sales_questionnaire"] = {"note": "previous answers"}
        row.normalized = normalized
        await db.commit()

    preview2 = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/preview",
        headers=manager_headers,
        json={"form_locale": "en"},
    )
    assert preview2.status_code == 200, preview2.text
    body2 = preview2.json()
    assert body2["clarification_required"] is True
    assert body2["invite_reused"] is False
    assert body2["invite"]["token"] != first_token
    assert body2["invite"]["status"] == "not_sent"
    assert "lang=en" in body2["questionnaire_url"]
    assert first_token not in body2["questionnaire_url"]

    send2 = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "en",
            "recipient_email": "client@example.test",
            "subject": body2["subject"],
            "body": body2["body"],
        },
    )
    assert send2.status_code == 200, send2.text
    assert send2.json()["invite"]["token"] == body2["invite"]["token"]
    assert send2.json()["invite"]["status"] == "sent"

    async with async_session_maker() as db:
        invites = (
            await db.execute(
                select(LeadQuestionnaireInvite)
                .where(LeadQuestionnaireInvite.lead_id == lead_id)
                .order_by(LeadQuestionnaireInvite.created_at.asc())
            )
        ).scalars().all()
        assert len(invites) == 2
        assert invites[0].token == first_token
        assert invites[0].status == "submitted"
        assert invites[1].token == body2["invite"]["token"]
        assert invites[1].status == "sent"
        row = await db.get(type(lead), lead.id)
        assert row is not None
        # Prior answers stay on the lead history blob.
        assert (row.normalized or {}).get("sales_questionnaire", {}).get("note") == "previous answers"
        assert (row.normalized or {}).get("sales_questionnaire_status") == "sent"
        assert row.stage == "waiting_for_response"


@pytest.mark.asyncio
async def test_questionnaire_email_send_failure_does_not_mark_sent(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_sales_profile(tenant_id)
    await _seed_smtp(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    monkeypatch.setattr(
        "backend.app.services.communication_deliveries.questionnaire_email.send_email_for_tenant",
        AsyncMock(side_effect=RuntimeError("SMTP timeout")),
    )

    send = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite/email/send",
        headers=manager_headers,
        json={
            "form_locale": "pl",
            "recipient_email": "client@example.test",
            "subject": "Temat",
            "body": "Treść z linkiem",
        },
    )
    assert send.status_code == 502, send.text
    assert send.json()["detail"]["code"] == "send_failed"

    from backend.app.db.session import async_session_maker

    async with async_session_maker() as db:
        invite = await db.scalar(
            select(LeadQuestionnaireInvite).where(LeadQuestionnaireInvite.lead_id == lead_id).limit(1)
        )
        assert invite is not None
        assert invite.status == "not_sent"
