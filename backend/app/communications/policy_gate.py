"""Shared communication policy gate (C3).

Owns: invoke published contract, request/decision shape, fail-closed, decision id.
Does NOT own: Recruitment/Sales purpose lists or module business rules.
"""

from __future__ import annotations

from typing import Any

from backend.app.communications.context_resolver import CommunicationContext
from backend.app.communications.policy_contract import (
    KNOWN_CHANNELS,
    POLICY_CONTRACT,
    REASON_DOMAIN_MISMATCH,
    REASON_INCOMPLETE,
    REASON_NO_ADAPTER,
    REASON_UNKNOWN_CHANNEL,
    CommunicationPolicyDecision,
    CommunicationPolicyPort,
    CommunicationPolicyRequest,
    deny,
)

_ADAPTERS: dict[str, CommunicationPolicyPort] | None = None
GATE_OWNER = "communications"
GATE_VERSION = "communication.policy_gate.v1"


def _load_default_adapters() -> dict[str, CommunicationPolicyPort]:
    # Lazy import of published module policy adapters only (not domain ORM/services).
    from backend.app.modules.recruitment.communication.policy_adapter import (
        RecruitmentCommunicationPolicyAdapter,
    )
    from backend.app.modules.sales.communication.policy_adapter import (
        SalesCommunicationPolicyAdapter,
    )

    return {
        "recruitment": RecruitmentCommunicationPolicyAdapter(),
        "sales": SalesCommunicationPolicyAdapter(),
    }


def registered_policy_adapters() -> dict[str, CommunicationPolicyPort]:
    global _ADAPTERS
    if _ADAPTERS is None:
        _ADAPTERS = _load_default_adapters()
    return dict(_ADAPTERS)


def reset_policy_adapters_for_tests(
    mapping: dict[str, CommunicationPolicyPort] | None = None,
) -> None:
    global _ADAPTERS
    _ADAPTERS = None if mapping is None else dict(mapping)


def _validate_request(request: CommunicationPolicyRequest) -> CommunicationPolicyDecision | None:
    owner = str(request.module_owner or "").strip().lower()
    domain = str(request.communication_domain or "").strip().lower()
    purpose = str(request.communication_purpose or "").strip()
    channel = str(request.channel or "").strip().lower()
    rtype = str(request.result_type or "").strip()
    rid = str(request.result_id or "").strip()
    if not owner or not domain or not purpose or not channel or not rtype or not rid:
        return deny(
            reason_code=REASON_INCOMPLETE,
            policy_owner=GATE_OWNER,
            policy_version=GATE_VERSION,
            details={"reason": REASON_INCOMPLETE, "contract": POLICY_CONTRACT},
        )
    if domain != owner:
        return deny(
            reason_code=REASON_DOMAIN_MISMATCH,
            policy_owner=GATE_OWNER,
            policy_version=GATE_VERSION,
            details={
                "module_owner": owner,
                "communication_domain": domain,
                "reason": REASON_DOMAIN_MISMATCH,
            },
        )
    if channel not in KNOWN_CHANNELS:
        return deny(
            reason_code=REASON_UNKNOWN_CHANNEL,
            policy_owner=GATE_OWNER,
            policy_version=GATE_VERSION,
            details={"channel": channel, "reason": REASON_UNKNOWN_CHANNEL},
        )
    return None


def evaluate_communication_policy(
    request: CommunicationPolicyRequest,
) -> CommunicationPolicyDecision:
    """Fail-closed policy decision via module-owned adapter."""
    early = _validate_request(request)
    if early is not None:
        return early

    owner = str(request.module_owner).strip().lower()
    adapter = registered_policy_adapters().get(owner)
    if adapter is None:
        return deny(
            reason_code=REASON_NO_ADAPTER,
            policy_owner=GATE_OWNER,
            policy_version=GATE_VERSION,
            details={
                "module_owner": owner,
                "reason": REASON_NO_ADAPTER,
                # Explicit: never invent Recruitment when adapter missing.
                "fallback": None,
            },
        )

    decision = adapter.evaluate(request)
    # Shared gate never rewrites allow → Recruitment; trust adapter owner stamp.
    if str(decision.policy_owner or "").strip().lower() != owner:
        return deny(
            reason_code=REASON_NO_ADAPTER,
            policy_owner=GATE_OWNER,
            policy_version=GATE_VERSION,
            details={
                "expected_policy_owner": owner,
                "actual_policy_owner": decision.policy_owner,
                "reason": "policy_owner_mismatch",
            },
        )
    return decision


def evaluate_policy_for_context(
    context: CommunicationContext,
    *,
    communication_purpose: str,
    channel: str,
    locale: str | None = None,
    actor_context: dict[str, Any] | None = None,
) -> CommunicationPolicyDecision:
    """Convenience: CommunicationContext → policy request → decision."""
    return evaluate_communication_policy(
        CommunicationPolicyRequest(
            module_owner=context.module_owner,
            result_type=context.result_type,
            result_id=context.result_id,
            communication_domain=context.communication_domain,
            communication_purpose=communication_purpose,
            channel=channel,
            locale=locale,
            actor_context=actor_context,
            resolver_version=context.resolver_version,
            thread_id=context.thread_id,
        )
    )
