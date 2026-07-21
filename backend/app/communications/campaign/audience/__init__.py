"""C2.3 PR-2 — Pure Audience Resolver.

definition → snapshot candidates. No SQL / ORM / send / Thread / Intent execute.
"""

from backend.app.communications.campaign.audience.engine import (
    diagnostics,
    dry_run,
    resolve,
)
from backend.app.communications.campaign.audience.types import (
    DEFINITION_TYPE_FILTER,
    DEFINITION_TYPE_STATIC_LIST,
    DEFINITION_TYPES,
    DIAG_DUPLICATE_RECIPIENT,
    DIAG_EMPTY_AUDIENCE,
    DIAG_ENTITY_POOL_REQUIRED,
    DIAG_ENTITY_SKIPPED,
    DIAG_FILTER_INVALID,
    DIAG_INVALID_DEFINITION,
    DIAG_INVALID_RECIPIENT,
    DIAG_UNKNOWN_DEFINITION_TYPE,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    AudienceDefinitionPayload,
    Diagnostic,
    EntityCandidate,
    ResolveContext,
    ResolvedRecipient,
    ResolveResult,
    SkippedCandidate,
)

__all__ = [
    "DEFINITION_TYPE_STATIC_LIST",
    "DEFINITION_TYPE_FILTER",
    "DEFINITION_TYPES",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "DIAG_INVALID_DEFINITION",
    "DIAG_UNKNOWN_DEFINITION_TYPE",
    "DIAG_EMPTY_AUDIENCE",
    "DIAG_INVALID_RECIPIENT",
    "DIAG_DUPLICATE_RECIPIENT",
    "DIAG_FILTER_INVALID",
    "DIAG_ENTITY_POOL_REQUIRED",
    "DIAG_ENTITY_SKIPPED",
    "AudienceDefinitionPayload",
    "EntityCandidate",
    "ResolveContext",
    "Diagnostic",
    "ResolvedRecipient",
    "SkippedCandidate",
    "ResolveResult",
    "resolve",
    "dry_run",
    "diagnostics",
]
