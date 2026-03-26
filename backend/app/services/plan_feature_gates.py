"""Plan-based feature gates (§2.2 paywall, §2.16): Team-tier features vs starter/trial/free."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import TenantLicense

# Plans that do not get Team-tier automation (aligned with lead auto-distribution).
_TEAM_TIER_BLOCKED_PLANS: frozenset[str] = frozenset({"starter", "trial", "free", "solo"})

# §2.11 paywall: SOLO/starter-style plans cap tenant-defined lead custom fields (active, non-system).
_STARTER_TIER_MAX_LEAD_CUSTOM_FIELD_DEFINITIONS = 10
# §2.11: Meta field mapping rules + integration "slots" on low tiers (SSOT monetization table).
_STARTER_TIER_MAX_META_FIELD_MAPPING_RULES = 25
_STARTER_TIER_MAX_META_LEAD_CREDENTIALS = 1


def plan_allows_team_tier_features(plan: str) -> bool:
    p = (plan or "").strip().lower() or "starter"
    return p not in _TEAM_TIER_BLOCKED_PLANS


def plan_is_pro_tier(plan: str) -> bool:
    """Highest public tier for NBA / distribution upsells (§2.16)."""
    return (plan or "").strip().lower() == "pro"


def lead_custom_field_definitions_cap(plan: str) -> int | None:
    """Max active non-system LEAD definitions; None = no cap (Team+)."""
    p = (plan or "").strip().lower() or "starter"
    if p in _TEAM_TIER_BLOCKED_PLANS:
        return _STARTER_TIER_MAX_LEAD_CUSTOM_FIELD_DEFINITIONS
    return None


def lead_meta_field_mapping_rules_cap(plan: str) -> int | None:
    """Max rows in meta_lead_settings.field_mapping; None = unlimited (Team+)."""
    p = (plan or "").strip().lower() or "starter"
    if p in _TEAM_TIER_BLOCKED_PLANS:
        return _STARTER_TIER_MAX_META_FIELD_MAPPING_RULES
    return None


def lead_meta_credentials_cap(plan: str) -> int | None:
    """Max Meta lead credentials per tenant; None = unlimited (Team+)."""
    p = (plan or "").strip().lower() or "starter"
    if p in _TEAM_TIER_BLOCKED_PLANS:
        return _STARTER_TIER_MAX_META_LEAD_CREDENTIALS
    return None


async def ensure_meta_lead_field_mapping_rows_allowed(
    db: AsyncSession, tenant_id: str, rule_count: int
) -> None:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    cap = lead_meta_field_mapping_rules_cap(plan)
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
    cap = lead_meta_credentials_cap(plan)
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
    cap = lead_custom_field_definitions_cap(plan)
    if cap is None:
        return
    n = await count_active_lead_custom_field_definitions(db, tenant_id)
    if n >= cap:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_lead_custom_fields_limit",
                "message": (
                    f"Lead custom field limit reached ({cap} fields on this plan). "
                    "Upgrade to a Team-tier plan to add more."
                ),
                "plan": plan,
                "limit": cap,
                "current": n,
            },
        )


async def resolve_tenant_plan_code(db: AsyncSession, tenant_id: str) -> str:
    row = await db.execute(
        select(TenantLicense.plan).where(TenantLicense.tenant_id == tenant_id).limit(1)
    )
    raw = row.scalar_one_or_none()
    return str(raw or "starter").strip().lower() or "starter"


async def ensure_automation_rules_mutation_allowed(db: AsyncSession, tenant_id: str) -> None:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    if not plan_allows_team_tier_features(plan):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_requires_team",
                "feature": "automation_rules",
                "plan": plan,
            },
        )
