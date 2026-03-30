"""Purchased one-time pack bonuses under tenant.settings.usage_v1 (§2.16).

Stripe Checkout (mode=payment) webhooks and mock billing apply increments here.
Enforcement reads these values via lead_quota / plan_feature_gates.
"""

from __future__ import annotations

from typing import Any

USAGE_ROOT = "usage_v1"
PACK_ADDONS_KEY = "pack_addons_v1"

# Keys inside pack_addons_v1 (stable API for settings JSON).
MONTHLY_LEADS_CAP = "monthly_leads_cap"
AUTOMATION_RULES_ENABLED_CAP = "automation_rules_enabled_cap"
LEAD_CUSTOM_FIELD_DEFINITIONS_CAP = "lead_custom_field_definitions_cap"
# Extra active lead-form slots from checkout_payment packs (§2.16).
LEAD_FORMS_ACTIVE_CAP = "lead_forms_active_cap"


def pack_addon_int(settings: dict[str, Any] | None, field: str) -> int:
    if not settings or not isinstance(settings, dict):
        return 0
    usage = settings.get(USAGE_ROOT)
    if not isinstance(usage, dict):
        return 0
    packs = usage.get(PACK_ADDONS_KEY)
    if not isinstance(packs, dict):
        return 0
    raw = packs.get(field)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def merge_pack_addon_into_settings(settings: dict[str, Any], field: str, increment: int) -> dict[str, Any]:
    root = dict(settings or {})
    usage = dict(root.get(USAGE_ROOT) or {})
    packs = dict(usage.get(PACK_ADDONS_KEY) or {})
    inc = max(0, int(increment))
    try:
        cur = max(0, int(packs.get(field) or 0))
    except (TypeError, ValueError):
        cur = 0
    packs[field] = cur + inc
    usage[PACK_ADDONS_KEY] = packs
    root[USAGE_ROOT] = usage
    return root
