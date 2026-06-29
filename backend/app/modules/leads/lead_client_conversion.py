"""Explicit conversion use-case: Lead → Client company (P5B)."""

from __future__ import annotations

from typing import Any, Optional

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.outcome_payload_mapping import map_normalized_to_client_company_create
from backend.app.models import Company, Lead
from backend.app.modules.companies import schemas as company_schemas
from backend.app.modules.companies.service import create_company_service
from backend.app.services.tenant_links import ensure_client_company_tenant_link


def _ensure_session_tenant_id(db: AsyncSession, tenant_id: str) -> None:
    tid = str(tenant_id)
    if isinstance(getattr(db, "info", None), dict):
        db.info["tenant_id"] = UUID(tid) if len(tid) == 36 else tid


async def create_client_from_lead_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source_channel: str,
    conversion_reason: str,
) -> tuple[Company, bool]:
    """Create or return existing Client company linked from intake Lead.

    Idempotency: if ``lead.converted_client_id`` points to a live tenant-scoped
    company row, return it with ``idempotent_replay=True``.
    """
    linked_id = getattr(lead, "converted_client_id", None)
    if linked_id:
        res = await db.execute(
            select(Company).where(
                Company.id == str(linked_id),
                Company.tenant_id == tenant_id,
            )
        )
        existing = res.scalar_one_or_none()
        if existing is not None:
            return existing, True

    payload = lead.payload if isinstance(getattr(lead, "payload", None), dict) else {}
    company_kwargs = map_normalized_to_client_company_create(
        normalized,
        lead_payload=payload,
        source_channel=source_channel,
        lead_id=str(lead.id),
    )
    company_in = company_schemas.CompanyCreate(**company_kwargs)
    _ensure_session_tenant_id(db, tenant_id)
    client = await create_company_service(db=db, data=company_in, actor_user_id=None)
    await ensure_client_company_tenant_link(
        db,
        agency_tenant_id=tenant_id,
        client_company_id=str(client.id),
        handoff_enabled=True,
    )

    lead.converted_client_id = str(client.id)
    normalized_updated = dict(normalized)
    normalized_updated["converted_client_id"] = str(client.id)
    normalized_updated["outcome_client_conversion_reason"] = conversion_reason
    lead.normalized = normalized_updated
    lead.status = "processed"
    lead.stage = "converted"
    lead.error = None
    await db.flush()
    return client, False


def existing_client_id_from_lead(lead: Lead, normalized: Optional[dict[str, Any]] = None) -> Optional[str]:
    linked = _trim(getattr(lead, "converted_client_id", None))
    if linked:
        return linked
    norm = normalized if isinstance(normalized, dict) else (lead.normalized if isinstance(lead.normalized, dict) else {})
    return _trim(norm.get("converted_client_id"))


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None
