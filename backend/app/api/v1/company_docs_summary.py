from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db_with_tenant as get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_document import CandidateDocument

router = APIRouter()


@router.get("/companies/{company_id}/docs-summary")
async def company_docs_summary(
    company_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Dict[str, Any]:
    """
    Агрегаты по документам для кандидатов компании.
    """
    db, tenant_id = db_tenant

    cand_ids_stmt = select(Candidate.id).where(
        Candidate.tenant_id == str(tenant_id),
        Candidate.deleted_at.is_(None),
        Candidate.company_id == str(company_id),
    )
    cand_ids = (await db.execute(cand_ids_stmt)).scalars().all()
    if not cand_ids:
        return {"total_docs": 0, "by_status": {}, "by_type": {}}

    # по статусам
    by_status_stmt = (
        select(CandidateDocument.status, func.count())
        .where(
            CandidateDocument.tenant_id == str(tenant_id),
            CandidateDocument.candidate_id.in_(cand_ids),
        )
        .group_by(CandidateDocument.status)
    )
    by_status_rows = await db.execute(by_status_stmt)
    by_status = {row[0] or "": int(row[1]) for row in by_status_rows.all()}

    # по типам (только если колонка существует)
    by_type: Dict[str, int] = {}
    type_code_col: Optional[Any] = getattr(CandidateDocument, "type_code", None)  # type: ignore[attr-defined]
    if type_code_col is not None:
        by_type_stmt = (
            select(type_code_col, func.count())
            .where(
                CandidateDocument.tenant_id == str(tenant_id),
                CandidateDocument.candidate_id.in_(cand_ids),
            )
            .group_by(type_code_col)
        )
        by_type_rows = await db.execute(by_type_stmt)
        by_type = {row[0] or "": int(row[1]) for row in by_type_rows.all()}

    total_stmt = select(func.count()).where(
        CandidateDocument.tenant_id == str(tenant_id),
        CandidateDocument.candidate_id.in_(cand_ids),
    )
    total_docs = (await db.execute(total_stmt)).scalar_one()

    return {
        "total_docs": int(total_docs or 0),
        "by_status": by_status,
        "by_type": by_type,
    }
