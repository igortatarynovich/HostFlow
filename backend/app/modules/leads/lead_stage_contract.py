"""Resolve FunnelStage.stage_contract_v1 for leads (§2.3)."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.funnel import FunnelStage
from backend.app.models.lead import Lead
from backend.app.modules.leads.schemas import LeadStageContractOut
from backend.app.services.recruitment_funnel_assignment import resolve_lead_funnel_id_for_display


async def _default_lead_funnel_id(db: AsyncSession, *, tenant_id: str) -> Optional[str]:
    """Legacy tenant-scoped fallback for leads without company_id (strangler)."""
    from backend.app.models.funnel import Funnel

    row = await db.execute(
        select(Funnel.id)
        .where(
            Funnel.tenant_id == tenant_id,
            Funnel.type == "lead",
        )
        .order_by(Funnel.is_default.desc(), Funnel.name)
        .limit(1)
    )
    fid = row.scalar_one_or_none()
    return str(fid) if fid else None


async def batch_lead_stage_contracts(
    db: AsyncSession,
    *,
    tenant_id: str,
    leads: Sequence[Lead],
) -> Dict[str, Optional[LeadStageContractOut]]:
    """
    Map lead.id -> validated stage contract for the lead's current CRM `stage` row
    in the lead funnel (explicit `lead.funnel_id` or tenant default lead funnel).
    """
    if not leads:
        return {}
    default_fid = await _default_lead_funnel_id(db, tenant_id=tenant_id)
    pairs_set: set[tuple[str, str]] = set()
    lead_to_pair: Dict[str, tuple[str, str]] = {}
    for lead in leads:
        lid = str(lead.id)
        stage_val = getattr(lead, "stage", None)
        if stage_val is None or not str(stage_val).strip():
            continue
        fid = lead.funnel_id
        if not fid and getattr(lead, "company_id", None):
            fid = await resolve_lead_funnel_id_for_display(
                db, tenant_id=tenant_id, lead=lead
            )
        if not fid:
            fid = default_fid
        if not fid:
            continue
        p = (str(fid), str(stage_val).strip())
        pairs_set.add(p)
        lead_to_pair[lid] = p

    contract_by_pair: Dict[tuple[str, str], Optional[LeadStageContractOut]] = {}
    if pairs_set:
        stmt = select(FunnelStage.funnel_id, FunnelStage.code, FunnelStage.stage_contract_v1).where(
            tuple_(FunnelStage.funnel_id, FunnelStage.code).in_(list(pairs_set))
        )
        res = await db.execute(stmt)
        for fid, code, raw in res.all():
            key = (str(fid), str(code))
            if raw is None or not isinstance(raw, dict) or not raw:
                contract_by_pair[key] = None
                continue
            try:
                contract_by_pair[key] = LeadStageContractOut.model_validate(raw)
            except Exception:
                contract_by_pair[key] = None

    out: Dict[str, Optional[LeadStageContractOut]] = {}
    for lead in leads:
        lid = str(lead.id)
        pair = lead_to_pair.get(lid)
        if not pair:
            out[lid] = None
            continue
        out[lid] = contract_by_pair.get(pair)
    return out
