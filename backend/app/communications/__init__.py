"""Communications domain helpers (Communication Context C1–C5)."""

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
from backend.app.communications.entity_link import (
    ThreadEntityLinkError,
    ThreadEntityLinkRequiredError,
    ThreadEntityLinkView,
    ensure_links_for_known_thread_origin,
    ensure_thread_entity_link,
    get_thread_entity_links,
    require_entity_links_for_outbound,
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
from backend.app.communications.send_pipeline import (
    CommunicationSendAuthorization,
    CommunicationSendRequest,
    CommunicationSendResult,
    authorize_outbound_communication,
    send_via_communication_pipeline,
    template_metadata_from_mapping,
)
from backend.app.communications.template_enforce import (
    TemplateEnforceDecision,
    enforce_template_metadata,
)
from backend.app.communications.template_metadata import (
    CommunicationTemplateMetadata,
    build_template_metadata,
)

__all__ = [
    "CommunicationContext",
    "CommunicationContextResolveError",
    "CommunicationPolicyDecision",
    "CommunicationPolicyRequest",
    "CommunicationSendAuthorization",
    "CommunicationSendRequest",
    "CommunicationSendResult",
    "CommunicationTemplateMetadata",
    "TemplateEnforceDecision",
    "ThreadEntityLinkError",
    "ThreadEntityLinkRequiredError",
    "ThreadEntityLinkView",
    "ThreadResultLinkConflictError",
    "ThreadResultLinkError",
    "ThreadResultLinkUnresolvedError",
    "ThreadResultLinkView",
    "attach_thread_result_from_confirmed_ledger",
    "attach_thread_result_link",
    "authorize_outbound_communication",
    "build_template_metadata",
    "enforce_template_metadata",
    "ensure_links_for_known_thread_origin",
    "ensure_thread_entity_link",
    "evaluate_communication_policy",
    "evaluate_policy_for_context",
    "get_thread_entity_links",
    "get_thread_result_link",
    "platform_communication_domain_registry",
    "require_confirmed_thread_result_link",
    "require_entity_links_for_outbound",
    "reset_communication_domain_registry_for_tests",
    "reset_policy_adapters_for_tests",
    "resolve_communication_context",
    "send_via_communication_pipeline",
    "template_metadata_from_mapping",
]
