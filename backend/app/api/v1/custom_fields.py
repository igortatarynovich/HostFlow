"""API endpoints for managing custom field definitions and values."""

from __future__ import annotations

from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.custom_field import (
    CustomFieldDefinition,
    CustomFieldValue,
    CustomFieldScope,
    CustomFieldEntityType,
    CustomFieldType,
)
from backend.app.models.user import Role
from backend.app.services.plan_feature_gates import ensure_lead_custom_field_definition_create_allowed

router = APIRouter(prefix="/custom-fields", tags=["custom-fields"])


class CustomFieldDefinitionIn(BaseModel):
    """Payload for creating/updating custom field definition."""

    scope: CustomFieldScope = Field(..., description="CANDIDATE, LEAD, or DOCUMENT")
    document_type_id: Optional[str] = Field(None, description="Required if scope=DOCUMENT")
    key: str = Field(..., min_length=1, max_length=128, description="Unique key (slug)")
    label: str = Field(..., min_length=1, max_length=256, description="Display label")
    field_type: CustomFieldType = Field(..., description="Field type")
    required: bool = Field(False, description="Whether field is required")
    options: Optional[List[str]] = Field(None, description="Options for select/multiselect")
    help_text: Optional[str] = Field(None, description="Help text")
    is_active: bool = Field(True, description="Whether field is active")
    order: int = Field(0, ge=0, description="Display order")


class CustomFieldDefinitionOut(BaseModel):
    """Response model for custom field definition."""

    id: str
    tenant_id: str
    scope: CustomFieldScope
    document_type_id: Optional[str]
    key: str
    label: str
    field_type: CustomFieldType
    required: bool
    options: Optional[List[str]]
    help_text: Optional[str]
    is_active: bool
    is_system: bool
    order: int
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, definition: CustomFieldDefinition) -> "CustomFieldDefinitionOut":
        """Create from ORM model."""
        return cls(
            id=definition.id,
            tenant_id=definition.tenant_id,
            scope=definition.scope,
            document_type_id=definition.document_type_id,
            key=definition.key,
            label=definition.label,
            field_type=definition.field_type,
            required=definition.required,
            options=definition.options if isinstance(definition.options, list) else None,
            help_text=definition.help_text,
            is_active=definition.is_active,
            is_system=definition.is_system,
            order=definition.order,
            created_at=definition.created_at.isoformat() if definition.created_at else "",
            updated_at=definition.updated_at.isoformat() if definition.updated_at else "",
        )


class CustomFieldValueIn(BaseModel):
    """Payload for setting custom field value."""

    value: Any = Field(..., description="Field value (type depends on field_type)")


class CustomFieldValueOut(BaseModel):
    """Response model for custom field value."""

    id: str
    tenant_id: str
    definition_id: str
    entity_type: CustomFieldEntityType
    entity_id: str
    value: Any
    updated_at: str
    updated_by_user_id: Optional[str]

    @classmethod
    def from_model(cls, value: CustomFieldValue) -> "CustomFieldValueOut":
        """Create from ORM model."""
        raw = value.value
        out_val: Any = raw
        if isinstance(raw, dict) and set(raw.keys()) == {"v"}:
            out_val = raw.get("v")
        return cls(
            id=value.id,
            tenant_id=value.tenant_id,
            definition_id=value.definition_id,
            entity_type=value.entity_type,
            entity_id=value.entity_id,
            value=out_val,
            updated_at=value.updated_at.isoformat() if value.updated_at else "",
            updated_by_user_id=value.updated_by_user_id,
        )


@router.get("/definitions", response_model=List[CustomFieldDefinitionOut])
async def list_custom_field_definitions(
    scope: Optional[CustomFieldScope] = Query(None, description="Filter by scope"),
    document_type_id: Optional[str] = Query(None, description="Filter by document type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> List[CustomFieldDefinitionOut]:
    """List custom field definitions for the tenant."""
    db, tenant_id = db_tenant
    stmt = select(CustomFieldDefinition).where(CustomFieldDefinition.tenant_id == str(tenant_id))

    if scope:
        stmt = stmt.where(CustomFieldDefinition.scope == scope)
    if document_type_id:
        stmt = stmt.where(CustomFieldDefinition.document_type_id == document_type_id)
    if is_active is not None:
        stmt = stmt.where(CustomFieldDefinition.is_active == is_active)

    rows = (
        (await db.execute(stmt.order_by(CustomFieldDefinition.order, CustomFieldDefinition.created_at)))
        .scalars()
        .all()
    )
    return [CustomFieldDefinitionOut.from_model(d) for d in rows]


@router.post("/definitions", response_model=CustomFieldDefinitionOut, status_code=status.HTTP_201_CREATED)
async def create_custom_field_definition(
    payload: CustomFieldDefinitionIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> CustomFieldDefinitionOut:
    """Create a new custom field definition."""
    db, tenant_id = db_tenant

    # Validate scope and document_type_id
    if payload.scope == CustomFieldScope.DOCUMENT:
        if not payload.document_type_id:
            raise HTTPException(
                status_code=422, detail="document_type_id is required for DOCUMENT scope"
            )
    elif payload.scope == CustomFieldScope.CANDIDATE:
        if payload.document_type_id:
            raise HTTPException(
                status_code=422, detail="document_type_id must be null for CANDIDATE scope"
            )
    elif payload.scope == CustomFieldScope.LEAD:
        if payload.document_type_id:
            raise HTTPException(
                status_code=422, detail="document_type_id must be null for LEAD scope"
            )

    # Validate options for select/multiselect
    if payload.field_type in (CustomFieldType.SELECT, CustomFieldType.MULTISELECT):
        if not payload.options or len(payload.options) == 0:
            raise HTTPException(
                status_code=422,
                detail=f"options are required for {payload.field_type.value} field type",
            )

    # Check uniqueness
    stmt = select(CustomFieldDefinition).where(CustomFieldDefinition.tenant_id == str(tenant_id))
    if payload.scope == CustomFieldScope.CANDIDATE:
        stmt = (
            stmt.where(CustomFieldDefinition.scope == CustomFieldScope.CANDIDATE)
            .where(CustomFieldDefinition.key == payload.key)
            .where(CustomFieldDefinition.document_type_id.is_(None))
        )
    elif payload.scope == CustomFieldScope.LEAD:
        stmt = (
            stmt.where(CustomFieldDefinition.scope == CustomFieldScope.LEAD)
            .where(CustomFieldDefinition.key == payload.key)
            .where(CustomFieldDefinition.document_type_id.is_(None))
        )
    else:
        stmt = (
            stmt.where(CustomFieldDefinition.scope == CustomFieldScope.DOCUMENT)
            .where(CustomFieldDefinition.document_type_id == payload.document_type_id)
            .where(CustomFieldDefinition.key == payload.key)
        )

    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Custom field definition with this key already exists")

    if payload.scope == CustomFieldScope.LEAD:
        await ensure_lead_custom_field_definition_create_allowed(db, str(tenant_id))

    from uuid import uuid4

    definition = CustomFieldDefinition(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        scope=payload.scope,
        document_type_id=payload.document_type_id,
        key=payload.key,
        label=payload.label,
        field_type=payload.field_type,
        required=payload.required,
        options=payload.options,
        help_text=payload.help_text,
        is_active=payload.is_active,
        is_system=False,
        order=payload.order,
    )
    db.add(definition)
    await db.commit()
    await db.refresh(definition)
    return CustomFieldDefinitionOut.from_model(definition)


@router.patch("/definitions/{definition_id}", response_model=CustomFieldDefinitionOut)
async def update_custom_field_definition(
    definition_id: str,
    payload: CustomFieldDefinitionIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> CustomFieldDefinitionOut:
    """Update an existing custom field definition."""
    db, tenant_id = db_tenant

    stmt = (
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.id == definition_id)
        .where(CustomFieldDefinition.tenant_id == str(tenant_id))
    )
    definition = (await db.execute(stmt)).scalar_one_or_none()
    if not definition:
        raise HTTPException(status_code=404, detail="Custom field definition not found")
    if definition.is_system:
        raise HTTPException(status_code=409, detail="System custom field cannot be modified")

    # Update fields (key and scope/document_type_id should not change)
    definition.label = payload.label
    definition.field_type = payload.field_type
    definition.required = payload.required
    definition.options = payload.options
    definition.help_text = payload.help_text
    definition.is_active = payload.is_active
    definition.order = payload.order

    await db.commit()
    await db.refresh(definition)
    return CustomFieldDefinitionOut.from_model(definition)


@router.delete("/definitions/{definition_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_custom_field_definition(
    definition_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> None:
    """Delete (deactivate) a custom field definition."""
    db, tenant_id = db_tenant

    stmt = (
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.id == definition_id)
        .where(CustomFieldDefinition.tenant_id == str(tenant_id))
    )
    definition = (await db.execute(stmt)).scalar_one_or_none()
    if not definition:
        raise HTTPException(status_code=404, detail="Custom field definition not found")
    if definition.is_system:
        raise HTTPException(status_code=409, detail="System custom field cannot be deleted")

    # Soft delete: set is_active=False instead of hard delete
    definition.is_active = False
    await db.commit()


@router.get("/values", response_model=List[CustomFieldValueOut])
async def list_custom_field_values(
    definition_id: Optional[str] = Query(None, description="Filter by definition ID"),
    entity_type: Optional[CustomFieldEntityType] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> List[CustomFieldValueOut]:
    """List custom field values."""
    db, tenant_id = db_tenant
    stmt = select(CustomFieldValue).where(CustomFieldValue.tenant_id == str(tenant_id))

    if definition_id:
        stmt = stmt.where(CustomFieldValue.definition_id == definition_id)
    if entity_type:
        stmt = stmt.where(CustomFieldValue.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(CustomFieldValue.entity_id == entity_id)

    rows = (await db.execute(stmt.order_by(CustomFieldValue.updated_at.desc()))).scalars().all()
    return [CustomFieldValueOut.from_model(v) for v in rows]


@router.put(
    "/values/{definition_id}/{entity_type}/{entity_id}",
    response_model=CustomFieldValueOut,
)
async def set_custom_field_value(
    definition_id: str,
    entity_type: CustomFieldEntityType,
    entity_id: str,
    payload: CustomFieldValueIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> CustomFieldValueOut:
    """Set or update a custom field value."""
    db, tenant_id = db_tenant

    # Verify definition exists and belongs to tenant
    stmt_def = (
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.id == definition_id)
        .where(CustomFieldDefinition.tenant_id == str(tenant_id))
        .where(CustomFieldDefinition.is_active == True)
    )
    definition = (await db.execute(stmt_def)).scalar_one_or_none()
    if not definition:
        raise HTTPException(status_code=404, detail="Custom field definition not found or inactive")

    scope_entity_ok = (
        (definition.scope == CustomFieldScope.CANDIDATE and entity_type == CustomFieldEntityType.CANDIDATE)
        or (definition.scope == CustomFieldScope.LEAD and entity_type == CustomFieldEntityType.LEAD)
        or (
            definition.scope == CustomFieldScope.DOCUMENT
            and entity_type == CustomFieldEntityType.CANDIDATE_DOCUMENT
        )
    )
    if not scope_entity_ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="entity_type does not match definition scope",
        )

    # Check if value already exists
    stmt_value = (
        select(CustomFieldValue)
        .where(CustomFieldValue.tenant_id == str(tenant_id))
        .where(CustomFieldValue.definition_id == definition_id)
        .where(CustomFieldValue.entity_type == entity_type)
        .where(CustomFieldValue.entity_id == entity_id)
    )
    existing_value = (await db.execute(stmt_value)).scalar_one_or_none()

    from uuid import uuid4
    from datetime import datetime, timezone

    stored_value: dict
    if isinstance(payload.value, dict):
        stored_value = dict(payload.value)
    else:
        stored_value = {"v": payload.value}

    if existing_value:
        existing_value.value = stored_value
        existing_value.updated_at = datetime.now(timezone.utc)
        existing_value.updated_by_user_id = current_user.user_id
        await db.commit()
        await db.refresh(existing_value)
        return CustomFieldValueOut.from_model(existing_value)
    else:
        new_value = CustomFieldValue(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            definition_id=definition_id,
            entity_type=entity_type,
            entity_id=entity_id,
            value=stored_value,
            updated_by_user_id=current_user.user_id,
        )
        db.add(new_value)
        await db.commit()
        await db.refresh(new_value)
        return CustomFieldValueOut.from_model(new_value)


@router.delete(
    "/values/{definition_id}/{entity_type}/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
)
async def delete_custom_field_value(
    definition_id: str,
    entity_type: CustomFieldEntityType,
    entity_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
    _: None = Depends(require_trust_write()),
) -> None:
    """Delete a custom field value."""
    db, tenant_id = db_tenant

    stmt = (
        select(CustomFieldValue)
        .where(CustomFieldValue.tenant_id == str(tenant_id))
        .where(CustomFieldValue.definition_id == definition_id)
        .where(CustomFieldValue.entity_type == entity_type)
        .where(CustomFieldValue.entity_id == entity_id)
    )
    value = (await db.execute(stmt)).scalar_one_or_none()
    if not value:
        raise HTTPException(status_code=404, detail="Custom field value not found")

    await db.delete(value)
    await db.commit()
