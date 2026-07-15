"""Create/list recruitment applications (intent MVP). Internal API + GET by candidate.

Status vocabulary and transitions: ``recruitment_application_lifecycle`` (see
``docs/specs/workflows/recruitment-application-lifecycle.md``). New intent rows
always start as ``applied`` (§3) via ``set_recruitment_application_status``.
Legacy ``active`` is normalized to ``applied`` on read and on assign through the helper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.services.recruitment_application_lifecycle import (
    INITIAL_APPLICATION_STATUS,
    InvalidRecruitmentApplicationTransition,
    normalize_application_status,
    set_recruitment_application_status,
)


class RecruitmentApplicationNotFound(LookupError):
    """Application row missing or not owned by tenant/candidate."""


# §7 — progressed rows must not silently change vacancy target.
_VACANCY_SWITCH_PROGRESS_STATUSES = frozenset(
    {"in_review", "shortlisted", "ready_for_handoff", "handed_off", "hired"}
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


async def _next_application_cycle(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> str:
    res = await db.execute(
        select(func.count())
        .select_from(RecruitmentApplication)
        .where(
            RecruitmentApplication.tenant_id == tenant_id,
            RecruitmentApplication.candidate_id == candidate_id,
        )
    )
    n = int(res.scalar_one() or 0)
    return f"cycle-{n + 1}"


def _append_vacancy_switch_audit(
    meta: Optional[Dict[str, Any]],
    *,
    from_application_id: str,
    from_vacancy_id: Optional[str],
    to_vacancy_id: str,
    actor_sub: Optional[str] = None,
) -> Dict[str, Any]:
    m = dict(meta) if isinstance(meta, dict) else {}
    trail = list(m.get("vacancy_switch_audit_v1") or [])
    entry: Dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "from_application_id": from_application_id,
        "from_vacancy_id": from_vacancy_id,
        "to_vacancy_id": to_vacancy_id,
    }
    if actor_sub:
        entry["actor_sub"] = str(actor_sub).strip()
    trail.append(entry)
    m["vacancy_switch_audit_v1"] = trail[-20:]
    return m


async def ensure_recruitment_application_for_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    external_id: str,
    source: str,
    vacancy_id: Optional[str] = None,
    recruiter_id: Optional[str] = None,
    applied_at: Optional[datetime] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[RecruitmentApplication]:
    """C2b — second apply without Lead: idempotent on ``(tenant, candidate, source, external_id)``."""
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    ext = str(external_id or "").strip()
    if not tid or not cid or not ext:
        return None

    cand = await db.get(Candidate, cid)
    if cand is None or str(cand.tenant_id) != tid or cand.deleted_at is not None:
        return None

    src = str(source or "portal").strip() or "portal"
    res = await db.execute(
        select(RecruitmentApplication).where(
            RecruitmentApplication.tenant_id == tid,
            RecruitmentApplication.candidate_id == cid,
            RecruitmentApplication.source == src,
            RecruitmentApplication.external_id == ext,
        )
    )
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing

    eff_vac = _norm_vacancy_id(vacancy_id) or _norm_vacancy_id(getattr(cand, "vacancy_id", None))
    if not eff_vac:
        return None

    if eff_vac and (not cand.vacancy_id or str(cand.vacancy_id) != eff_vac):
        cand.vacancy_id = eff_vac

    rid = str(recruiter_id).strip() if recruiter_id else None
    if rid == "":
        rid = None

    when = applied_at if applied_at is not None else datetime.now(timezone.utc)
    cycle = await _next_application_cycle(db, tenant_id=tid, candidate_id=cid)
    app = RecruitmentApplication(
        tenant_id=tid,
        candidate_id=cid,
        lead_id=None,
        vacancy_id=eff_vac,
        source=src,
        external_id=ext,
        recruiter_id=rid,
        applied_at=when,
        application_cycle=cycle,
        meta=dict(meta) if isinstance(meta, dict) else {},
    )
    set_recruitment_application_status(app, INITIAL_APPLICATION_STATUS)
    db.add(app)
    await db.flush()
    return app


async def switch_recruitment_application_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    application_id: str,
    to_vacancy_id: str,
    actor_sub: Optional[str] = None,
    close_previous: bool = True,
) -> Tuple[RecruitmentApplication, RecruitmentApplication]:
    """I1 — §7 default: new Application row for target vacancy; never overwrite progressed row."""
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    aid = str(application_id).strip()
    to_vac = _norm_vacancy_id(to_vacancy_id)
    if not to_vac:
        raise ValueError("to_vacancy_id is required")

    app = await db.get(RecruitmentApplication, aid)
    if app is None or str(app.tenant_id) != tid or str(app.candidate_id) != cid:
        raise RecruitmentApplicationNotFound(aid)

    from_vac = _norm_vacancy_id(getattr(app, "vacancy_id", None))
    if from_vac == to_vac:
        return app, app

    cur = normalize_application_status(app.status)
    if close_previous and cur in _VACANCY_SWITCH_PROGRESS_STATUSES.union({"applied", "reopened"}):
        try:
            if cur not in ("withdrawn", "rejected", "archived"):
                set_recruitment_application_status(app, "withdrawn")
                m = dict(app.meta) if isinstance(app.meta, dict) else {}
                m["vacancy_switch_closed_v1"] = {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "reason": "rerouted",
                    "to_vacancy_id": to_vac,
                }
                if actor_sub:
                    m["vacancy_switch_closed_v1"]["actor_sub"] = str(actor_sub).strip()
                app.meta = m
        except InvalidRecruitmentApplicationTransition:
            pass

    cand = await db.get(Candidate, cid)
    if cand is not None and (not cand.vacancy_id or str(cand.vacancy_id) != to_vac):
        cand.vacancy_id = to_vac

    cycle = await _next_application_cycle(db, tenant_id=tid, candidate_id=cid)
    new_meta = _append_vacancy_switch_audit(
        {},
        from_application_id=aid,
        from_vacancy_id=from_vac,
        to_vacancy_id=to_vac,
        actor_sub=actor_sub,
    )
    new_app = RecruitmentApplication(
        tenant_id=tid,
        candidate_id=cid,
        lead_id=app.lead_id,
        vacancy_id=to_vac,
        source=str(app.source or "meta"),
        external_id=None,
        recruiter_id=app.recruiter_id,
        applied_at=datetime.now(timezone.utc),
        application_cycle=cycle,
        meta=new_meta,
    )
    set_recruitment_application_status(new_app, INITIAL_APPLICATION_STATUS)
    db.add(new_app)
    await db.flush()
    return app, new_app


async def patch_recruitment_application_status(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    application_id: str,
    new_status: str,
) -> RecruitmentApplication:
    """Status PATCH writer — uses lifecycle helper only; **no** WorkforceEmployee side effects (C3)."""
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    aid = str(application_id).strip()
    row = await db.get(RecruitmentApplication, aid)
    if row is None or str(row.tenant_id) != tid or str(row.candidate_id) != cid:
        raise RecruitmentApplicationNotFound(aid)
    set_recruitment_application_status(row, new_status)
    await db.flush()
    return row
