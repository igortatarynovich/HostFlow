"""Communications domain helpers (Communication Context C1–C3)."""

from backend.app.communications.context_resolver import (
    CommunicationContext,
    CommunicationContextResolveError,
    resolve_communication_context,
)
from backend.app.communications.domain_registry import (
    platform_communication_domain_registry,
    reset_communication_domain_registry_for_tests,
)
from backend.app.communications.policy_contract import (
    CommunicationPolicyDecision,
    CommunicationPolicyRequest,
)
from backend.app.communications.policy_gate import (
    evaluate_communication_policy,
    evaluate_policy_for_context,
    reset_policy_adapters_for_tests,
)
from backend.app.communications.result_link import (
    ThreadResultLinkConflictError,
    ThreadResultLinkError,
    ThreadResultLinkUnresolvedError,
    ThreadResultLinkView,
    attach_thread_result_from_confirmed_ledger,
    attach_thread_result_link,
    get_thread_result_link,
    require_confirmed_thread_result_link,
)

__all__ = [
    "CommunicationContext",
    "CommunicationContextResolveError",
    "CommunicationPolicyDecision",
    "CommunicationPolicyRequest",
    "ThreadResultLinkConflictError",
    "ThreadResultLinkError",
    "ThreadResultLinkUnresolvedError",
    "ThreadResultLinkView",
    "attach_thread_result_from_confirmed_ledger",
    "attach_thread_result_link",
    "evaluate_communication_policy",
    "evaluate_policy_for_context",
    "get_thread_result_link",
    "platform_communication_domain_registry",
    "require_confirmed_thread_result_link",
    "reset_communication_domain_registry_for_tests",
    "reset_policy_adapters_for_tests",
    "resolve_communication_context",
]
