"""Communication Intent — enum façade over the unified Intent Registry (C0.1b).

Registry SoT: ``intent_registry.py``. Do not add parallel policy tables here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet

from backend.app.communications.intent_registry import (
    IntentDefinition,
    UnknownIntentRegistryError,
    get_intent_definition,
    list_intent_definitions,
)


class CommunicationIntent(str, Enum):
    """Stable intent keys — members must match Intent Registry entries."""

    REQUEST_QUESTIONNAIRE = "request_questionnaire"
    REQUEST_DOCUMENTS = "request_documents"
    INVITE_TO_INTERVIEW = "invite_to_interview"
    SEND_OFFER = "send_offer"
    FOLLOW_UP = "follow_up"
    MARKETING_CAMPAIGN = "marketing_campaign"
    GDPR_NOTICE = "gdpr_notice"
    DOCUMENT_EXPIRY_REMINDER = "document_expiry_reminder"
    MANUAL_OUTBOUND = "manual_outbound"


@dataclass(frozen=True, slots=True)
class IntentPolicy:
    """Backward-compatible view of IntentDefinition for C0.1 callers."""

    intent: CommunicationIntent
    allowed_channels: FrozenSet[str]
    allowed_template_keys: FrozenSet[str]
    link_intents: FrozenSet[str]
    requires_consent: bool
    allows_automation: bool
    allows_manual: bool = True
    purpose: str = "workflow"


class UnknownCommunicationIntentError(ValueError):
    def __init__(self, intent: str) -> None:
        super().__init__(f"Unknown communication intent: {intent}")
        self.intent = intent


def normalize_intent(value: CommunicationIntent | str | None) -> CommunicationIntent:
    if value is None or value == "":
        return CommunicationIntent.MANUAL_OUTBOUND
    if isinstance(value, CommunicationIntent):
        # Ensure registry has the key (fail closed for drift).
        get_intent_definition(value.value)
        return value
    key = str(value).strip().lower()
    try:
        get_intent_definition(key)
        return CommunicationIntent(key)
    except (UnknownIntentRegistryError, ValueError) as exc:
        raise UnknownCommunicationIntentError(key) from exc


def _definition_to_policy(definition: IntentDefinition) -> IntentPolicy:
    return IntentPolicy(
        intent=CommunicationIntent(definition.intent_key),
        allowed_channels=definition.allowed_channels,
        allowed_template_keys=definition.allowed_template_keys,
        link_intents=definition.link_intents,
        requires_consent=definition.requires_consent,
        allows_automation=definition.allows_automation,
        allows_manual=definition.allows_manual,
        purpose=definition.purpose,
    )


def resolve_intent_policy(intent: CommunicationIntent | str | None) -> IntentPolicy:
    """Legacy helper — prefer ``evaluate_intent_policy`` for typed results."""
    normalized = normalize_intent(intent)
    return _definition_to_policy(get_intent_definition(normalized.value))


def assert_enum_matches_registry() -> None:
    """Dev/test helper: enum members ↔ registry keys must be identical sets."""
    enum_keys = {m.value for m in CommunicationIntent}
    registry_keys = {d.intent_key for d in list_intent_definitions()}
    if enum_keys != registry_keys:
        raise RuntimeError(
            "CommunicationIntent enum drifted from Intent Registry: "
            f"only_enum={sorted(enum_keys - registry_keys)} "
            f"only_registry={sorted(registry_keys - enum_keys)}"
        )
