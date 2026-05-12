"""Slice 4 Guard 1 — suppress default UOS \"Call candidate\" after Lead→Candidate when lead already has operational touch.

Lives under ``services/`` (not ``modules.leads``) so ``uos_auto_activities`` can import without loading the leads API package (import-cycle safe).
"""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import ActivityLog

# Logged when default first-contact reminder is intentionally not created.
FIRST_CONTACT_SUPPRESSED_ACTION = "lead_to_candidate.first_contact_suppressed"

_INTAKE_STATUSES_SUPPRESS: frozenset[str] = frozenset(
    {
        "qualified",
        "rejected",
        "pooled",
        "info_requested",
        "duplicate_review_requested",
    }
)

# CRM stages on the lead that imply the lead is past \"cold\" first outreach.
_LEAD_STAGES_POST_TOUCH: frozenset[str] = frozenset({"contacted", "qualified"})

# From ``lead.stage_changed`` audit payloads — reached a post-touch CRM stage at least once.
_ACTIVITY_TO_STAGES_TOUCH: frozenset[str] = frozenset({"contacted", "qualified"})


def lead_first_contact_suppression_reasons_sync(lead: Any) -> List[str]:
    """Signals available without extra DB reads (normalized + lead columns)."""
    reasons: List[str] = []
    norm = getattr(lead, "normalized", None)
    if not isinstance(norm, dict):
        norm = {}

    ir = norm.get("intake_resolution_v1")
    if isinstance(ir, dict):
        st = str(ir.get("status") or "").strip().lower()
        if st in _INTAKE_STATUSES_SUPPRESS:
            reasons.append(f"intake_resolution:{st}")

    stage = str(getattr(lead, "stage", None) or "").strip().lower()
    if stage in _LEAD_STAGES_POST_TOUCH:
        reasons.append(f"lead_stage:{stage}")

    return reasons


async def _activity_log_lead_touched_via_stage_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    stmt = select(ActivityLog.payload).where(
        ActivityLog.tenant_id == tenant_id,
        ActivityLog.target_type == "lead",
        ActivityLog.target_id == str(lead_id),
        ActivityLog.action == "lead.stage_changed",
    )
    res = await db.execute(stmt)
    for (payload,) in res.all():
        if not isinstance(payload, dict):
            continue
        ts = str(payload.get("to_stage") or "").strip().lower()
        if ts in _ACTIVITY_TO_STAGES_TOUCH:
            return True
    return False


async def lead_first_contact_suppression_reasons(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
) -> List[str]:
    """Merge sync signals with ActivityLog (stage transitions into contacted/qualified)."""
    reasons = list(lead_first_contact_suppression_reasons_sync(lead))
    if reasons:
        return _uniq_preserve(reasons)

    lead_id = str(getattr(lead, "id", "") or "").strip()
    if not lead_id:
        return []

    if await _activity_log_lead_touched_via_stage_audit(db, tenant_id=tenant_id, lead_id=lead_id):
        reasons.append("activity_log:lead.stage_changed→contacted|qualified")

    return _uniq_preserve(reasons)


def _uniq_preserve(seq: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


async def should_skip_default_first_contact_after_lead_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
) -> Tuple[bool, List[str]]:
    reasons = await lead_first_contact_suppression_reasons(db, tenant_id=tenant_id, lead=lead)
    return (bool(reasons), reasons)
