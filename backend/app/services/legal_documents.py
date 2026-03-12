"""Service for legal documents (RODO clause, privacy policy)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.legal_document import LegalDocument


async def get_active_legal_document(
    db: AsyncSession,
    tenant_id: str,
    doc_type: str,
) -> LegalDocument | None:
    """Get the active legal document for tenant and type."""
    stmt = (
        select(LegalDocument)
        .where(LegalDocument.tenant_id == tenant_id)
        .where(LegalDocument.type == doc_type)
        .where(LegalDocument.is_active.is_(True))
        .order_by(LegalDocument.published_at.desc().nullslast())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_active_for_tenant(
    db: AsyncSession,
    tenant_id: str,
) -> dict[str, LegalDocument | None]:
    """Return active rodo_clause and privacy_policy for tenant."""
    rodo = await get_active_legal_document(db, tenant_id, "rodo_clause")
    privacy = await get_active_legal_document(db, tenant_id, "privacy_policy")
    return {"rodo_clause": rodo, "privacy_policy": privacy}
