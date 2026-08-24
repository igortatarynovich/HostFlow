"""Entity Profile Definition Registry package (Platform Core)."""

from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    DecisionResult,
    IngestDisposition,
    OutcomeDecisionContext,
    evaluate_ingest_decision,
    evaluate_outcome_event_decision,
    stamp_decision_blocks,
)
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import (
    resolve_entity_profile_facade,
    resolve_entity_profile_for_intake_source,
)
from backend.app.entity_profile.ingest_runtime import (
    IngestEnvelope,
    prepare_meta_ingest_runtime,
    prepare_public_intake_runtime,
    resolve_public_intake_source_profile_id,
    stamp_ingest_envelope_v1,
)
from backend.app.entity_profile.outcome_executor import (
    OutcomeExecutionResult,
    apply_blocked_duplicate_outcome,
    execute_create_candidate_outcome,
    execute_create_client_outcome,
    execute_create_service_order_outcome,
    execute_outcome_decision,
)
from backend.app.entity_profile.presentation_runtime import (
    FORM_PRESENTATION_RUNTIME_V1,
    FormPresentationNotFoundError,
    resolve_form_presentation,
    resolve_form_presentation_for_intake_source,
)
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID as ENTITY_PROFILE_MEMBERSHIP_V1,
    is_field_member,
    presence_level,
    resolve_membership,
)
from backend.app.entity_profile.registry import EntityProfileRegistry, UnknownCanonicalFieldError
from backend.app.entity_profile.resolver import resolve_effective_entity_profile
from backend.app.entity_profile.reverse_map import find_entity_profile_code_by_legacy_candidate_code
from backend.app.entity_profile.seed import (
    ensure_platform_entity_profile_catalog,
    ensure_tenant_entity_profile_defaults,
)

__all__ = [
    "DecisionInput",
    "DecisionResult",
    "FORM_PRESENTATION_RUNTIME_V1",
    "FormPresentationNotFoundError",
    "ENTITY_PROFILE_MEMBERSHIP_V1",
    "EntityProfileRegistry",
    "OutcomeDecisionContext",
    "OutcomeExecutionResult",
    "IngestEnvelope",
    "UnknownCanonicalFieldError",
    "apply_blocked_duplicate_outcome",
    "ensure_platform_entity_profile_catalog",
    "ensure_tenant_entity_profile_defaults",
    "IngestDisposition",
    "evaluate_ingest_decision",
    "evaluate_outcome_event_decision",
    "execute_create_candidate_outcome",
    "execute_create_client_outcome",
    "execute_create_service_order_outcome",
    "execute_outcome_decision",
    "find_entity_profile_code_by_legacy_candidate_code",
    "is_field_member",
    "prepare_meta_ingest_runtime",
    "presence_level",
    "prepare_public_intake_runtime",
    "resolve_effective_entity_profile",
    "resolve_entity_profile_facade",
    "resolve_entity_profile_for_intake_source",
    "resolve_membership",
    "resolve_form_presentation",
    "resolve_form_presentation_for_intake_source",
    "resolve_public_intake_source_profile_id",
    "stamp_decision_blocks",
    "stamp_ingest_envelope_v1",
]
