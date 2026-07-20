"""prepare_and_send_communication — intent/capabilities gate then platform send."""

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
    """Injectable send port — questionnaire and future callers depend on this, not SMTP."""

    async def send(
        self,
        db: AsyncSession,
        command: CommunicationCommand,
        *,
        transport: TransportFn | None = None,
        skip_transport: bool = False,
    ) -> SendCommunicationResult: ...


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
    """Validate intent/capabilities, then execute durable SendCommunication.

    Template/link composition stays with the caller for now (questionnaire compose),
    but must go through TemplateResolver / LinkResolver — not ad-hoc registry/URL code.
    """
    if command.content is None or (
        not (command.content.subject or command.content.body_text or command.content.body_html)
    ):
        raise SendCommunicationError(
            "CommunicationCommand.content is required before send "
            "(resolve template/links via TemplateResolver / LinkResolver first)",
            details={"reason": "missing_content"},
        )

    intent = command.normalized_intent()
    policy = resolve_intent_policy(intent)
    channel = str(command.channel or "").strip().lower() or "email"
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
                "denial": caps.denial_reasons.get(channel),
            },
        )
    if intent.value not in caps.allowed_intents:
        raise SendCommunicationError(
            f"intent {intent.value!r} is not allowed for entity {caps.entity_type}",
            details={
                "reason": "capability_intent_denied",
                "entity_type": caps.entity_type,
                "intent": intent.value,
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

    enriched_meta: dict[str, Any] = {
        **dict(command.meta or {}),
        "intent": intent.value,
        "intent_purpose": policy.purpose,
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
        correlation_id=command.correlation_id,
        source_event_id=command.source_event_id,
        meta=enriched_meta,
    )
    return await send_communication(
        db,
        executable,
        transport=transport,
        skip_transport=skip_transport,
    )
