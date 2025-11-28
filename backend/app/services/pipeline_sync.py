from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company import CandidateVacancy


async def sync_candidate_links(
    db: AsyncSession,
    tenant_id: UUID,
    candidate_id: UUID,
    candidate_stage: Optional[str],
) -> None:
    """
    Синхронизирует статус всех связей CandidateVacancy (линков кандидата с вакансиями)
    с колонкой канбана, вычисленной из кода этапа кандидата.
    """
    # вычисляем нужную колонку
    stage_code = (candidate_stage or "").strip().lower()
    pipeline_status = pipeline_for_stage_code(stage_code)

    res = await db.execute(
        select(CandidateVacancy).where(
            CandidateVacancy.tenant_id == str(tenant_id),
            CandidateVacancy.candidate_id == str(candidate_id),
        )
    )
    links = res.scalars().all()
    if not links:
        return

    now = datetime.utcnow()
    changed = False
    for link in links:
        cur = (link.status or "").strip().lower()
        if cur != pipeline_status:
            await db.execute(
                update(CandidateVacancy)
                .where(CandidateVacancy.id == link.id)
                .values(status=pipeline_status, updated_at=now)
            )
            changed = True

    if changed:
        await db.commit()


# Helper to normalize UI stage codes to pipeline status codes


def pipeline_for_stage_code(stage_code: Optional[str]) -> str:
    """
    Normalize UI stage codes to internal pipeline column/status codes.
    Safe fallback: returns 'unknown' when empty; passes through unknown codes.
    """
    if not stage_code:
        return "unknown"

    code = str(stage_code).strip().lower()

    mapping = {
        # intake / new
        "new": "new",
        "created": "new",
        "lead": "new",
        # initial processing
        "screen": "screening",
        "screening": "screening",
        "call": "screening",
        # documents
        "docs": "documents",
        "documents": "documents",
        # offer / contract
        "offer": "offer",
        "contract": "offer",
        # outcomes
        "hired": "hired",
        "rejected": "rejected",
    }
    return mapping.get(code, code)
