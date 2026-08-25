"""Operational scope helpers for Application matching and inbox filters (ADR-022)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.models.lead import Lead

# Stages excluded from default operational inbox / analytics (Phase 1).
OPERATIONAL_EXCLUDED_LEAD_STAGES: frozenset[str] = frozenset({"intake_draft_abandoned"})

# Terminal statuses — never auto-attach targets.
TERMINAL_LEAD_STATUSES: frozenset[str] = frozenset(
    {"rejected", "spam", "archived", "closed", "processed", "converted", "lost"}
)

# Open lifecycle statuses eligible for match_or_create auto-attach (Sales Inquiry Phase 1).
OPEN_SALES_LIFECYCLE_STATUSES: frozenset[str] = frozenset(
    {"new", "reviewing", "waiting_for_information"}
)


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def is_operational_lead_row(lead: Lead) -> bool:
    stage = str(getattr(lead, "stage", "") or "").strip().lower()
    return stage not in OPERATIONAL_EXCLUDED_LEAD_STAGES


def is_open_sales_application(
    lead: Lead,
    *,
    allowed_lifecycle_statuses: list[str] | None = None,
) -> bool:
    if str(getattr(lead, "lead_type", "") or "") != "client":
        return False
    if str(getattr(lead, "lead_target_type", "") or "") != "client_lead":
        return False
    stage = str(getattr(lead, "stage", "") or "").strip().lower()
    if stage in OPERATIONAL_EXCLUDED_LEAD_STAGES or stage == "intake_draft":
        return False
    status = str(getattr(lead, "status", "") or "").strip().lower()
    if status in TERMINAL_LEAD_STATUSES:
        return False
    allowed = {s.strip().lower() for s in (allowed_lifecycle_statuses or []) if str(s).strip()}
    if not allowed:
        allowed = set(OPEN_SALES_LIFECYCLE_STATUSES)
    return status in allowed


def lead_offering_context(lead: Lead) -> dict[str, Optional[str]]:
    normalized = _record(lead.normalized)
    attribution = _record(normalized.get("intake_attribution_v1"))
    publication_id = str(attribution.get("publication_id") or normalized.get("publication_id") or "").strip() or None
    intake_source_profile_id = (
        str(attribution.get("intake_source_profile_id") or normalized.get("intake_source_profile_id") or "").strip()
        or None
    )
    campaign = str(attribution.get("campaign") or "").strip() or None
    return {
        "publication_id": publication_id,
        "intake_source_profile_id": intake_source_profile_id,
        "campaign": campaign,
    }


def offering_context_matches(
    *,
    lead: Lead,
    publication_id: Optional[str],
    intake_source_profile_id: Optional[str],
    require_offering_match: bool,
) -> bool:
    if not require_offering_match:
        return True
    target = lead_offering_context(lead)
    current_pub = str(publication_id or "").strip() or None
    current_isp = str(intake_source_profile_id or "").strip() or None
    if current_pub and target.get("publication_id"):
        return current_pub == target["publication_id"]
    if current_isp and target.get("intake_source_profile_id"):
        return current_isp == target["intake_source_profile_id"]
    # No stored offering on existing Application — do not auto-attach on offering gate.
    return False
