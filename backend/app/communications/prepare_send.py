"""prepare_and_send_communication — IntentPolicyResult gate then platform send."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.command import CommunicationCommand, SendCommunicationContent
from backend.app.communications.intent_policy import evaluate_intent_policy
from backend.app.communications.send_communication import (
    SendCommunicationError,
    SendCommunicationResult,
    TransportFn,
    send_communication,
)
from backend.app.communications.snapshot import build_outbound_snapshot


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
) -> SendCommunicationResult:
    """Evaluate typed IntentPolicyResult, then execute durable send.

    Forbidden combinations are denied before message/outbox creation.
    """
    if command.content is None or (
        not (command.content.subject or command.content.body_text or command.content.body_html)
    ):
        raise SendCommunicationError(
            "CommunicationCommand.content is required before send",
            details={"reason": "missing_content"},
        )

    origin = command.origin.normalized()
    channel = _trim(command.channel).lower() or "email"
    intent = command.normalized_intent()
    automation = bool(_trim(command.automation_identity))

    policy = evaluate_intent_policy(
        intent_key=intent.value,
        entity_type=origin.entity_type,
        channel=channel,
        automation=automation,
        template_key=command.template_key,
    )
    if not policy.allowed:
        raise SendCommunicationError(
            policy.reason_message,
            details={
                "reason": policy.reason_code,
                "intent": policy.intent_key,
                "entity_type": origin.entity_type,
                "channel": channel,
                "policy": policy.to_dict(),
            },
        )

    signature_meta = dict((command.meta or {}).get("signature") or {}) or None
    snapshot = build_outbound_snapshot(
        command,
        policy=policy,
        signature=signature_meta,
    )

    enriched_meta: dict[str, Any] = {
        **dict(command.meta or {}),
        "intent": policy.intent_key,
        "intent_purpose": policy.purpose,
        "policy_decision": policy.to_dict(),
        "snapshot": snapshot.to_dict(),
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
        origin=origin,
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
        delivery_purpose=command.delivery_purpose or command.purpose or policy.purpose,
        template_key=command.template_key or policy.default_template_key,
        template_version=command.template_version,
        locale=command.locale,
        requested_link_intents=command.requested_link_intents,
        resolved_links=command.resolved_links,
        render_variables=command.render_variables,
        policy_decision=policy.to_dict(),
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
