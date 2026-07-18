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
from backend.app.acquisition.result_attribution import (
    AttributionError,
    AttributionSnapshot,
    build_attribution_from_routing,
    get_attribution_for_result,
    get_attribution_for_submission,
    record_result_attribution_from_routing,
    try_record_result_attribution_from_routing,
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
    "AttributionError",
    "AttributionSnapshot",
    "CampaignServiceError",
    "UniversalRoutingDecision",
    "ValidatedTarget",
    "add_campaign_target",
    "build_attribution_from_routing",
    "create_campaign",
    "get_attribution_for_result",
    "get_attribution_for_submission",
    "get_campaign",
    "list_campaigns",
    "record_result_attribution_from_routing",
    "remove_campaign_target",
    "resolve_universal_submission_routing",
    "stamp_acquisition_routing_on_lead",
    "try_record_result_attribution_from_routing",
    "update_campaign",
    "validate_goal_kpi_pair",
    "validate_promotion_target",
]
