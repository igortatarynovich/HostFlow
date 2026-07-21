"""Immutable outbound communication snapshot (C0.1b).

Sufficient to reconstruct what was sent without reading live templates/settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationRecipient,
    ResolvedLinkSnapshot,
)
from backend.app.communications.intent_policy import IntentPolicyResult

SNAPSHOT_SCHEMA = "communications.outbound_snapshot.v1"


@dataclass(frozen=True, slots=True)
class CommunicationOutboundSnapshot:
    intent_key: str
    intent_version: int
    policy_decision: Mapping[str, Any]
    origin: Mapping[str, str]
    recipients: tuple[Mapping[str, Any], ...]
    channel: str
    template_key: str | None
    template_version: int | None
    template_version_id: str | None
    rendered_subject: str | None
    rendered_body_text: str | None
    rendered_body_html: str | None
    resolved_variables: Mapping[str, Any]
    links: tuple[Mapping[str, Any], ...]
    actor_id: str | None
    automation_identity: str | None
    signature: Mapping[str, Any] | None
    compliance_decision: Mapping[str, Any]
    correlation_id: str | None
    source_event_id: str | None
    idempotency_key: str | None
    purpose: str | None
    schema_version: str = SNAPSHOT_SCHEMA
    related_entities: tuple[Mapping[str, str], ...] = ()
    locale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "intent_key": self.intent_key,
            "intent_version": self.intent_version,
            "policy_decision": dict(self.policy_decision or {}),
            "origin": dict(self.origin or {}),
            "related_entities": [dict(x) for x in self.related_entities],
            "recipients": [dict(r) for r in self.recipients],
            "channel": self.channel,
            "locale": self.locale,
            "template_key": self.template_key,
            "template_version": self.template_version,
            "template_version_id": self.template_version_id,
            "rendered_subject": self.rendered_subject,
            "rendered_body_text": self.rendered_body_text,
            "rendered_body_html": self.rendered_body_html,
            "resolved_variables": dict(self.resolved_variables or {}),
            "links": [dict(x) for x in self.links],
            "actor_id": self.actor_id,
            "automation_identity": self.automation_identity,
            "signature": dict(self.signature) if self.signature else None,
            "compliance_decision": dict(self.compliance_decision or {}),
            "correlation_id": self.correlation_id,
            "source_event_id": self.source_event_id,
            "idempotency_key": self.idempotency_key,
            "purpose": self.purpose,
        }


def _recipient_dict(r: CommunicationRecipient) -> dict[str, Any]:
    return {
        "address": r.address,
        "label": r.label,
        "recipient_type": r.recipient_type,
        "recipient_id": r.recipient_id,
    }


def build_outbound_snapshot(
    command: CommunicationCommand,
    *,
    policy: IntentPolicyResult | Mapping[str, Any] | None = None,
    signature: Mapping[str, Any] | None = None,
) -> CommunicationOutboundSnapshot:
    origin = command.origin.normalized()
    content = command.content
    if isinstance(policy, IntentPolicyResult):
        policy_dict = policy.to_dict()
        intent_version = policy.intent_version
        compliance = {
            "requires_consent": policy.requires_consent,
            "compliance_profile": policy.compliance_profile,
            "allowed": policy.allowed,
            "reason_code": policy.reason_code,
        }
        intent_key = policy.intent_key
    else:
        policy_dict = dict(policy or command.policy_decision or {})
        intent_version = int(policy_dict.get("intent_version") or 1)
        compliance = dict(policy_dict.get("compliance_decision") or {})
        if not compliance:
            compliance = {
                "requires_consent": bool(policy_dict.get("requires_consent")),
                "compliance_profile": policy_dict.get("compliance_profile"),
                "allowed": policy_dict.get("allowed", True),
                "reason_code": policy_dict.get("reason_code"),
            }
        intent_key = str(
            policy_dict.get("intent_key") or command.normalized_intent().value
        )

    links: Sequence[ResolvedLinkSnapshot] = command.resolved_links or ()
    return CommunicationOutboundSnapshot(
        intent_key=intent_key,
        intent_version=intent_version,
        policy_decision=policy_dict,
        origin={"entity_type": origin.entity_type, "entity_id": origin.entity_id},
        related_entities=tuple(
            {"entity_type": r.normalized().entity_type, "entity_id": r.normalized().entity_id}
            for r in (command.related_entities or ())
        ),
        recipients=tuple(_recipient_dict(r) for r in command.recipients),
        channel=str(command.channel or "").strip().lower(),
        locale=command.locale,
        template_key=command.template_key,
        template_version=int(command.template_version or 1) if command.template_key else None,
        template_version_id=(
            str(command.template_version_id).strip() if command.template_version_id else None
        ),
        rendered_subject=(content.subject if content else None),
        rendered_body_text=(content.body_text if content else None),
        rendered_body_html=(content.body_html if content else None),
        resolved_variables=dict(command.render_variables or {}),
        links=tuple(lnk.to_dict() for lnk in links),
        actor_id=command.actor_id,
        automation_identity=command.automation_identity,
        signature=dict(signature) if signature else None,
        compliance_decision=compliance,
        correlation_id=command.correlation_id,
        source_event_id=command.source_event_id,
        idempotency_key=command.idempotency_key,
        purpose=command.purpose,
    )
