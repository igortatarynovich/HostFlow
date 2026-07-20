"""execute_communication_intent — business entry: Intent → Policy → Resolvers → Command → Sender.

Callers supply intent + context + non-URL variables + link *requests*.
They must not resolve templates, mint URLs, write G13, or pick providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.capability_resolver import (
    CapabilityResolver,
    get_capability_resolver,
)
from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    ResolvedLinkSnapshot,
    SendCommunicationContent,
)
from backend.app.communications.intent import CommunicationIntent, normalize_intent, resolve_intent_policy
from backend.app.communications.link_resolver import LinkResolveRequest, LinkResolver, get_link_resolver
from backend.app.communications.prepare_send import prepare_and_send_communication
from backend.app.communications.send_communication import (
    SendCommunicationError,
    SendCommunicationResult,
    TransportFn,
)
from backend.app.communications.template_resolver import TemplateResolver, get_template_resolver
from backend.app.services.communication_templates.registry import CommunicationTemplateNotFoundError


@dataclass(frozen=True, slots=True)
class IntentExecutionRequest:
    """Business intent + context. No rendered body, no public URLs, no provider choice."""

    tenant_id: str
    intent: CommunicationIntent | str
    origin: CommunicationOrigin
    recipients: Sequence[CommunicationRecipient]
    channel: str
    locale: str | None = None
    template_variables: Mapping[str, Any] = field(default_factory=dict)
    link_requests: Sequence[LinkResolveRequest] = ()
    actor_id: str | None = None
    automation_identity: str | None = None
    own_company_id: str | None = None
    related_entities: Sequence[CommunicationOrigin] = ()
    thread_id: str | None = None
    idempotency_key: str | None = None
    purpose: str | None = None
    delivery_purpose: str | None = None
    thread_subject: str | None = None
    correlation_id: str | None = None
    source_event_id: str | None = None
    preferred_template_key: str | None = None
    body_html_from_plain: bool = True
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IntentRenderResult:
    command: CommunicationCommand
    subject: str
    body_text: str
    body_html: str | None
    resolved_links: tuple[ResolvedLinkSnapshot, ...]


def _trim(value: Any) -> str:
    return str(value or "").strip()


async def render_communication_intent(
    request: IntentExecutionRequest,
    *,
    capability_resolver: CapabilityResolver | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> IntentRenderResult:
    """Intent → Policy → Resolvers → rendered Command (no persistence)."""
    intent = normalize_intent(request.intent)
    policy = resolve_intent_policy(intent)
    channel = _trim(request.channel).lower() or "email"
    if channel not in policy.allowed_channels:
        raise SendCommunicationError(
            f"channel {channel!r} is not allowed for intent {intent.value}",
            details={
                "reason": "intent_channel_denied",
                "intent": intent.value,
                "channel": channel,
            },
        )

    caps = await (capability_resolver or get_capability_resolver()).resolve(
        tenant_id=request.tenant_id,
        origin=request.origin,
        actor_id=request.actor_id,
    )
    if channel not in caps.allowed_channels:
        raise SendCommunicationError(
            f"channel {channel!r} is not allowed for entity {caps.entity_type}",
            details={
                "reason": "capability_channel_denied",
                "entity_type": caps.entity_type,
                "channel": channel,
                "denial": caps.denial_reasons.get(channel) or "channel_not_allowed",
            },
        )
    if intent.value not in caps.allowed_intents:
        raise SendCommunicationError(
            f"intent {intent.value!r} is not allowed for entity {caps.entity_type}",
            details={
                "reason": "capability_intent_denied",
                "entity_type": caps.entity_type,
                "intent": intent.value,
                "denial": caps.denial_reasons.get("intent") or "intent_not_allowed",
            },
        )

    templates = template_resolver or get_template_resolver()
    try:
        resolved_tpl = templates.resolve_for_intent(
            intent,
            channel=channel,
            preferred_key=request.preferred_template_key,
        )
    except CommunicationTemplateNotFoundError as exc:
        raise SendCommunicationError(
            f"template resolution failed for intent {intent.value}",
            details={
                "reason": "template_resolution_failed",
                "intent": intent.value,
                "template_key": getattr(exc, "key", None),
            },
        ) from exc

    links_impl = link_resolver or get_link_resolver()
    resolved_links: list[ResolvedLinkSnapshot] = []
    link_vars: dict[str, Any] = {}
    for link_req in request.link_requests or ():
        if link_req.link_intent not in policy.link_intents:
            raise SendCommunicationError(
                f"link intent {link_req.link_intent!r} not allowed for {intent.value}",
                details={
                    "reason": "link_intent_denied",
                    "intent": intent.value,
                    "link_intent": link_req.link_intent,
                },
            )
        try:
            resolved = await links_impl.resolve(link_req)
        except Exception as exc:  # noqa: BLE001
            raise SendCommunicationError(
                f"link resolution failed for {link_req.link_intent}",
                details={
                    "reason": "link_resolution_failed",
                    "link_intent": link_req.link_intent,
                    "error": str(exc) or type(exc).__name__,
                },
            ) from exc
        snap = ResolvedLinkSnapshot(
            link_intent=resolved.link_intent,
            public_url=resolved.public_url,
            token=resolved.token,
            expires_at=resolved.expires_at,
            variable_name=resolved.variable_name,
        )
        resolved_links.append(snap)
        link_vars[snap.variable_name] = snap.public_url
        # Legacy template vars still expect questionnaire_url for sales questionnaire.
        if snap.link_intent in {"sales_questionnaire", "candidate_questionnaire"}:
            link_vars.setdefault("questionnaire_url", snap.public_url)

    variables = {**dict(request.template_variables or {}), **link_vars}
    rendered = templates.render(
        resolved_tpl, locale=_trim(request.locale) or "pl", variables=variables
    )
    subject = _trim(rendered.get("subject"))
    body_text = _trim(rendered.get("body"))
    body_html = None
    if request.body_html_from_plain and body_text:
        from backend.app.services.email_signature import plain_body_to_html

        body_html = plain_body_to_html(body_text)

    policy_decision = {
        "allowed": True,
        "intent": intent.value,
        "intent_purpose": policy.purpose,
        "channel": channel,
        "entity_type": caps.entity_type,
        "requires_consent": policy.requires_consent,
        "allows_automation": policy.allows_automation,
        "template_key": resolved_tpl.key,
        "template_version": resolved_tpl.version,
        "link_intents": [lnk.link_intent for lnk in resolved_links],
    }

    command = CommunicationCommand(
        tenant_id=str(request.tenant_id),
        intent=intent,
        origin=request.origin,
        recipients=request.recipients,
        channel=channel,
        content=SendCommunicationContent(
            subject=subject or None,
            body_text=body_text or None,
            body_html=body_html,
            message_type="email" if channel == "email" else "text",
        ),
        actor_id=request.actor_id,
        automation_identity=request.automation_identity,
        own_company_id=request.own_company_id,
        related_entities=request.related_entities,
        thread_id=request.thread_id,
        idempotency_key=request.idempotency_key,
        purpose=request.purpose or policy.purpose,
        delivery_purpose=request.delivery_purpose or request.purpose or policy.purpose,
        thread_subject=request.thread_subject,
        template_key=resolved_tpl.key,
        template_version=resolved_tpl.version,
        locale=request.locale,
        requested_link_intents=tuple(lnk.link_intent for lnk in resolved_links),
        resolved_links=tuple(resolved_links),
        render_variables=variables,
        policy_decision=policy_decision,
        correlation_id=request.correlation_id,
        source_event_id=request.source_event_id,
        meta=dict(request.meta or {}),
    )
    return IntentRenderResult(
        command=command,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        resolved_links=tuple(resolved_links),
    )


async def execute_communication_intent(
    db: AsyncSession,
    request: IntentExecutionRequest,
    *,
    transport: TransportFn | None = None,
    skip_transport: bool = False,
    capability_resolver: CapabilityResolver | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
) -> SendCommunicationResult:
    """Full path: render from Intent, then prepare_and_send (persistence + optional transport)."""
    rendered = await render_communication_intent(
        request,
        capability_resolver=capability_resolver,
        template_resolver=template_resolver,
        link_resolver=link_resolver,
    )
    return await prepare_and_send_communication(
        db,
        rendered.command,
        transport=transport,
        skip_transport=skip_transport,
        capability_resolver=capability_resolver,
    )
