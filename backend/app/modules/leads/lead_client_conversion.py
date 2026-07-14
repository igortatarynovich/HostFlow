"""Explicit conversion use-case: Lead → ClientAccount (+ optional Company) (Stage 1A)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.outcome_payload_mapping import map_normalized_to_client_company_create
from backend.app.models import Company, Lead
from backend.app.modules.client_accounts.conversion import convert_client_lead
from backend.app.modules.companies import schemas as company_schemas


async def create_client_from_lead_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source_channel: str,
    conversion_reason: str,
) -> tuple[Company | None, bool]:
    """Create or return existing ClientAccount / Company linked from intake Lead.

    Idempotency: replays return existing rows with ``idempotent_replay=True``.
    Legacy callers receive ``Company`` when a billing party exists, else ``None``.
    """
    company_in: company_schemas.CompanyCreate | None = None
    try:
        payload = lead.payload if isinstance(getattr(lead, "payload", None), dict) else {}
        company_kwargs = map_normalized_to_client_company_create(
            normalized,
            lead_payload=payload,
            source_channel=source_channel,
            lead_id=str(lead.id),
        )
        company_in = company_schemas.CompanyCreate(**company_kwargs)
    except Exception:
        company_in = None

    result = await convert_client_lead(
        db,
        tenant_id=tenant_id,
        lead=lead,
        actor_id=None,
        conversion_reason=conversion_reason,
        company_in=company_in,
    )
    return result.company, result.idempotent_replay


def existing_client_id_from_lead(lead: Lead, normalized: Optional[dict[str, Any]] = None) -> Optional[str]:
    linked = _trim(getattr(lead, "converted_client_id", None))
    if linked:
        return linked
    norm = normalized if isinstance(normalized, dict) else (lead.normalized if isinstance(lead.normalized, dict) else {})
    return _trim(norm.get("converted_client_id"))


def existing_client_account_id_from_lead(lead: Lead, normalized: Optional[dict[str, Any]] = None) -> Optional[str]:
    linked = _trim(getattr(lead, "client_account_id", None))
    if linked:
        return linked
    norm = normalized if isinstance(normalized, dict) else (lead.normalized if isinstance(lead.normalized, dict) else {})
    return _trim(norm.get("client_account_id"))


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None
