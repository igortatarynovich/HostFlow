"""Enforce TenantLicense caps (§2.16) for candidates, open vacancies, documents — 0 = unlimited."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.vacancy import Vacancy
from backend.app.services.tenant_limits import get_tenant_limits


def sum_file_entries_bytes(files: Any) -> int:
    """Sum `size` from document file entries (JSON list); missing/invalid sizes count as 0."""
    if not isinstance(files, list):
        return 0
    total = 0
    for item in files:
        if not isinstance(item, dict):
            continue
        raw = item.get("size")
        if raw is None:
            continue
        try:
            total += int(raw)
        except (TypeError, ValueError):
            continue
    return max(total, 0)


async def sum_tenant_document_storage_bytes(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(Document.files).where(
        Document.tenant_id == tenant_id,
        Document.deleted_at.is_(None),
    )
    rows = (await db.execute(stmt)).all()
    total = 0
    for (raw,) in rows:
        total += sum_file_entries_bytes(raw)
    return total


async def ensure_tenant_storage_bytes_fits(
    db: AsyncSession,
    tenant_id: str,
    *,
    previous_doc_attribution_bytes: int = 0,
    next_doc_attribution_bytes: int = 0,
) -> None:
    """Block when persisted documents' file sizes would exceed `max_storage_gb` (0 = unlimited)."""
    limits = await get_tenant_limits(db, tenant_id)
    cap_gb = int(limits.max_storage_gb or 0)
    if cap_gb <= 0:
        return
    cap_bytes = cap_gb * 1024 * 1024 * 1024
    current_total = await sum_tenant_document_storage_bytes(db, tenant_id)
    prev_b = max(int(previous_doc_attribution_bytes), 0)
    next_b = max(int(next_doc_attribution_bytes), 0)
    projected = current_total - prev_b + next_b
    if projected > cap_bytes:
        used_gb = current_total / (1024**3)
        raise HTTPException(
            status_code=402,
            detail={
                "code": "storage_limit_reached",
                "limit_gb": cap_gb,
                "current_gb": round(used_gb, 4),
            },
        )


async def count_active_candidates(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(Candidate).where(
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_active_candidate_quota(db: AsyncSession, tenant_id: str) -> None:
    limits = await get_tenant_limits(db, tenant_id)
    cap = limits.max_candidates_active
    if cap <= 0:
        return
    n = await count_active_candidates(db, tenant_id)
    if n >= cap:
        raise HTTPException(
            status_code=402,
            detail={"code": "candidate_limit_reached", "limit": cap, "current": n},
        )


async def count_open_vacancies(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(Vacancy).where(
        Vacancy.tenant_id == tenant_id,
        Vacancy.status == "open",
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_open_vacancy_quota(db: AsyncSession, tenant_id: str, *, extra_open: int = 1) -> None:
    if extra_open <= 0:
        return
    limits = await get_tenant_limits(db, tenant_id)
    cap = limits.max_vacancies_active
    if cap <= 0:
        return
    n = await count_open_vacancies(db, tenant_id)
    if n + extra_open > cap:
        raise HTTPException(
            status_code=402,
            detail={"code": "open_vacancy_limit_reached", "limit": cap, "current": n},
        )


async def count_tenant_documents(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(Document).where(Document.tenant_id == tenant_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_tenant_document_quota(db: AsyncSession, tenant_id: str) -> None:
    limits = await get_tenant_limits(db, tenant_id)
    cap = limits.max_documents
    if cap <= 0:
        return
    n = await count_tenant_documents(db, tenant_id)
    if n >= cap:
        raise HTTPException(
            status_code=402,
            detail={"code": "document_limit_reached", "limit": cap, "current": n},
        )
