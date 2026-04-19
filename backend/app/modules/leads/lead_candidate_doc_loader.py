"""Batch-load document statuses from the Documents module for lead fit (§2.5)."""

from __future__ import annotations

from typing import AbstractSet, Dict, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Document
from backend.app.services.document_catalog import normalize_doc_type


async def batch_candidate_document_status_sets(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_ids: AbstractSet[str],
) -> Dict[str, Dict[str, Set[str]]]:
    """
    For each candidate_id, map canonical doc_type -> set of observed status strings (lowercase).
    Candidates with no rows still appear with an empty inner dict.
    """
    out: Dict[str, Dict[str, Set[str]]] = {str(cid): {} for cid in candidate_ids if str(cid).strip()}
    if not out:
        return {}
    ids = list(out.keys())
    stmt = select(Document.candidate_id, Document.doc_type, Document.status).where(
        Document.tenant_id == tenant_id,
        Document.candidate_id.in_(ids),
        Document.deleted_at.is_(None),
    )
    rows = (await db.execute(stmt)).all()
    for cid, dtype, status in rows:
        cs = str(cid or "").strip()
        if cs not in out:
            continue
        canon = normalize_doc_type(str(dtype or ""))
        st = getattr(status, "value", status)
        st_s = str(st or "").strip().lower()
        if not st_s:
            continue
        bucket = out[cs].setdefault(canon, set())
        bucket.add(st_s)
    return out


def vacancy_extra_requires_candidate_documents_module(vacancy_extra: object) -> bool:
    """True if vacancy criteria include module-backed document requirements."""
    # Local import: keep loader importable without pulling full eval graph at module init.
    from backend.app.modules.leads.lead_criteria_eval import (
        criteria_from_vacancy_extra,
        lead_fit_evaluation_effective,
    )

    if not lead_fit_evaluation_effective(vacancy_extra):
        return False
    c = criteria_from_vacancy_extra(vacancy_extra)
    if not isinstance(c, dict):
        return False
    v = c.get("requires_candidate_documents_v1")
    return isinstance(v, list) and len(v) > 0
