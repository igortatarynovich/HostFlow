"""Recruitment Application lifecycle — canonical statuses and transition rules.

Source of truth: ``docs/specs/workflows/recruitment-application-lifecycle.md`` §3–§4 (§12 = code contract).
Reconciliation / open gaps vs spec: ``docs/specs/workflows/recruitment-application-lifecycle-sync-note.md``.
Legacy MVP bucket ``active`` maps to ``applied`` (lifecycle doc §3 legacy note).
Use ``set_recruitment_application_status`` for all ORM writes to ``RecruitmentApplication.status`` from services.
"""

from __future__ import annotations

from typing import Any, FrozenSet, Optional, Tuple

# §3 canonical enum (storage / API strings).
CANONICAL_APPLICATION_STATUSES: FrozenSet[str] = frozenset(
    {
        "applied",
        "in_review",
        "shortlisted",
        "rejected",
        "withdrawn",
        "hired",
        "archived",
        "reopened",
        # Handoff / transfer (intent layer; see product canon 2026-05)
        "ready_for_handoff",
        "handed_off",
        "returned_for_revision",
    }
)

# First status for a newly recorded intent (§3 ``applied``).
INITIAL_APPLICATION_STATUS: str = "applied"

# MVP coarse ``active`` → ``applied`` per lifecycle doc §3 Note.
_LEGACY_STATUS_ALIASES = {"active": "applied"}


class InvalidRecruitmentApplicationStatus(ValueError):
    """Status string is not a canonical lifecycle value (after normalization)."""


class InvalidRecruitmentApplicationTransition(ValueError):
    """Transition not allowed by §4 matrix."""


def normalize_application_status(raw: Optional[str]) -> str:
    """Lowercase strip + map legacy ``active`` → ``applied``."""
    s = str(raw or "").strip().lower()
    if not s:
        return INITIAL_APPLICATION_STATUS
    return _LEGACY_STATUS_ALIASES.get(s, s)


def assert_canonical_application_status(raw: Optional[str]) -> str:
    """Return canonical status or raise."""
    n = normalize_application_status(raw)
    if n not in CANONICAL_APPLICATION_STATUSES:
        raise InvalidRecruitmentApplicationStatus(n)
    return n


# §4 transition matrix — (from_status, to_status). Conditional (c) cells are included as allowed;
# stricter guards (hire binding, reopen policy) belong in future service/API layers.
_ALLOWED_TRANSITIONS: FrozenSet[Tuple[str, str]] = frozenset(
    {
        ("applied", "in_review"),
        ("applied", "shortlisted"),
        ("applied", "rejected"),
        ("applied", "withdrawn"),
        ("applied", "hired"),
        ("applied", "archived"),
        ("in_review", "shortlisted"),
        ("in_review", "rejected"),
        ("in_review", "withdrawn"),
        ("in_review", "hired"),
        ("in_review", "archived"),
        ("shortlisted", "in_review"),
        ("shortlisted", "rejected"),
        ("shortlisted", "withdrawn"),
        ("shortlisted", "hired"),
        ("shortlisted", "archived"),
        ("shortlisted", "ready_for_handoff"),
        ("applied", "ready_for_handoff"),
        ("in_review", "ready_for_handoff"),
        ("ready_for_handoff", "handed_off"),
        ("ready_for_handoff", "archived"),
        ("ready_for_handoff", "rejected"),
        ("ready_for_handoff", "withdrawn"),
        ("ready_for_handoff", "returned_for_revision"),
        ("handed_off", "archived"),
        ("handed_off", "returned_for_revision"),
        ("returned_for_revision", "applied"),
        ("returned_for_revision", "in_review"),
        ("returned_for_revision", "shortlisted"),
        ("returned_for_revision", "ready_for_handoff"),
        ("returned_for_revision", "archived"),
        ("returned_for_revision", "withdrawn"),
        ("returned_for_revision", "rejected"),
        ("applied", "returned_for_revision"),
        ("in_review", "returned_for_revision"),
        ("shortlisted", "returned_for_revision"),
        ("rejected", "archived"),
        ("rejected", "reopened"),
        ("withdrawn", "archived"),
        ("withdrawn", "reopened"),
        ("hired", "archived"),
        ("hired", "reopened"),
        ("archived", "reopened"),
        ("reopened", "applied"),
        ("reopened", "in_review"),
        ("reopened", "shortlisted"),
        ("reopened", "rejected"),
        ("reopened", "withdrawn"),
        ("reopened", "hired"),
        ("reopened", "archived"),
        ("reopened", "ready_for_handoff"),
        ("reopened", "handed_off"),
    }
)


def validate_application_status_transition(from_status: str, to_status: str) -> None:
    """Raise ``InvalidRecruitmentApplicationTransition`` if §4 disallows the edge."""
    fs = assert_canonical_application_status(from_status)
    ts = assert_canonical_application_status(to_status)
    if fs == ts:
        return
    if (fs, ts) not in _ALLOWED_TRANSITIONS:
        raise InvalidRecruitmentApplicationTransition(f"{fs!r} -> {ts!r}")


def apply_application_status_transition(
    *,
    current_status: str,
    new_status: str,
) -> str:
    """Validate and return canonical ``new_status`` (for ORM assign)."""
    validate_application_status_transition(current_status, new_status)
    return assert_canonical_application_status(new_status)


def set_recruitment_application_status(row: Any, new_status: str) -> str:
    """Assign ``row.status`` after normalization and §4 transition checks.

    All writes to ``RecruitmentApplication.status`` in application code should go
    through this helper (not raw ORM assignment), except Alembic migrations.

    * Legacy ``active`` is normalized to ``applied`` (same as reads).
    * ``current == target`` after normalization is a **no-op** (idempotent retries).
    """
    cur_raw = getattr(row, "status", None)
    cur_n = normalize_application_status(cur_raw)
    new_n = assert_canonical_application_status(new_status)
    if cur_n != new_n:
        validate_application_status_transition(cur_n, new_n)
    row.status = new_n
    return new_n
