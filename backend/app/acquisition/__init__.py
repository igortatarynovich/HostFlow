"""ADR-024 Stage 3 — Acquisition / Campaign + universal submission routing."""

from backend.app.acquisition.campaign_service import (
    CampaignServiceError,
    add_campaign_target,
    create_campaign,
    get_campaign,
    list_campaigns,
    remove_campaign_target,
    update_campaign,
)
from backend.app.acquisition.submission_routing import (
    UniversalRoutingDecision,
    resolve_universal_submission_routing,
    stamp_acquisition_routing_on_lead,
)
from backend.app.acquisition.validation import (
    ValidatedTarget,
    validate_goal_kpi_pair,
    validate_promotion_target,
)

__all__ = [
    "CampaignServiceError",
    "UniversalRoutingDecision",
    "ValidatedTarget",
    "add_campaign_target",
    "create_campaign",
    "get_campaign",
    "list_campaigns",
    "remove_campaign_target",
    "resolve_universal_submission_routing",
    "stamp_acquisition_routing_on_lead",
    "update_campaign",
    "validate_goal_kpi_pair",
    "validate_promotion_target",
]
