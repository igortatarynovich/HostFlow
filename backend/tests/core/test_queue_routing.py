"""Phase 0 #5: `app.core.queue.enqueue_job` routing and fallback behaviour."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import pytest

from backend.app.core import arq_worker, queue


@pytest.mark.anyio
async def test_enqueue_job_runs_inprocess_when_backend_is_inprocess(monkeypatch):
    """Default backend → executes the coroutine in-process."""
    monkeypatch.setattr(queue.settings, "job_queue_backend", "inprocess", raising=False)
    called: list[Dict[str, Any]] = []

    async def fake(ctx, **kw):
        called.append(dict(kw))

    monkeypatch.setitem(arq_worker.JOB_REGISTRY, "_t_inproc", fake)
    rid = await queue.enqueue_job("_t_inproc", alpha=1, beta="x")
    assert rid == "inprocess:_t_inproc"
    # The in-process fallback schedules as create_task; give the loop a tick.
    for _ in range(10):
        if called:
            break
        await asyncio.sleep(0.01)
    assert called == [{"alpha": 1, "beta": "x"}]


@pytest.mark.anyio
async def test_enqueue_job_rejects_unknown_name(monkeypatch):
    monkeypatch.setattr(queue.settings, "job_queue_backend", "inprocess", raising=False)
    with pytest.raises(ValueError):
        await queue.enqueue_job("does_not_exist")


@pytest.mark.anyio
async def test_enqueue_job_falls_back_to_inprocess_when_redis_down(monkeypatch):
    """ARQ backend with unreachable Redis must run the job in-process (no data loss)."""
    # Point ARQ at a port nothing is listening on.
    monkeypatch.setenv("JOB_QUEUE_REDIS_URL", "redis://127.0.0.1:16399/0")
    monkeypatch.setattr(queue.settings, "job_queue_backend", "arq", raising=False)
    monkeypatch.setattr(queue.settings, "job_queue_redis_url", "redis://127.0.0.1:16399/0", raising=False)

    called: list[int] = []

    async def fake(ctx, value: int = 0):
        called.append(value)

    monkeypatch.setitem(arq_worker.JOB_REGISTRY, "_t_fallback", fake)
    rid = await queue.enqueue_job("_t_fallback", value=42)
    assert rid == "inprocess:_t_fallback"
    for _ in range(20):
        if called:
            break
        await asyncio.sleep(0.05)
    assert called == [42]


def test_job_registry_has_phase0_critical_jobs():
    """Guard so we do not accidentally drop the three Phase 0 #5 jobs."""
    assert "stripe_webhook_process" in arq_worker.JOB_REGISTRY
    assert "communications_dispatch_once" in arq_worker.JOB_REGISTRY
    assert "automation_evaluate_trigger" in arq_worker.JOB_REGISTRY


def test_worker_settings_exposes_all_registered_jobs():
    """WorkerSettings.functions must mirror JOB_REGISTRY."""
    assert arq_worker.arq_available() is True
    expected = set(arq_worker.JOB_REGISTRY.values())
    assert set(arq_worker.WorkerSettings.functions) >= expected


def test_build_redis_settings_returns_none_without_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(queue.settings, "job_queue_redis_url", None, raising=False)
    assert arq_worker.build_redis_settings() is None


def test_build_redis_settings_builds_from_dsn(monkeypatch):
    monkeypatch.setattr(queue.settings, "job_queue_redis_url", "redis://localhost:6379/5", raising=False)
    rs = arq_worker.build_redis_settings()
    assert rs is not None
    assert rs.database == 5
