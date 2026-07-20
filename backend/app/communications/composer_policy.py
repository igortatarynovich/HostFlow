"""C1.1 — backend authority for Composer outbound (frontend context is display-only).

Re-evaluates intent × channel × origin × actor against platform policy on every send.
Protects against stale ThreadContext and direct API calls that bypass the UI allow-list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.capability_resolver import DefaultCapabilityResolver
from backend.app.communications.command import CommunicationOrigin
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.intent_policy import evaluate_intent_policy
from backend.app.models.communication import CommunicationThread


@dataclass(frozen=True, slots=True)
class ComposerPolicyDenial:
    reason_code: str
    reason_message: str
    details: dict[str, Any]


class ComposerPolicyError(Exception):
    def __init__(self, denial: ComposerPolicyDenial):
        self.denial = denial
        super().__init__(denial.reason_message)


async def enforce_manual_outbound_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_id: str | None,
    intent_key: str | None,
    channel: str | None = None,
) -> dict[str, Any]:
    """Authority check for interactive Composer outbound (not Campaign/Automation)."""
    if thread.is_archived:
        raise ComposerPolicyError(
            ComposerPolicyDenial(
                reason_code="thread_archived",
                reason_message="Cannot compose on an archived thread",
                details={"thread_id": str(thread.id)},
            )
        )

    from backend.app.communications.entity_link import get_thread_entity_links

    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=str(thread.id)
    )
    if links:
        origin = CommunicationOrigin(
            entity_type=links[0].entity_type, entity_id=links[0].entity_id
        )
    else:
        origin = CommunicationOrigin(
            entity_type=str(thread.entity_type or "lead"),
            entity_id=str(thread.entity_id or thread.id),
        )

    caps = await DefaultCapabilityResolver().resolve(
        tenant_id=tenant_id,
        origin=origin,
        actor_id=actor_id,
    )
    ch = str(channel or thread.channel or "").strip().lower()
    intent = str(intent_key or CommunicationIntent.MANUAL_OUTBOUND.value).strip().lower()

    if not caps.allowed_intents:
        raise ComposerPolicyError(
            ComposerPolicyDenial(
                reason_code="no_allowed_intents",
                reason_message="No intents allowed for this thread origin",
                details={
                    "origin": {"entity_type": caps.entity_type, "entity_id": caps.entity_id},
                    "policy_denials": dict(caps.denial_reasons or {}),
                },
            )
        )
    if intent not in caps.allowed_intents:
        raise ComposerPolicyError(
            ComposerPolicyDenial(
                reason_code="intent_not_allowed",
                reason_message=f"Intent '{intent}' is not allowed for this origin",
                details={
                    "intent": intent,
                    "allowed_intents": list(caps.allowed_intents),
                    "stale_context": True,
                },
            )
        )
    if ch not in caps.allowed_channels:
        raise ComposerPolicyError(
            ComposerPolicyDenial(
                reason_code="channel_not_allowed",
                reason_message=f"Channel '{ch}' is not allowed for this origin",
                details={
                    "channel": ch,
                    "allowed_channels": list(caps.allowed_channels),
                    "stale_context": True,
                },
            )
        )

    policy = evaluate_intent_policy(
        intent_key=intent,
        entity_type=caps.entity_type,
        channel=ch,
        automation=False,
    )
    if not policy.allowed:
        raise ComposerPolicyError(
            ComposerPolicyDenial(
                reason_code=policy.reason_code or "intent_policy_denied",
                reason_message=policy.reason_message or "Intent policy denied",
                details={
                    "policy": policy.to_dict(),
                    "stale_context": True,
                },
            )
        )

    return {
        "intent": intent,
        "channel": ch,
        "origin": {"entity_type": caps.entity_type, "entity_id": caps.entity_id},
        "policy": policy.to_dict(),
    }


__all__ = [
    "ComposerPolicyDenial",
    "ComposerPolicyError",
    "enforce_manual_outbound_policy",
]
