"""Tenant business type resolution — neutral layer (no leads service imports)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Company, OwnCompany, Tenant


def normalize_business_type(raw_business_type: Any, tenant_type: Any) -> str:
    normalized = str(raw_business_type or "").strip().lower()
    if normalized in {"agency", "employer", "services"}:
        return normalized
    tenant_type_value = str(getattr(tenant_type, "value", tenant_type or "")).strip().lower()
    return "employer" if tenant_type_value == "company" else "agency"


async def load_tenant_business_type(
    db: AsyncSession,
    tenant_id: str,
    own_company_id: Optional[str] = None,
) -> str:
    operating_company_type: Optional[str] = None
    if own_company_id:
        try:
            row = await db.execute(
                select(OwnCompany.extra)
                .where(
                    OwnCompany.tenant_id == tenant_id,
                    OwnCompany.id == own_company_id,
                    OwnCompany.is_archived.is_(False),
                )
                .limit(1)
            )
            extra = row.scalar_one_or_none()
            if isinstance(extra, dict):
                ct = (
                    extra.get("business_type")
                    or extra.get("company_type")
                    or extra.get("company_kind")
                    or extra.get("kind")
                )
                if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                    operating_company_type = ct.strip().lower()
        except Exception:
            operating_company_type = None

    try:
        if operating_company_type is None:
            rows = await db.execute(
                select(Company.extra)
                .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
                .order_by(Company.created_at.asc())
                .limit(50)
            )
            for (extra,) in rows.all():
                if not isinstance(extra, dict):
                    continue
                role = str(extra.get("company_role") or "").strip().lower()
                if role != "operating":
                    continue
                ct = (
                    extra.get("company_type")
                    or extra.get("business_type")
                    or extra.get("company_kind")
                    or extra.get("kind")
                )
                if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                    operating_company_type = ct.strip().lower()
                    break
    except Exception:
        operating_company_type = None

    row = (await db.execute(select(Tenant.settings, Tenant.type).where(Tenant.id == tenant_id).limit(1))).first()
    if not row:
        return "agency"
    settings_payload, tenant_type = row
    settings_dict = settings_payload if isinstance(settings_payload, dict) else {}
    raw = operating_company_type if operating_company_type is not None else settings_dict.get("business_type")
    return normalize_business_type(raw, tenant_type)


__all__ = ["load_tenant_business_type", "normalize_business_type"]
