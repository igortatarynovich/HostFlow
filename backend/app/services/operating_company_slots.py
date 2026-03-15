from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLicense


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_company_role(raw: Any) -> str:
    return str(raw or "").strip().lower() or "client"


def extract_extra_operating_company_slots(subscription_payload: dict[str, Any] | None) -> int:
    payload = _as_dict(subscription_payload)
    candidates = [
        payload.get("extra_operating_company_slots"),
        payload.get("additional_operating_company_slots"),
        payload.get("operating_company_addon_slots"),
    ]
    for raw in candidates:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def extract_extra_operating_company_slots_from_tenant_settings(settings_payload: dict[str, Any] | None) -> int:
    settings_data = _as_dict(settings_payload)
    billing = _as_dict(settings_data.get("billing"))
    subscription = _as_dict(billing.get("subscription"))
    return extract_extra_operating_company_slots(subscription)


def resolve_effective_company_limit(included_limit: int, extra_slots: int) -> int:
    base = max(0, int(included_limit or 0))
    addon = max(0, int(extra_slots or 0))
    if base == 0:
        return 0
    return base + addon


@dataclass
class OperatingCompanySlots:
    included_limit: int
    extra_slots: int
    effective_limit: int
    used: int

    @property
    def unlimited(self) -> bool:
        return self.effective_limit == 0

    @property
    def available(self) -> int:
        if self.unlimited:
            return 0
        return max(0, self.effective_limit - self.used)


async def count_operating_companies(db: AsyncSession, tenant_id: str) -> int:
    rows = (
        await db.execute(select(Company).where(Company.tenant_id == tenant_id))
    ).scalars().all()
    count = 0
    for company in rows:
        extra = _as_dict(getattr(company, "extra", None))
        if _normalize_company_role(extra.get("company_role")) == "operating":
            count += 1
    return count


async def get_operating_company_slots(
    db: AsyncSession,
    tenant_id: str,
    *,
    preloaded_tenant: Tenant | None = None,
    preloaded_license: TenantLicense | None = None,
) -> OperatingCompanySlots:
    tenant = preloaded_tenant
    if tenant is None:
        tenant = await db.get(Tenant, tenant_id)
    license_entry = preloaded_license
    if license_entry is None:
        license_entry = (
            await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
        ).scalar_one_or_none()
    included_limit = int(getattr(license_entry, "max_companies", 0) or 0)
    extra_slots = extract_extra_operating_company_slots_from_tenant_settings(
        _as_dict(getattr(tenant, "settings", None)) if tenant is not None else {}
    )
    effective_limit = resolve_effective_company_limit(included_limit, extra_slots)
    used = await count_operating_companies(db, tenant_id)
    return OperatingCompanySlots(
        included_limit=included_limit,
        extra_slots=extra_slots,
        effective_limit=effective_limit,
        used=used,
    )
