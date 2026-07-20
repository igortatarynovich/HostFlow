"""Send questionnaire invite by email via tenant SMTP.

Compose uses platform TemplateResolver + LinkResolver.
Send goes through CommunicationSender / prepare_and_send (not a private engine).
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
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.link_resolver import (
    LinkResolveRequest,
    LinkResolver,
    absolute_public_url,
    get_link_resolver,
)
from backend.app.communications.prepare_send import (
    CommunicationSender,
    get_communication_sender,
)
from backend.app.communications.send_communication import SendCommunicationError
from backend.app.communications.template_resolver import (
    TemplateResolver,
    get_template_resolver,
)
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
from backend.app.services.tenant_email import get_tenant_email_config, send_email_for_tenant

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_QUESTIONNAIRE_LINK_INTENT = "sales_questionnaire"


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
    """Back-compat wrapper — prefer LinkResolver in new code."""
    return absolute_public_url(apply_url)


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
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> QuestionnaireEmailCompose:
    # C5: domain is not inferred from Lead.lead_type — pipeline owns eligibility.
    # Compose may prepare content, but send requires thread_id + pipeline authorize.
    _ = thread_id  # validated at send time

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

    templates = template_resolver or get_template_resolver()
    links = link_resolver or get_link_resolver()
    resolved_tpl = templates.resolve_for_intent(
        CommunicationIntent.REQUEST_QUESTIONNAIRE,
        channel=DELIVERY_CHANNEL_EMAIL,
    )
    resolved_link = await links.resolve(
        LinkResolveRequest(
            tenant_id=str(tenant_id),
            link_intent=_QUESTIONNAIRE_LINK_INTENT,
            entity_type="lead",
            entity_id=str(lead.id),
            locale=locale,
            apply_path_or_url=str(invite_payload.get("apply_url") or ""),
            actor_id=_trim(actor_user_id) or None,
        )
    )
    questionnaire_url = resolved_link.public_url

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

    rendered = templates.render(
        resolved_tpl,
        locale=locale,
        variables={
            "contact_name": contact_name,
            resolved_link.variable_name: questionnaire_url,
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
        template_key=resolved_tpl.key,
        template_version=resolved_tpl.version,
        link_intent=resolved_link.link_intent,
        intent=CommunicationIntent.REQUEST_QUESTIONNAIRE.value,
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
    sender: CommunicationSender | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> dict[str, Any]:
    from backend.app.communications.send_pipeline import (
        CommunicationSendRequest,
        authorize_outbound_communication,
        template_metadata_from_mapping,
    )

    # C5: no transport without full Communication Pipeline authorization.
    # Sales UI may omit pipeline fields — module-owned binder resolves them from
    # SalesInquiry (Thread Result Link + purpose + template metadata).
    thread = _trim(thread_id)
    purpose = _trim(communication_purpose)
    template = template_metadata_from_mapping(
        template_metadata if isinstance(template_metadata, dict) else None
    )
    if not thread or not purpose or template is None:
        from backend.app.modules.sales.communication.questionnaire_pipeline import (
            SalesQuestionnairePipelineError,
            ensure_sales_questionnaire_pipeline_binding,
        )

        try:
            binding = await ensure_sales_questionnaire_pipeline_binding(
                db,
                tenant_id=str(tenant_id),
                lead=lead,
                locale=_trim(locale) or _trim(form_locale) or None,
                actor_user_id=actor_user_id,
                thread_id=thread or None,
            )
        except SalesQuestionnairePipelineError as exc:
            reason = str((exc.details or {}).get("reason") or "").strip()
            raise QuestionnaireEmailError(
                reason or "sales_questionnaire_pipeline_error",
                exc.message,
                details=dict(exc.details or {}),
            ) from exc
        thread = thread or binding.thread_id
        purpose = purpose or binding.communication_purpose
        if template is None:
            template = binding.template

    if not thread or not purpose or template is None:
        raise QuestionnaireEmailError(
            "communication_pipeline_required",
            "Outbound questionnaire email requires thread_id, communication_purpose, "
            "and template_metadata approved by the Communication Pipeline.",
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
    compose = await compose_questionnaire_invite_email(
        db,
        tenant_id=tenant_id,
        lead=lead,
        form_locale=form_locale,
        lead_form_id=lead_form_id,
        force_new_invite=force_new,
        recipient_email=recipient_email,
        actor_user_id=actor_user_id,
        thread_id=thread,
        template_resolver=template_resolver,
        link_resolver=link_resolver,
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

    from backend.app.communications.entity_link import get_thread_entity_links
    from backend.app.models.communication import CommunicationMessage
    from backend.app.models.communication_delivery import CommunicationDelivery

    sales_inquiry_id = None
    for lnk in await get_thread_entity_links(db, tenant_id=str(tenant_id), thread_id=str(thread)):
        if lnk.entity_type == "sales_inquiry":
            sales_inquiry_id = lnk.entity_id
            break
    if not sales_inquiry_id:
        raise QuestionnaireEmailError(
            "thread_entity_link_required",
            "Questionnaire email requires a sales_inquiry G13 link before send.",
            details={"thread_id": str(thread), "reason": "missing_thread_entity_link"},
        )

    async def _transport() -> None:
        await send_email_for_tenant(
            db,
            tenant_id=str(tenant_id),
            to=email,
            subject=subject_final,
            body=body_final,
            html_body=compose.body_html,
        )

    command = CommunicationCommand(
        tenant_id=str(tenant_id),
        intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
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
        content=SendCommunicationContent(
            subject=subject_final,
            body_text=body_final,
            body_html=compose.body_html,
            message_type="email",
        ),
        actor_id=_trim(actor_user_id) or None,
        own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        related_entities=[
            CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
        ],
        thread_id=str(thread),
        purpose=PURPOSE_QUESTIONNAIRE_INVITE,
        delivery_purpose=PURPOSE_QUESTIONNAIRE_INVITE,
        template_key=compose.template_key,
        template_version=compose.template_version,
        locale=compose.locale,
        requested_link_intents=(_QUESTIONNAIRE_LINK_INTENT,),
        meta={
            "invite_id": str(compose.invite.id),
            "questionnaire_url": questionnaire_url,
            "link_intent": compose.link_intent,
            "form_locale": compose.locale,
            "message_hash": _message_hash(subject=subject_final, body=body_final),
        },
    )

    try:
        send_result = await (sender or get_communication_sender()).send(
            db,
            command,
            transport=_transport,
        )
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
                "intent": compose.intent,
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

    # Enrich delivery journal with invite/template stamps (platform row already exists).
    if send_result.delivery_id:
        delivery_row = await db.get(CommunicationDelivery, send_result.delivery_id)
        if delivery_row is not None:
            delivery_row.invite_id = str(compose.invite.id)
            delivery_row.template_key = compose.template_key
            delivery_row.template_version = compose.template_version
            delivery_row.message_hash = _message_hash(subject=subject_final, body=body_final)
            delivery_row.encoding = "utf8"
            delivery_row.parts_count = 1
            meta = dict(delivery_row.meta or {})
            meta.update(
                {
                    "questionnaire_url": questionnaire_url,
                    "link_intent": compose.link_intent,
                    "intent": compose.intent,
                    "form_locale": compose.locale,
                    "invite_id": str(compose.invite.id),
                }
            )
            delivery_row.meta = meta
            await db.flush()

    _ = await db.get(CommunicationMessage, send_result.message_id)
    delivery_id = send_result.delivery_id

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
            "intent": compose.intent,
            "questionnaire_url": questionnaire_url,
            "delivery_id": delivery_id,
            "message_id": send_result.message_id,
            "thread_id": send_result.thread_id,
            "invite_id": str(invite.id),
            "form_locale": compose.locale,
            "subject": subject_final,
        },
    )

    return {
        "invite": questionnaire_invite_out_payload(invite),
        "delivery_id": delivery_id,
        "message_id": send_result.message_id,
        "thread_id": send_result.thread_id,
        "recipient_email": email,
        "questionnaire_url": questionnaire_url,
        "subject": subject_final,
        "status": "sent",
        "intent": compose.intent,
    }
