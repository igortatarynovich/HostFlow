"""prepare_and_send_communication — validate Command then platform send.

Receives a ready CommunicationCommand (after Intent → Resolvers).
Does not re-make template/link business decisions; re-checks intent/capabilities.
"""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.capability_resolver import (
    CapabilityResolver,
    get_capability_resolver,
)
from backend.app.communications.command import CommunicationCommand, SendCommunicationContent
from backend.app.communications.intent import resolve_intent_policy
from backend.app.communications.send_communication import (
    SendCommunicationError,
    SendCommunicationResult,
    TransportFn,
    send_communication,
)


class CommunicationSender(Protocol):
    """Injectable send port — product callers depend on this, not SMTP/G13 writers."""

    async def send(
        self,
        db: AsyncSession,
        command: CommunicationCommand,
        *,
        transport: TransportFn | None = None,
        skip_transport: bool = False,
    ) -> SendCommunicationResult: ...


def _trim(value: Any) -> str:
    return str(value or "").strip()


async def _default_email_transport(
    db: AsyncSession,
    *,
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
    html_body: str | None,
) -> None:
    from backend.app.services.tenant_email import send_email_for_tenant

    await send_email_for_tenant(
        db,
        tenant_id=str(tenant_id),
        to=to,
        subject=subject,
        body=body,
        html_body=html_body,
    )


class PlatformCommunicationSender:
    async def send(
        self,
        db: AsyncSession,
        command: CommunicationCommand,
        *,
        transport: TransportFn | None = None,
        skip_transport: bool = False,
    ) -> SendCommunicationResult:
        return await prepare_and_send_communication(
            db,
            command,
            transport=transport,
            skip_transport=skip_transport,
        )


_default_sender: CommunicationSender = PlatformCommunicationSender()


def get_communication_sender() -> CommunicationSender:
    return _default_sender


async def prepare_and_send_communication(
    db: AsyncSession,
    command: CommunicationCommand,
    *,
    transport: TransportFn | None = None,
    skip_transport: bool = False,
    capability_resolver: CapabilityResolver | None = None,
) -> SendCommunicationResult:
    """Validate intent/capabilities on a ready Command, then execute durable send.

    When ``transport`` is omitted and channel is email and not ``skip_transport``,
    the platform supplies the SMTP transport — callers must not.
    """
    if command.content is None or (
        not (command.content.subject or command.content.body_text or command.content.body_html)
    ):
        raise SendCommunicationError(
            "CommunicationCommand.content is required before send",
            details={"reason": "missing_content"},
        )

    intent = command.normalized_intent()
    policy = resolve_intent_policy(intent)
    channel = _trim(command.channel).lower() or "email"
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
        tenant_id=command.tenant_id,
        origin=command.origin,
        actor_id=command.actor_id,
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

    if command.template_key and policy.allowed_template_keys:
        if command.template_key not in policy.allowed_template_keys:
            raise SendCommunicationError(
                f"template {command.template_key!r} is not allowed for intent {intent.value}",
                details={
                    "reason": "intent_template_denied",
                    "intent": intent.value,
                    "template_key": command.template_key,
                },
            )

    # Intent-bound product templates cannot ride MANUAL_OUTBOUND.
    _INTENT_BOUND_TEMPLATES = {
        "questionnaire_invite_email_v1": "request_questionnaire",
    }
    tpl = _trim(command.template_key)
    if tpl in _INTENT_BOUND_TEMPLATES and intent.value != _INTENT_BOUND_TEMPLATES[tpl]:
        raise SendCommunicationError(
            f"template {tpl!r} requires intent {_INTENT_BOUND_TEMPLATES[tpl]!r}, got {intent.value!r}",
            details={
                "reason": "intent_required_for_template",
                "template_key": tpl,
                "required_intent": _INTENT_BOUND_TEMPLATES[tpl],
                "intent": intent.value,
            },
        )

    policy_decision = dict(command.policy_decision or {})
    policy_decision.setdefault("allowed", True)
    policy_decision.setdefault("intent", intent.value)
    policy_decision.setdefault("intent_purpose", policy.purpose)
    policy_decision.setdefault("channel", channel)
    policy_decision.setdefault("entity_type", caps.entity_type)

    enriched_meta: dict[str, Any] = {
        **dict(command.meta or {}),
        "intent": intent.value,
        "intent_purpose": policy.purpose,
        "policy_decision": policy_decision,
        "resolved_links": [lnk.to_dict() for lnk in (command.resolved_links or ())],
        "render_variables": dict(command.render_variables or {}),
    }
    if command.correlation_id:
        enriched_meta["correlation_id"] = command.correlation_id
    if command.source_event_id:
        enriched_meta["source_event_id"] = command.source_event_id
    if command.automation_identity:
        enriched_meta["automation_identity"] = command.automation_identity
    if command.requested_link_intents:
        enriched_meta["requested_link_intents"] = list(command.requested_link_intents)

    content = command.content
    assert content is not None
    executable = CommunicationCommand(
        tenant_id=command.tenant_id,
        origin=command.origin,
        recipients=command.recipients,
        channel=channel,
        intent=intent,
        content=SendCommunicationContent(
            subject=content.subject,
            body_text=content.body_text,
            body_html=content.body_html,
            message_type=content.message_type,
        ),
        actor_id=command.actor_id,
        automation_identity=command.automation_identity,
        own_company_id=command.own_company_id,
        related_entities=command.related_entities,
        thread_id=command.thread_id,
        idempotency_key=command.idempotency_key,
        purpose=command.purpose or policy.purpose,
        thread_subject=command.thread_subject,
        delivery_purpose=command.delivery_purpose or command.purpose,
        template_key=command.template_key,
        template_version=command.template_version,
        locale=command.locale,
        requested_link_intents=command.requested_link_intents,
        resolved_links=command.resolved_links,
        render_variables=command.render_variables,
        policy_decision=policy_decision,
        correlation_id=command.correlation_id,
        source_event_id=command.source_event_id,
        meta=enriched_meta,
    )

    effective_transport = transport
    if (
        effective_transport is None
        and not skip_transport
        and channel == "email"
        and content.body_text is not None
    ):
        primary = command.recipients[0]
        to_addr = _trim(primary.address)
        subject = _trim(content.subject) or ""
        body = _trim(content.body_text) or ""
        html = content.body_html

        async def _platform_email_transport() -> None:
            await _default_email_transport(
                db,
                tenant_id=command.tenant_id,
                to=to_addr,
                subject=subject,
                body=body,
                html_body=html,
            )

        effective_transport = _platform_email_transport

    return await send_communication(
        db,
        executable,
        transport=effective_transport,
        skip_transport=skip_transport,
    )
