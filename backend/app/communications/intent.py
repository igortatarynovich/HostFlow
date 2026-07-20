"""Communication Intent — primary business layer (C0.0).

Sends start as an intent, not as “send email”. Intent drives templates,
channels, link needs, consent, initiator rules, and automation eligibility.
``prepare_and_send_communication`` / ``send_communication`` execute the intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class CommunicationIntent(str, Enum):
    """Stable intent keys. Product modules request these; they do not compose mail."""

    REQUEST_QUESTIONNAIRE = "request_questionnaire"
    REQUEST_DOCUMENTS = "request_documents"
    INVITE_TO_INTERVIEW = "invite_to_interview"
    SEND_OFFER = "send_offer"
    FOLLOW_UP = "follow_up"
    MARKETING_CAMPAIGN = "marketing_campaign"
    GDPR_NOTICE = "gdpr_notice"
    DOCUMENT_EXPIRY_REMINDER = "document_expiry_reminder"
    # Escape hatch for tests / legacy callers until they migrate to a named intent.
    MANUAL_OUTBOUND = "manual_outbound"


@dataclass(frozen=True, slots=True)
class IntentPolicy:
    """What an intent allows. ActionPolicy/stage gates refine further later."""

    intent: CommunicationIntent
    allowed_channels: FrozenSet[str]
    allowed_template_keys: FrozenSet[str]
    link_intents: FrozenSet[str]
    requires_consent: bool
    allows_automation: bool
    allows_manual: bool = True
    purpose: str = "workflow"  # transaction | workflow | marketing


# Seed policies — thin registry for C0.1 extension points (not full product catalog).
_INTENT_POLICIES: dict[CommunicationIntent, IntentPolicy] = {
    CommunicationIntent.REQUEST_QUESTIONNAIRE: IntentPolicy(
        intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
        allowed_channels=frozenset({"email"}),
        allowed_template_keys=frozenset({"questionnaire_invite_email_v1"}),
        link_intents=frozenset({"sales_questionnaire", "candidate_questionnaire"}),
        requires_consent=False,
        allows_automation=True,
        purpose="workflow",
    ),
    CommunicationIntent.REQUEST_DOCUMENTS: IntentPolicy(
        intent=CommunicationIntent.REQUEST_DOCUMENTS,
        allowed_channels=frozenset({"email", "sms"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset({"document_upload"}),
        requires_consent=False,
        allows_automation=True,
        purpose="workflow",
    ),
    CommunicationIntent.INVITE_TO_INTERVIEW: IntentPolicy(
        intent=CommunicationIntent.INVITE_TO_INTERVIEW,
        allowed_channels=frozenset({"email", "sms", "whatsapp"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset({"meeting_booking"}),
        requires_consent=False,
        allows_automation=True,
        purpose="workflow",
    ),
    CommunicationIntent.SEND_OFFER: IntentPolicy(
        intent=CommunicationIntent.SEND_OFFER,
        allowed_channels=frozenset({"email"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset({"offer_review", "proposal_review"}),
        requires_consent=False,
        allows_automation=False,
        purpose="transaction",
    ),
    CommunicationIntent.FOLLOW_UP: IntentPolicy(
        intent=CommunicationIntent.FOLLOW_UP,
        allowed_channels=frozenset({"email", "sms", "whatsapp"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset(),
        requires_consent=False,
        allows_automation=True,
        purpose="workflow",
    ),
    CommunicationIntent.MARKETING_CAMPAIGN: IntentPolicy(
        intent=CommunicationIntent.MARKETING_CAMPAIGN,
        allowed_channels=frozenset({"email", "sms"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset({"unsubscribe"}),
        requires_consent=True,
        allows_automation=True,
        purpose="marketing",
    ),
    CommunicationIntent.GDPR_NOTICE: IntentPolicy(
        intent=CommunicationIntent.GDPR_NOTICE,
        allowed_channels=frozenset({"email"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset({"privacy_notice"}),
        requires_consent=False,
        allows_automation=True,
        purpose="transaction",
    ),
    CommunicationIntent.DOCUMENT_EXPIRY_REMINDER: IntentPolicy(
        intent=CommunicationIntent.DOCUMENT_EXPIRY_REMINDER,
        allowed_channels=frozenset({"email", "sms"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset(),
        requires_consent=False,
        allows_automation=True,
        purpose="workflow",
    ),
    CommunicationIntent.MANUAL_OUTBOUND: IntentPolicy(
        intent=CommunicationIntent.MANUAL_OUTBOUND,
        allowed_channels=frozenset({"email", "sms", "whatsapp"}),
        allowed_template_keys=frozenset(),
        link_intents=frozenset(),
        requires_consent=False,
        allows_automation=False,
        purpose="workflow",
    ),
}


class UnknownCommunicationIntentError(ValueError):
    def __init__(self, intent: str) -> None:
        super().__init__(f"Unknown communication intent: {intent}")
        self.intent = intent


def normalize_intent(value: CommunicationIntent | str | None) -> CommunicationIntent:
    if value is None or value == "":
        return CommunicationIntent.MANUAL_OUTBOUND
    if isinstance(value, CommunicationIntent):
        return value
    key = str(value).strip().lower()
    try:
        return CommunicationIntent(key)
    except ValueError as exc:
        raise UnknownCommunicationIntentError(key) from exc


def resolve_intent_policy(intent: CommunicationIntent | str | None) -> IntentPolicy:
    normalized = normalize_intent(intent)
    policy = _INTENT_POLICIES.get(normalized)
    if policy is None:
        raise UnknownCommunicationIntentError(str(normalized))
    return policy
