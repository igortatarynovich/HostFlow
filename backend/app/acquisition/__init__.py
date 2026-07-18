"""ADR-024 Stage 3A — Acquisition / Campaign foundation package."""

from backend.app.acquisition.campaign_service import (
    CampaignServiceError,
    add_campaign_target,
    create_campaign,
    get_campaign,
    list_campaigns,
    remove_campaign_target,
    update_campaign,
)
from backend.app.acquisition.validation import (
    ValidatedTarget,
    validate_goal_kpi_pair,
    validate_promotion_target,
)

__all__ = [
    "CampaignServiceError",
    "ValidatedTarget",
    "add_campaign_target",
    "create_campaign",
    "get_campaign",
    "list_campaigns",
    "remove_campaign_target",
    "update_campaign",
    "validate_goal_kpi_pair",
    "validate_promotion_target",
]
