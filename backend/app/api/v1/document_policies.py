"""API endpoints for managing document policies (tenant/client/vacancy-level document requirements)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.document_policy import DocumentPolicy, DocumentPolicyScope, RequirementLevel
from backend.app.models.user import Role
from backend.app.reference.requirement_policy_parallel_authority_retirement import (
    raise_document_policies_writes_retired,
)

router = APIRouter(prefix="/document-policies", tags=["document-policies"])


def _required_bool(level: RequirementLevel) -> bool:
    return level in (RequirementLevel.REQUIRED, RequirementLevel.BLOCKING)


def _level_from_required(required: bool) -> RequirementLevel:
    return RequirementLevel.REQUIRED if required else RequirementLevel.OPTIONAL


def _policy_scope_filter(active_own_company_id: str):
    return or_(
        DocumentPolicy.own_company_id == active_own_company_id,
        DocumentPolicy.own_company_id.is_(None),
    )


class DocumentPolicyIn(BaseModel):
    """Payload for creating/updating document policy."""

    scope: DocumentPolicyScope = Field(..., description="TENANT, CLIENT, or VACANCY")
    scope_id: Optional[str] = Field(None, description="Client ID or Vacancy ID (null for TENANT scope)")
    document_type_id: str = Field(..., description="Document type ID")
    enabled: bool = Field(True, description="Whether document type is enabled for this scope")
    required: bool = Field(False, description="Whether document is required")
    alert_days_before_expiry: Optional[int] = Field(None, ge=1, le=365, description="Days before expiry to alert")
    owner_user_id: Optional[str] = Field(None, description="User responsible for this document")
    notes: Optional[str] = Field(None, description="Internal notes")


class DocumentPolicyOut(BaseModel):
    """Response model for document policy."""

    id: str
    tenant_id: str
    own_company_id: Optional[str] = None
    scope: DocumentPolicyScope
    scope_id: Optional[str]
    document_type_id: Optional[str]
    enabled: bool
    required: bool
    alert_days_before_expiry: Optional[int]
    owner_user_id: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, policy: DocumentPolicy) -> "DocumentPolicyOut":
        """Create from ORM model."""
        return cls(
            id=policy.id,
            tenant_id=policy.tenant_id,
            own_company_id=getattr(policy, "own_company_id", None),
            scope=policy.scope,
            scope_id=policy.scope_id,
            document_type_id=policy.document_type_id,
            enabled=policy.enabled,
            required=_required_bool(policy.required_level),
            alert_days_before_expiry=policy.alert_days_before_expiry,
            owner_user_id=policy.owner_user_id,
            notes=policy.notes,
            created_at=policy.created_at.isoformat() if policy.created_at else "",
            updated_at=policy.updated_at.isoformat() if policy.updated_at else "",
        )


@router.get("", response_model=List[DocumentPolicyOut])
@router.get("/", response_model=List[DocumentPolicyOut])
async def list_document_policies(
    scope: Optional[DocumentPolicyScope] = Query(None, description="Filter by scope"),
    scope_id: Optional[str] = Query(None, description="Filter by scope_id (client/vacancy ID)"),
    document_type_id: Optional[str] = Query(None, description="Filter by document type"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
    active_own_company_id: str = Depends(resolve_active_own_company_id),
) -> List[DocumentPolicyOut]:
    """List document policies for the tenant (scoped to active own-company + legacy rows)."""
    db, tenant_id = db_tenant
    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
        .where(_policy_scope_filter(active_own_company_id))
    )

    if scope:
        stmt = stmt.where(DocumentPolicy.scope == scope)
    if scope_id:
        stmt = stmt.where(DocumentPolicy.scope_id == scope_id)
    if document_type_id:
        stmt = stmt.where(DocumentPolicy.document_type_id == document_type_id)

    rows = (await db.execute(stmt.order_by(DocumentPolicy.created_at.desc()))).scalars().all()
    return [DocumentPolicyOut.from_model(p) for p in rows]


@router.post("", response_model=DocumentPolicyOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DocumentPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_document_policy(
    payload: DocumentPolicyIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
    active_own_company_id: str = Depends(resolve_active_own_company_id),
) -> DocumentPolicyOut:
    """Create a new document policy."""
    raise_document_policies_writes_retired()
    db, tenant_id = db_tenant

    if payload.scope == DocumentPolicyScope.TENANT:
        if payload.scope_id is not None:
            raise HTTPException(
                status_code=422, detail="scope_id must be null for TENANT scope"
            )
    elif payload.scope in (DocumentPolicyScope.CLIENT, DocumentPolicyScope.VACANCY):
        if not payload.scope_id:
            raise HTTPException(
                status_code=422, detail=f"scope_id is required for {payload.scope.value} scope"
            )

    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
        .where(DocumentPolicy.scope == payload.scope)
        .where(DocumentPolicy.scope_id == payload.scope_id)
        .where(DocumentPolicy.document_type_id == payload.document_type_id)
        .where(DocumentPolicy.own_company_id == active_own_company_id)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Document policy already exists")

    policy = DocumentPolicy(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        own_company_id=active_own_company_id,
        scope=payload.scope,
        scope_id=payload.scope_id,
        document_type_id=payload.document_type_id,
        enabled=payload.enabled,
        required_level=_level_from_required(payload.required),
        alert_days_before_expiry=payload.alert_days_before_expiry,
        owner_user_id=payload.owner_user_id,
        notes=payload.notes,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return DocumentPolicyOut.from_model(policy)


@router.patch("/{policy_id}", response_model=DocumentPolicyOut)
async def update_document_policy(
    policy_id: str,
    payload: DocumentPolicyIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
    active_own_company_id: str = Depends(resolve_active_own_company_id),
) -> DocumentPolicyOut:
    """Update an existing document policy."""
    raise_document_policies_writes_retired()
    db, tenant_id = db_tenant

    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.id == policy_id)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
        .where(_policy_scope_filter(active_own_company_id))
    )
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Document policy not found")

    policy.scope = payload.scope
    policy.scope_id = payload.scope_id
    policy.document_type_id = payload.document_type_id
    policy.enabled = payload.enabled
    policy.required_level = _level_from_required(payload.required)
    policy.alert_days_before_expiry = payload.alert_days_before_expiry
    policy.owner_user_id = payload.owner_user_id
    policy.notes = payload.notes
    policy.own_company_id = active_own_company_id

    await db.commit()
    await db.refresh(policy)
    return DocumentPolicyOut.from_model(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_document_policy(
    policy_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
    active_own_company_id: str = Depends(resolve_active_own_company_id),
) -> None:
    """Delete a document policy."""
    raise_document_policies_writes_retired()
    db, tenant_id = db_tenant

    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.id == policy_id)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
        .where(_policy_scope_filter(active_own_company_id))
    )
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Document policy not found")

    await db.delete(policy)
    await db.commit()
