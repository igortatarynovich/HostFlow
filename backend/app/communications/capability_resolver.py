"""CapabilityResolver — derived from Intent Registry entity profiles (C0.1b).

Do not maintain a parallel entity×intent matrix here; use intent_registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from backend.app.communications.command import CommunicationOrigin
from backend.app.communications.intent_registry import (
    UnknownEntityProfileError,
    get_entity_profile,
    intents_for_entity,
)


@dataclass(frozen=True, slots=True)
class ResolvedRecipientHint:
    address: str
    channel: str
    label: str | None = None
    recipient_type: str | None = None
    recipient_id: str | None = None


@dataclass(frozen=True, slots=True)
class CommunicationCapabilities:
    entity_type: str
    entity_id: str
    allowed_channels: tuple[str, ...]
    allowed_intents: tuple[str, ...]
    bulk_allowed: bool
    recipient_hints: tuple[ResolvedRecipientHint, ...] = ()
    denial_reasons: dict[str, str] = field(default_factory=dict)
    existing_thread_id: str | None = None


class CapabilityResolver(Protocol):
    async def resolve(
        self,
        *,
        tenant_id: str,
        origin: CommunicationOrigin,
        actor_id: str | None = None,
    ) -> CommunicationCapabilities: ...


class DefaultCapabilityResolver:
    """Platform default — channels/intents from Intent Registry only."""

    async def resolve(
        self,
        *,
        tenant_id: str,
        origin: CommunicationOrigin,
        actor_id: str | None = None,
    ) -> CommunicationCapabilities:
        del tenant_id, actor_id
        origin = origin.normalized()
        try:
            profile = get_entity_profile(origin.entity_type)
        except UnknownEntityProfileError:
            return CommunicationCapabilities(
                entity_type=origin.entity_type,
                entity_id=origin.entity_id,
                allowed_channels=(),
                allowed_intents=(),
                bulk_allowed=False,
                denial_reasons={
                    "entity": "unknown_entity_type",
                    "channel": "unknown_entity_type",
                    "intent": "unknown_entity_type",
                },
            )
        intents = intents_for_entity(origin.entity_type)
        denial = dict(profile.channel_denial_reasons)
        if not profile.bulk_allowed:
            denial.setdefault("bulk", "bulk_not_allowed")
        return CommunicationCapabilities(
            entity_type=origin.entity_type,
            entity_id=origin.entity_id,
            allowed_channels=tuple(sorted(profile.allowed_channels)),
            allowed_intents=intents,
            bulk_allowed=profile.bulk_allowed,
            denial_reasons=denial,
        )


_default_capability_resolver: CapabilityResolver = DefaultCapabilityResolver()


def get_capability_resolver() -> CapabilityResolver:
    return _default_capability_resolver


async def resolve_communication_capabilities(
    *,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None = None,
    resolver: CapabilityResolver | None = None,
) -> CommunicationCapabilities:
    impl = resolver or get_capability_resolver()
    return await impl.resolve(
        tenant_id=tenant_id,
        origin=CommunicationOrigin(entity_type=entity_type, entity_id=entity_id),
        actor_id=actor_id,
    )
