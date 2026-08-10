"""Hiring CRM trust allowlists (ADR-036).

Coarse ceiling only — ACL / handoff / module matrix enforce scope and permissions.
Legacy job/portal DB roles still authenticate via ``actor_satisfies_role_allowlist``.
"""

from __future__ import annotations

from backend.app.auth.trust_role_deps import TRUST_READ_ROLES, TRUST_WRITE_ROLES

HIRING_CANDIDATE_VIEW_ROLES = TRUST_READ_ROLES
HIRING_CANDIDATE_MUTATE_ROLES = TRUST_WRITE_ROLES
HIRING_CANDIDATE_PROFILE_READ_ROLES = TRUST_READ_ROLES
HIRING_CANDIDATE_PROFILE_WRITE_ROLES = TRUST_WRITE_ROLES
