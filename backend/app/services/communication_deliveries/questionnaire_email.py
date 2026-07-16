"""Send questionnaire invite by email via tenant SMTP."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models import Lead
from backend.app.models.communication_delivery import (
    DELIVERY_CHANNEL_EMAIL,
    DELIVERY_PROVIDER_SMTP,
    DELIVERY_STATUS_ACCEPTED,
    DELIVERY_STATUS_FAILED,
    PURPOSE_QUESTIONNAIRE_INVITE,
    CommunicationDelivery,
)
from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
from backend.app.modules.leads.lead_questionnaire_invite import (
    INVITE_STATUS_SUBMITTED,
    attach_questionnaire_invite_to_lead,
    questionnaire_invite_out_payload,
)
from backend.app.services.audit import log_activity
from backend.app.services.communication_templates import render_template, resolve_template
from backend.app.services.email_signature import (
    append_outgoing_signature,
    append_outgoing_signature_html,
    plain_body_to_html,
    resolve_outgoing_signature,
)
from backend.app.services.tenant_email import get_tenant_email_config, send_email_for_tenant

TEMPLATE_KEY = "questionnaire_invite_email_v1"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class QuestionnaireEmailError(Exception):
    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _trim(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def lead_contact_email(lead: Lead) -> str:
    normalized = _record(lead.normalized)
    payload = _record(lead.payload)
    return (
        _trim(normalized.get("email"))
        or _trim(payload.get("email"))
        or _trim((_record(normalized.get("contact")).get("email")))
        or _trim((_record(payload.get("contact")).get("email")))
    )


def lead_contact_name(lead: Lead) -> str:
    normalized = _record(lead.normalized)
    payload = _record(lead.payload)
    return (
        _trim(normalized.get("full_name"))
        or _trim(normalized.get("contact_name"))
        or _trim(normalized.get("first_name"))
        or _trim(payload.get("full_name"))
        or "—"
    )


def absolute_questionnaire_url(apply_url: str) -> str:
    url = _trim(apply_url)
    if not url:
        return ""
    if re.match(r"^https?://", url, flags=re.I):
        return url
    base = _trim(getattr(settings, "frontend_url", None) or "") or "https://hostflow.cc"
    base = base.rstrip("/")
    return f"{base}{url if url.startswith('/') else '/' + url}"


def normalize_recipient_email(value: str) -> str:
    email = _trim(value).lower()
    if not email or not _EMAIL_RE.match(email):
        raise QuestionnaireEmailError("invalid_email", "Enter a valid recipient email address.")
    return email


def _message_hash(*, subject: str, body: str) -> str:
    raw = f"{subject}\n{body}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class QuestionnaireEmailCompose:
    invite: LeadQuestionnaireInvite | None
    invite_payload: dict[str, Any]
    recipient_email: str
    subject: str
    body: str
    body_html: str
    questionnaire_url: str
    email_configured: bool
    clarification_required: bool
    invite_reused: bool
    locale: str


def _should_mint_new_invite_for_email(lead: Lead, *, force_new_invite: bool) -> bool:
    if force_new_invite:
        return True
    status = _trim((_record(lead.normalized).get("sales_questionnaire_status")))
    return status == INVITE_STATUS_SUBMITTED


async def compose_questionnaire_invite_email(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    form_locale: str | None,
    lead_form_id: str | None = None,
    force_new_invite: bool = False,
    recipient_email: str | None = None,
    actor_user_id: str | None = None,
) -> QuestionnaireEmailCompose:
    if str(getattr(lead, "lead_type", "") or "").lower() != "client":
        raise QuestionnaireEmailError(
            "not_client_lead",
            "Questionnaire email is only available for client leads",
        )

    locale = (_trim(form_locale) or "pl").lower()[:2]
    submitted_before = (
        _trim((_record(lead.normalized).get("sales_questionnaire_status"))) == INVITE_STATUS_SUBMITTED
    )
    mint_new = _should_mint_new_invite_for_email(lead, force_new_invite=force_new_invite)

    from backend.app.modules.leads.lead_questionnaire_invite import (
        find_active_questionnaire_invite_for_lead,
    )

    existing_before = None
    if not mint_new:
        existing_before = await find_active_questionnaire_invite_for_lead(
            db, tenant_id=str(tenant_id), lead_id=str(lead.id)
        )

    try:
        invite = await attach_questionnaire_invite_to_lead(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            mark_sent=False,
            lead_form_id=lead_form_id,
            form_locale=locale,
            create_if_missing=True,
            force_new=mint_new,
        )
    except LookupError as exc:
        raise QuestionnaireEmailError("invite_error", str(exc)) from exc

    # Keep prior sales_questionnaire answers; reset waiting status until this invite is sent.
    if mint_new and submitted_before and invite.status != INVITE_STATUS_SUBMITTED:
        normalized = _record(lead.normalized)
        normalized["sales_questionnaire_status"] = "not_sent"
        lead.normalized = normalized

    invite_reused = bool(existing_before is not None and not mint_new)
    invite_payload = questionnaire_invite_out_payload(invite)
    questionnaire_url = absolute_questionnaire_url(str(invite_payload.get("apply_url") or ""))

    contact_name = lead_contact_name(lead)
    signature = await resolve_outgoing_signature(
        db,
        user_id=actor_user_id,
        tenant_id=str(tenant_id),
        own_company_id=_trim(getattr(lead, "own_company_id", None)) or None,
        locale=locale,
    )
    signature_plain = signature.plain_text() if signature is not None else ""
    signature_html = signature.html() if signature is not None else ""

    template = resolve_template(TEMPLATE_KEY)
    rendered = render_template(
        template,
        locale=locale,
        variables={
            "contact_name": contact_name,
            "questionnaire_url": questionnaire_url,
        },
    )
    body = append_outgoing_signature(rendered["body"], signature_plain)
    body_html = append_outgoing_signature_html(plain_body_to_html(rendered["body"]), signature_html)

    recipient = _trim(recipient_email) or lead_contact_email(lead)
    email_cfg = await get_tenant_email_config(db, str(tenant_id))
    email_configured = bool(email_cfg and email_cfg.smtp_host and email_cfg.from_email)

    return QuestionnaireEmailCompose(
        invite=invite,
        invite_payload=invite_payload,
        recipient_email=recipient,
        subject=rendered["subject"],
        body=body,
        body_html=body_html,
        questionnaire_url=questionnaire_url,
        email_configured=email_configured,
        clarification_required=submitted_before,
        invite_reused=invite_reused,
        locale=locale,
    )


async def send_questionnaire_invite_email(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    form_locale: str | None,
    lead_form_id: str | None = None,
    force_new_invite: bool = False,
    recipient_email: str,
    subject: str,
    body: str,
    actor_user_id: str | None = None,
    save_email_to_lead: bool = True,
) -> dict[str, Any]:
    force_new = force_new_invite or _should_mint_new_invite_for_email(lead, force_new_invite=False)
    compose = await compose_questionnaire_invite_email(
        db,
        tenant_id=tenant_id,
        lead=lead,
        form_locale=form_locale,
        lead_form_id=lead_form_id,
        force_new_invite=force_new,
        recipient_email=recipient_email,
        actor_user_id=actor_user_id,
    )
    if compose.invite is None:
        raise QuestionnaireEmailError("invite_error", "Questionnaire invite is missing")
    if str(compose.invite.status) == INVITE_STATUS_SUBMITTED:
        raise QuestionnaireEmailError(
            "invite_already_submitted",
            "Cannot send a submitted questionnaire link. A new invite is required.",
            invite=compose.invite_payload,
        )

    email = normalize_recipient_email(recipient_email or compose.recipient_email)
    subject_final = _trim(subject) or compose.subject
    # Always send the server-composed body so the canonical profile signature is applied.
    # The UI may still show an editable preview, but stale client text must not override it.
    body_final = compose.body
    if not subject_final or not body_final:
        raise QuestionnaireEmailError("empty_message", "Email subject and body are required.")

    if not compose.email_configured:
        raise QuestionnaireEmailError(
            "email_not_configured",
            "Connect email in settings",
            settings_path="/app/settings/email",
        )

    questionnaire_url = compose.questionnaire_url
    now = _now()
    delivery = CommunicationDelivery(
        tenant_id=str(tenant_id),
        company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        entity_type="lead",
        entity_id=str(lead.id),
        purpose=PURPOSE_QUESTIONNAIRE_INVITE,
        channel=DELIVERY_CHANNEL_EMAIL,
        provider=DELIVERY_PROVIDER_SMTP,
        invite_id=str(compose.invite.id),
        recipient_normalized=email[:32],
        template_key=TEMPLATE_KEY,
        template_version=1,
        message_hash=_message_hash(subject=subject_final, body=body_final),
        encoding="utf8",
        parts_count=1,
        status=DELIVERY_STATUS_ACCEPTED,
        sent_by_user_id=_trim(actor_user_id) or None,
        queued_at=now,
        sent_at=now,
        meta={
            "recipient_email": email,
            "subject": subject_final,
            "questionnaire_url": questionnaire_url,
            "form_locale": compose.locale,
            "channel": DELIVERY_CHANNEL_EMAIL,
            "invite_id": str(compose.invite.id),
        },
    )
    db.add(delivery)
    await db.flush()

    try:
        await send_email_for_tenant(
            db,
            tenant_id=str(tenant_id),
            to=email,
            subject=subject_final,
            body=body_final,
            html_body=compose.body_html,
        )
    except ValueError as exc:
        if str(exc) == "TENANT_EMAIL_NOT_CONFIGURED":
            delivery.status = DELIVERY_STATUS_FAILED
            delivery.error_code = "email_not_configured"
            delivery.error_detail = "Connect email in settings"
            delivery.sent_at = None
            await db.flush()
            await log_activity(
                db,
                tenant_id=str(tenant_id),
                action="lead.questionnaire_email_failed",
                actor_id=_trim(actor_user_id) or None,
                target_type="lead",
                target_id=str(lead.id),
                payload={
                    "channel": DELIVERY_CHANNEL_EMAIL,
                    "recipient": email,
                    "error_code": "email_not_configured",
                    "delivery_id": str(delivery.id),
                    "questionnaire_url": questionnaire_url,
                },
            )
            raise QuestionnaireEmailError(
                "email_not_configured",
                "Connect email in settings",
                settings_path="/app/settings/email",
                delivery_id=str(delivery.id),
            ) from exc
        delivery.status = DELIVERY_STATUS_FAILED
        delivery.error_code = "send_failed"
        delivery.error_detail = str(exc)
        delivery.sent_at = None
        await db.flush()
        await log_activity(
            db,
            tenant_id=str(tenant_id),
            action="lead.questionnaire_email_failed",
            actor_id=_trim(actor_user_id) or None,
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "channel": DELIVERY_CHANNEL_EMAIL,
                "recipient": email,
                "error": str(exc),
                "delivery_id": str(delivery.id),
                "questionnaire_url": questionnaire_url,
            },
        )
        raise QuestionnaireEmailError("send_failed", str(exc), delivery_id=str(delivery.id)) from exc
    except Exception as exc:  # noqa: BLE001
        delivery.status = DELIVERY_STATUS_FAILED
        delivery.error_code = "send_failed"
        delivery.error_detail = str(exc) or type(exc).__name__
        delivery.sent_at = None
        await db.flush()
        await log_activity(
            db,
            tenant_id=str(tenant_id),
            action="lead.questionnaire_email_failed",
            actor_id=_trim(actor_user_id) or None,
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "channel": DELIVERY_CHANNEL_EMAIL,
                "recipient": email,
                "error": delivery.error_detail,
                "delivery_id": str(delivery.id),
                "questionnaire_url": questionnaire_url,
            },
        )
        raise QuestionnaireEmailError(
            "send_failed",
            delivery.error_detail or "Failed to send email",
            delivery_id=str(delivery.id),
        ) from exc

    invite = await attach_questionnaire_invite_to_lead(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        mark_sent=True,
        lead_form_id=lead_form_id,
        form_locale=compose.locale,
        create_if_missing=False,
        force_new=False,
    )

    if save_email_to_lead:
        normalized = _record(lead.normalized)
        if _trim(normalized.get("email")).lower() != email:
            normalized["email"] = email
            lead.normalized = normalized

    await log_activity(
        db,
        tenant_id=str(tenant_id),
        action="lead.questionnaire_email_sent",
        actor_id=_trim(actor_user_id) or None,
        target_type="lead",
        target_id=str(lead.id),
        payload={
            "channel": DELIVERY_CHANNEL_EMAIL,
            "recipient": email,
            "sent_at": now.isoformat(),
            "questionnaire_url": questionnaire_url,
            "delivery_id": str(delivery.id),
            "invite_id": str(invite.id),
            "form_locale": compose.locale,
            "subject": subject_final,
        },
    )

    return {
        "invite": questionnaire_invite_out_payload(invite),
        "delivery_id": str(delivery.id),
        "recipient_email": email,
        "questionnaire_url": questionnaire_url,
        "subject": subject_final,
        "status": "sent",
    }
