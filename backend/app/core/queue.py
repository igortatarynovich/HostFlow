"""
Task queue abstraction (Phase 0 #5).

Two call styles are supported:

1. Legacy fire-and-forget of an already-constructed coroutine — used for ad-hoc
   "run this in the background of the current request" work. Always stays
   in-process; it is explicitly not a durable job.

       await enqueue("name", some_coro())

2. Named durable jobs registered in `app.core.arq_worker.JOB_REGISTRY`. These
   route to:

       • in-process asyncio.create_task when `settings.job_queue_backend != "arq"`
         OR when ARQ/Redis is not available (dev, tests, bootstrap);
       • ARQ when `settings.job_queue_backend == "arq"` and a Redis URL is set.

   Either way, the API is identical:

       from backend.app.core.queue import enqueue_job
       await enqueue_job("stripe_webhook_process", event_id=..., event_type=..., event_obj=...)

Only the named-job path is safe across multiple replicas. For anything that
must survive a crash — Stripe webhooks, outgoing comms, automations — use
`enqueue_job` with a name from `JOB_REGISTRY`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Coroutine, Optional, TypeVar

from backend.app.core.settings import settings

logger = logging.getLogger("hostflow.jobs")

T = TypeVar("T")

# Global ARQ pool (process-level singleton). Created lazily on the first
# `enqueue_job` call so web processes that never enqueue pay nothing.
_arq_pool: Any = None
_arq_pool_lock = asyncio.Lock()


async def enqueue(
    name: str,
    coro: Coroutine[Any, Any, T],
    *,
    fire_and_forget: bool = True,
) -> T | None:
    """
    Run a coroutine as an in-process background task.

    This is the legacy helper preserved for backwards compatibility — use
    `enqueue_job()` for anything durable or multi-replica.
    """
    if fire_and_forget:
        asyncio.create_task(_run_and_log(name, coro))
        return None
    return await _run_and_log(name, coro)


async def _run_and_log(name: str, coro: Coroutine[Any, Any, T]) -> T:
    try:
        return await coro
    except Exception as exc:
        logger.exception("[queue] task %s failed: %s", name, exc)
        raise


def run_later(name: str, fn: Callable[[], Awaitable[Any]]) -> None:
    """
    Schedule an async function to run in-process (fire-and-forget).

    Same caveats as `enqueue()` — use `enqueue_job()` for durable work.
    """
    asyncio.create_task(_run_and_log(name, fn()))


# ---------------------------------------------------------------------------
# Named durable jobs
# ---------------------------------------------------------------------------


def _use_arq() -> bool:
    """True if ARQ is wired up AND enabled by settings."""
    backend = str(settings.job_queue_backend or "").strip().lower()
    if backend != "arq":
        return False
    try:
        from backend.app.core.arq_worker import arq_available, build_redis_settings

        if not arq_available():
            return False
        return build_redis_settings() is not None
    except Exception:  # pragma: no cover - defensive
        return False


async def _get_arq_pool() -> Any:
    """Return a cached ARQ pool; create it on first use."""
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool
    async with _arq_pool_lock:
        if _arq_pool is not None:
            return _arq_pool
        from arq import create_pool  # type: ignore

        from backend.app.core.arq_worker import build_redis_settings

        redis_settings = build_redis_settings()
        if redis_settings is None:
            raise RuntimeError("ARQ redis settings are unavailable")
        _arq_pool = await create_pool(redis_settings)
        return _arq_pool


async def close_arq_pool() -> None:
    """Close the cached ARQ pool on application shutdown."""
    global _arq_pool
    if _arq_pool is None:
        return
    try:
        await _arq_pool.close()
    except Exception:  # pragma: no cover
        pass
    finally:
        _arq_pool = None


async def enqueue_job(
    name: str,
    *,
    job_id: Optional[str] = None,
    defer_by: Optional[float] = None,
    **kwargs: Any,
) -> Optional[str]:
    """
    Enqueue a named job declared in `app.core.arq_worker.JOB_REGISTRY`.

    Returns the backend job id (ARQ) or an internal marker ("inprocess:<name>")
    when running via the in-process fallback.

    Parameters
    ----------
    name       : job registry key (e.g. "stripe_webhook_process").
    job_id     : optional dedupe id — when two enqueue calls share the same
                 non-empty `job_id` and both still sit in the queue, ARQ keeps
                 only one. Used for "poke tenant T" style jobs.
    defer_by   : optional delay in seconds before the job becomes visible.
    **kwargs   : keyword arguments forwarded to the job function.

    The function validates `name` against `JOB_REGISTRY` before enqueuing so a
    typo raises immediately in the web process instead of silently vanishing.
    """
    from backend.app.core.arq_worker import JOB_REGISTRY

    fn = JOB_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown job name {name!r}; register it in JOB_REGISTRY first")

    if _use_arq():
        try:
            pool = await _get_arq_pool()
            from datetime import timedelta

            kw: dict[str, Any] = {"_queue_name": settings.job_queue_name}
            if job_id:
                kw["_job_id"] = job_id
            if defer_by is not None and defer_by > 0:
                kw["_defer_by"] = timedelta(seconds=float(defer_by))
            job = await pool.enqueue_job(name, **kwargs, **kw)
            if job is not None:
                logger.info("[queue] enqueued arq job name=%s job_id=%s", name, job.job_id)
                return str(job.job_id)
            # ARQ returns None if deduped by job_id.
            logger.info("[queue] arq job deduped name=%s job_id=%s", name, job_id)
            return job_id
        except Exception as exc:
            logger.exception("[queue] arq enqueue failed; falling back to in-process for %s: %s", name, exc)
            # Fall through to in-process so we never drop work.

    # In-process fallback: execute the job in the current event loop.
    async def _inprocess_runner() -> None:
        if defer_by and defer_by > 0:
            try:
                await asyncio.sleep(float(defer_by))
            except Exception:
                pass
        await _run_and_log(name, fn({}, **kwargs))

    asyncio.create_task(_inprocess_runner())
    return f"inprocess:{name}"
