"""Bulk retry for Lead-stage art.14 RODO after Pipeline migration (ADR-031).

Re-sends via ``send_lead_rodo_email`` (Sales/Recruitment binders). Does not
bypass Result Link / SMTP. Skips already-satisfied and pending_channel without email.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.services.lead_rodo import (
    lead_normalized_rodo_block,
    lead_rodo_satisfied_from_normalized,
    lead_rodo_sent_from_normalized,
    send_lead_rodo_email,
)
from backend.app.services.lead_rodo_settings import get_lead_rodo_settings

DEFAULT_RETRY_STATUSES = ("failed",)
ALLOWED_RETRY_STATUSES = frozenset(
    {
        "failed",
        "manual_required",
        "pending_channel",
        "unsatisfied",  # no / empty rodo block
    }
)
_TERMINAL_LEAD_STATUSES = frozenset({"processed", "rejected", "lost", "archived"})


@dataclass(frozen=True, slots=True)
class LeadRodoBulkRetryItem:
    lead_id: str
    outcome: str  # sent | skipped | failed | dry_run
    rodo_status_before: str
    message: str
    rodo_status_after: Optional[str] = None


@dataclass(frozen=True, slots=True)
class LeadRodoBulkRetryResult:
    items: list[LeadRodoBulkRetryItem]
    attempted: int
    sent: int
    skipped: int
    failed: int
    dry_run: bool


def _rodo_status_label(normalized: Optional[dict[str, Any]]) -> str:
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else None)
    st = str(block.get("status") or "").strip().lower()
    if st:
        return st
    return "unsatisfied"


def _matches_retry_status(normalized: Optional[dict[str, Any]], statuses: Sequence[str]) -> bool:
    label = _rodo_status_label(normalized)
    wanted = {str(s).strip().lower() for s in statuses if str(s).strip()}
    if label in wanted:
        return True
    if "unsatisfied" in wanted and label in {"unsatisfied", "manual_required"}:
        # UI maps empty → manual_required; both covered by unsatisfied filter.
        return True
    if "manual_required" in wanted and label == "unsatisfied":
        return True
    return False


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
    Retry art.14 for leads matching ``statuses`` (default: ``failed`` only).

    ``dry_run`` lists candidates without calling send.
    """
    tid = str(tenant_id).strip()
    limit = max(1, min(int(max_items or 50), 200))
    status_filter: Sequence[str] = tuple(statuses) if statuses else DEFAULT_RETRY_STATUSES
    bad = [s for s in status_filter if str(s).strip().lower() not in ALLOWED_RETRY_STATUSES]
    if bad:
        raise ValueError(f"unsupported rodo retry statuses: {bad}")

    ids = [str(x).strip() for x in (lead_ids or []) if str(x).strip()]
    q = select(Lead).where(Lead.tenant_id == tid)
    if ids:
        q = q.where(Lead.id.in_(ids))
    if not include_terminal:
        q = q.where(~Lead.status.in_(sorted(_TERMINAL_LEAD_STATUSES)))

    # Prefer failed JSON path when possible; still filter in Python for unsatisfied.
    rodo_st = Lead.normalized["rodo"]["status"].as_string()
    status_wanted = {str(s).strip().lower() for s in status_filter}
    json_statuses = sorted(status_wanted & {"failed", "pending_channel", "manual_required", "sent", "satisfied", "source_provided"})
    if ids:
        pass  # explicit ids — load then filter
    elif "unsatisfied" in status_wanted or "manual_required" in status_wanted:
        # Broad open-lead scan; Python filter applies status match.
        pass
    elif json_statuses:
        q = q.where(rodo_st.in_(json_statuses))
    else:
        q = q.where(rodo_st.in_(["failed"]))

    q = q.order_by(Lead.created_at.asc()).limit(limit * 3 if not ids else limit)
    rows = list((await db.execute(q)).scalars().all())

    candidates: list[Lead] = []
    for lead in rows:
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        if lead_rodo_satisfied_from_normalized(norm):
            continue
        if lead_rodo_sent_from_normalized(norm):
            continue
        if not _matches_retry_status(norm, status_filter):
            continue
        candidates.append(lead)
        if len(candidates) >= limit:
            break

    rodo_cfg = await get_lead_rodo_settings(db, tid)
    items: list[LeadRodoBulkRetryItem] = []
    sent_n = skipped_n = failed_n = 0

    for lead in candidates:
        before = _rodo_status_label(lead.normalized if isinstance(lead.normalized, dict) else None)
        if dry_run:
            items.append(
                LeadRodoBulkRetryItem(
                    lead_id=str(lead.id),
                    outcome="dry_run",
                    rodo_status_before=before,
                    message="would_retry",
                    rodo_status_after=before,
                )
            )
            skipped_n += 1
            continue

        ok, msg = await send_lead_rodo_email(
            db,
            lead=lead,
            tenant_id=tid,
            actor_id=actor_id,
            channels=rodo_cfg.channels,
            template_id=rodo_cfg.template_id,
            message_template_id=rodo_cfg.message_template_id,
            auto_trigger="bulk_retry",
            ingest_source="bulk_rodo_retry",
        )
        after = _rodo_status_label(lead.normalized if isinstance(lead.normalized, dict) else None)
        if ok:
            outcome = "sent"
            sent_n += 1
        else:
            # pending_channel / already sent / pipeline required → classify
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
