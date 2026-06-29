"""Explicit conversion use-case: Lead → Service Order (P5B)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.outcome_payload_mapping import map_normalized_to_service_order_create
from backend.app.models import Lead
from backend.app.models.additional_service import ServiceOrder
from backend.app.services.additional_services import AdditionalServicesService


def existing_service_order_id_from_lead(
    lead: Lead,
    normalized: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    norm = normalized if isinstance(normalized, dict) else (lead.normalized if isinstance(lead.normalized, dict) else {})
    return _trim(norm.get("service_order_id"))


async def create_service_order_from_lead_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source_channel: str,
    conversion_reason: str,
) -> tuple[ServiceOrder, bool]:
    """Create or return existing ServiceOrder linked from intake Lead."""
    existing_id = existing_service_order_id_from_lead(lead, normalized)
    svc = AdditionalServicesService(db, tenant_id)
    if existing_id:
        order = await svc.get_order(existing_id)
        return order, True

    order_payload = map_normalized_to_service_order_create(
        normalized,
        lead=lead,
        source_channel=source_channel,
    )
    order = await svc.create_order(order_payload, [])

    normalized_updated = dict(normalized)
    normalized_updated["service_order_id"] = order.id
    normalized_updated["service_order_created_at"] = (
        order.created_at.isoformat() if getattr(order, "created_at", None) else None
    )
    normalized_updated["outcome_service_order_conversion_reason"] = conversion_reason
    lead.normalized = normalized_updated
    lead.status = "processed"
    lead.error = None
    await db.flush()
    return order, False


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None
