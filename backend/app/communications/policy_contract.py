"""Published communication policy contract (C3).

Shared layer owns the request/decision shape and fail-closed gate.
Module-owned adapters own which purposes are allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from uuid import uuid4

POLICY_CONTRACT = "communication.policy_contract.v1"

# Transport channels known to the shared layer (not module purposes).
KNOWN_CHANNELS = frozenset({"email", "sms", "whatsapp", "telegram", "system"})

REASON_ALLOWED = "allowed"
REASON_NO_ADAPTER = "missing_policy_adapter"
REASON_UNKNOWN_PURPOSE = "unknown_purpose"
REASON_INCOMPATIBLE = "incompatible_module_purpose"
REASON_UNKNOWN_CHANNEL = "unknown_channel"
REASON_DOMAIN_MISMATCH = "communication_domain_mismatch"
REASON_INCOMPLETE = "incomplete_policy_request"
REASON_DENIED_BY_POLICY = "denied_by_module_policy"


@dataclass(frozen=True, slots=True)
class CommunicationPolicyRequest:
    module_owner: str
    result_type: str
    result_id: str
    communication_domain: str
    communication_purpose: str
    channel: str
    locale: Optional[str] = None
    actor_context: Optional[dict[str, Any]] = None
    resolver_version: Optional[str] = None
    thread_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CommunicationPolicyDecision:
    allowed: bool
    reason_code: str
    policy_owner: str
    policy_version: str
    decision_id: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "policy_owner": self.policy_owner,
            "policy_version": self.policy_version,
            "decision_id": self.decision_id,
            "details": dict(self.details),
        }


def new_decision_id() -> str:
    return str(uuid4())


def deny(
    *,
    reason_code: str,
    policy_owner: str,
    policy_version: str,
    details: dict[str, Any] | None = None,
) -> CommunicationPolicyDecision:
    return CommunicationPolicyDecision(
        allowed=False,
        reason_code=reason_code,
        policy_owner=policy_owner,
        policy_version=policy_version,
        decision_id=new_decision_id(),
        details=dict(details or {}),
    )


def allow(
    *,
    policy_owner: str,
    policy_version: str,
    details: dict[str, Any] | None = None,
) -> CommunicationPolicyDecision:
    return CommunicationPolicyDecision(
        allowed=True,
        reason_code=REASON_ALLOWED,
        policy_owner=policy_owner,
        policy_version=policy_version,
        decision_id=new_decision_id(),
        details=dict(details or {}),
    )


class CommunicationPolicyPort(Protocol):
    """Inbound port implemented by Recruitment / Sales policy adapters."""

    policy_owner: str
    policy_version: str

    def evaluate(self, request: CommunicationPolicyRequest) -> CommunicationPolicyDecision: ...
