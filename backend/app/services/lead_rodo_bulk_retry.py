"""Bulk retry for open Lead RODO obligations (canonical ``compliance_state``).

Re-sends via ``send_lead_rodo_email`` only for retryable open states
(``delivery_failed``, ``delivery_required``). Does not retry ``review_required``,
does not bypass Result Link / SMTP, and does not overwrite ``delivery_failed``
when a retry still fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.services.lead_rodo import (
    lead_normalized_rodo_block,
    lead_rodo_satisfied_from_normalized,
    send_lead_rodo_email,
)
from backend.app.services.lead_rodo_obligation import current_compliance_state
from backend.app.services.lead_rodo_ops import (
    RETRYABLE_COMPLIANCE_STATES,
    is_retryable_open_state,
    maybe_escalate_delivery_exhaustion,
)
from backend.app.services.lead_rodo_settings import get_lead_rodo_settings

DEFAULT_RETRY_STATUSES = ("delivery_failed",)
_LEGACY_FAILED_ALIASES = frozenset(
    {
        "failed",
        "pending_channel",
        "pending_policy",
        "deferred",
        "undelivered",
        "unsatisfied",
    }
)
ALLOWED_RETRY_STATUSES = frozenset(RETRYABLE_COMPLIANCE_STATES) | _LEGACY_FAILED_ALIASES
_TERMINAL_LEAD_STATUSES = frozenset({"processed", "rejected", "lost", "archived"})


@dataclass(frozen=True, slots=True)
class LeadRodoBulkRetryItem:
    lead_id: str
    outcome: str  # sent | skipped | failed | dry_run
    rodo_status_before: str
    message: str
    rodo_status_after: Optional[str] = None
    compliance_state_before: Optional[str] = None
    compliance_state_after: Optional[str] = None


@dataclass(frozen=True, slots=True)
class LeadRodoBulkRetryResult:
    items: list[LeadRodoBulkRetryItem]
    attempted: int
    sent: int
    skipped: int
    failed: int
    dry_run: bool


def _canonical_retry_states(statuses: Sequence[str]) -> set[str]:
    wanted: set[str] = set()
    for raw in statuses:
        token = str(raw).strip().lower()
        if token in RETRYABLE_COMPLIANCE_STATES:
            wanted.add(token)
        elif token in _LEGACY_FAILED_ALIASES:
            wanted.add("delivery_failed")
    return wanted


def _rodo_status_label(normalized: Optional[dict[str, Any]]) -> str:
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else None)
    st = str(block.get("status") or "").strip().lower()
    if st:
        return st
    cs = current_compliance_state(block)
    return cs or "unsatisfied"


def _matches_retry_state(normalized: Optional[dict[str, Any]], wanted: set[str]) -> bool:
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else None)
    cs = current_compliance_state(block)
    if not is_retryable_open_state(cs):
        return False
    if not wanted:
        return cs == "delivery_failed"
    return cs in wanted


async def bulk_retry_lead_rodo(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: Optional[str] = None,
    lead_ids: Optional[Sequence[str]] = None,
    statuses: Optional[Sequence[str]] = None,
    max_items: int = 50,
    include_terminal: bool = False,
    dry_run: bool = False,
) -> LeadRodoBulkRetryResult:
    """
    Retry fulfillment for leads in retryable open states.

    Default: canonical ``delivery_failed`` (legacy ``failed`` / ``pending_channel``
    map here). ``review_required`` is never retried. ``dry_run`` lists candidates
    without calling send.
    """
    tid = str(tenant_id).strip()
    limit = max(1, min(int(max_items or 50), 200))
    status_filter: Sequence[str] = tuple(statuses) if statuses else DEFAULT_RETRY_STATUSES
    bad = [s for s in status_filter if str(s).strip().lower() not in ALLOWED_RETRY_STATUSES]
    if bad:
        raise ValueError(f"unsupported rodo retry statuses: {bad}")
    if any(str(s).strip().lower() == "review_required" for s in status_filter):
        raise ValueError("review_required is not retried")

    wanted = _canonical_retry_states(status_filter)
    ids = [str(x).strip() for x in (lead_ids or []) if str(x).strip()]
    q = select(Lead).where(Lead.tenant_id == tid)
    if ids:
        q = q.where(Lead.id.in_(ids))
    if not include_terminal:
        q = q.where(~Lead.status.in_(sorted(_TERMINAL_LEAD_STATUSES)))

    cs_col = Lead.normalized["rodo"]["compliance_state"].as_string()
    st_col = Lead.normalized["rodo"]["status"].as_string()
    if ids:
        pass
    else:
        status_aliases: set[str] = set(wanted)
        if "delivery_failed" in wanted:
            status_aliases.update(_LEGACY_FAILED_ALIASES | {"delivery_failed"})
        q = q.where(or_(cs_col.in_(sorted(wanted)), st_col.in_(sorted(status_aliases))))

    q = q.order_by(Lead.created_at.asc()).limit(limit * 3 if not ids else limit)
    rows = list((await db.execute(q)).scalars().all())

    candidates: list[Lead] = []
    for lead in rows:
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        if lead_rodo_satisfied_from_normalized(norm):
            continue
        if not _matches_retry_state(norm, wanted):
            continue
        candidates.append(lead)
        if len(candidates) >= limit:
            break

    rodo_cfg = await get_lead_rodo_settings(db, tid)
    items: list[LeadRodoBulkRetryItem] = []
    sent_n = skipped_n = failed_n = 0

    from backend.app.services.lead_lifecycle_email_policy import (
        PURPOSE_GDPR_NOTICE,
        resolve_lifecycle_email_policy_for_lead,
    )
    from backend.app.services.lead_rodo_settings import DEFAULT_LEAD_RODO_CHANNELS

    for lead in candidates:
        norm_before = lead.normalized if isinstance(lead.normalized, dict) else None
        before = _rodo_status_label(norm_before)
        cs_before = current_compliance_state(lead_normalized_rodo_block(norm_before))
        if dry_run:
            items.append(
                LeadRodoBulkRetryItem(
                    lead_id=str(lead.id),
                    outcome="dry_run",
                    rodo_status_before=before,
                    message="would_retry",
                    rodo_status_after=before,
                    compliance_state_before=cs_before,
                    compliance_state_after=cs_before,
                )
            )
            skipped_n += 1
            continue

        decision = await resolve_lifecycle_email_policy_for_lead(
            db, tenant_id=tid, lead=lead, purpose=PURPOSE_GDPR_NOTICE
        )
        channels = tuple(rodo_cfg.channels) if rodo_cfg.channels else DEFAULT_LEAD_RODO_CHANNELS
        ok, msg = await send_lead_rodo_email(
            db,
            lead=lead,
            tenant_id=tid,
            actor_id=actor_id,
            channels=channels,
            template_id=None,
            message_template_id=decision.template_ref or rodo_cfg.message_template_id,
            auto_trigger="bulk_retry",
            ingest_source="bulk_rodo_retry",
        )
        if not ok:
            await maybe_escalate_delivery_exhaustion(
                db, tenant_id=tid, lead=lead, actor_id=actor_id
            )
        after_norm = lead.normalized if isinstance(lead.normalized, dict) else None
        after = _rodo_status_label(after_norm)
        cs_after = current_compliance_state(lead_normalized_rodo_block(after_norm))
        if ok:
            outcome = "sent"
            sent_n += 1
        else:
            low = (msg or "").lower()
            if "already sent" in low or after in {"sent", "satisfied", "source_provided"}:
                outcome = "skipped"
                skipped_n += 1
            elif "no email" in low or after == "pending_channel":
                outcome = "skipped"
                skipped_n += 1
            else:
                outcome = "failed"
                failed_n += 1
        items.append(
            LeadRodoBulkRetryItem(
                lead_id=str(lead.id),
                outcome=outcome,
                rodo_status_before=before,
                message=str(msg or "")[:500],
                rodo_status_after=after,
                compliance_state_before=cs_before,
                compliance_state_after=cs_after,
            )
        )

    return LeadRodoBulkRetryResult(
        items=items,
        attempted=len(items),
        sent=sent_n,
        skipped=skipped_n,
        failed=failed_n,
        dry_run=bool(dry_run),
    )


def summarize_bulk_retry(result: LeadRodoBulkRetryResult) -> dict[str, Any]:
    return {
        "attempted": result.attempted,
        "sent": result.sent,
        "skipped": result.skipped,
        "failed": result.failed,
        "dry_run": result.dry_run,
        "items": [
            {
                "lead_id": i.lead_id,
                "outcome": i.outcome,
                "rodo_status_before": i.rodo_status_before,
                "rodo_status_after": i.rodo_status_after,
                "compliance_state_before": i.compliance_state_before,
                "compliance_state_after": i.compliance_state_after,
                "message": i.message,
            }
            for i in result.items
        ],
    }


__all__ = [
    "ALLOWED_RETRY_STATUSES",
    "DEFAULT_RETRY_STATUSES",
    "LeadRodoBulkRetryItem",
    "LeadRodoBulkRetryResult",
    "bulk_retry_lead_rodo",
    "summarize_bulk_retry",
]
