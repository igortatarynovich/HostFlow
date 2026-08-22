"""Documents public contract v1 — entity-link resolve (E3 + E4 + E5).

Same adapter id as E2. Not a second Adapter. Not a candidate_id column list.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.document_hub_delivery_contract import (
    ADAPTER_ID,
    ALLOWED_ENTITY_LINK_RESOLVE,
    E3_RELATION_TYPE,
    PUBLIC_CONTRACT_ID,
    list_entity_link_documents_via_contract,
)

router = APIRouter(
    prefix="/platform/documents",
    tags=["documents-platform"],
    redirect_slashes=False,
)


class DocumentLinkOut(BaseModel):
    id: str
    linked_entity_type: str
    linked_entity_id: str
    relation_type: str


class DocumentHubViewOut(BaseModel):
    id: str
    title: str
    doc_type: str
    status: str
    expires_at: str | None = None
    link: DocumentLinkOut


class DocumentsResolveOut(BaseModel):
    contract_id: str = PUBLIC_CONTRACT_ID
    adapter_id: str = ADAPTER_ID
    items: list[DocumentHubViewOut] = Field(default_factory=list)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


@router.get("/resolve", response_model=DocumentsResolveOut)
async def resolve_documents_via_public_contract(
    linked_entity_type: str = Query(..., min_length=1),
    linked_entity_id: str = Query(..., min_length=1),
    relation_type: str = Query(E3_RELATION_TYPE),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, Any] = Depends(get_db_with_tenant),
) -> DocumentsResolveOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    etype = linked_entity_type.strip()
    rel = (relation_type or E3_RELATION_TYPE).strip() or E3_RELATION_TYPE
    if (etype, rel) not in ALLOWED_ENTITY_LINK_RESOLVE:
        raise HTTPException(
            status_code=400,
            detail="entity-link resolve allows workforce_employee / reused_for_hr or candidate / primary only",
        )
    try:
        items = await list_entity_link_documents_via_contract(
            db,
            tenant_id=tenant_id,
            linked_entity_type=etype,
            linked_entity_id=linked_entity_id.strip(),
            relation_type=rel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentsResolveOut(items=[DocumentHubViewOut.model_validate(row) for row in items])
