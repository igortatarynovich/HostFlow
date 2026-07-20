"""Typed IntentPolicyResult — evaluate Intent against registry matrix (C0.1b)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from backend.app.communications.intent_registry import (
    IntentDefinition,
    UnknownEntityProfileError,
    UnknownIntentRegistryError,
    get_entity_profile,
    get_intent_definition,
    is_combination_allowed,
)


@dataclass(frozen=True, slots=True)
class IntentPolicyResult:
    allowed: bool
    reason_code: str
    reason_message: str
    intent_key: str
    intent_version: int
    purpose: str
    channel: str | None
    allowed_channels: tuple[str, ...]
    entity_type: str | None
    requires_consent: bool
    allows_automation: bool
    allows_manual: bool
    required_link_intents: tuple[str, ...]
    allowed_template_keys: tuple[str, ...]
    default_template_key: str | None
    template_strategy: str
    compliance_profile: str | None
    audit: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "reason_message": self.reason_message,
            "intent_key": self.intent_key,
            "intent_version": self.intent_version,
            "purpose": self.purpose,
            "channel": self.channel,
            "allowed_channels": list(self.allowed_channels),
            "entity_type": self.entity_type,
            "requires_consent": self.requires_consent,
            "allows_automation": self.allows_automation,
            "allows_manual": self.allows_manual,
            "required_link_intents": list(self.required_link_intents),
            "allowed_template_keys": list(self.allowed_template_keys),
            "default_template_key": self.default_template_key,
            "template_strategy": self.template_strategy,
            "compliance_profile": self.compliance_profile,
            "audit": dict(self.audit or {}),
        }


def _deny(
    *,
    definition: IntentDefinition | None,
    intent_key: str,
    entity_type: str | None,
    channel: str | None,
    reason_code: str,
    reason_message: str,
    audit: Mapping[str, Any] | None = None,
) -> IntentPolicyResult:
    return IntentPolicyResult(
        allowed=False,
        reason_code=reason_code,
        reason_message=reason_message,
        intent_key=intent_key,
        intent_version=int(definition.version) if definition else 0,
        purpose=definition.purpose if definition else "",
        channel=channel,
        allowed_channels=tuple(sorted(definition.allowed_channels)) if definition else (),
        entity_type=entity_type,
        requires_consent=bool(definition.requires_consent) if definition else False,
        allows_automation=bool(definition.allows_automation) if definition else False,
        allows_manual=bool(definition.allows_manual) if definition else False,
        required_link_intents=tuple(sorted(definition.link_intents)) if definition else (),
        allowed_template_keys=tuple(sorted(definition.allowed_template_keys))
        if definition
        else (),
        default_template_key=definition.default_template_key if definition else None,
        template_strategy=definition.template_strategy if definition else "none",
        compliance_profile=definition.compliance_profile if definition else None,
        audit={
            "registry_version": 1,
            **dict(audit or {}),
        },
    )


def evaluate_intent_policy(
    *,
    intent_key: str,
    entity_type: str,
    channel: str,
    automation: bool = False,
    template_key: str | None = None,
) -> IntentPolicyResult:
    """Evaluate entity × intent × channel (+ automation/template) against the registry.

    Unknown combinations deny by default — before any message/outbox write.
    """
    key = str(intent_key or "").strip().lower()
    entity = str(entity_type or "").strip().lower()
    ch = str(channel or "").strip().lower()

    try:
        definition = get_intent_definition(key)
    except UnknownIntentRegistryError:
        return _deny(
            definition=None,
            intent_key=key,
            entity_type=entity or None,
            channel=ch or None,
            reason_code="unknown_intent",
            reason_message=f"Intent {key!r} is not registered",
        )

    try:
        profile = get_entity_profile(entity)
    except UnknownEntityProfileError:
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity or None,
            channel=ch or None,
            reason_code="unknown_entity_type",
            reason_message=f"Entity type {entity!r} has no communication profile",
        )

    if entity not in definition.allowed_entity_types:
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch or None,
            reason_code="intent_entity_denied",
            reason_message=f"Intent {key!r} is not allowed for entity {entity!r}",
            audit={"allowed_entity_types": sorted(definition.allowed_entity_types)},
        )

    if ch not in definition.allowed_channels:
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch or None,
            reason_code="intent_channel_denied",
            reason_message=f"Channel {ch!r} is not allowed for intent {key!r}",
            audit={"allowed_channels": sorted(definition.allowed_channels)},
        )

    if ch not in profile.allowed_channels:
        denial = profile.channel_denial_reasons.get(ch) or "entity_channel_denied"
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch,
            reason_code="capability_channel_denied",
            reason_message=f"Channel {ch!r} is not allowed for entity {entity!r}",
            audit={"denial": denial},
        )

    if not is_combination_allowed(
        entity_type=entity, intent_key=key, channel=ch
    ):
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch,
            reason_code="combination_denied",
            reason_message=(
                f"Combination entity={entity!r} intent={key!r} channel={ch!r} is denied"
            ),
        )

    if automation and not definition.allows_automation:
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch,
            reason_code="automation_denied",
            reason_message=f"Intent {key!r} does not allow automation",
        )

    if not automation and not definition.allows_manual:
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch,
            reason_code="manual_denied",
            reason_message=f"Intent {key!r} does not allow manual send",
        )

    tpl = str(template_key or "").strip() or None
    if tpl and definition.allowed_template_keys and tpl not in definition.allowed_template_keys:
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch,
            reason_code="intent_template_denied",
            reason_message=f"Template {tpl!r} is not allowed for intent {key!r}",
            audit={"allowed_template_keys": sorted(definition.allowed_template_keys)},
        )

    # Intent-bound product templates cannot ride a different intent.
    if tpl == "questionnaire_invite_email_v1" and key != "request_questionnaire":
        return _deny(
            definition=definition,
            intent_key=key,
            entity_type=entity,
            channel=ch,
            reason_code="intent_required_for_template",
            reason_message="template 'questionnaire_invite_email_v1' requires intent 'request_questionnaire'",
            audit={"required_intent": "request_questionnaire", "template_key": tpl},
        )

    return IntentPolicyResult(
        allowed=True,
        reason_code="allowed",
        reason_message="Intent policy allows this communication",
        intent_key=key,
        intent_version=int(definition.version),
        purpose=definition.purpose,
        channel=ch,
        allowed_channels=tuple(sorted(definition.allowed_channels & profile.allowed_channels)),
        entity_type=entity,
        requires_consent=definition.requires_consent,
        allows_automation=definition.allows_automation,
        allows_manual=definition.allows_manual,
        required_link_intents=tuple(sorted(definition.link_intents)),
        allowed_template_keys=tuple(sorted(definition.allowed_template_keys)),
        default_template_key=definition.default_template_key,
        template_strategy=definition.template_strategy,
        compliance_profile=definition.compliance_profile,
        audit={
            "registry_version": 1,
            "bulk_allowed": profile.bulk_allowed,
            "bulk_eligible_intent": definition.bulk_eligible,
        },
    )
