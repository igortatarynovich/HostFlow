"""C2.3 PR-4 — Campaign Run Orchestration.

Drives a Run through pending → running → completed|cancelled.
Emits Intents per item via the PR-3 emitter; item failures never abort the run.

No HTTP, no provider/Sender, no Workspace Commands, no Thread ORM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.campaign.emitter import (
    CampaignEmitContext,
    ItemEmitResult,
    emit_run_items,
)
from backend.app.communications.campaign.errors import CampaignDomainError
from backend.app.communications.campaign.lifecycle import get_run, mark_run_item_outcome
from backend.app.communications.link_resolver import LinkResolver
from backend.app.communications.send_communication import TransportFn
from backend.app.communications.template_resolver import TemplateResolver
from backend.app.models.communication_campaign import (
    CAMPAIGN_RUN_STATUS_CANCELLED,
    CAMPAIGN_RUN_STATUS_COMPLETED,
    CAMPAIGN_RUN_STATUS_FAILED,
    CAMPAIGN_RUN_STATUS_PENDING,
    CAMPAIGN_RUN_STATUS_RUNNING,
    RUN_ITEM_STATUS_EMITTED,
    RUN_ITEM_STATUS_FAILED,
    RUN_ITEM_STATUS_PENDING,
    RUN_ITEM_STATUS_READY,
    RUN_ITEM_STATUS_SKIPPED,
    CommunicationCampaignRun,
)

_TERMINAL_ITEM = frozenset(
    {
        RUN_ITEM_STATUS_EMITTED,
        RUN_ITEM_STATUS_SKIPPED,
        RUN_ITEM_STATUS_FAILED,
    }
)
_RUN_ACTIVE = frozenset({CAMPAIGN_RUN_STATUS_PENDING, CAMPAIGN_RUN_STATUS_RUNNING})
_RUN_TERMINAL = frozenset(
    {
        CAMPAIGN_RUN_STATUS_COMPLETED,
        CAMPAIGN_RUN_STATUS_FAILED,
        CAMPAIGN_RUN_STATUS_CANCELLED,
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RunSummary:
    total: int
    emitted: int
    skipped: int
    failed: int
    pending: int
    ready: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "emitted": self.emitted,
            "skipped": self.skipped,
            "failed": self.failed,
            "pending": self.pending,
            "ready": self.ready,
        }


@dataclass(frozen=True, slots=True)
class RunOrchestrationResult:
    run_id: str
    status: str
    summary: RunSummary
    item_results: tuple[ItemEmitResult, ...] = ()
    already_terminal: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "summary": self.summary.to_dict(),
            "already_terminal": self.already_terminal,
            "item_results": [r.to_dict() for r in self.item_results],
        }


def summarize_items(run: CommunicationCampaignRun) -> RunSummary:
    items = list(run.items or [])
    counts = {
        RUN_ITEM_STATUS_EMITTED: 0,
        RUN_ITEM_STATUS_SKIPPED: 0,
        RUN_ITEM_STATUS_FAILED: 0,
        RUN_ITEM_STATUS_PENDING: 0,
        RUN_ITEM_STATUS_READY: 0,
    }
    for item in items:
        st = str(item.status or "")
        if st in counts:
            counts[st] += 1
    return RunSummary(
        total=len(items),
        emitted=counts[RUN_ITEM_STATUS_EMITTED],
        skipped=counts[RUN_ITEM_STATUS_SKIPPED],
        failed=counts[RUN_ITEM_STATUS_FAILED],
        pending=counts[RUN_ITEM_STATUS_PENDING],
        ready=counts[RUN_ITEM_STATUS_READY],
    )


async def mark_pending_items_ready(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
) -> int:
    """Move pending items to ready before emission (optional prep step)."""
    run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
    if str(run.status) in _RUN_TERMINAL:
        raise CampaignDomainError(
            "run_terminal",
            f"Cannot prepare items on terminal run status={run.status}",
            details={"run_id": run_id, "status": run.status},
        )
    n = 0
    for item in run.items or []:
        if str(item.status) == RUN_ITEM_STATUS_PENDING:
            await mark_run_item_outcome(
                db,
                tenant_id=tenant_id,
                run_id=run_id,
                item_id=str(item.id),
                status=RUN_ITEM_STATUS_READY,
            )
            n += 1
    return n


async def cancel_campaign_run(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    reason: str | None = None,
) -> CommunicationCampaignRun:
    """Cancel a pending/running run. Does not unwind already emitted items."""
    run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
    if str(run.status) in _RUN_TERMINAL:
        raise CampaignDomainError(
            "run_terminal",
            f"Run already terminal status={run.status}",
            details={"run_id": run_id, "status": run.status},
        )
    run.status = CAMPAIGN_RUN_STATUS_CANCELLED
    run.completed_at = _now()
    meta = dict(run.meta or {})
    meta["cancel_reason"] = str(reason or "cancelled").strip() or "cancelled"
    run.meta = meta
    await db.flush()
    return run


async def execute_campaign_run(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    context: CampaignEmitContext | None = None,
    mode: str = "execute",
    skip_transport: bool = True,
    transport: TransportFn | None = None,
    template_resolver: TemplateResolver | None = None,
    link_resolver: LinkResolver | None = None,
    mark_ready: bool = True,
    run_item_ids: Sequence[str] | None = None,
) -> RunOrchestrationResult:
    """Drive one CampaignRun: emit Intents for items, then finalize run status.

    Item-level failures are isolated (via emit_run_items). The run completes
    when all targeted items are terminal — partial failures still yield
    ``completed`` with a summary (not run-level ``failed``).

    Run-level ``failed`` is reserved for orchestration aborts (e.g. unexpected
    exception before finalization). Cancelled runs are left cancelled.
    """
    run = await get_run(db, tenant_id=tenant_id, run_id=run_id)

    if str(run.status) == CAMPAIGN_RUN_STATUS_CANCELLED:
        summary = summarize_items(run)
        return RunOrchestrationResult(
            run_id=str(run.id),
            status=CAMPAIGN_RUN_STATUS_CANCELLED,
            summary=summary,
            already_terminal=True,
        )

    if str(run.status) == CAMPAIGN_RUN_STATUS_COMPLETED:
        summary = summarize_items(run)
        return RunOrchestrationResult(
            run_id=str(run.id),
            status=CAMPAIGN_RUN_STATUS_COMPLETED,
            summary=summary,
            already_terminal=True,
        )

    if str(run.status) == CAMPAIGN_RUN_STATUS_FAILED:
        summary = summarize_items(run)
        return RunOrchestrationResult(
            run_id=str(run.id),
            status=CAMPAIGN_RUN_STATUS_FAILED,
            summary=summary,
            already_terminal=True,
        )

    if str(run.status) not in _RUN_ACTIVE:
        raise CampaignDomainError(
            "invalid_run_status",
            f"Cannot execute run in status={run.status}",
            details={"run_id": run_id, "status": run.status},
        )

    if str(run.status) == CAMPAIGN_RUN_STATUS_PENDING:
        run.status = CAMPAIGN_RUN_STATUS_RUNNING
        run.started_at = _now()
        await db.flush()

    if mark_ready:
        # Re-load after status flip so we mark current pending rows.
        run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
        if str(run.status) == CAMPAIGN_RUN_STATUS_CANCELLED:
            return RunOrchestrationResult(
                run_id=str(run.id),
                status=CAMPAIGN_RUN_STATUS_CANCELLED,
                summary=summarize_items(run),
                already_terminal=True,
            )
        await mark_pending_items_ready(db, tenant_id=tenant_id, run_id=run_id)

    item_results: list[ItemEmitResult] = []
    try:
        item_results = await emit_run_items(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            run_item_ids=run_item_ids,
            context=context,
            mode=mode,
            skip_transport=skip_transport,
            transport=transport,
            template_resolver=template_resolver,
            link_resolver=link_resolver,
        )
    except Exception as exc:  # noqa: BLE001 — run-level abort only
        run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
        if str(run.status) != CAMPAIGN_RUN_STATUS_CANCELLED:
            run.status = CAMPAIGN_RUN_STATUS_FAILED
            run.completed_at = _now()
            meta = dict(run.meta or {})
            meta["orchestration_error"] = str(exc) or type(exc).__name__
            run.meta = meta
            await db.flush()
        summary = summarize_items(run)
        return RunOrchestrationResult(
            run_id=str(run.id),
            status=str(run.status),
            summary=summary,
            item_results=tuple(item_results),
        )

    run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
    if str(run.status) == CAMPAIGN_RUN_STATUS_CANCELLED:
        return RunOrchestrationResult(
            run_id=str(run.id),
            status=CAMPAIGN_RUN_STATUS_CANCELLED,
            summary=summarize_items(run),
            item_results=tuple(item_results),
            already_terminal=True,
        )

    summary = summarize_items(run)
    # If a subset was targeted, only require those; otherwise all items.
    if run_item_ids is not None:
        target_ids = {str(i) for i in run_item_ids}
        relevant = [i for i in (run.items or []) if str(i.id) in target_ids]
        all_terminal = all(str(i.status) in _TERMINAL_ITEM for i in relevant) if relevant else True
    else:
        all_terminal = (
            all(str(i.status) in _TERMINAL_ITEM for i in (run.items or []))
            if (run.items or [])
            else True
        )

    if all_terminal:
        run.status = CAMPAIGN_RUN_STATUS_COMPLETED
        run.completed_at = _now()
    # else leave running (partial subset still in flight — rare with sync emit)

    meta = dict(run.meta or {})
    meta["orchestration"] = {
        "finished_at": _now().isoformat(),
        "mode": str(mode),
        "skip_transport": bool(skip_transport) if mode == "execute" else None,
        "summary": summary.to_dict(),
        "item_results": [r.to_dict() for r in item_results],
    }
    run.meta = meta
    await db.flush()

    return RunOrchestrationResult(
        run_id=str(run.id),
        status=str(run.status),
        summary=summary,
        item_results=tuple(item_results),
    )


__all__ = [
    "RunSummary",
    "RunOrchestrationResult",
    "summarize_items",
    "mark_pending_items_ready",
    "cancel_campaign_run",
    "execute_campaign_run",
]
