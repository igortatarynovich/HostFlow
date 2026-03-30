"""§2.11: public generic JSON webhook → Lead (same pipeline as Meta; source=webhook)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.app.db.deps import get_db
from backend.app.modules.leads import crud, service
from backend.app.modules.leads.schemas import MetaLeadResponse
from backend.app.services.plan_feature_gates import ensure_leads_generic_inbound_webhook_allowed

logger = logging.getLogger("backend.app.modules.leads.inbound_public")

router = APIRouter()


async def _apply_tenant_context(db: AsyncSession, tenant_id: str) -> None:
    db.info["tenant_id"] = UUID(tenant_id)
    try:
        await db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, false)"), {"tenant_id": tenant_id})
    except Exception:
        pass


@router.post(
    "/public/leads/inbound/{webhook_secret}",
    response_model=MetaLeadResponse,
    status_code=status.HTTP_200_OK,
)
async def post_generic_lead_inbound(
    webhook_secret: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MetaLeadResponse:
    secret = (webhook_secret or "").strip()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    settings_row = await crud.get_meta_settings_by_generic_inbound_webhook_secret(db, secret=secret)
    if not settings_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    tenant_id = str(settings_row.tenant_id)
    await _apply_tenant_context(db, tenant_id)
    await ensure_leads_generic_inbound_webhook_allowed(db, tenant_id)

    raw_body = await request.body()
    try:
        parsed: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON object expected")

    try:
        result = await service.process_generic_inbound_webhook_lead(
            db=db,
            tenant_id=tenant_id,
            own_company_id=None,
            body=parsed,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    await db.commit()
    logger.info("[webhook] inbound lead tenant=%s status=%s", tenant_id, result.status)
    return result.to_schema()
