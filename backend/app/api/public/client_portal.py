"""Public client portal: token access, handoff decisions, candidate list."""

from __future__ import annotations

from datetime import datetime, timezone
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLink
from backend.app.models import User
from backend.app.services.handoff import accept_handoff, reject_handoff, return_handoff

router = APIRouter(prefix="/public/client-portal", tags=["public-client-portal"])


def _mask_candidate(d: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce PII for see_reduced_profiles."""
    out = dict(d)
    for key in ("email", "phone", "phone_country_code", "address", "birth_date"):
        if key in out:
            out[key] = None
    return out


def _handoff_scope_condition(link: TenantLink):
    cond = CandidateHandoff.agency_tenant_id == link.agency_tenant_id
    if link.client_company_id:
        return and_(cond, CandidateHandoff.client_company_id == link.client_company_id)
    if link.client_tenant_id:
        if link.handoff_include_company_id:
            return and_(
                cond,
                CandidateHandoff.client_tenant_id == link.client_tenant_id,
                CandidateHandoff.client_company_id == link.handoff_include_company_id,
            )
        return and_(cond, CandidateHandoff.client_tenant_id == link.client_tenant_id)
    raise HTTPException(status_code=400, detail="Link has no client")


def _handoff_matches_link(handoff: CandidateHandoff, link: TenantLink) -> bool:
    if str(handoff.agency_tenant_id) != str(link.agency_tenant_id):
        return False
    if link.client_company_id:
        return str(handoff.client_company_id or "") == str(link.client_company_id)
    if link.client_tenant_id:
        if link.handoff_include_company_id:
            return (
                str(handoff.client_tenant_id or "") == str(link.client_tenant_id)
                and str(handoff.client_company_id or "") == str(link.handoff_include_company_id)
            )
        return str(handoff.client_tenant_id or "") == str(link.client_tenant_id)
    return False


async def _resolve_portal_link(db: AsyncSession, token: str) -> TenantLink:
    raw = (token or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Missing token")
    result = await db.execute(
        select(TenantLink).where(
            TenantLink.portal_token == raw,
            TenantLink.status == "active",
        ).limit(1)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if link.portal_expires_at:
        if link.portal_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=404, detail="Link expired")
    return link


def _company_name_for_link(link: TenantLink, company: Company | None, tenant: Tenant | None) -> str | None:
    if link.client_company_id and company:
        return company.name
    if link.client_tenant_id and tenant:
        return tenant.name
    if link.features_json:
        return (link.features_json or {}).get("client_display_name")
    return None


async def _recruiter_presented_by(db: AsyncSession, requested_by_user_id: str) -> Dict[str, Any]:
    u = await db.get(User, requested_by_user_id)
    if not u:
        return {"kind": "generic"}
    fn = (getattr(u, "first_name", None) or "").strip()
    if fn:
        return {"kind": "named", "first_name": fn}
    return {"kind": "generic"}


def _waiting_hours(requested_at: datetime | None) -> int | None:
    if not requested_at:
        return None
    ra = requested_at
    if ra.tzinfo is None:
        ra = ra.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ra
    return max(0, int(delta.total_seconds() // 3600))


@router.get("")
async def get_client_portal(
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Portal home: summary, activity, candidates with primary handoff (pending review or accepted).
    """
    link = await _resolve_portal_link(db, token)

    company = await db.get(Company, link.client_company_id) if link.client_company_id else None
    tenant = await db.get(Tenant, link.client_tenant_id) if link.client_tenant_id else None
    company_name = _company_name_for_link(link, company, tenant)

    scope = _handoff_scope_condition(link)
    status_cond = CandidateHandoff.status.in_(("pending_review", "accepted", "rejected", "returned"))

    ho_rows = await db.execute(
        select(CandidateHandoff).where(and_(scope, status_cond)).order_by(CandidateHandoff.updated_at.desc())
    )
    all_handoffs: List[CandidateHandoff] = list(ho_rows.scalars().all())

    by_cand: Dict[str, List[CandidateHandoff]] = defaultdict(list)
    for h in all_handoffs:
        by_cand[str(h.candidate_id)].append(h)

    def _ts(dt: datetime | None) -> float:
        if not dt:
            return 0.0
        d = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return d.timestamp()

    def _pick_primary(hs: List[CandidateHandoff]) -> CandidateHandoff | None:
        pending = [h for h in hs if h.status == "pending_review"]
        if pending:
            return max(pending, key=lambda x: _ts(x.requested_at or x.updated_at))
        acc = [h for h in hs if h.status == "accepted"]
        if acc:
            return max(acc, key=lambda x: _ts(x.reviewed_at or x.updated_at))
        return None

    primary_by_cand: Dict[str, CandidateHandoff] = {}
    for cid, hs in by_cand.items():
        p = _pick_primary(hs)
        if p:
            primary_by_cand[cid] = p

    pending_ids = {cid for cid, h in primary_by_cand.items() if h.status == "pending_review"}
    accepted_active = sum(1 for h in primary_by_cand.values() if h.status == "accepted")

    activity: List[Dict[str, Any]] = []
    for h in all_handoffs[:8]:
        activity.append(
            {
                "handoff_id": str(h.id),
                "candidate_id": str(h.candidate_id),
                "status": h.status,
                "at": h.updated_at.isoformat() if h.updated_at else None,
            }
        )

    # Visible candidates: pending or accepted primary; exclude rejected/returned-only from main list
    visible_cids = [
        cid
        for cid, h in primary_by_cand.items()
        if h.status in ("pending_review", "accepted")
    ]
    if not visible_cids:
        return {
            "company_name": company_name,
            "summary": {
                "pending_decisions": 0,
                "candidates_in_progress": 0,
            },
            "activity": activity,
            "candidates": [],
        }

    cand_rows = await db.execute(
        select(Candidate).where(Candidate.id.in_(visible_cids)).where(Candidate.deleted_at.is_(None))
    )
    candidates_raw = {str(c.id): c for c in cand_rows.scalars().all()}
    see_reduced = bool((link.features_json or {}).get("see_reduced_profiles", False))

    # pending first, then by name
    def sort_key(cid: str) -> Tuple[int, str]:
        h = primary_by_cand[cid]
        c = candidates_raw.get(cid)
        name = ""
        if c:
            name = f"{getattr(c, 'first_name', '') or ''} {getattr(c, 'last_name', '') or ''}".strip()
        pr = 0 if h.status == "pending_review" else 1
        return (pr, name.lower())

    candidates_out: List[Dict[str, Any]] = []
    for cid in sorted(visible_cids, key=sort_key):
        c = candidates_raw.get(cid)
        if not c:
            continue
        h = primary_by_cand[cid]
        presented = await _recruiter_presented_by(db, str(h.requested_by_user_id))
        item = {
            "id": str(c.id),
            "short_id": getattr(c, "short_id", None) or (str(c.id)[:8] if c.id else ""),
            "first_name": getattr(c, "first_name", None),
            "last_name": getattr(c, "last_name", None),
            "stage": getattr(c, "stage", None),
            "status": getattr(c, "status", None),
            "handoff": {
                "id": str(h.id),
                "status": h.status,
                "requested_at": h.requested_at.isoformat() if h.requested_at else None,
                "waiting_hours": _waiting_hours(h.requested_at),
                "presented_by": presented,
            },
        }
        if not see_reduced:
            item["email"] = getattr(c, "email", None)
            item["phone"] = getattr(c, "phone", None)
        else:
            item = _mask_candidate(item)
        candidates_out.append(item)

    return {
        "company_name": company_name,
        "summary": {
            "pending_decisions": len(pending_ids),
            "candidates_in_progress": accepted_active,
        },
        "activity": activity,
        "candidates": candidates_out,
    }


class PortalRejectBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4000)


class PortalClarifyBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


def _audit_tenant_for_portal(link: TenantLink) -> str:
    return str(link.client_tenant_id or link.agency_tenant_id)


@router.post("/handoffs/{handoff_id}/accept")
async def portal_accept_handoff(
    handoff_id: str,
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    link = await _resolve_portal_link(db, token)
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff or not _handoff_matches_link(handoff, link):
        raise HTTPException(status_code=404, detail="Handoff not found")
    audit_tid = _audit_tenant_for_portal(link)
    ho, err = await accept_handoff(
        db,
        handoff_id=handoff_id,
        reviewed_by_user_id=None,
        tenant_id=audit_tid,
    )
    if err or not ho:
        raise HTTPException(status_code=400, detail=err or "Cannot accept")
    await db.commit()
    return {"status": "accepted", "handoff_id": str(ho.id)}


@router.post("/handoffs/{handoff_id}/reject")
async def portal_reject_handoff(
    handoff_id: str,
    body: PortalRejectBody,
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    link = await _resolve_portal_link(db, token)
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff or not _handoff_matches_link(handoff, link):
        raise HTTPException(status_code=404, detail="Handoff not found")
    audit_tid = _audit_tenant_for_portal(link)
    ho, err = await reject_handoff(
        db,
        handoff_id=handoff_id,
        reviewed_by_user_id=None,
        rejection_reason=body.reason.strip(),
        tenant_id=audit_tid,
    )
    if err or not ho:
        raise HTTPException(status_code=400, detail=err or "Cannot reject")
    await db.commit()
    return {"status": "rejected", "handoff_id": str(ho.id)}


@router.post("/handoffs/{handoff_id}/request-clarification")
async def portal_request_clarification(
    handoff_id: str,
    body: PortalClarifyBody,
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Return handoff to agency with a message (pending or accepted)."""
    link = await _resolve_portal_link(db, token)
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff or not _handoff_matches_link(handoff, link):
        raise HTTPException(status_code=404, detail="Handoff not found")
    audit_tid = _audit_tenant_for_portal(link)
    ho, err = await return_handoff(
        db,
        handoff_id=handoff_id,
        reviewed_by_user_id=None,
        return_reason=body.message.strip(),
        tenant_id=audit_tid,
    )
    if err or not ho:
        raise HTTPException(status_code=400, detail=err or "Cannot return")
    await db.commit()
    return {"status": "returned", "handoff_id": str(ho.id)}
