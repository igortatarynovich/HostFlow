"""Intake Readiness — Meta-like inbound becomes an actionable Application.

Policy id: ``intake_readiness.v1``.

Does not implement Transfer / Formalize / Started. Does not amend #359.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

POLICY_ID: Final[str] = "intake_readiness.v1"
ARCH_REL: Final[str] = "docs/specs/gates/intake-readiness-gate.md"
RSO_BRIEF_REL: Final[str] = "docs/specs/tasks/recruitment-spine-orchestrator-v1.md"
WALK_API: Final[str] = "recruitment_next_action_after_intake"

FITS_NEXT_ACTION: Final[str] = "fits"
AUTO_CONVERT_GATED: Final[str] = "auto_convert_gated"
BLOCKING_LEAD_STATUSES = frozenset(
    {"needs_routing", "failed", "duplicated", "duplicate_review", "rejected"}
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def intake_auto_convert_gated_is_actionable(
    *,
    disposition: str,
    blocking_reasons: Any,
    vacancy_resolved: bool,
    triage_gate_bypass: bool,
) -> bool:
    """Manual/assisted ``auto_convert_gated`` is not a Recruitment routing STOP.

    Known vacancy + candidate-application intent is already an Application.
    Operator Fits creates the person. Do not park as ``needs_routing``.
    """
    reasons = blocking_reasons if isinstance(blocking_reasons, (list, tuple, set, frozenset)) else []
    return (
        bool(triage_gate_bypass)
        and bool(vacancy_resolved)
        and _text(disposition).lower() == "needs_routing"
        and AUTO_CONVERT_GATED in {_text(reason) for reason in reasons}
    )


def recruitment_facts_sufficient(lead: Any) -> bool:
    """Vacancy bound + person identity present — enough to offer Fits."""
    vacancy_id = _text(getattr(lead, "vacancy_id", None))
    if not vacancy_id:
        return False
    norm = _record(getattr(lead, "normalized", None))
    name = (
        _text(norm.get("full_name"))
        or " ".join(
            p
            for p in (_text(norm.get("first_name")), _text(norm.get("last_name")))
            if p
        )
    ).strip()
    if not name and not (_text(getattr(lead, "first_name", None)) or _text(getattr(lead, "last_name", None))):
        contact = _record(norm.get("contact_person"))
        name = _text(contact.get("full_name"))
    return bool(name)


def recruitment_next_action_after_intake(lead: Any) -> str | None:
    """Return ``fits`` when intake produced a recruitment-actionable Application."""
    status = _text(getattr(lead, "status", None)).lower()
    if status in BLOCKING_LEAD_STATUSES:
        return None
    if not recruitment_facts_sufficient(lead):
        return None
    return FITS_NEXT_ACTION


__all__ = (
    "ARCH_REL",
    "AUTO_CONVERT_GATED",
    "BLOCKING_LEAD_STATUSES",
    "FITS_NEXT_ACTION",
    "POLICY_ID",
    "RSO_BRIEF_REL",
    "WALK_API",
    "intake_auto_convert_gated_is_actionable",
    "recruitment_facts_sufficient",
    "recruitment_next_action_after_intake",
)
