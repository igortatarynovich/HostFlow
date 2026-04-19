"""
ARQ worker: single source of truth for background jobs.

Usage
-----

Run the worker in production:

    arq backend.app.core.arq_worker.WorkerSettings

The FastAPI web process NEVER runs jobs — it only enqueues. The worker
drains the queue and executes registered functions below.

Registered jobs (Phase 0 #5)
----------------------------

    job_stripe_webhook_process       — process Stripe webhook event out-of-band.
    job_communications_dispatch_once — run one outgoing-comms dispatch for a tenant.
    job_automation_evaluate_trigger  — evaluate automation rules for a trigger.

All jobs are idempotent and safe to retry; failures bubble up so ARQ's
retry policy (exponential backoff up to `settings.job_queue_max_tries`)
triggers automatically.

Contract
--------

    1. Every job takes (ctx: dict, **payload) and returns JSON-serialisable data.
    2. Jobs open their own `AsyncSession` — never receive one from the caller.
    3. Jobs log via the `hostflow.jobs` logger; tenant_id is the first tag.
    4. Jobs MUST stay pure-async; CPU-bound work goes through `asyncio.to_thread`.

This module is safely importable even when `arq` is not installed — the
import guard keeps `app.core.queue` usable in the in-process mode.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from backend.app.core.settings import settings

logger = logging.getLogger("hostflow.jobs")

try:  # pragma: no cover - optional dependency at import time
    from arq.connections import RedisSettings  # type: ignore

    _ARQ_AVAILABLE = True
except Exception:  # pragma: no cover
    RedisSettings = None  # type: ignore[assignment]
    _ARQ_AVAILABLE = False


def arq_available() -> bool:
    """Whether the optional `arq` dependency is importable."""
    return _ARQ_AVAILABLE


def _resolve_redis_url() -> Optional[str]:
    """Pick ARQ's Redis URL: explicit setting → REDIS_URL → None."""
    explicit = (settings.job_queue_redis_url or "").strip()
    if explicit:
        return explicit
    import os

    env_url = os.environ.get("REDIS_URL", "").strip()
    return env_url or None


def build_redis_settings() -> Optional["RedisSettings"]:
    """Build ARQ RedisSettings from URL; returns None when arq is missing or URL unset."""
    if not _ARQ_AVAILABLE:
        return None
    url = _resolve_redis_url()
    if not url:
        return None
    try:
        return RedisSettings.from_dsn(url)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[arq] invalid redis url %r: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Job implementations
# ---------------------------------------------------------------------------


async def job_stripe_webhook_process(
    ctx: Dict[str, Any],
    *,
    event_id: str,
    event_type: str,
    event_obj: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the heavy Stripe webhook handler out-of-band. The HTTP endpoint has
    already verified the signature and claimed `event_id` in the idempotency
    log, so this job just routes the event to the right handler. On failure
    we release the claim so ARQ (or Stripe itself) can retry.
    """
    from backend.app.api.v1.settings import billing
    from backend.app.db.session import async_session_maker

    try:
        async with async_session_maker() as db:
            try:
                if event_type == "checkout.session.completed":
                    detail = await billing._handle_checkout_completed(db, event_obj)
                elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
                    detail = await billing._handle_invoice_paid(db, event_obj)
                elif event_type == "invoice.finalized":
                    detail = await billing._handle_invoice_finalized(db, event_obj)
                elif event_type == "invoice.payment_failed":
                    detail = await billing._handle_invoice_payment_failed(db, event_obj)
                elif event_type in (
                    "customer.subscription.created",
                    "customer.subscription.updated",
                ):
                    detail = await billing._handle_subscription_event(db, event_obj, deleted=False)
                elif event_type == "customer.subscription.deleted":
                    detail = await billing._handle_subscription_event(db, event_obj, deleted=True)
                else:
                    detail = f"Ignored: unsupported event type {event_type or '<empty>'}"
                await db.commit()
            except Exception:
                await db.rollback()
                raise
        logger.info(
            "[arq] stripe_webhook_process event_id=%s type=%s detail=%s",
            event_id,
            event_type,
            detail,
        )
        return {"ok": True, "event_id": event_id, "detail": detail}
    except Exception as exc:
        # Release the claim so the next retry (from ARQ or Stripe) can re-run.
        try:
            async with async_session_maker() as db:
                await billing._stripe_webhook_release_claim(db, event_id)
                await db.commit()
        except Exception as release_exc:  # pragma: no cover
            logger.warning(
                "[arq] stripe_webhook_process release_claim failed event_id=%s: %s",
                event_id,
                release_exc,
            )
        logger.exception(
            "[arq] stripe_webhook_process failed event_id=%s type=%s: %s",
            event_id,
            event_type,
            exc,
        )
        raise


async def job_communications_dispatch_once(
    ctx: Dict[str, Any],
    *,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run one iteration of the outgoing-communications dispatch loop.

    In the in-process mode the `communications_scheduler_loop` already runs in
    the API process; exposing this as a job lets us:
      * drive dispatch from webhooks / API actions (e.g. "send a test" buttons),
      * eventually replace the in-process loop with an ARQ cron schedule.

    When `tenant_id` is given we scope dispatch to a single tenant; otherwise
    we run the full tick. The job is safe to retry — the scheduler itself
    tracks per-tenant `last_sent_at` timestamps.
    """
    from backend.app.services.communications_scheduler import run_scheduler_tick_once

    try:
        summary = await run_scheduler_tick_once()
        logger.info(
            "[arq] communications_dispatch_once tenant_id=%s summary=%s",
            tenant_id or "<all>",
            (summary or {}).get("last_tick_summary"),
        )
        return {"ok": True, "tenant_id": tenant_id, "summary": summary.get("last_tick_summary")}
    except Exception as exc:
        logger.exception(
            "[arq] communications_dispatch_once failed tenant_id=%s: %s",
            tenant_id or "<all>",
            exc,
        )
        raise


async def job_automation_evaluate_trigger(
    ctx: Dict[str, Any],
    *,
    tenant_id: str,
    trigger: str,
    context: Dict[str, Any],
    actor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate and fire matching automation rules for a single trigger occurrence.

    Call sites (leads stage changed, candidate created, etc.) push a context
    payload; the worker loads rules, matches conditions and executes them.
    Designed to be cheap and idempotent — re-running simply re-applies the
    same rules (any dedupe policy lives inside the rule engine via
    `was_rule_fired_for_candidate_since`).
    """
    from backend.app.db.session import async_session_maker
    from backend.app.services.automation_rules import (
        _matches_conditions,
        _loads_or_empty,
        execute_automation_rule,
        list_rules,
    )

    fired = 0
    examined = 0
    try:
        async with async_session_maker() as db:
            rules = await list_rules(db, tenant_id=tenant_id, trigger=trigger)
            for rule in rules:
                examined += 1
                conditions = _loads_or_empty(rule.conditions_json)
                if conditions and not _matches_conditions(conditions, context or {}):
                    continue
                await execute_automation_rule(
                    db,
                    tenant_id=tenant_id,
                    rule=rule,
                    trigger=trigger,
                    actor_id=actor_id,
                    context=context or {},
                )
                fired += 1
            await db.commit()
        logger.info(
            "[arq] automation_evaluate_trigger tenant_id=%s trigger=%s fired=%d/%d",
            tenant_id,
            trigger,
            fired,
            examined,
        )
        return {"ok": True, "tenant_id": tenant_id, "trigger": trigger, "fired": fired, "examined": examined}
    except Exception as exc:
        logger.exception(
            "[arq] automation_evaluate_trigger failed tenant_id=%s trigger=%s: %s",
            tenant_id,
            trigger,
            exc,
        )
        raise


# Registry of (name → callable) used both by ARQ (via WorkerSettings.functions)
# and by the in-process fallback in `app.core.queue`.
JOB_REGISTRY: Dict[str, Callable[..., Awaitable[Any]]] = {
    "stripe_webhook_process": job_stripe_webhook_process,
    "communications_dispatch_once": job_communications_dispatch_once,
    "automation_evaluate_trigger": job_automation_evaluate_trigger,
}


# ---------------------------------------------------------------------------
# ARQ worker configuration (loaded by `arq` CLI; harmless when unused)
# ---------------------------------------------------------------------------

if _ARQ_AVAILABLE:

    async def _startup(ctx: Dict[str, Any]) -> None:  # pragma: no cover - arq runtime
        logger.info("[arq] worker started queue=%s", settings.job_queue_name)

    async def _shutdown(ctx: Dict[str, Any]) -> None:  # pragma: no cover - arq runtime
        logger.info("[arq] worker stopping")

    class WorkerSettings:  # type: ignore[no-redef]
        """
        ARQ picks this class up via `arq backend.app.core.arq_worker.WorkerSettings`.
        Functions are registered from `JOB_REGISTRY` so adding a job is a one-line
        dict mutation above.
        """

        functions: List[Callable[..., Awaitable[Any]]] = list(JOB_REGISTRY.values())
        redis_settings = build_redis_settings()
        queue_name = settings.job_queue_name
        max_tries = settings.job_queue_max_tries
        job_timeout = settings.job_queue_default_timeout_sec
        on_startup = _startup
        on_shutdown = _shutdown
        allow_abort_jobs = True
