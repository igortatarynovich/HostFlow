# Background job queue (ARQ + Redis)

_Status:_ stable since Phase 0 #5 (2026-04)
_Owner:_ platform / backend
_Scope:_ `backend/app/core/queue.py`, `backend/app/core/arq_worker.py`, every caller that pushes work via `enqueue_job`.

This document captures **how HostFlow runs side-effectful work out-of-band**, so that:

* a slow Stripe callback, outgoing email, or automation never blocks an API response;
* an API pod crash does not lose an in-flight webhook or notification;
* the system still works without Redis in local dev / unit tests (graceful fallback).

---

## 1. Backends

Two backends sit behind one client API (`enqueue_job`):

| Backend   | Activated when                                              | Durability     | Multi-replica | Use in prod |
| --------- | ----------------------------------------------------------- | -------------- | ------------- | ----------- |
| inprocess | `JOB_QUEUE_BACKEND=inprocess` (default) or ARQ unavailable  | None (in-RAM)  | No            | Only for single-pod / dev |
| arq       | `JOB_QUEUE_BACKEND=arq` AND Redis URL resolvable            | Redis streams  | Yes           | Default in production deploys |

When ARQ is configured but Redis is unreachable, `enqueue_job` logs the exception and **falls back to in-process execution** — we never drop the job inside an HTTP request.

---

## 2. Public API

```python
from backend.app.core.queue import enqueue_job

await enqueue_job(
    "stripe_webhook_process",
    job_id=f"stripe:{event_id}",    # optional dedupe key
    defer_by=2.5,                   # optional delay in seconds
    event_id=event_id,
    event_type=event_type,
    event_obj=obj,
)
```

`enqueue_job` validates the job name against `JOB_REGISTRY`; unknown names raise immediately (typo guard).

The legacy helpers `enqueue()` and `run_later()` remain in place for fire-and-forget coroutines that don't need durability — they always run in-process.

---

## 3. Registered jobs (Phase 0 #5)

| Name                             | Purpose                                              | Called from                              |
| -------------------------------- | ---------------------------------------------------- | ---------------------------------------- |
| `stripe_webhook_process`         | Runs `_handle_checkout_completed / _handle_invoice_* / _handle_subscription_event` for a verified event. On failure the idempotency claim is released so ARQ or Stripe can retry. | `POST /api/v1/settings/billing/webhook` |
| `communications_dispatch_once`   | One iteration of `communications_scheduler` tick. Useful for "send a test" buttons and for a future migration away from the in-process loop. | API actions, future ARQ cron |
| `automation_evaluate_trigger`    | Loads matching automation rules for `(tenant_id, trigger)`, evaluates conditions and fires actions. | Any domain event hook (leads, candidates, docs, …) |

Adding a new job:

1. Define `async def job_name(ctx, **kwargs)` in `arq_worker.py`.
2. Register it in `JOB_REGISTRY`.
3. Enqueue via `enqueue_job("job_name", ...)`. `WorkerSettings.functions` picks it up automatically.

---

## 4. Retry policy

ARQ uses exponential backoff with:

| Setting                                 | Default |
| --------------------------------------- | ------- |
| `settings.job_queue_max_tries`          | 5       |
| `settings.job_queue_default_timeout_sec`| 120     |

Jobs are expected to:

1. Be idempotent (re-running the same payload must be safe).
2. Raise on failure so ARQ retries instead of swallowing the error.
3. Open their own DB sessions (`async_session_maker`) and commit explicitly.

`stripe_webhook_process` maintains this contract through the `stripe_webhook_event_log` table — see Phase 0 #5 section of `docs/HOSTFLOW_AUDIT_AND_PLAN.md`.

---

## 5. Deployment

Two containers share the same image:

* `backend`     — uvicorn, serves HTTP; enqueues jobs.
* `arq-worker`  — `arq backend.app.core.arq_worker.WorkerSettings`; drains the queue.

`docker-compose.yml` ships the `arq-worker` service under the `arq` and `full` profiles. Local development activates it via:

```bash
docker compose --profile arq up -d
# or set JOB_QUEUE_BACKEND=inprocess to keep everything in one process
```

Production compose / Kubernetes deploys should always run at least one `arq-worker` replica alongside the API pods and set `JOB_QUEUE_BACKEND=arq` on both.

---

## 6. Observability

* Jobs log to the `hostflow.jobs` logger (structured JSON when `LOG_FORMAT=json`).
* Failures bubble to Sentry via the standard FastAPI / asyncio exception hooks.
* `WorkerSettings.on_startup` emits `[arq] worker started queue=<name>`; use this as a liveness probe target.

---

## 7. Failure modes

| Symptom                                                         | Cause                                        | Mitigation |
| --------------------------------------------------------------- | -------------------------------------------- | ---------- |
| Webhook handler fails mid-flight                                | Bug in handler                               | `stripe_webhook_process` releases the idempotency claim; ARQ retries with backoff. |
| Redis unreachable from API pod                                  | Network / misconfiguration                   | `enqueue_job` logs + runs the handler in-process for the current request — nothing is lost, but multi-replica durability is degraded until Redis is back. |
| Worker container down                                           | Deployment / scaling outage                  | Jobs accumulate in the Redis queue; when the worker returns, ARQ drains them in FIFO. Stripe keeps retrying unseen events on its side for 72 h. |
| New job name pushed by web, unknown on worker                   | Deploy skew                                  | `enqueue_job` raises `ValueError` on unknown names in the web process. Roll-forward: deploy worker first, then API. |

---

## 8. Phase 1+ follow-ups (documented, not yet landed)

* Migrate `communications_scheduler_loop` from in-process asyncio to an ARQ cron job, so a multi-pod deployment does not double-send messages.
* Port `lead_quota` rollover + `meta_leads` polling jobs to the same registry.
* Move heavy `document.ocr` extraction into a dedicated queue (`hostflow:docs`) with a higher `job_timeout`.
