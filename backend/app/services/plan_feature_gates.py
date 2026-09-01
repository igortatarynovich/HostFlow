"""Plan-based feature gates (§2.2 paywall, §2.16): Team-tier features vs starter/free/solo.

Trial (license ``plan=trial`` or ``subscription.status=trial``) unlocks Team-tier
feature flags with separate volume caps — SSOT: 30-day full product, not Solo.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.models.lead import MetaLeadCredential, MetaLeadSettings
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.constants.hostflow_canonical_tenants import is_focus_personnel_tenant
from backend.app.services.billing_pack_addons import (
    AUTOMATION_RULES_ENABLED_CAP,
    LEAD_CUSTOM_FIELD_DEFINITIONS_CAP,
    pack_addon_int,
)

# Paid / free Solo-style plans. ``trial`` is intentionally absent: trial is Team-tier
# features with SSOT volume caps (leads / conversion actions / portal / automation runs).
_TEAM_TIER_BLOCKED_PLANS: frozenset[str] = frozenset({"starter", "free", "solo"})

# §2.11 paywall: SOLO/starter-style plans cap tenant-defined lead custom fields (active, non-system).
_STARTER_TIER_MAX_LEAD_CUSTOM_FIELD_DEFINITIONS = 10
# §2.11: Meta field mapping rules + integration "slots" on low tiers (SSOT monetization table).
_STARTER_TIER_MAX_META_FIELD_MAPPING_RULES = 25
_STARTER_TIER_MAX_META_LEAD_CREDENTIALS = 1
TRIAL_LEADS_MONTHLY_CAP = 50
TRIAL_CONVERSION_ACTIONS_CAP = 20
TRIAL_PORTAL_SHARES_CAP = 2
TRIAL_AUTOMATION_RUNS_CAP = 5
TRIAL_CONVERSION_ACTIONS_METRIC = "conversion_actions"
TRIAL_AUTOMATION_RUNS_METRIC = "automation_runs"


def plan_allows_team_tier_features(plan: str, *, tenant_id: str | None = None) -> bool:
    if is_focus_personnel_tenant(tenant_id):
        return True
    p = (plan or "").strip().lower() or "starter"
    if p == "trial":
        return True
    return p not in _TEAM_TIER_BLOCKED_PLANS


def plan_allows_smart_operations_bundle(plan: str, *, tenant_id: str | None = None) -> bool:
    """
    **Умные** сквозные фичи (тот же UX/эндпойнты, что и «ручные»):

    * взвешенная маршрутизация / «умная» ротация в manager queue;
    * дальше сюда же — расширения «умного планера» и AI-подсказок по той же лицензии.

    Коммерчески сейчас выровнено с Team+ (см. ``_TEAM_TIER_BLOCKED_PLANS``).
    **Focus Personnel** (канонический tenant id) — всё включено по продуктовой политике.
    """
    return plan_allows_team_tier_features(plan, tenant_id=tenant_id)


def plan_is_pro_tier(plan: str, *, tenant_id: str | None = None) -> bool:
    """Business+ tier for NBA / distribution upsells (§2.16)."""
    if is_focus_personnel_tenant(tenant_id):
        return True
    return (plan or "").strip().lower() in {"pro", "enterprise"}


def lead_custom_field_definitions_cap(plan: str, *, tenant_id: str | None = None) -> int | None:
    """Max active non-system LEAD definitions; None = no cap (Team+)."""
    if is_focus_personnel_tenant(tenant_id):
        return None
    p = (plan or "").strip().lower() or "starter"
    if p in _TEAM_TIER_BLOCKED_PLANS:
        return _STARTER_TIER_MAX_LEAD_CUSTOM_FIELD_DEFINITIONS
    return None


def lead_meta_field_mapping_rules_cap(plan: str, *, tenant_id: str | None = None) -> int | None:
    """Max rows in meta_lead_settings.field_mapping; None = unlimited (Team+)."""
    if is_focus_personnel_tenant(tenant_id):
        return None
    p = (plan or "").strip().lower() or "starter"
    if p in _TEAM_TIER_BLOCKED_PLANS:
        return _STARTER_TIER_MAX_META_FIELD_MAPPING_RULES
    return None


def lead_meta_credentials_cap(plan: str, *, tenant_id: str | None = None) -> int | None:
    """Max Meta lead credentials per tenant; None = unlimited (Team+)."""
    if is_focus_personnel_tenant(tenant_id):
        return None
    p = (plan or "").strip().lower() or "starter"
    if p in _TEAM_TIER_BLOCKED_PLANS:
        return _STARTER_TIER_MAX_META_LEAD_CREDENTIALS
    return None


def plan_allows_meta_leads_oauth(plan: str, *, tenant_id: str | None = None) -> bool:
    """Facebook Login quick-connect for Meta Leads (Team-tier, including trial)."""
    return plan_allows_team_tier_features(plan, tenant_id=tenant_id)


def trial_usage_caps() -> dict[str, int]:
    """SSOT §2.16 trial-only caps (independent from starter paid plan caps)."""
    return {
        "leads_monthly": TRIAL_LEADS_MONTHLY_CAP,
        "conversion_actions": TRIAL_CONVERSION_ACTIONS_CAP,
        "portal_shares": TRIAL_PORTAL_SHARES_CAP,
        "automation_runs": TRIAL_AUTOMATION_RUNS_CAP,
    }


async def _tenant_trial_active(db: AsyncSession, tenant_id: str) -> bool:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is not None and isinstance(tenant.settings, dict):
        billing = tenant.settings.get("billing")
        if isinstance(billing, dict):
            sub = billing.get("subscription")
            if isinstance(sub, dict):
                status_code = str(sub.get("status") or "").strip().lower()
                if status_code == "trial":
                    return True
    row = await db.execute(
        select(TenantLicense.plan).where(TenantLicense.tenant_id == tenant_id).limit(1)
    )
    plan = str(row.scalar_one_or_none() or "").strip().lower()
    return plan == "trial"


async def enforce_trial_usage_cap_and_increment(
    db: AsyncSession,
    *,
    tenant_id: str,
    metric: str,
    increment: int = 1,
) -> None:
    """Apply trial monthly usage cap for selected metric, then persist increment."""
    if increment <= 0:
        return
    metric_key = str(metric or "").strip().lower()
    cap = trial_usage_caps().get(metric_key)
    if cap is None:
        return
    if not await _tenant_trial_active(db, tenant_id):
        return
    from backend.app.services.tenant_limits import ensure_usage_limit_not_exceeded, increment_tenant_usage

    await ensure_usage_limit_not_exceeded(
        db,
        tenant_id,
        metric_key,
        limit_per_month=cap,
        increment=increment,
    )
    await increment_tenant_usage(db, tenant_id, metric_key, delta=increment)


async def tenant_allows_team_tier_features(db: AsyncSession, tenant_id: str) -> bool:
    """Team-tier flags for a live tenant: Focus, active trial, or paid Team+ license."""
    if is_focus_personnel_tenant(tenant_id):
        return True
    if await _tenant_trial_active(db, tenant_id):
        return True
    plan = await resolve_tenant_plan_code(db, tenant_id)
    return plan_allows_team_tier_features(plan, tenant_id=tenant_id)


async def ensure_meta_leads_oauth_allowed(db: AsyncSession, tenant_id: str) -> None:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    if await tenant_allows_team_tier_features(db, tenant_id):
        return
    raise HTTPException(
        status_code=403,
        detail={
            "code": "plan_meta_leads_oauth",
            "feature": "meta_leads_oauth",
            "plan": plan,
            "message": "Meta quick connect (OAuth) requires a Team-tier plan or higher.",
        },
    )


async def ensure_meta_lead_field_mapping_rows_allowed(
    db: AsyncSession, tenant_id: str, rule_count: int
) -> None:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    cap = lead_meta_field_mapping_rules_cap(plan, tenant_id=tenant_id)
    if cap is None:
        return
    if rule_count > cap:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_meta_field_mapping_limit",
                "message": (
                    f"Field mapping rule limit reached ({cap} rules on this plan). "
                    "Upgrade to a Team-tier plan for a larger mapping table."
                ),
                "plan": plan,
                "limit": cap,
                "current": rule_count,
            },
        )


async def ensure_meta_lead_credential_create_allowed(db: AsyncSession, tenant_id: str) -> None:
    from backend.app.modules.leads import crud as leads_crud

    plan = await resolve_tenant_plan_code(db, tenant_id)
    cap = lead_meta_credentials_cap(plan, tenant_id=tenant_id)
    if cap is None:
        return
    rows = await leads_crud.list_meta_credentials(db, tenant_id=tenant_id)
    n = len(rows)
    if n >= cap:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_meta_lead_credentials_limit",
                "message": (
                    f"This plan allows {cap} Meta lead integration credential(s). "
                    "Upgrade to a Team-tier plan to connect additional sources."
                ),
                "plan": plan,
                "limit": cap,
                "current": n,
            },
        )


async def count_active_lead_custom_field_definitions(db: AsyncSession, tenant_id: str) -> int:
    from backend.app.models.custom_field import CustomFieldDefinition, CustomFieldScope

    stmt = (
        select(func.count())
        .select_from(CustomFieldDefinition)
        .where(CustomFieldDefinition.tenant_id == tenant_id)
        .where(CustomFieldDefinition.scope == CustomFieldScope.LEAD)
        .where(CustomFieldDefinition.is_system.is_(False))
        .where(CustomFieldDefinition.is_active.is_(True))
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_lead_custom_field_definition_create_allowed(db: AsyncSession, tenant_id: str) -> None:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    cap = lead_custom_field_definitions_cap(plan, tenant_id=tenant_id)
    if cap is None:
        return
    tenant = await db.get(Tenant, tenant_id)
    st = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else None
    effective = cap + pack_addon_int(st, LEAD_CUSTOM_FIELD_DEFINITIONS_CAP)
    n = await count_active_lead_custom_field_definitions(db, tenant_id)
    if n >= effective:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_lead_custom_fields_limit",
                "message": (
                    f"Lead custom field limit reached ({effective} fields on this plan, including add-ons). "
                    "Upgrade to a Team-tier plan to add more."
                ),
                "plan": plan,
                "limit": effective,
                "current": n,
            },
        )


async def resolve_tenant_plan_code(db: AsyncSession, tenant_id: str) -> str:
    row = await db.execute(
        select(TenantLicense.plan).where(TenantLicense.tenant_id == tenant_id).limit(1)
    )
    raw = row.scalar_one_or_none()
    return str(raw or "starter").strip().lower() or "starter"


def plan_bucket_for_limits(plan: str) -> str:
    """Map license.plan (incl. legacy segment names) to starter | team | pro for §2.16 numeric caps."""
    p = (plan or "").strip().lower() or "starter"
    if p in ("pro", "enterprise", "agency_premium", "business"):
        return "pro"
    if p in ("team", "trial", "agency_basic", "employer_basic", "services_basic"):
        return "team"
    return "starter"


async def resolve_plan_bucket_for_limits(db: AsyncSession, tenant_id: str) -> str:
    if is_focus_personnel_tenant(tenant_id):
        return "pro"
    return plan_bucket_for_limits(await resolve_tenant_plan_code(db, tenant_id))


def communication_channel_accounts_cap_for_bucket(bucket: str) -> int:
    if bucket == "pro":
        return 10
    if bucket == "team":
        return 3
    return 1


def lead_sources_cap_for_bucket(bucket: str) -> int:
    """SSOT §2.16: max lead sources per plan bucket (starter/team/pro)."""
    if bucket == "pro":
        return 10
    if bucket == "team":
        return 3
    return 1


async def count_tenant_lead_sources(db: AsyncSession, tenant_id: str) -> int:
    """
    Count configured lead sources:
    - active/inactive Meta credentials (one source per credential)
    - generic inbound webhook secret (one source if present)
    - active lead forms (one source per form)
    """
    meta_credentials = int(
        (
            await db.execute(
                select(func.count()).select_from(MetaLeadCredential).where(MetaLeadCredential.tenant_id == tenant_id)
            )
        ).scalar_one()
        or 0
    )
    active_lead_forms = int(
        (
            await db.execute(
                select(func.count())
                .select_from(TenantLeadForm)
                .where(TenantLeadForm.tenant_id == tenant_id, TenantLeadForm.is_active.is_(True))
            )
        ).scalar_one()
        or 0
    )
    webhook_enabled = int(
        (
            await db.execute(
                select(func.count())
                .select_from(MetaLeadSettings)
                .where(
                    MetaLeadSettings.tenant_id == tenant_id,
                    MetaLeadSettings.generic_inbound_webhook_secret.is_not(None),
                    MetaLeadSettings.generic_inbound_webhook_secret != "",
                )
            )
        ).scalar_one()
        or 0
    )
    return meta_credentials + active_lead_forms + min(webhook_enabled, 1)


async def ensure_lead_source_limit(
    db: AsyncSession,
    tenant_id: str,
    *,
    current_count: int | None = None,
    extra_sources: int = 1,
) -> None:
    if extra_sources <= 0:
        return
    bucket = await resolve_plan_bucket_for_limits(db, tenant_id)
    cap = lead_sources_cap_for_bucket(bucket)
    n = current_count if current_count is not None else await count_tenant_lead_sources(db, tenant_id)
    if n + extra_sources > cap:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "lead_sources_limit_reached",
                "message": (
                    f"Lead source limit reached ({cap} on this plan). "
                    "Remove a source or upgrade in Billing."
                ),
                "plan_bucket": bucket,
                "limit": cap,
                "current": n,
            },
        )


def custom_funnel_definitions_cap_for_bucket(bucket: str) -> int:
    if bucket == "pro":
        return 20
    if bucket == "team":
        return 3
    return 1


async def count_communication_channel_accounts(db: AsyncSession, tenant_id: str) -> int:
    from backend.app.models.communication import CommunicationChannelAccount

    stmt = select(func.count()).select_from(CommunicationChannelAccount).where(
        CommunicationChannelAccount.tenant_id == tenant_id
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_communication_channel_account_create_allowed(db: AsyncSession, tenant_id: str) -> None:
    bucket = await resolve_plan_bucket_for_limits(db, tenant_id)
    cap = communication_channel_accounts_cap_for_bucket(bucket)
    n = await count_communication_channel_accounts(db, tenant_id)
    if n >= cap:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "communication_channels_limit_reached",
                "message": (
                    f"Communication channel limit reached ({cap} on this plan). "
                    "Remove an account or upgrade in Billing."
                ),
                "plan_bucket": bucket,
                "limit": cap,
                "current": n,
            },
        )


async def count_tenant_owned_funnels(db: AsyncSession, tenant_id: str) -> int:
    from backend.app.models.funnel import Funnel

    stmt = select(func.count()).select_from(Funnel).where(Funnel.tenant_id == tenant_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_custom_funnel_create_allowed(db: AsyncSession, tenant_id: str) -> None:
    bucket = await resolve_plan_bucket_for_limits(db, tenant_id)
    cap = custom_funnel_definitions_cap_for_bucket(bucket)
    n = await count_tenant_owned_funnels(db, tenant_id)
    if n >= cap:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "funnel_definitions_limit_reached",
                "message": (
                    f"Pipeline (funnel) definition limit reached ({cap} on this plan). "
                    "Archive/remove a funnel or upgrade in Billing."
                ),
                "plan_bucket": bucket,
                "limit": cap,
                "current": n,
            },
        )


async def ensure_automation_rules_mutation_allowed(db: AsyncSession, tenant_id: str) -> None:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    if not await tenant_allows_team_tier_features(db, tenant_id):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_requires_team",
                "feature": "automation_rules",
                "plan": plan,
            },
        )


def automation_rules_enabled_cap(plan: str, *, tenant_id: str | None = None) -> int | None:
    """Max enabled rules for Team-tier plans; None if tier cannot use rules (caller gates first)."""
    if is_focus_personnel_tenant(tenant_id):
        return 10_000
    p = (plan or "").strip().lower() or "starter"
    if not plan_allows_team_tier_features(p, tenant_id=tenant_id):
        return None
    return 10 if p in {"team", "trial"} else 50


async def count_enabled_automation_rules(db: AsyncSession, tenant_id: str) -> int:
    from backend.app.models.automation_rule import AutomationRule

    stmt = (
        select(func.count())
        .select_from(AutomationRule)
        .where(AutomationRule.tenant_id == tenant_id)
        .where(AutomationRule.enabled.is_(True))
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_automation_rules_enabled_count_allows_transition(
    db: AsyncSession,
    tenant_id: str,
    *,
    was_enabled: bool,
    will_be_enabled: bool,
) -> None:
    """§2.16: Team 10 / Business (pro) 50 enabled automation rules."""
    if not will_be_enabled or was_enabled:
        return
    plan = await resolve_tenant_plan_code(db, tenant_id)
    cap = automation_rules_enabled_cap(plan, tenant_id=tenant_id)
    if cap is None:
        return
    tenant = await db.get(Tenant, tenant_id)
    st = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else None
    effective = cap + pack_addon_int(st, AUTOMATION_RULES_ENABLED_CAP)
    n = await count_enabled_automation_rules(db, tenant_id)
    if n >= effective:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "automation_rules_limit_reached",
                "message": (
                    f"Enabled automation rule limit reached ({effective} on this plan, including add-ons). "
                    "Disable a rule or upgrade in Billing."
                ),
                "plan": plan,
                "limit": effective,
                "current": n,
            },
        )


async def ensure_leads_generic_inbound_webhook_allowed(db: AsyncSession, tenant_id: str) -> None:
    """§2.11 generic JSON webhook ingest + secret rotation (Team-tier, same slice as funnel slices)."""
    plan = await resolve_tenant_plan_code(db, tenant_id)
    if not await tenant_allows_team_tier_features(db, tenant_id):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_requires_team",
                "feature": "leads_generic_inbound_webhook",
                "plan": plan,
            },
        )
