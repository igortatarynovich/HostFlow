"""Create/list recruitment applications (intent MVP). Internal API + GET by candidate.

Status vocabulary and transitions: ``recruitment_application_lifecycle`` (see
``docs/specs/workflows/recruitment-application-lifecycle.md``). New intent rows
always start as ``applied`` (§3) via ``set_recruitment_application_status``.
Legacy ``active`` is normalized to ``applied`` on read and on assign through the helper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.services.recruitment_application_lifecycle import (
    INITIAL_APPLICATION_STATUS,
    set_recruitment_application_status,
)


def _norm_vacancy_id(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _effective_vacancy_id(
    vacancy_id: Optional[str],
    candidate: Optional[Candidate],
    lead: Optional[Lead],
) -> Optional[str]:
    for v in (vacancy_id, getattr(candidate, "vacancy_id", None) if candidate else None):
        nv = _norm_vacancy_id(v)
        if nv:
            return nv
    if lead is not None:
        return _norm_vacancy_id(getattr(lead, "vacancy_id", None))
    return None


def _explicit_pool_intent(lead: Optional[Lead]) -> bool:
    """True when product marked pool/talent intent without a resolved vacancy."""
    if lead is None:
        return False
    if getattr(lead, "funnel_id", None):
        return True
    norm = lead.normalized if isinstance(lead.normalized, dict) else {}
    if norm.get("recruitment_pool_intent_v1") is True:
        return True
    return False


def _should_create_application_row(
    *,
    vacancy_id: Optional[str],
    candidate: Optional[Candidate],
    lead: Optional[Lead],
) -> bool:
    if _effective_vacancy_id(vacancy_id, candidate, lead):
        return True
    return _explicit_pool_intent(lead)


async def _load_lead(db: AsyncSession, tenant_id: str, lead_id: str) -> Optional[Lead]:
    res = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


def _append_pool_to_vacancy_audit(
    meta: Optional[Dict[str, Any]],
    *,
    from_vacancy_id: Optional[str],
    to_vacancy_id: str,
) -> Dict[str, Any]:
    """§6 pool → vacancy: record target change (same row) for auditability."""
    m = dict(meta) if isinstance(meta, dict) else {}
    trail = list(m.get("pool_to_vacancy_audit_v1") or [])
    trail.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "from_vacancy_id": from_vacancy_id,
            "to_vacancy_id": to_vacancy_id,
        }
    )
    m["pool_to_vacancy_audit_v1"] = trail[-20:]
    return m


async def ensure_recruitment_application_for_lead_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    lead_id: Optional[str] = None,
    lead: Optional[Lead] = None,
    vacancy_id: Optional[str] = None,
    source: str = "meta",
    recruiter_id: Optional[str] = None,
    applied_at: Optional[datetime] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[RecruitmentApplication]:
    """
    Idempotent intent row for lead-driven conversion.

    * No row when lead is in ``duplicate_review`` (conversion not finalized).
    * No row without a resolved vacancy unless ``lead.funnel_id`` or
      ``normalized["recruitment_pool_intent_v1"] is True`` (explicit pool intent).
    * Idempotency: ``(tenant_id, candidate_id, lead_id)`` when ``lead_id`` is set;
      else ``(tenant_id, candidate_id, vacancy_id, source)`` when there is no lead.

    New rows always use ``status=applied`` (recruitment-application-lifecycle.md §3).

    Dual-write: when an effective vacancy is known, sets ``Candidate.vacancy_id`` if empty/different.
    """
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    if not tid or not cid:
        return None

    lead_row = lead
    lid: Optional[str] = str(lead_id).strip() if lead_id else None
    if lid == "":
        lid = None
    if lead_row is None and lid:
        lead_row = await _load_lead(db, tid, lid)
    if lead_row is not None:
        lid = str(lead_row.id)

    if lead_row is not None and str(getattr(lead_row, "status", "") or "") == "duplicate_review":
        return None

    cand = await db.get(Candidate, cid)
    if cand is None or str(cand.tenant_id) != tid or cand.deleted_at is not None:
        return None

    if not _should_create_application_row(vacancy_id=vacancy_id, candidate=cand, lead=lead_row):
        return None

    eff_vac = _effective_vacancy_id(vacancy_id, cand, lead_row)
    src = str(source or "meta").strip() or "meta"

    existing: Optional[RecruitmentApplication] = None
    if lid:
        res = await db.execute(
            select(RecruitmentApplication).where(
                RecruitmentApplication.tenant_id == tid,
                RecruitmentApplication.candidate_id == cid,
                RecruitmentApplication.lead_id == lid,
            )
        )
        existing = res.scalar_one_or_none()
    elif eff_vac:
        res = await db.execute(
            select(RecruitmentApplication).where(
                RecruitmentApplication.tenant_id == tid,
                RecruitmentApplication.candidate_id == cid,
                RecruitmentApplication.lead_id.is_(None),
                RecruitmentApplication.vacancy_id == eff_vac,
                RecruitmentApplication.source == src,
            )
        )
        existing = res.scalar_one_or_none()

    rid = str(recruiter_id).strip() if recruiter_id else None
    if rid == "":
        rid = None

    if existing is not None:
        changed = False
        if rid and existing.recruiter_id != rid:
            existing.recruiter_id = rid
            changed = True
        if eff_vac and existing.vacancy_id != eff_vac:
            prev_v = existing.vacancy_id
            existing.vacancy_id = eff_vac
            if prev_v is None and eff_vac is not None:
                existing.meta = _append_pool_to_vacancy_audit(
                    existing.meta,
                    from_vacancy_id=prev_v,
                    to_vacancy_id=eff_vac,
                )
            changed = True
        if eff_vac and (not cand.vacancy_id or str(cand.vacancy_id) != eff_vac):
            cand.vacancy_id = eff_vac
            changed = True
        if changed:
            await db.flush()
        return existing

    if eff_vac:
        if not cand.vacancy_id or str(cand.vacancy_id) != eff_vac:
            cand.vacancy_id = eff_vac

    when = applied_at if applied_at is not None else datetime.now(timezone.utc)
    app = RecruitmentApplication(
        tenant_id=tid,
        candidate_id=cid,
        lead_id=lid,
        vacancy_id=eff_vac,
        source=src,
        recruiter_id=rid,
        applied_at=when,
        application_cycle=None,
        meta=dict(meta) if isinstance(meta, dict) else {},
    )
    set_recruitment_application_status(app, INITIAL_APPLICATION_STATUS)
    db.add(app)
    await db.flush()
    return app


async def get_application_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: Optional[str],
    application_id: Optional[str] = None,
) -> Optional[RecruitmentApplication]:
    """Resolve the recruitment intent row tied to a handoff (explicit id or latest matching vacancy)."""
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    if application_id:
        aid = str(application_id).strip()
        row = await db.get(RecruitmentApplication, aid)
        if row and str(row.tenant_id) == tid and str(row.candidate_id) == cid:
            return row
        return None
    stmt = select(RecruitmentApplication).where(
        RecruitmentApplication.tenant_id == tid,
        RecruitmentApplication.candidate_id == cid,
    )
    nv = _norm_vacancy_id(vacancy_id)
    if nv:
        stmt = stmt.where(RecruitmentApplication.vacancy_id == nv)
    stmt = stmt.order_by(
        RecruitmentApplication.applied_at.desc(),
        RecruitmentApplication.created_at.desc(),
    ).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_recruitment_applications_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> List[RecruitmentApplication]:
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    res = await db.execute(
        select(RecruitmentApplication)
        .where(
            RecruitmentApplication.tenant_id == tid,
            RecruitmentApplication.candidate_id == cid,
        )
        .order_by(RecruitmentApplication.applied_at.desc(), RecruitmentApplication.created_at.desc())
    )
    return list(res.scalars().all())
