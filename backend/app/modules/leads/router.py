from __future__ import annotations

import hashlib
import hmac
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.leads import admin_service, service
from backend.app.modules.leads.schemas import LeadListResponse, MetaLeadResponse


router = APIRouter(prefix="/leads", tags=["leads"])


def _signature_matches(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.get("/", response_model=LeadListResponse)
@router.get("", response_model=LeadListResponse, include_in_schema=False)
async def list_leads_endpoint(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadListResponse:
    db, tenant_id = db_tenant
    return await service.list_leads(
        db,
        tenant_id=str(tenant_id),
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/meta", response_model=MetaLeadResponse)
async def ingest_meta_lead(
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaLeadResponse:
    body = await request.body()
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    header_signature = request.headers.get("X-Hub-Signature-256")
    signatures = await admin_service.get_active_secret_candidates(db, tenant_id)
    signature_status = "not_configured"

    if signatures:
        if not header_signature:
            await admin_service.mark_signature_status(db, tenant_id, "missing_header")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")

        matched = False
        matched_credential = None
        for credential_id, credential_obj, secret in signatures:
            if _signature_matches(secret, body, header_signature):
                matched = True
                matched_credential = credential_obj
                break

        if not matched:
            await admin_service.mark_signature_status(db, tenant_id, "mismatch")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature mismatch")

        signature_status = "ok"
        await admin_service.mark_credential_verified(db, matched_credential)
    else:
        signature_status = "not_configured"

    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - invalid payload
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    try:
        result = await service.process_meta_lead(
            db=db,
            tenant_id=str(tenant_id),
            payload=payload,
        )
    except service.LeadProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc

    await admin_service.mark_signature_status(db, tenant_id, signature_status)
    await db.commit()

    return result.to_schema()
