"""HR Inbox queue: internal-HR handoffs + snapshot + workforce linkage."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.workforce_employee import WorkforceEmployee


async def _workforce_employee_id_by_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoffs: Sequence[CandidateHandoff],
) -> dict[str, str]:
    """Map handoff id -> workforce_employee.id using meta.internal_hr_handoff_id."""
    if not handoffs:
        return {}
    cand_ids = {str(h.candidate_id) for h in handoffs if h.candidate_id}
    if not cand_ids:
        return {}
    rows = await db.execute(
        select(WorkforceEmployee).where(
            WorkforceEmployee.tenant_id == str(tenant_id),
            WorkforceEmployee.candidate_id.in_(list(cand_ids)),
        )
    )
    out: dict[str, str] = {}
    for emp in rows.scalars().all():
        hid = (emp.meta or {}).get("internal_hr_handoff_id")
        if hid:
            out[str(hid)] = str(emp.id)
    return out


async def list_internal_hr_handoffs_for_hr_inbox(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return paginated inbox rows for internal HR lane (`destination == internal_hr`)."""
    tid = str(tenant_id).strip()
    st = str(status).strip()
    if st not in ("pending_review", "accepted"):
        raise ValueError("status must be pending_review or accepted")

    base = (
        select(CandidateHandoff, CandidateHandoffSnapshot)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .outerjoin(
            CandidateHandoffSnapshot,
            CandidateHandoffSnapshot.handoff_id == CandidateHandoff.id,
        )
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status == st,
            Candidate.deleted_at.is_(None),
        )
    )

    count_stmt = (
        select(func.count())
        .select_from(CandidateHandoff)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status == st,
            Candidate.deleted_at.is_(None),
        )
    )
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    stmt = (
        base.order_by(CandidateHandoff.requested_at.desc())
        .offset(max(0, offset))
        .limit(min(max(1, limit), 200))
    )
    result = await db.execute(stmt)
    pairs = result.all()

    handoffs_only = [p[0] for p in pairs]
    wf_by_hid = await _workforce_employee_id_by_handoff(db, tenant_id=tid, handoffs=handoffs_only)

    items: list[dict[str, Any]] = []
    for handoff, snap in pairs:
        items.append(
            {
                "handoff": handoff,
                "snapshot": dict(snap.payload) if snap is not None else None,
                "workforce_employee_id": wf_by_hid.get(str(handoff.id)),
            }
        )
    return items, total
