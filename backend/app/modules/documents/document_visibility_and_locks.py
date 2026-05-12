"""
ADR-014 Product Phase 2 — minimal visibility + process-lock **signals** (no policy graph).

Values are carried on ``DocumentAccessContext`` as strings / frozensets. Callers may
populate locks from ``Candidate.extra`` (or future handoff/payroll services) without
introducing a DSL or per-module ACL forks.
"""

from __future__ import annotations

from typing import Any, FrozenSet

# Visibility scopes (extend when HR/transport/finance surfaces attach real rules).
VISIBILITY_SCOPES: FrozenSet[str] = frozenset(
    {"recruitment", "hr", "transport", "finance", "shared"}
)

# Viewer channel (module / surface) — not a role matrix; drives read filtering only.
DOCUMENT_VIEWER_CHANNELS: FrozenSet[str] = frozenset(
    {"recruitment", "hr", "transport", "finance"}
)

_TRANSPORT_DOC_TYPES: FrozenSet[str] = frozenset(
    {
        "code95",
        "tacho_card",
        "adr",
        "driver_certificate",
    }
)

# Types that multiple surfaces need (fleet + recruitment) without a policy graph yet:
# primary scope ``shared`` ⇒ visible under every viewer channel (see ADR-014 Phase 2).
_SHARED_PRIMARY_DOC_TYPES: FrozenSet[str] = frozenset(
    {
        "driver_license",
        "driver_license_code95",
    }
)

_HR_DOC_TYPES: FrozenSet[str] = frozenset(
    {
        "medical_certificate",
        "psych_tests",
    }
)

_FINANCE_DOC_TYPES: FrozenSet[str] = frozenset(
    {
        # Reserved for payroll / invoicing surfaces; empty until catalog gains codes.
    }
)

# Process locks that block destructive document operations (upload replace / delete).
PROCESS_LOCK_DESTRUCTIVE_BLOCKERS: FrozenSet[str] = frozenset(
    {
        "destructive_blocked",  # explicit test / policy hook
        "employment_handoff_locked",
        "payroll_locked",
        "transport_compliance_locked",
    }
)


def resolve_visibility_scope_stub(candidate: Any) -> str:
    """Default ``recruitment``; optional override via ``extra.document_visibility_scope``."""
    extra: dict[str, Any] = {}
    try:
        raw = candidate._get_extra()
        if isinstance(raw, dict):
            extra = raw
    except Exception:
        extra = getattr(candidate, "extra", {}) or {}
        if not isinstance(extra, dict):
            extra = {}
    raw_scope = str(extra.get("document_visibility_scope") or "recruitment").strip().lower()
    if raw_scope in VISIBILITY_SCOPES:
        return raw_scope
    return "recruitment"


def resolve_process_locks_stub(candidate: Any) -> frozenset[str]:
    """
    Optional list on candidate ``extra``:

    - ``process_locks`` or ``document_process_locks``: iterable of known lock tokens.
    """
    extra: dict[str, Any] = {}
    try:
        raw = candidate._get_extra()
        if isinstance(raw, dict):
            extra = raw
    except Exception:
        extra = getattr(candidate, "extra", {}) or {}
        if not isinstance(extra, dict):
            extra = {}
    locks = extra.get("process_locks")
    if locks is None:
        locks = extra.get("document_process_locks")
    if not isinstance(locks, (list, tuple, set)):
        return frozenset()
    out: set[str] = set()
    for item in locks:
        token = str(item).strip()
        if token:
            out.add(token)
    return frozenset(out)


def normalize_viewer_channel(raw: str | None) -> str:
    """Default ``recruitment``; lowercase strip."""
    if not raw or not str(raw).strip():
        return "recruitment"
    return str(raw).strip().lower()


def viewer_readable_scopes(viewer_channel: str) -> frozenset[str]:
    """
    Each channel may **read** documents whose primary scope is in
    ``{that_channel, shared}``.
    """
    ch = normalize_viewer_channel(viewer_channel)
    mapping: dict[str, frozenset[str]] = {
        "recruitment": frozenset({"recruitment", "shared"}),
        "hr": frozenset({"hr", "shared"}),
        "transport": frozenset({"transport", "shared"}),
        "finance": frozenset({"finance", "shared"}),
    }
    return mapping.get(ch, mapping["recruitment"])


def document_type_primary_visibility_scope(doc_type: str | None) -> str:
    """
    Single primary scope per canonical type (read policy v1).

    Ruleset / flags still decide *obligation*; this only labels *which surface*
    primarily owns the document row for viewer read filtering.
    """
    from backend.app.services.document_catalog import normalize_doc_type

    raw = str(doc_type or "").strip().lower()
    if raw.startswith("shared"):
        return "shared"
    dt = normalize_doc_type(doc_type or "")
    if dt.startswith("shared"):
        return "shared"
    if dt in _SHARED_PRIMARY_DOC_TYPES:
        return "shared"
    if dt in _TRANSPORT_DOC_TYPES:
        return "transport"
    if dt in _HR_DOC_TYPES:
        return "hr"
    if dt in _FINANCE_DOC_TYPES:
        return "finance"
    return "recruitment"


def document_visible_to_viewer(doc_type: str | None, viewer_channel: str) -> bool:
    primary = document_type_primary_visibility_scope(doc_type)
    return primary in viewer_readable_scopes(viewer_channel)


def document_operation_allowed(
    *,
    access_policy: str,
    process_locks: frozenset[str],
) -> bool:
    """
    Minimal matrix: destructive blocked when ``process_locks`` hits a destructive
    blocker token. Read/mutate always allowed at this layer (narrow in policy later).
    """
    if access_policy == "destructive_mutate":
        return not (process_locks & PROCESS_LOCK_DESTRUCTIVE_BLOCKERS)
    return True


__all__ = [
    "DOCUMENT_VIEWER_CHANNELS",
    "PROCESS_LOCK_DESTRUCTIVE_BLOCKERS",
    "VISIBILITY_SCOPES",
    "document_operation_allowed",
    "document_type_primary_visibility_scope",
    "document_visible_to_viewer",
    "normalize_viewer_channel",
    "resolve_process_locks_stub",
    "resolve_visibility_scope_stub",
    "viewer_readable_scopes",
]
