"""Read-only canonical Document Type Version authoring catalog."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user
from backend.app.auth.trust_role_deps import require_trust_read
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.document_type_version_assignment_resolver import (
    DocumentTypeVersionAssignmentResolver,
)

router = APIRouter(
    prefix="/platform/reference/document-type-versions",
    tags=["document-type-versions"],
    redirect_slashes=False,
)


class CurrentDocumentTypeVersionOut(BaseModel):
    document_type_id: str
    document_type_code: str
    public_name: str
    description: str | None = None
    category_code: str
    subcategory_code: str | None = None
    document_type_status: str
    document_type_version_id: str
    version_code: str
    valid_from: date
    valid_to: date | None = None
    status_model: str
    deprecation_reason: str | None = None


class CurrentDocumentTypeVersionListOut(BaseModel):
    items: list[CurrentDocumentTypeVersionOut] = Field(default_factory=list)
    count: int


@router.get("", response_model=CurrentDocumentTypeVersionListOut)
async def list_current_document_type_versions(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> CurrentDocumentTypeVersionListOut:
    """List active canonical document types with their current pinned version."""

    db, _tenant_uuid = db_tenant
    resolved = (
        await DocumentTypeVersionAssignmentResolver.list_current_applicable_versions(
            db
        )
    )
    items = [
        CurrentDocumentTypeVersionOut(
            document_type_id=str(item.document_type.id),
            document_type_code=str(item.document_type.code),
            public_name=str(item.document_type.public_name),
            description=item.document_type.description,
            category_code=str(item.document_type.category_code),
            subcategory_code=item.document_type.subcategory_code,
            document_type_status=str(item.document_type.status),
            document_type_version_id=str(item.version.id),
            version_code=str(item.version.version_code),
            valid_from=item.version.valid_from,
            valid_to=item.version.valid_to,
            status_model=str(item.version.status_model),
            deprecation_reason=item.version.deprecation_reason,
        )
        for item in resolved
    ]
    return CurrentDocumentTypeVersionListOut(items=items, count=len(items))


__all__ = ["router"]
