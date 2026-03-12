"""API endpoints for managing document policies (tenant/client/vacancy-level document requirements)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.document_policy import DocumentPolicy, DocumentPolicyScope
from backend.app.models.user import Role

router = APIRouter(prefix="/document-policies", tags=["document-policies"])


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
    scope: DocumentPolicyScope
    scope_id: Optional[str]
    document_type_id: str
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
            scope=policy.scope,
            scope_id=policy.scope_id,
            document_type_id=policy.document_type_id,
            enabled=policy.enabled,
            required=policy.required,
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
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> List[DocumentPolicyOut]:
    """List document policies for the tenant."""
    db, tenant_id = db_tenant
    stmt = select(DocumentPolicy).where(DocumentPolicy.tenant_id == str(tenant_id))

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
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> DocumentPolicyOut:
    """Create a new document policy."""
    db, tenant_id = db_tenant

    # Validate scope_id based on scope
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

    # Check if policy already exists
    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
        .where(DocumentPolicy.scope == payload.scope)
        .where(DocumentPolicy.scope_id == payload.scope_id)
        .where(DocumentPolicy.document_type_id == payload.document_type_id)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Document policy already exists")

    from uuid import uuid4

    policy = DocumentPolicy(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        scope=payload.scope,
        scope_id=payload.scope_id,
        document_type_id=payload.document_type_id,
        enabled=payload.enabled,
        required=payload.required,
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
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> DocumentPolicyOut:
    """Update an existing document policy."""
    db, tenant_id = db_tenant

    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.id == policy_id)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
    )
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Document policy not found")

    # Update fields
    policy.scope = payload.scope
    policy.scope_id = payload.scope_id
    policy.document_type_id = payload.document_type_id
    policy.enabled = payload.enabled
    policy.required = payload.required
    policy.alert_days_before_expiry = payload.alert_days_before_expiry
    policy.owner_user_id = payload.owner_user_id
    policy.notes = payload.notes

    await db.commit()
    await db.refresh(policy)
    return DocumentPolicyOut.from_model(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_policy(
    policy_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_roles(Role.admin, Role.supervisor)),
) -> None:
    """Delete a document policy."""
    db, tenant_id = db_tenant

    stmt = (
        select(DocumentPolicy)
        .where(DocumentPolicy.id == policy_id)
        .where(DocumentPolicy.tenant_id == str(tenant_id))
    )
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Document policy not found")

    await db.delete(policy)
    await db.commit()

