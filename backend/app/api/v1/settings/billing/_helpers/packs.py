"""Add-on pack application — translates a purchased SKU into tenant mutations.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 5/N).

Contents:

* ``_apply_portal_candidates_pack_to_tenant`` — bumps
  ``usage_v1.portal_monthly_cap_addon_v1`` (§2.16).
* ``_apply_client_portal_pack_5_to_tenant`` — bumps ``max_public_portal_links``
  on the license row by 5, then re-syncs the addon-v1 deltas.
* ``_apply_pack_addon_to_tenant`` — generic ``pack_addons_v1`` field bumper
  (used for monthly leads, automation rules, custom fields, lead forms).
* ``_apply_license_numeric_pack_to_tenant`` — generic ``TenantLicense``
  numeric-column bumper (used for active records and storage GB).
* ``_apply_addon_pack_by_sku`` — top-level dispatcher: SKU → which apply fn.
  Raises ``ValueError`` for unknown SKUs.
* ``_checkout_session_line_items_contain_price`` — utility for webhook handlers
  to verify a Checkout session expanded ``line_items`` contains the expected
  Stripe price id.

Each apply-fn is idempotent via ``dedupe_key`` checked through
``state._history_contains``.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services import portal_candidate_usage
from backend.app.services.billing_pack_addons import (
    AUTOMATION_RULES_ENABLED_CAP,
    LEAD_CUSTOM_FIELD_DEFINITIONS_CAP,
    LEAD_FORMS_ACTIVE_CAP,
    MONTHLY_LEADS_CAP,
    merge_pack_addon_into_settings,
)

from .history import _history_entry
from .license_sync import sync_subscription_license_addon_v1
from .state import _history_contains, _now_utc


async def _apply_portal_candidates_pack_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    increment: int,
    history_title: str,
    history_description: str,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    st = dict(tenant.settings or {})
    st = portal_candidate_usage.merge_increment_portal_monthly_cap_addon(st, increment)
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="portal_candidates.pack_purchased",
            status="success",
            title=history_title,
            description=history_description,
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_client_portal_pack_5_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    tenant_id = str(tenant.id)
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if license_row is None:
        license_row = TenantLicense(tenant_id=tenant_id, plan="team", auto_renew=True, notes="billing-managed")
        db.add(license_row)
        await db.flush()
    license_row.max_public_portal_links = int(getattr(license_row, "max_public_portal_links", 0) or 0) + 5
    await db.commit()
    await db.refresh(license_row)
    await sync_subscription_license_addon_v1(db, tenant_id=tenant_id, license_row=license_row)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    st = dict(tenant.settings or {})
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="addon_pack.purchased",
            status="success",
            title="Client portal pack purchased",
            description="+5 client portal link slots (add-on).",
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_pack_addon_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    field: str,
    increment: int,
    history_title: str,
    history_description: str,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    st = dict(tenant.settings or {})
    st = merge_pack_addon_into_settings(st, field, int(increment))
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="addon_pack.purchased",
            status="success",
            title=history_title,
            description=history_description,
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_license_numeric_pack_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    attr_name: str,
    increment: int,
    history_title: str,
    history_description: str,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    tenant_id = str(tenant.id)
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if license_row is None:
        license_row = TenantLicense(tenant_id=tenant_id, plan="team", auto_renew=True, notes="billing-managed")
        db.add(license_row)
        await db.flush()
    cur = int(getattr(license_row, attr_name, 0) or 0)
    setattr(license_row, attr_name, cur + max(0, int(increment)))
    await db.commit()
    await db.refresh(license_row)
    await sync_subscription_license_addon_v1(db, tenant_id=tenant_id, license_row=license_row)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    st = dict(tenant.settings or {})
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="addon_pack.purchased",
            status="success",
            title=history_title,
            description=history_description,
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_addon_pack_by_sku(
    db: AsyncSession,
    tenant: Tenant,
    *,
    sku: str,
    increment: int,
    dedupe_key: str,
    plan_code: str | None,
    history_source: Literal["app", "stripe"],
) -> None:
    if sku == "pack_portal_candidates":
        await _apply_portal_candidates_pack_to_tenant(
            db,
            tenant,
            increment=int(increment),
            history_title="Candidate portal pack purchased",
            history_description=f"+{increment} active portal candidates / month (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_client_portal_5":
        await _apply_client_portal_pack_5_to_tenant(
            db,
            tenant,
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_leads_500":
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=MONTHLY_LEADS_CAP,
            increment=int(increment),
            history_title="Leads pack purchased",
            history_description=f"+{increment} inbound leads / month (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku in ("pack_automation_rules_10", "pack_automation_rules_25"):
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=AUTOMATION_RULES_ENABLED_CAP,
            increment=int(increment),
            history_title="Automation rules pack purchased",
            history_description=f"+{increment} enabled automation rules capacity (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku in ("pack_custom_fields_25", "pack_custom_fields_100"):
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=LEAD_CUSTOM_FIELD_DEFINITIONS_CAP,
            increment=int(increment),
            history_title="Lead custom fields pack purchased",
            history_description=f"+{increment} lead custom field definitions on starter-tier cap (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_active_records_2000":
        await _apply_license_numeric_pack_to_tenant(
            db,
            tenant,
            attr_name="max_candidates_active",
            increment=int(increment),
            history_title="Active records pack purchased",
            history_description=f"+{increment} active candidate records (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_storage_50gb":
        await _apply_license_numeric_pack_to_tenant(
            db,
            tenant,
            attr_name="max_storage_gb",
            increment=int(increment),
            history_title="Storage pack purchased",
            history_description=f"+{increment} GB storage (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_lead_forms_5":
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=LEAD_FORMS_ACTIVE_CAP,
            increment=int(increment),
            history_title="Lead forms pack purchased",
            history_description=f"+{increment} active lead form slots (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    raise ValueError(f"Add-on SKU apply not implemented: {sku}")


def _checkout_session_line_items_contain_price(session_full: dict[str, Any], expected_price_id: str) -> bool:
    exp = (expected_price_id or "").strip()
    if not exp:
        return False
    li_container = session_full.get("line_items") if isinstance(session_full.get("line_items"), dict) else {}
    lines = li_container.get("data") if isinstance(li_container.get("data"), list) else []
    for line in lines:
        if not isinstance(line, dict):
            continue
        price_obj = line.get("price")
        if isinstance(price_obj, dict):
            pid = str(price_obj.get("id") or "").strip()
            if pid == exp:
                return True
    return False
