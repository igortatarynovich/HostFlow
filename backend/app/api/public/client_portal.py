"""Public client portal: access by token, read-only list of handed-off candidates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLink


router = APIRouter(prefix="/public/client-portal", tags=["public-client-portal"])


def _mask_candidate(d: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce PII for see_reduced_profiles."""
    out = dict(d)
    for key in ("email", "phone", "phone_country_code", "address", "birth_date"):
        if key in out:
            out[key] = None
    return out


@router.get("")
async def get_client_portal(
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Resolve token to tenant_link and return client name + read-only list of candidates
    handed off to this client (accepted handoffs). No auth required.
    """
    if not token or not token.strip():
        raise HTTPException(status_code=400, detail="Missing token")
    result = await db.execute(
        select(TenantLink).where(
            TenantLink.portal_token == token.strip(),
            TenantLink.status == "active",
        ).limit(1)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if link.portal_expires_at:
        from datetime import datetime, timezone
        if link.portal_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=404, detail="Link expired")

    company_name = None
    if link.client_company_id:
        company = await db.get(Company, link.client_company_id)
        company_name = company.name if company else None
    elif link.client_tenant_id:
        tenant = await db.get(Tenant, link.client_tenant_id)
        company_name = tenant.name if tenant else None
    if not company_name and link.features_json:
        company_name = (link.features_json or {}).get("client_display_name")

    # Handoffs that belong to this link: accepted, agency matches, client matches
    handoff_cond = and_(
        CandidateHandoff.status == "accepted",
        CandidateHandoff.agency_tenant_id == link.agency_tenant_id,
    )
    if link.client_company_id:
        handoff_cond = and_(handoff_cond, CandidateHandoff.client_company_id == link.client_company_id)
    elif link.client_tenant_id:
        if link.handoff_include_company_id:
            handoff_cond = and_(
                handoff_cond,
                CandidateHandoff.client_tenant_id == link.client_tenant_id,
                CandidateHandoff.client_company_id == link.handoff_include_company_id,
            )
        else:
            handoff_cond = and_(
                handoff_cond,
                CandidateHandoff.client_tenant_id == link.client_tenant_id,
            )
    else:
        raise HTTPException(status_code=400, detail="Link has no client")

    handoff_ids = await db.execute(
        select(CandidateHandoff.candidate_id).where(handoff_cond).distinct()
    )
    candidate_ids = [r[0] for r in handoff_ids.all()]
    if not candidate_ids:
        return {
            "company_name": company_name,
            "candidates": [],
        }

    stmt = (
        select(Candidate)
        .where(Candidate.id.in_(candidate_ids))
        .where(Candidate.deleted_at.is_(None))
    )
    rows = await db.execute(stmt)
    candidates_raw = list(rows.scalars().all())
    see_reduced = bool((link.features_json or {}).get("see_reduced_profiles", False))
    candidates: List[Dict[str, Any]] = []
    for c in candidates_raw:
        item = {
            "id": str(c.id),
            "short_id": getattr(c, "short_id", None) or (str(c.id)[:8] if c.id else ""),
            "first_name": getattr(c, "first_name", None),
            "last_name": getattr(c, "last_name", None),
            "stage": getattr(c, "stage", None),
            "status": getattr(c, "status", None),
        }
        if not see_reduced:
            item["email"] = getattr(c, "email", None)
            item["phone"] = getattr(c, "phone", None)
        else:
            item = _mask_candidate(item)
        candidates.append(item)

    return {
        "company_name": company_name,
        "candidates": candidates,
    }
