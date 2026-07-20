"""CapabilityResolver — what an actor may send for an entity (C0.0 extension point)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.command import CommunicationOrigin


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


# Thin seed matrix — Candidate + SalesInquiry (+ aliases). Expand later without callers changing.
_ENTITY_CHANNEL_MATRIX: dict[str, tuple[tuple[str, ...], bool]] = {
    "candidate": (("email", "sms", "whatsapp"), True),
    "application": (("email", "sms", "whatsapp"), True),
    "sales_inquiry": (("email", "sms", "whatsapp"), False),  # bulk limited → False for now
    "lead": (("email", "sms", "whatsapp"), False),
    "client_account": (("email", "sms", "whatsapp"), True),
    "contact_person": (("email", "sms", "whatsapp"), True),
    "employee": (("email", "sms", "whatsapp"), False),
    "service_order": (("email",), False),
}

_ENTITY_INTENTS: dict[str, tuple[str, ...]] = {
    "candidate": (
        CommunicationIntent.REQUEST_QUESTIONNAIRE.value,
        CommunicationIntent.REQUEST_DOCUMENTS.value,
        CommunicationIntent.INVITE_TO_INTERVIEW.value,
        CommunicationIntent.SEND_OFFER.value,
        CommunicationIntent.FOLLOW_UP.value,
        CommunicationIntent.MANUAL_OUTBOUND.value,
    ),
    "application": (
        CommunicationIntent.REQUEST_QUESTIONNAIRE.value,
        CommunicationIntent.REQUEST_DOCUMENTS.value,
        CommunicationIntent.INVITE_TO_INTERVIEW.value,
        CommunicationIntent.SEND_OFFER.value,
        CommunicationIntent.FOLLOW_UP.value,
        CommunicationIntent.MANUAL_OUTBOUND.value,
    ),
    "sales_inquiry": (
        CommunicationIntent.REQUEST_QUESTIONNAIRE.value,
        CommunicationIntent.FOLLOW_UP.value,
        CommunicationIntent.GDPR_NOTICE.value,
        CommunicationIntent.MANUAL_OUTBOUND.value,
    ),
    "lead": (
        CommunicationIntent.REQUEST_QUESTIONNAIRE.value,
        CommunicationIntent.FOLLOW_UP.value,
        CommunicationIntent.GDPR_NOTICE.value,
        CommunicationIntent.MANUAL_OUTBOUND.value,
    ),
}


class DefaultCapabilityResolver:
    """Platform default — matrix for Candidate / SalesInquiry first; others conservative."""

    async def resolve(
        self,
        *,
        tenant_id: str,
        origin: CommunicationOrigin,
        actor_id: str | None = None,
    ) -> CommunicationCapabilities:
        del tenant_id, actor_id  # actor rules land with full auth later
        origin = origin.normalized()
        channels, bulk = _ENTITY_CHANNEL_MATRIX.get(
            origin.entity_type, (("email",), False)
        )
        intents = _ENTITY_INTENTS.get(
            origin.entity_type, (CommunicationIntent.MANUAL_OUTBOUND.value,)
        )
        denial: dict[str, str] = {}
        if origin.entity_type == "service_order":
            denial["sms"] = "service_order_via_contact_only"
            denial["whatsapp"] = "service_order_via_contact_only"
            denial["bulk"] = "service_order_bulk_forbidden"
        if origin.entity_type in {"sales_inquiry", "lead"}:
            denial["bulk"] = "bulk_limited_for_inquiry"
        return CommunicationCapabilities(
            entity_type=origin.entity_type,
            entity_id=origin.entity_id,
            allowed_channels=channels,
            allowed_intents=intents,
            bulk_allowed=bulk,
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
