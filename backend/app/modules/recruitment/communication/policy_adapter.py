"""Recruitment-owned communication policy adapter (C3).

Owns Recruitment-allowed purposes. Must not import Sales.
"""

from __future__ import annotations

from backend.app.communications.policy_contract import (
    REASON_INCOMPATIBLE,
    REASON_UNKNOWN_PURPOSE,
    CommunicationPolicyDecision,
    CommunicationPolicyRequest,
    allow,
    deny,
)

POLICY_OWNER = "recruitment"
POLICY_VERSION = "recruitment.communication_policy.v1"

# Module-owned allow-list — not duplicated in shared communications layer.
_ALLOWED_PURPOSES = frozenset(
    {
        "submission_acknowledgement",
        "additional_information_request",
        "interview_invitation",
        "document_request",
    }
)
_ALLOWED_RESULT_TYPES = frozenset({"application"})
_ALLOWED_CHANNELS = frozenset({"email", "sms", "whatsapp", "telegram", "system"})


class RecruitmentCommunicationPolicyAdapter:
    policy_owner = POLICY_OWNER
    policy_version = POLICY_VERSION

    def evaluate(self, request: CommunicationPolicyRequest) -> CommunicationPolicyDecision:
        owner = str(request.module_owner or "").strip().lower()
        domain = str(request.communication_domain or "").strip().lower()
        purpose = str(request.communication_purpose or "").strip()
        channel = str(request.channel or "").strip().lower()
        rtype = str(request.result_type or "").strip().lower()

        if owner != POLICY_OWNER or domain != POLICY_OWNER:
            return deny(
                reason_code=REASON_INCOMPATIBLE,
                policy_owner=POLICY_OWNER,
                policy_version=POLICY_VERSION,
                details={
                    "module_owner": owner,
                    "communication_domain": domain,
                    "reason": REASON_INCOMPATIBLE,
                },
            )
        if rtype not in _ALLOWED_RESULT_TYPES:
            return deny(
                reason_code=REASON_INCOMPATIBLE,
                policy_owner=POLICY_OWNER,
                policy_version=POLICY_VERSION,
                details={"result_type": rtype, "reason": REASON_INCOMPATIBLE},
            )
        if channel not in _ALLOWED_CHANNELS:
            return deny(
                reason_code="unknown_channel",
                policy_owner=POLICY_OWNER,
                policy_version=POLICY_VERSION,
                details={"channel": channel, "reason": "unknown_channel"},
            )
        if purpose not in _ALLOWED_PURPOSES:
            return deny(
                reason_code=REASON_UNKNOWN_PURPOSE,
                policy_owner=POLICY_OWNER,
                policy_version=POLICY_VERSION,
                details={
                    "communication_purpose": purpose,
                    "reason": REASON_UNKNOWN_PURPOSE,
                },
            )
        return allow(
            policy_owner=POLICY_OWNER,
            policy_version=POLICY_VERSION,
            details={"communication_purpose": purpose, "channel": channel},
        )
