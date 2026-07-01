from __future__ import annotations

# Doc type codes (normalized via `normalize_doc_type`) that must never receive a pipeline waiver.
# Identity + work-authorization / legal gates — align with hiring OS fail-safe (plan §12).
# Tenant-specific tuning: future settings hook may replace or extend this set.
NON_OVERRIDABLE_DOC_TYPES: frozenset[str] = frozenset(
    {
        "national_id",
        "passport",
        "residence_permit",
        "visa",
        "work_permit",
        "decision",
    }
)

SCOPE_PIPELINE = "pipeline"
SCOPE_BOTH = "both"

VALID_REQUESTED_SCOPES = frozenset({SCOPE_PIPELINE, SCOPE_BOTH})
VALID_GRANTED_SCOPES = frozenset({SCOPE_PIPELINE, SCOPE_BOTH})

# Requirement codes that must never receive a pipeline waiver (identity / work authorization gates).
NON_OVERRIDABLE_REQUIREMENT_CODES: frozenset[str] = frozenset(
    {
        "identity_document",
        "work_authorization",
    }
)

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_REVOKED = "revoked"
