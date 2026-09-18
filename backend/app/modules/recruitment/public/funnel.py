"""Recruitment funnel assignment — public contract for Process Engine / intake."""

from __future__ import annotations

from backend.app.services.recruitment_funnel_assignment import (
    assign_recruitment_funnel_to_lead,
    reconcile_candidate_funnel_on_company_change,
    reconcile_lead_funnel_on_company_change,
    resolve_candidate_funnel_id_for_runtime,
    resolve_lead_funnel_id_for_display,
    resolve_recruitment_funnel_for_candidate,
)

__all__ = [
    "assign_recruitment_funnel_to_lead",
    "reconcile_candidate_funnel_on_company_change",
    "reconcile_lead_funnel_on_company_change",
    "resolve_candidate_funnel_id_for_runtime",
    "resolve_lead_funnel_id_for_display",
    "resolve_recruitment_funnel_for_candidate",
]
