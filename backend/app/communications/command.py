"""CommunicationCommand — unified prepare/send input (C0.0 / C0.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from backend.app.communications.entity_link import _normalize_entity_type
from backend.app.communications.intent import CommunicationIntent, normalize_intent


@dataclass(frozen=True, slots=True)
class CommunicationOrigin:
    entity_type: str
    entity_id: str

    def normalized(self) -> "CommunicationOrigin":
        return CommunicationOrigin(
            entity_type=_normalize_entity_type(self.entity_type),
            entity_id=str(self.entity_id or "").strip(),
        )


@dataclass(frozen=True, slots=True)
class CommunicationRecipient:
    address: str
    label: str | None = None
    recipient_type: str | None = None
    recipient_id: str | None = None


@dataclass(frozen=True, slots=True)
class SendCommunicationContent:
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    message_type: str = "email"


@dataclass(frozen=True, slots=True)
class ResolvedLinkSnapshot:
    """Provenance of a link minted for this command (LinkResolver result)."""

    link_intent: str
    public_url: str
    token: str | None = None
    expires_at: str | None = None
    variable_name: str = "public_action_url"

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_intent": self.link_intent,
            "public_url": self.public_url,
            "token": self.token,
            "expires_at": self.expires_at,
            "variable_name": self.variable_name,
        }


@dataclass(frozen=True, slots=True)
class CommunicationCommand:
    """Business command produced after Intent → Policy → Resolvers.

    ``intent`` is required — callers must not invent template-only sends.
    ``send_communication`` executes durable writes; it re-validates intent/capabilities.
    """

    tenant_id: str
    origin: CommunicationOrigin
    recipients: Sequence[CommunicationRecipient]
    channel: str
    intent: CommunicationIntent | str
    content: SendCommunicationContent | None = None
    actor_id: str | None = None
    automation_identity: str | None = None
    own_company_id: str | None = None
    related_entities: Sequence[CommunicationOrigin] = ()
    thread_id: str | None = None
    idempotency_key: str | None = None
    purpose: str | None = None
    thread_subject: str | None = None
    delivery_purpose: str | None = None
    template_key: str | None = None
    template_version: int = 1
    locale: str | None = None
    requested_link_intents: Sequence[str] = ()
    resolved_links: Sequence[ResolvedLinkSnapshot] = ()
    render_variables: Mapping[str, Any] = field(default_factory=dict)
    policy_decision: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    source_event_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def normalized_intent(self) -> CommunicationIntent:
        return normalize_intent(self.intent)


# Back-compat name used by early C0.1 tests/callers.
SendCommunicationRequest = CommunicationCommand
