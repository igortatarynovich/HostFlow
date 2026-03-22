"""API for legal documents (RODO, privacy policy) and RODO send."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, get_current_user, require_roles, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.legal_document import LegalDocument
from backend.app.models.rodo_notification import RodoNotification
from backend.app.services.legal_documents import get_active_legal_document, list_active_for_tenant
from backend.app.services.rodo import get_first_rodo_sent, send_rodo_email
from backend.app.api.v1.candidates.acl import ensure_candidate_access

router = APIRouter(prefix="/legal-documents", tags=["legal-documents"])


class LegalDocumentOut(BaseModel):
    id: str
    type: str
    version_id: str
    content_url: Optional[str] = None
    is_active: bool
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LegalDocumentCreate(BaseModel):
    type: str = Field(..., pattern="^(rodo_clause|privacy_policy)$")
    version_id: str
    content_html: Optional[str] = None
    content_url: Optional[str] = None
    is_active: bool = False


class ActiveLegalDocsOut(BaseModel):
    rodo_clause: Optional[LegalDocumentOut] = None
    privacy_policy: Optional[LegalDocumentOut] = None


class RodoStatusOut(BaseModel):
    sent: bool
    sent_at: Optional[datetime] = None
    sent_by_user_id: Optional[str] = None
    recipient: Optional[str] = None
    rodo_version_id: Optional[str] = None
    can_send: bool
    # Hints when sent=false — why «Send RODO» may be disabled (UI / contact-attempts copy).
    candidate_has_email: bool = False
    active_rodo_template: bool = False


class LegalDocumentUpdate(BaseModel):
    version_id: Optional[str] = None
    content_html: Optional[str] = None
    content_url: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/", response_model=List[LegalDocumentOut])
async def list_legal_documents(
    db_tenant=Depends(get_db_with_tenant),
    _: None = Depends(require_roles(Role.admin, Role.owner)),
):
    """List all legal documents for tenant (admin only)."""
    db, tenant_id = db_tenant
    stmt = select(LegalDocument).where(LegalDocument.tenant_id == str(tenant_id)).order_by(
        LegalDocument.type.asc(), LegalDocument.published_at.desc().nullslast()
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [LegalDocumentOut.model_validate(d) for d in docs]


@router.patch("/{doc_id}", response_model=LegalDocumentOut)
async def update_legal_document(
    doc_id: UUID,
    payload: LegalDocumentUpdate,
    db_tenant=Depends(get_db_with_tenant),
    _: None = Depends(require_roles(Role.admin, Role.owner)),
):
    """Update legal document (admin only)."""
    from sqlalchemy import update

    db, tenant_id = db_tenant
    doc = await db.get(LegalDocument, str(doc_id))
    if not doc or doc.tenant_id != str(tenant_id):
        raise HTTPException(status_code=404, detail="Document not found")
    updates = payload.model_dump(exclude_unset=True)
    if "is_active" in updates and updates["is_active"]:
        await db.execute(
            update(LegalDocument)
            .where(LegalDocument.tenant_id == str(tenant_id))
            .where(LegalDocument.type == doc.type)
            .values(is_active=False)
        )
    for k, v in updates.items():
        setattr(doc, k, v)
    await db.commit()
    await db.refresh(doc)
    return LegalDocumentOut.model_validate(doc)


@router.get("/active", response_model=ActiveLegalDocsOut)
async def get_active_docs(
    db_tenant=Depends(get_db_with_tenant),
):
    """Get active RODO and privacy policy for current tenant."""
    db, tenant_id = db_tenant
    docs = await list_active_for_tenant(db, str(tenant_id))
    return ActiveLegalDocsOut(
        rodo_clause=LegalDocumentOut.model_validate(docs["rodo_clause"]) if docs["rodo_clause"] else None,
        privacy_policy=LegalDocumentOut.model_validate(docs["privacy_policy"]) if docs["privacy_policy"] else None,
    )


@router.post("/", response_model=LegalDocumentOut, status_code=201)
async def create_legal_document(
    payload: LegalDocumentCreate,
    db_tenant=Depends(get_db_with_tenant),
    _: None = Depends(require_roles(Role.admin, Role.owner)),
):
    """Create a legal document (admin only)."""
    from backend.app.models.legal_document import LegalDocument
    import uuid

    db, tenant_id = db_tenant
    doc = LegalDocument(
        id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        type=payload.type,
        version_id=payload.version_id,
        content_html=payload.content_html,
        content_url=payload.content_url,
        is_active=payload.is_active,
    )
    if payload.is_active:
        from sqlalchemy import update
        await db.execute(
            update(LegalDocument)
            .where(LegalDocument.tenant_id == str(tenant_id))
            .where(LegalDocument.type == payload.type)
            .values(is_active=False)
        )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return LegalDocumentOut.model_validate(doc)


@router.get("/candidates/{candidate_id}/rodo-status", response_model=RodoStatusOut)
async def get_rodo_status(
    candidate_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Get RODO send status for candidate (for UI block)."""
    from backend.app.models.candidate import Candidate

    db, tenant_id = db_tenant
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    first = await get_first_rodo_sent(db, str(candidate_id))
    cand = await db.get(Candidate, str(candidate_id))
    email = (cand.email or "").strip() if cand else ""
    rodo_doc = await get_active_legal_document(db, str(tenant_id), "rodo_clause")
    has_email = bool(email)
    has_template = rodo_doc is not None
    sent = first is not None
    can_send = bool(has_email and has_template and not sent)
    return RodoStatusOut(
        sent=sent,
        sent_at=first.sent_at if first else None,
        sent_by_user_id=first.sent_by_user_id if first else None,
        recipient=first.recipient if first else email or None,
        rodo_version_id=first.rodo_version_id if first else (rodo_doc.version_id if rodo_doc else None),
        can_send=can_send,
        candidate_has_email=has_email,
        active_rodo_template=has_template,
    )


@router.post("/candidates/{candidate_id}/send-rodo")
async def send_rodo(
    candidate_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """Send RODO info email to candidate (Wyślij informację RODO)."""
    from backend.app.models.candidate import Candidate

    db, tenant_id = db_tenant
    await ensure_candidate_access(db, str(tenant_id), str(candidate_id), current_user)
    success, msg, notification = await send_rodo_email(
        db,
        candidate_id=str(candidate_id),
        tenant_id=str(tenant_id),
        actor_id=current_user.sub,
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    return {"ok": True, "message": msg}
