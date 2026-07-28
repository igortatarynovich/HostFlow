"""API for legal documents (RODO, privacy policy) and RODO send."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, get_current_user, require_roles, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.legal_document import LegalDocument
from backend.app.models.rodo_notification import RodoNotification
from backend.app.legal.billing_terms_templates_v1 import ALL_LEGAL_DOC_TYPES, default_billing_template_items
from backend.app.services.legal_documents import get_active_legal_document, list_active_for_tenant
from backend.app.services.rodo import get_first_rodo_sent, rodo_lead_audit_satisfied_from_candidate, send_rodo_email
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
    type: str
    version_id: str
    content_html: Optional[str] = None
    content_url: Optional[str] = None
    is_active: bool = False

    @field_validator("type")
    @classmethod
    def _legal_type_ok(cls, v: str) -> str:
        s = (v or "").strip()
        if s not in ALL_LEGAL_DOC_TYPES:
            raise ValueError("unsupported legal document type")
        return s


class ActiveLegalDocsOut(BaseModel):
    rodo_clause: Optional[LegalDocumentOut] = None
    privacy_policy: Optional[LegalDocumentOut] = None
    trial_terms: Optional[LegalDocumentOut] = None
    downgrade_cancellation: Optional[LegalDocumentOut] = None
    overage_autodebit: Optional[LegalDocumentOut] = None
    data_retention: Optional[LegalDocumentOut] = None
    automation_disclaimer: Optional[LegalDocumentOut] = None
    mapping_disclaimer: Optional[LegalDocumentOut] = None


class DefaultBillingTemplateItem(BaseModel):
    type: str
    version_id: str
    content_html: str


class DefaultBillingTemplatesOut(BaseModel):
    items: List[DefaultBillingTemplateItem]


class RodoStatusOut(BaseModel):
    sent: bool
    sent_at: Optional[datetime] = None
    sent_by_user_id: Optional[str] = None
    recipient: Optional[str] = None
    rodo_version_id: Optional[str] = None
    can_send: bool
    """True when RODO was satisfied on the originating lead before conversion (read-only on candidate)."""
    from_lead_conversion: bool = False
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
    _current_user: UserCtx = Depends(get_current_user),
):
    """Get active RODO, privacy, and §2.16 billing exhibits for current tenant."""
    db, tenant_id = db_tenant
    docs = await list_active_for_tenant(db, str(tenant_id))
    kwargs = {
        k: LegalDocumentOut.model_validate(v) if v is not None else None
        for k, v in docs.items()
    }
    return ActiveLegalDocsOut(**kwargs)


@router.get(
    "/default-templates/billing-v1",
    response_model=DefaultBillingTemplatesOut,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def get_default_billing_templates(
    _db_tenant=Depends(get_db_with_tenant),
):
    """Draft HTML for §2.16 checklist (counsel must review before production use)."""
    raw = default_billing_template_items()
    return DefaultBillingTemplatesOut(
        items=[DefaultBillingTemplateItem.model_validate(x) for x in raw],
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
    from_lead = bool(cand and rodo_lead_audit_satisfied_from_candidate(cand))
    sent = first is not None or from_lead
    lead_audit: dict = {}
    if cand and from_lead:
        try:
            lead_audit = cand._get_extra().get("rodo_lead_audit") or {}
        except Exception:
            lead_audit = {}
    if first:
        sent_at = first.sent_at
        recipient = first.recipient
        version_id = first.rodo_version_id
        sent_by = first.sent_by_user_id
    elif from_lead and isinstance(lead_audit, dict):
        raw_at = lead_audit.get("sent_at") or lead_audit.get("source_provided_at")
        sent_at = None
        if raw_at:
            try:
                s = str(raw_at).strip().replace("Z", "+00:00")
                sent_at = datetime.fromisoformat(s)
            except Exception:
                sent_at = None
        recipient = email or None
        rv = str(lead_audit.get("rodo_version_id") or "").strip()
        version_id = rv or (getattr(rodo_doc, "version_id", None) if rodo_doc else None)
        sent_by = None
    else:
        sent_at = None
        recipient = email or None
        version_id = rodo_doc.version_id if rodo_doc else None
        sent_by = None
    can_send = bool(has_email and has_template and first is None and not from_lead)
    return RodoStatusOut(
        sent=sent,
        sent_at=sent_at,
        sent_by_user_id=sent_by,
        recipient=recipient,
        rodo_version_id=version_id,
        can_send=can_send,
        from_lead_conversion=bool(from_lead and first is None),
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
    cand = await db.get(Candidate, str(candidate_id))
    if cand and rodo_lead_audit_satisfied_from_candidate(cand):
        raise HTTPException(
            status_code=400,
            detail="RODO was sent on the lead before conversion; use lead workspace for audit.",
        )
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
