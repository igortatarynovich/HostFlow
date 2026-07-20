"""Questionnaire invite — thin business caller of Communication Canon.

Forms Intent + context (lead/invite/recipient). Does not mint public URLs,
pick template versions, write G13, create deliveries, or choose SMTP.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
)
from backend.app.communications.execute_intent import (
    IntentExecutionRequest,
    render_communication_intent,
)
from backend.app.communications.prepare_send import prepare_and_send_communication
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.link_resolver import LinkResolveRequest
from backend.app.communications.send_communication import SendCommunicationError
from backend.app.models import Lead
from backend.app.models.communication_delivery import (
    DELIVERY_CHANNEL_EMAIL,
    PURPOSE_QUESTIONNAIRE_INVITE,
)
from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
from backend.app.modules.leads.lead_questionnaire_invite import (
    INVITE_STATUS_SUBMITTED,
    attach_questionnaire_invite_to_lead,
    questionnaire_invite_out_payload,
)
from backend.app.services.audit import log_activity
from backend.app.services.email_signature import (
    append_outgoing_signature,
    append_outgoing_signature_html,
    plain_body_to_html,
    resolve_outgoing_signature,
)
from backend.app.services.tenant_email import get_tenant_email_config

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_QUESTIONNAIRE_LINK_INTENT = "sales_questionnaire"
_INTENT = CommunicationIntent.REQUEST_QUESTIONNAIRE


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
    template_key: str
    template_version: int
    link_intent: str
    intent: str


def _should_mint_new_invite_for_email(lead: Lead, *, force_new_invite: bool) -> bool:
    if force_new_invite:
        return True
    status = _trim((_record(lead.normalized).get("sales_questionnaire_status")))
    return status == INVITE_STATUS_SUBMITTED


async def _mint_invite(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    locale: str,
    lead_form_id: str | None,
    force_new_invite: bool,
) -> tuple[LeadQuestionnaireInvite, dict[str, Any], bool, bool]:
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

    if mint_new and submitted_before and invite.status != INVITE_STATUS_SUBMITTED:
        normalized = _record(lead.normalized)
        normalized["sales_questionnaire_status"] = "not_sent"
        lead.normalized = normalized

    invite_reused = bool(existing_before is not None and not mint_new)
    return invite, questionnaire_invite_out_payload(invite), invite_reused, submitted_before


def _intent_request(
    *,
    tenant_id: str,
    lead: Lead,
    sales_inquiry_id: str,
    email: str,
    locale: str,
    invite_payload: dict[str, Any],
    actor_user_id: str | None,
    thread_id: str | None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> IntentExecutionRequest:
    return IntentExecutionRequest(
        tenant_id=str(tenant_id),
        intent=_INTENT,
        origin=CommunicationOrigin(
            entity_type="sales_inquiry",
            entity_id=str(sales_inquiry_id),
        ),
        recipients=[
            CommunicationRecipient(
                address=email,
                recipient_type="lead",
                recipient_id=str(lead.id),
            )
        ],
        channel=DELIVERY_CHANNEL_EMAIL,
        locale=locale,
        template_variables={"contact_name": lead_contact_name(lead)},
        link_requests=(
            LinkResolveRequest(
                tenant_id=str(tenant_id),
                link_intent=_QUESTIONNAIRE_LINK_INTENT,
                entity_type="lead",
                entity_id=str(lead.id),
                locale=locale,
                # Token path from domain invite — LinkResolver is SoT for absolute URL.
                apply_path_or_url=str(invite_payload.get("apply_url") or ""),
                actor_id=_trim(actor_user_id) or None,
            ),
        ),
        actor_id=_trim(actor_user_id) or None,
        own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        related_entities=(
            CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
        ),
        thread_id=thread_id,
        idempotency_key=idempotency_key,
        purpose=PURPOSE_QUESTIONNAIRE_INVITE,
        delivery_purpose=PURPOSE_QUESTIONNAIRE_INVITE,
        correlation_id=correlation_id,
        meta={"invite_id": str(invite_payload.get("id") or "") or None},
    )


async def _apply_signature(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    actor_user_id: str | None,
    locale: str,
    subject: str,
    body_text: str,
) -> tuple[str, str, str]:
    signature = await resolve_outgoing_signature(
        db,
        user_id=actor_user_id,
        tenant_id=str(tenant_id),
        own_company_id=_trim(getattr(lead, "own_company_id", None)) or None,
        locale=locale,
    )
    signature_plain = signature.plain_text() if signature is not None else ""
    signature_html = signature.html() if signature is not None else ""
    body = append_outgoing_signature(body_text, signature_plain)
    body_html = append_outgoing_signature_html(plain_body_to_html(body_text), signature_html)
    return subject, body, body_html


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
    thread_id: str | None = None,
    sales_inquiry_id: str | None = None,
) -> QuestionnaireEmailCompose:
    """Preview path: mint invite + render Intent (no send / no G13 write)."""
    _ = thread_id
    locale = (_trim(form_locale) or "pl").lower()[:2]
    invite, invite_payload, invite_reused, submitted_before = await _mint_invite(
        db,
        tenant_id=tenant_id,
        lead=lead,
        locale=locale,
        lead_form_id=lead_form_id,
        force_new_invite=force_new_invite,
    )
    recipient = _trim(recipient_email) or lead_contact_email(lead)
    # Preview may not have sales_inquiry yet — use placeholder origin for render only.
    origin_id = _trim(sales_inquiry_id) or f"preview:{lead.id}"
    try:
        rendered = await render_communication_intent(
            _intent_request(
                tenant_id=tenant_id,
                lead=lead,
                sales_inquiry_id=origin_id,
                email=recipient or "preview@invalid.local",
                locale=locale,
                invite_payload=invite_payload,
                actor_user_id=actor_user_id,
                thread_id=None,
            )
        )
    except SendCommunicationError as exc:
        # Preview for unbound lead: capability may deny fake origin — fall back with lead origin.
        if (exc.details or {}).get("reason") == "capability_intent_denied" and not sales_inquiry_id:
            rendered = await render_communication_intent(
                IntentExecutionRequest(
                    tenant_id=str(tenant_id),
                    intent=_INTENT,
                    origin=CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
                    recipients=[
                        CommunicationRecipient(address=recipient or "preview@invalid.local")
                    ],
                    channel=DELIVERY_CHANNEL_EMAIL,
                    locale=locale,
                    template_variables={"contact_name": lead_contact_name(lead)},
                    link_requests=(
                        LinkResolveRequest(
                            tenant_id=str(tenant_id),
                            link_intent=_QUESTIONNAIRE_LINK_INTENT,
                            entity_type="lead",
                            entity_id=str(lead.id),
                            locale=locale,
                            apply_path_or_url=str(invite_payload.get("apply_url") or ""),
                            actor_id=_trim(actor_user_id) or None,
                        ),
                    ),
                    actor_id=_trim(actor_user_id) or None,
                    purpose=PURPOSE_QUESTIONNAIRE_INVITE,
                )
            )
        else:
            raise QuestionnaireEmailError(
                str((exc.details or {}).get("reason") or "compose_failed"),
                exc.message,
                details=dict(exc.details or {}),
            ) from exc

    subject, body, body_html = await _apply_signature(
        db,
        tenant_id=tenant_id,
        lead=lead,
        actor_user_id=actor_user_id,
        locale=locale,
        subject=rendered.subject,
        body_text=rendered.body_text,
    )
    questionnaire_url = ""
    if rendered.resolved_links:
        questionnaire_url = rendered.resolved_links[0].public_url

    email_cfg = await get_tenant_email_config(db, str(tenant_id))
    email_configured = bool(email_cfg and email_cfg.smtp_host and email_cfg.from_email)

    return QuestionnaireEmailCompose(
        invite=invite,
        invite_payload=invite_payload,
        recipient_email=recipient,
        subject=subject,
        body=body,
        body_html=body_html,
        questionnaire_url=questionnaire_url,
        email_configured=email_configured,
        clarification_required=submitted_before,
        invite_reused=invite_reused,
        locale=locale,
        template_key=rendered.command.template_key or "",
        template_version=int(rendered.command.template_version or 1),
        link_intent=_QUESTIONNAIRE_LINK_INTENT,
        intent=_INTENT.value,
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
    thread_id: str | None = None,
    communication_purpose: str | None = None,
    template_metadata: dict[str, Any] | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    from backend.app.communications.send_pipeline import (
        CommunicationSendRequest,
        authorize_outbound_communication,
        template_metadata_from_mapping,
    )
    from backend.app.models.communication import CommunicationMessage
    from backend.app.models.communication_delivery import CommunicationDelivery

    # Always bind SalesInquiry + G13 via module binder. Client-supplied thread_id may be a
    # C5 authorization stub and must not skip durable origin linkage.
    from backend.app.modules.sales.communication.questionnaire_pipeline import (
        SalesQuestionnairePipelineError,
        ensure_sales_questionnaire_pipeline_binding,
    )

    purpose = _trim(communication_purpose)
    template = template_metadata_from_mapping(
        template_metadata if isinstance(template_metadata, dict) else None
    )
    try:
        # Do not trust client thread_id for binding — C5 stubs are not durable threads.
        # Binder creates/reuses the real SalesInquiry-linked thread + G13.
        _ = thread_id
        binding = await ensure_sales_questionnaire_pipeline_binding(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            locale=_trim(locale) or _trim(form_locale) or None,
            actor_user_id=actor_user_id,
            thread_id=None,
        )
    except SalesQuestionnairePipelineError as exc:
        reason = str((exc.details or {}).get("reason") or "").strip()
        raise QuestionnaireEmailError(
            reason or "sales_questionnaire_pipeline_error",
            exc.message,
            details=dict(exc.details or {}),
        ) from exc

    thread = binding.thread_id
    sales_inquiry_id = binding.sales_inquiry_id
    purpose = purpose or binding.communication_purpose
    if template is None:
        template = binding.template

    if not thread or not purpose or template is None or not sales_inquiry_id:
        raise QuestionnaireEmailError(
            "communication_pipeline_required",
            "Outbound questionnaire email requires bound thread, sales_inquiry origin, "
            "communication_purpose, and template_metadata.",
        )

    auth = await authorize_outbound_communication(
        db,
        CommunicationSendRequest(
            tenant_id=str(tenant_id),
            thread_id=thread,
            channel=DELIVERY_CHANNEL_EMAIL,
            communication_purpose=purpose,
            template=template,
            locale=_trim(locale) or _trim(form_locale) or None,
        ),
    )
    if not auth.allowed:
        raise QuestionnaireEmailError(
            str(auth.reason_code or "communication_pipeline_denied"),
            "Communication Pipeline denied questionnaire email send.",
            authorization=auth.to_dict(),
        )

    force_new = force_new_invite or _should_mint_new_invite_for_email(lead, force_new_invite=False)
    locale_final = (_trim(locale) or _trim(form_locale) or "pl").lower()[:2]
    invite, invite_payload, _reused, _submitted = await _mint_invite(
        db,
        tenant_id=tenant_id,
        lead=lead,
        locale=locale_final,
        lead_form_id=lead_form_id,
        force_new_invite=force_new,
    )
    if str(invite.status) == INVITE_STATUS_SUBMITTED:
        raise QuestionnaireEmailError(
            "invite_already_submitted",
            "Cannot send a submitted questionnaire link. A new invite is required.",
            invite=invite_payload,
        )

    email = normalize_recipient_email(recipient_email or lead_contact_email(lead))
    email_cfg = await get_tenant_email_config(db, str(tenant_id))
    if not (email_cfg and email_cfg.smtp_host and email_cfg.from_email):
        raise QuestionnaireEmailError(
            "email_not_configured",
            "Connect email in settings",
            settings_path="/app/settings/email",
        )

    # Render via Intent resolvers, then apply signature (tenant branding) before send.
    # Idempotency covers transport retries of the same rendered content, not intentional re-sends.
    try:
        rendered = await render_communication_intent(
            _intent_request(
                tenant_id=tenant_id,
                lead=lead,
                sales_inquiry_id=str(sales_inquiry_id),
                email=email,
                locale=locale_final,
                invite_payload={**invite_payload, "id": str(invite.id)},
                actor_user_id=actor_user_id,
                thread_id=str(thread),
                idempotency_key=None,
                correlation_id=str(invite.id),
            )
        )
    except SendCommunicationError as exc:
        raise QuestionnaireEmailError(
            str((exc.details or {}).get("reason") or "intent_render_failed"),
            exc.message,
            details=dict(exc.details or {}),
        ) from exc

    _subj, body_signed, body_html = await _apply_signature(
        db,
        tenant_id=tenant_id,
        lead=lead,
        actor_user_id=actor_user_id,
        locale=locale_final,
        subject=rendered.subject,
        body_text=rendered.body_text,
    )
    # Server-composed body wins; client subject may override empty only.
    subject_final = _trim(subject) or rendered.subject
    body_final = body_signed
    if not subject_final or not body_final:
        raise QuestionnaireEmailError("empty_message", "Email subject and body are required.")

    signed_command = CommunicationCommand(
        tenant_id=rendered.command.tenant_id,
        intent=rendered.command.intent,
        origin=rendered.command.origin,
        recipients=rendered.command.recipients,
        channel=rendered.command.channel,
        content=SendCommunicationContent(
            subject=subject_final,
            body_text=body_final,
            body_html=body_html,
            message_type="email",
        ),
        actor_id=rendered.command.actor_id,
        own_company_id=rendered.command.own_company_id,
        related_entities=rendered.command.related_entities,
        thread_id=rendered.command.thread_id,
        purpose=rendered.command.purpose,
        delivery_purpose=rendered.command.delivery_purpose,
        template_key=rendered.command.template_key,
        template_version=rendered.command.template_version,
        locale=rendered.command.locale,
        requested_link_intents=rendered.command.requested_link_intents,
        resolved_links=rendered.command.resolved_links,
        render_variables=rendered.command.render_variables,
        policy_decision=rendered.command.policy_decision,
        correlation_id=rendered.command.correlation_id,
        source_event_id=rendered.command.source_event_id,
        idempotency_key=(
            f"questionnaire_invite:{invite.id}:{email}:{locale_final}:"
            f"{_message_hash(subject=subject_final, body=body_final)[:16]}"
        )[:128],
        meta={
            **dict(rendered.command.meta or {}),
            "invite_id": str(invite.id),
            "lead_id": str(lead.id),
            "message_hash": _message_hash(subject=subject_final, body=body_final),
        },
    )

    questionnaire_url = (
        rendered.resolved_links[0].public_url if rendered.resolved_links else ""
    )
    now = _now()

    try:
        send_result = await prepare_and_send_communication(db, signed_command)
    except SendCommunicationError as exc:
        reason = str((exc.details or {}).get("reason") or "")
        code = "email_not_configured" if "TENANT_EMAIL_NOT_CONFIGURED" in exc.message else (
            "send_failed" if reason == "transport_failed" else "send_communication_failed"
        )
        if "TENANT_EMAIL_NOT_CONFIGURED" in exc.message or "Connect email" in exc.message:
            code = "email_not_configured"
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
                "error": exc.message,
                "error_code": code,
                "intent": _INTENT.value,
                "delivery_id": (exc.details or {}).get("delivery_id"),
                "message_id": (exc.details or {}).get("message_id"),
                "questionnaire_url": questionnaire_url,
            },
        )
        raise QuestionnaireEmailError(
            code,
            exc.message,
            settings_path="/app/settings/email" if code == "email_not_configured" else None,
            delivery_id=(exc.details or {}).get("delivery_id"),
            message_id=(exc.details or {}).get("message_id"),
            details=dict(exc.details or {}),
        ) from exc

    if send_result.delivery_id:
        delivery_row = await db.get(CommunicationDelivery, send_result.delivery_id)
        if delivery_row is not None:
            delivery_row.invite_id = str(invite.id)
            delivery_row.template_key = signed_command.template_key
            delivery_row.template_version = signed_command.template_version
            delivery_row.message_hash = _message_hash(subject=subject_final, body=body_final)
            meta = dict(delivery_row.meta or {})
            meta.update(
                {
                    "questionnaire_url": questionnaire_url,
                    "link_intent": _QUESTIONNAIRE_LINK_INTENT,
                    "intent": _INTENT.value,
                    "form_locale": locale_final,
                    "invite_id": str(invite.id),
                }
            )
            delivery_row.meta = meta
            await db.flush()

    _ = await db.get(CommunicationMessage, send_result.message_id)

    invite = await attach_questionnaire_invite_to_lead(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        mark_sent=True,
        lead_form_id=lead_form_id,
        form_locale=locale_final,
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
            "intent": _INTENT.value,
            "questionnaire_url": questionnaire_url,
            "delivery_id": send_result.delivery_id,
            "message_id": send_result.message_id,
            "thread_id": send_result.thread_id,
            "invite_id": str(invite.id),
            "form_locale": locale_final,
            "subject": subject_final,
        },
    )

    return {
        "invite": questionnaire_invite_out_payload(invite),
        "delivery_id": send_result.delivery_id,
        "message_id": send_result.message_id,
        "thread_id": send_result.thread_id,
        "recipient_email": email,
        "questionnaire_url": questionnaire_url,
        "subject": subject_final,
        "status": "sent",
        "intent": _INTENT.value,
    }

