"""C0.2 — normalized inbound DTO + resolution / ingest result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ResolutionReason = Literal[
    "reply_headers",
    "provider_thread",
    "known_participant",
    "entity_contact",
    "manual",
    "unresolved",
]

RESOLUTION_REASONS: frozenset[str] = frozenset(
    {
        "reply_headers",
        "provider_thread",
        "known_participant",
        "entity_contact",
        "manual",
        "unresolved",
    }
)

INBOUND_AUDIT_SCHEMA = "communications.inbound_audit.v1"


@dataclass(frozen=True, slots=True)
class NormalizedInboundMessage:
    """Provider-agnostic inbound message after normalization."""

    tenant_id: str
    channel: str
    provider: str | None = None
    channel_account_id: str | None = None
    provider_thread_ref: str | None = None
    external_message_ref: str | None = None
    subject: str | None = None
    sender_address: str | None = None
    sender_label: str | None = None
    recipient_address: str | None = None
    recipient_label: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    received_at: datetime | None = None
    headers: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    # Optional operator / API hints (manual resolution).
    hinted_entity_type: str | None = None
    hinted_entity_id: str | None = None
    linked_candidate_id: str | None = None
    linked_company_id: str | None = None
    cc: tuple[str, ...] = ()
    bcc: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InboundResolution:
    reason: ResolutionReason
    thread_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    correlation_id: str | None = None
    matched_outbound_message_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_linked(self) -> bool:
        return self.reason != "unresolved" and bool(self.thread_id or self.entity_id)

    @property
    def has_entity(self) -> bool:
        return bool(self.entity_type and self.entity_id)


@dataclass(frozen=True, slots=True)
class InboundIngestResult:
    thread_id: str
    message_id: str
    created_thread: bool
    duplicate_message: bool
    resolution: InboundResolution
    entity_link_ids: tuple[str, ...] = ()
    unresolved_id: str | None = None
    correlation_id: str | None = None
