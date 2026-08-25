"""Communications domain helpers (Communication Context C1–C5 + C0 platform)."""

from backend.app.communications.capability_resolver import (
    CommunicationCapabilities,
    DefaultCapabilityResolver,
    resolve_communication_capabilities,
)
from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    ResolvedLinkSnapshot,
    SendCommunicationContent,
    SendCommunicationRequest,
)
from backend.app.communications.execute_intent import (
    IntentExecutionRequest,
    IntentRenderResult,
    execute_communication_intent,
    render_communication_intent,
)
from backend.app.communications.context_resolver import (
    CommunicationContext,
    CommunicationContextResolveError,
    resolve_communication_context,
)
from backend.app.communications.domain_registry import (
    platform_communication_domain_registry,
    reset_communication_domain_registry_for_tests,
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
from backend.app.communications.intent import (
    CommunicationIntent,
    IntentPolicy,
    resolve_intent_policy,
)
from backend.app.communications.intent_policy import (
    IntentPolicyResult,
    evaluate_intent_policy,
)
from backend.app.communications.intent_registry import (
    EntityCommunicationProfile,
    IntentDefinition,
    get_intent_definition,
    is_combination_allowed,
    list_intent_definitions,
)
from backend.app.communications.snapshot import (
    CommunicationOutboundSnapshot,
    build_outbound_snapshot,
)
from backend.app.communications.link_resolver import (
    LinkResolveRequest,
    QuestionnaireLinkResolver,
    ResolvedPublicLink,
    get_link_resolver,
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
from backend.app.communications.prepare_send import (
    PlatformCommunicationSender,
    get_communication_sender,
    prepare_and_send_communication,
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
from backend.app.communications.send_communication import (
    SendCommunicationError,
    SendCommunicationResult,
    find_thread_id_for_origin,
    send_communication,
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
from backend.app.communications.template_resolver import (
    ResolvedTemplate,
    SeedTemplateResolver,
    get_template_resolver,
)

__all__ = [
    "CommunicationCapabilities",
    "CommunicationCommand",
    "CommunicationContext",
    "CommunicationContextResolveError",
    "CommunicationIntent",
    "CommunicationOrigin",
    "CommunicationPolicyDecision",
    "CommunicationPolicyRequest",
    "CommunicationRecipient",
    "CommunicationSendAuthorization",
    "CommunicationSendRequest",
    "CommunicationSendResult",
    "CommunicationTemplateMetadata",
    "CommunicationOutboundSnapshot",
    "DefaultCapabilityResolver",
    "EntityCommunicationProfile",
    "IntentDefinition",
    "IntentExecutionRequest",
    "IntentPolicy",
    "IntentPolicyResult",
    "IntentRenderResult",
    "LinkResolveRequest",
    "PlatformCommunicationSender",
    "QuestionnaireLinkResolver",
    "ResolvedLinkSnapshot",
    "ResolvedPublicLink",
    "ResolvedTemplate",
    "SeedTemplateResolver",
    "SendCommunicationContent",
    "SendCommunicationError",
    "SendCommunicationRequest",
    "SendCommunicationResult",
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
    "build_outbound_snapshot",
    "build_template_metadata",
    "enforce_template_metadata",
    "ensure_links_for_known_thread_origin",
    "ensure_thread_entity_link",
    "evaluate_communication_policy",
    "evaluate_intent_policy",
    "evaluate_policy_for_context",
    "execute_communication_intent",
    "find_thread_id_for_origin",
    "get_communication_sender",
    "get_intent_definition",
    "get_link_resolver",
    "get_template_resolver",
    "get_thread_entity_links",
    "get_thread_result_link",
    "is_combination_allowed",
    "list_intent_definitions",
    "platform_communication_domain_registry",
    "prepare_and_send_communication",
    "render_communication_intent",
    "require_confirmed_thread_result_link",
    "require_entity_links_for_outbound",
    "reset_communication_domain_registry_for_tests",
    "reset_policy_adapters_for_tests",
    "resolve_communication_capabilities",
    "resolve_communication_context",
    "resolve_intent_policy",
    "send_communication",
    "send_via_communication_pipeline",
    "template_metadata_from_mapping",
]
