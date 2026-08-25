"""Unified Communication Intent Registry — single SoT (C0.1b).

New intents MUST be added here. Policy, capability matrix, and template
strategies derive from these definitions — do not duplicate elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping


REGISTRY_VERSION = 1


@dataclass(frozen=True, slots=True)
class IntentDefinition:
    intent_key: str
    purpose: str  # transaction | workflow | marketing
    allowed_entity_types: FrozenSet[str]
    allowed_channels: FrozenSet[str]
    allows_automation: bool
    allows_manual: bool
    requires_consent: bool
    link_intents: FrozenSet[str]
    allowed_template_keys: FrozenSet[str]
    default_template_key: str | None
    template_strategy: str  # fixed | none | catalog
    compliance_profile: str | None = None
    version: int = 1
    bulk_eligible: bool = False


@dataclass(frozen=True, slots=True)
class EntityCommunicationProfile:
    entity_type: str
    allowed_channels: FrozenSet[str]
    bulk_allowed: bool
    channel_denial_reasons: Mapping[str, str]


def _fs(*items: str) -> frozenset[str]:
    return frozenset(items)


# ── Entity profiles (channel / bulk). Intent eligibility lives on IntentDefinition. ──

_ENTITY_PROFILES: tuple[EntityCommunicationProfile, ...] = (
    EntityCommunicationProfile(
        entity_type="candidate",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=True,
        channel_denial_reasons={},
    ),
    EntityCommunicationProfile(
        entity_type="application",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=True,
        channel_denial_reasons={},
    ),
    EntityCommunicationProfile(
        entity_type="sales_inquiry",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=False,
        channel_denial_reasons={"bulk": "bulk_limited_for_inquiry"},
    ),
    EntityCommunicationProfile(
        entity_type="lead",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=False,
        channel_denial_reasons={"bulk": "bulk_limited_for_inquiry"},
    ),
    EntityCommunicationProfile(
        entity_type="client_account",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=True,
        channel_denial_reasons={},
    ),
    EntityCommunicationProfile(
        entity_type="contact_person",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=True,
        channel_denial_reasons={},
    ),
    EntityCommunicationProfile(
        entity_type="employee",
        allowed_channels=_fs("email", "sms", "whatsapp"),
        bulk_allowed=False,
        channel_denial_reasons={"bulk": "employee_bulk_hr_rules"},
    ),
    EntityCommunicationProfile(
        entity_type="service_order",
        allowed_channels=_fs("email"),
        bulk_allowed=False,
        channel_denial_reasons={
            "sms": "service_order_via_contact_only",
            "whatsapp": "service_order_via_contact_only",
            "bulk": "service_order_bulk_forbidden",
        },
    ),
    EntityCommunicationProfile(
        entity_type="company",
        allowed_channels=_fs("email"),
        bulk_allowed=False,
        channel_denial_reasons={},
    ),
    EntityCommunicationProfile(
        entity_type="user",
        allowed_channels=_fs("email"),
        bulk_allowed=False,
        channel_denial_reasons={},
    ),
)

_RECRUITMENT_ENTITIES = _fs("candidate", "application")
_SALES_ENTITIES = _fs("sales_inquiry", "lead")
_CLIENT_ENTITIES = _fs("client_account", "contact_person")
_BROAD_ENTITIES = _RECRUITMENT_ENTITIES | _SALES_ENTITIES | _CLIENT_ENTITIES | _fs(
    "employee", "company", "user", "service_order"
)

# ── Intent definitions (SoT) ──

_INTENT_DEFINITIONS: tuple[IntentDefinition, ...] = (
    IntentDefinition(
        intent_key="request_questionnaire",
        purpose="workflow",
        allowed_entity_types=_RECRUITMENT_ENTITIES | _SALES_ENTITIES,
        allowed_channels=_fs("email"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs("sales_questionnaire", "candidate_questionnaire"),
        allowed_template_keys=_fs("questionnaire_invite_email_v1"),
        default_template_key="questionnaire_invite_email_v1",
        template_strategy="fixed",
        compliance_profile="workflow_transactional",
    ),
    IntentDefinition(
        intent_key="request_documents",
        purpose="workflow",
        allowed_entity_types=_RECRUITMENT_ENTITIES,
        allowed_channels=_fs("email", "sms"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs("document_upload"),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="workflow_transactional",
    ),
    IntentDefinition(
        intent_key="invite_to_interview",
        purpose="workflow",
        allowed_entity_types=_RECRUITMENT_ENTITIES,
        allowed_channels=_fs("email", "sms", "whatsapp"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs("meeting_booking"),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="workflow_transactional",
    ),
    IntentDefinition(
        intent_key="send_offer",
        purpose="transaction",
        allowed_entity_types=_RECRUITMENT_ENTITIES,
        allowed_channels=_fs("email"),
        allows_automation=False,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs("offer_review", "proposal_review"),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="workflow_transactional",
    ),
    IntentDefinition(
        intent_key="follow_up",
        purpose="workflow",
        allowed_entity_types=_RECRUITMENT_ENTITIES | _SALES_ENTITIES | _CLIENT_ENTITIES,
        allowed_channels=_fs("email", "sms", "whatsapp"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs(),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="workflow_transactional",
    ),
    IntentDefinition(
        intent_key="marketing_campaign",
        purpose="marketing",
        allowed_entity_types=_RECRUITMENT_ENTITIES | _CLIENT_ENTITIES | _fs("lead"),
        allowed_channels=_fs("email", "sms"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=True,
        link_intents=_fs("unsubscribe"),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="catalog",
        compliance_profile="marketing_consent",
        bulk_eligible=True,
    ),
    IntentDefinition(
        intent_key="gdpr_notice",
        purpose="transaction",
        allowed_entity_types=_SALES_ENTITIES
        | _CLIENT_ENTITIES
        | _RECRUITMENT_ENTITIES
        | _fs("candidate"),
        allowed_channels=_fs("email"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs("privacy_notice"),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="gdpr_notice",
    ),
    IntentDefinition(
        intent_key="document_expiry_reminder",
        purpose="workflow",
        allowed_entity_types=_RECRUITMENT_ENTITIES | _fs("employee", "client_account"),
        allowed_channels=_fs("email", "sms"),
        allows_automation=True,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs(),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="workflow_transactional",
    ),
    IntentDefinition(
        intent_key="manual_outbound",
        purpose="workflow",
        allowed_entity_types=_BROAD_ENTITIES,
        allowed_channels=_fs("email", "sms", "whatsapp"),
        allows_automation=False,
        allows_manual=True,
        requires_consent=False,
        link_intents=_fs(),
        allowed_template_keys=_fs(),
        default_template_key=None,
        template_strategy="none",
        compliance_profile="workflow_transactional",
    ),
)

_INTENT_BY_KEY: dict[str, IntentDefinition] = {d.intent_key: d for d in _INTENT_DEFINITIONS}
_ENTITY_BY_TYPE: dict[str, EntityCommunicationProfile] = {
    p.entity_type: p for p in _ENTITY_PROFILES
}


class UnknownIntentRegistryError(LookupError):
    def __init__(self, intent_key: str) -> None:
        super().__init__(f"Intent not in Communication Intent Registry: {intent_key}")
        self.intent_key = intent_key


class UnknownEntityProfileError(LookupError):
    def __init__(self, entity_type: str) -> None:
        super().__init__(f"Entity type not in Communication entity profiles: {entity_type}")
        self.entity_type = entity_type


def list_intent_definitions() -> tuple[IntentDefinition, ...]:
    return _INTENT_DEFINITIONS


def list_entity_profiles() -> tuple[EntityCommunicationProfile, ...]:
    return _ENTITY_PROFILES


def get_intent_definition(intent_key: str) -> IntentDefinition:
    key = str(intent_key or "").strip().lower()
    definition = _INTENT_BY_KEY.get(key)
    if definition is None:
        raise UnknownIntentRegistryError(key)
    return definition


def get_entity_profile(entity_type: str) -> EntityCommunicationProfile:
    key = str(entity_type or "").strip().lower()
    profile = _ENTITY_BY_TYPE.get(key)
    if profile is None:
        raise UnknownEntityProfileError(key)
    return profile


def intents_for_entity(entity_type: str) -> tuple[str, ...]:
    key = str(entity_type or "").strip().lower()
    return tuple(
        sorted(
            d.intent_key
            for d in _INTENT_DEFINITIONS
            if key in d.allowed_entity_types
        )
    )


def is_combination_allowed(
    *,
    entity_type: str,
    intent_key: str,
    channel: str,
) -> bool:
    """Deny-by-default matrix check derived solely from the registry."""
    try:
        definition = get_intent_definition(intent_key)
        profile = get_entity_profile(entity_type)
    except (UnknownIntentRegistryError, UnknownEntityProfileError):
        return False
    ch = str(channel or "").strip().lower()
    et = str(entity_type or "").strip().lower()
    if et not in definition.allowed_entity_types:
        return False
    if ch not in definition.allowed_channels:
        return False
    if ch not in profile.allowed_channels:
        return False
    return True


def iter_allowed_matrix() -> Iterable[tuple[str, str, str]]:
    """All allowed (entity_type, intent_key, channel) triples from registry."""
    for definition in _INTENT_DEFINITIONS:
        for entity_type in sorted(definition.allowed_entity_types):
            profile = _ENTITY_BY_TYPE.get(entity_type)
            if profile is None:
                continue
            for channel in sorted(definition.allowed_channels & profile.allowed_channels):
                yield entity_type, definition.intent_key, channel
