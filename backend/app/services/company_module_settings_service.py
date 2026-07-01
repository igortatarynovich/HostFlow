"""CRUD for company_module_settings (ADR-005)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.product_module_keys import COMPANY_MODULE_SETTING_KEYS
from backend.app.models.company import Company
from backend.app.models.company_module_settings import CompanyModuleSettings


def normalize_module_key(raw: str) -> str:
    key = (raw or "").strip().lower()
    if key not in COMPANY_MODULE_SETTING_KEYS:
        raise ValueError(f"module_key must be one of: {', '.join(sorted(COMPANY_MODULE_SETTING_KEYS))}")
    return key


async def get_company_for_tenant(
    db: AsyncSession, tenant_id: str, company_id: str
) -> Optional[Company]:
    res = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def get_row(
    db: AsyncSession,
    tenant_id: str,
    company_id: str,
    module_key: str,
) -> Optional[CompanyModuleSettings]:
    res = await db.execute(
        select(CompanyModuleSettings).where(
            CompanyModuleSettings.tenant_id == tenant_id,
            CompanyModuleSettings.company_id == company_id,
            CompanyModuleSettings.module_key == module_key,
        )
    )
    return res.scalar_one_or_none()


async def list_rows_for_company(
    db: AsyncSession,
    tenant_id: str,
    company_id: str,
) -> list[CompanyModuleSettings]:
    res = await db.execute(
        select(CompanyModuleSettings)
        .where(
            CompanyModuleSettings.tenant_id == tenant_id,
            CompanyModuleSettings.company_id == company_id,
        )
        .order_by(CompanyModuleSettings.module_key.asc())
    )
    return list(res.scalars().all())


async def upsert_settings(
    db: AsyncSession,
    tenant_id: str,
    company_id: str,
    module_key: str,
    *,
    settings_json: Optional[dict[str, Any]] = None,
    is_enabled: Optional[bool] = None,
) -> CompanyModuleSettings:
    row = await get_row(db, tenant_id, company_id, module_key)
    now = datetime.now(timezone.utc)
    if row is None:
        payload: dict[str, Any] = dict(settings_json) if isinstance(settings_json, dict) else {}
        en = bool(is_enabled) if is_enabled is not None else False
        configured_at = now if (en or bool(payload)) else None
        row = CompanyModuleSettings(
            id=str(uuid4()),
            tenant_id=tenant_id,
            company_id=company_id,
            module_key=module_key,
            settings_json=payload,
            is_enabled=en,
            configured_at=configured_at,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    if settings_json is not None:
        row.settings_json = dict(settings_json)
    if is_enabled is not None:
        row.is_enabled = bool(is_enabled)
    row.updated_at = now
    if row.configured_at is None and (row.is_enabled or bool(row.settings_json)):
        row.configured_at = now
    await db.flush()
    return row
