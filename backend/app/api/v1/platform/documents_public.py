"""Documents public contract v1 — entity-link resolve (E3 + E4 + E5 + E6 + E7 + E8-bind).

Same adapter id as E2. Not a second Adapter. Not a candidate_id column list.
E6 projects Hub expiry (`expires_at` / `expiry_state`) on the resolve view.
E7 projects Hub outstanding asks (`outstanding_asks`) on the same resolve.
DR1-runtime may persist Engine-projected asks on this adapter; resolve
prefers those rows when present. E8-bind projects canonical registry type
identity (display / select / persist). Aliases resolve via R4 only.
Not a Hub request table. Not E8-eval. Not mass D3–D9 bind.
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
    list_canonical_types_for_select_via_contract,
    list_entity_link_documents_via_contract,
    load_outstanding_asks_via_contract,
    persist_canonical_type_identity_via_contract,
    project_outstanding_asks_via_contract,
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
    expiry_state: str | None = None
    days_left: int | None = None
    link: DocumentLinkOut


class OutstandingAskOut(BaseModel):
    doc_type: str
    state: str


class DocumentsResolveOut(BaseModel):
    contract_id: str = PUBLIC_CONTRACT_ID
    adapter_id: str = ADAPTER_ID
    items: list[DocumentHubViewOut] = Field(default_factory=list)
    outstanding_asks: list[OutstandingAskOut] = Field(default_factory=list)
    canonical_types: list[str] = Field(default_factory=list)


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
    persisted = load_outstanding_asks_via_contract(
        linked_entity_type=etype,
        linked_entity_id=linked_entity_id.strip(),
    )
    if persisted is not None:
        asks = []
        for row in persisted:
            code = persist_canonical_type_identity_via_contract(row.get("doc_type"))
            state = str(row.get("state") or "").strip()
            if code and state:
                asks.append({"doc_type": code, "state": state})
    else:
        asks = project_outstanding_asks_via_contract(items)
    return DocumentsResolveOut(
        items=[DocumentHubViewOut.model_validate(row) for row in items],
        outstanding_asks=[OutstandingAskOut.model_validate(row) for row in asks],
        canonical_types=list_canonical_types_for_select_via_contract(),
    )
