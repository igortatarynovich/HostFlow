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
from datetime import timedelta
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


async def job_calendar_sync_ingest(
    ctx: Dict[str, Any],
    *,
    sync_job_id: str,
) -> Dict[str, Any]:
    """
    Consume one queued calendar sync job.

    For now this is a safe scaffold: it marks the job as processing and then
    completed so webhook->queue->worker flow is verifiable end-to-end.
    Provider-specific mapping/sync logic will replace the placeholder block.
    """
    from datetime import datetime, timezone
    from sqlalchemy import and_, select

    from backend.app.db.session import async_session_maker
    from backend.app.models.calendar_integration import (
        CalendarChannel,
        CalendarConnection,
        CalendarItem,
        CalendarItemLink,
        CalendarSyncCursor,
        CalendarSyncJob,
    )
    from backend.app.services.calendar_provider_sync import (
        CalendarProviderSyncError,
        fetch_google_events,
        fetch_microsoft_events,
    )

    def _read_event_id(data: dict[str, Any]) -> Optional[str]:
        for key in ("event_id", "eventId", "id", "event_ref", "eventRef"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        event_obj = data.get("event")
        if isinstance(event_obj, dict):
            for key in ("id", "event_id", "eventId"):
                val = event_obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return None

    def _read_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None
        if isinstance(value, dict):
            # Google and Microsoft commonly nest timestamps under dateTime/start/end.
            for key in ("dateTime", "datetime", "start", "end", "value", "time"):
                nested = value.get(key)
                if isinstance(nested, str) and nested.strip():
                    try:
                        return datetime.fromisoformat(nested.replace("Z", "+00:00"))
                    except Exception:
                        continue
            date_only = value.get("date")
            if isinstance(date_only, str) and date_only.strip():
                try:
                    return datetime.fromisoformat(f"{date_only}T00:00:00+00:00")
                except Exception:
                    return None
        return None

    def _extract_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
        event_obj = payload.get("event")
        if isinstance(event_obj, dict):
            return event_obj
        # MS Graph notifications may wrap event under resourceData.
        resource_data = payload.get("resourceData")
        if isinstance(resource_data, dict):
            return resource_data
        return payload

    def _extract_title(data: dict[str, Any], fallback: str) -> str:
        for key in ("title", "summary", "subject", "name"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return fallback

    def _extract_description(data: dict[str, Any]) -> str | None:
        direct = str(data.get("description") or data.get("bodyPreview") or "").strip()
        if direct:
            return direct
        body = data.get("body")
        if isinstance(body, dict):
            text = str(body.get("content") or "").strip()
            if text:
                return text
        return None

    def _extract_location(data: dict[str, Any]) -> str | None:
        direct = str(data.get("location") or "").strip()
        if direct:
            return direct
        loc = data.get("location")
        if isinstance(loc, dict):
            display = str(loc.get("displayName") or "").strip()
            if display:
                return display
        return None

    def _extract_attendees(data: dict[str, Any]) -> list[dict[str, Any]]:
        raw = data.get("attendees")
        if not isinstance(raw, list):
            return []
        rows: list[dict[str, Any]] = []
        for att in raw:
            if not isinstance(att, dict):
                continue
            email = str(att.get("email") or "").strip()
            name = str(att.get("displayName") or "").strip()
            status = str(att.get("responseStatus") or "").strip()
            if not email:
                email_address = att.get("emailAddress")
                if isinstance(email_address, dict):
                    email = str(email_address.get("address") or "").strip()
                    if not name:
                        name = str(email_address.get("name") or "").strip()
                response = att.get("status")
                if isinstance(response, dict) and not status:
                    status = str(response.get("response") or "").strip()
            if not email:
                continue
            rows.append(
                {
                    "email": email,
                    "name": name or None,
                    "response_status": status or None,
                }
            )
        return rows

    def _extract_meeting_link(data: dict[str, Any]) -> str | None:
        for key in ("hangoutLink", "webLink", "meeting_link"):
            val = str(data.get(key) or "").strip()
            if val:
                return val
        online = data.get("onlineMeeting")
        if isinstance(online, dict):
            join = str(online.get("joinUrl") or "").strip()
            if join:
                return join
        return None

    def _extract_recurrence(data: dict[str, Any]) -> Any:
        recurrence = data.get("recurrence")
        if recurrence is not None:
            return recurrence
        recurring_id = str(data.get("recurringEventId") or "").strip()
        return recurring_id or None

    def _extract_enriched_payload(data: dict[str, Any]) -> dict[str, Any]:
        enriched: dict[str, Any] = {}
        location = _extract_location(data)
        if location:
            enriched["location"] = location
        attendees = _extract_attendees(data)
        if attendees:
            enriched["attendees"] = attendees
        meeting_link = _extract_meeting_link(data)
        if meeting_link:
            enriched["meeting_link"] = meeting_link
            enriched["is_online_meeting"] = True
        visibility = str(data.get("visibility") or data.get("sensitivity") or "").strip().lower()
        if visibility:
            enriched["visibility"] = visibility
        transparency = str(data.get("transparency") or "").strip().lower()
        if transparency:
            enriched["transparency"] = transparency
        recurrence = _extract_recurrence(data)
        if recurrence is not None:
            enriched["recurrence"] = recurrence
        return enriched

    def _is_event_deleted(data: dict[str, Any]) -> bool:
        status_val = str(data.get("status") or "").strip().lower()
        if status_val in {"cancelled", "canceled", "deleted"}:
            return True
        removed = data.get("@removed")
        if isinstance(removed, dict):
            return True
        return False

    now = datetime.now(timezone.utc)
    async with async_session_maker() as db:
        row = await db.execute(select(CalendarSyncJob).where(CalendarSyncJob.id == str(sync_job_id)).limit(1))
        job = row.scalar_one_or_none()
        if job is None:
            logger.warning("[arq] calendar_sync_ingest job not found sync_job_id=%s", sync_job_id)
            return {"ok": False, "reason": "not_found", "sync_job_id": sync_job_id}
        if job.status in {"processing", "done"}:
            return {"ok": True, "reason": "already_processed", "sync_job_id": sync_job_id}

        job.status = "processing"
        job.started_at = now
        await db.flush()
        try:
            payload = dict(job.payload or {})
            source_kind = str(job.source_kind or "").strip().lower()
            provider = "google" if source_kind.startswith("google") else "microsoft" if source_kind.startswith("microsoft") else None
            event_data = _extract_event_payload(payload)
            action = str(payload.get("action") or event_data.get("action") or "").strip().lower()
            operation = str(getattr(job, "operation", "") or "").strip().lower()

            if operation == "renew_subscription":
                connection_id = str(payload.get("connection_id") or "").strip()
                if not connection_id or provider is None:
                    job.status = "failed"
                    job.retry_count = int(job.retry_count or 0) + 1
                    job.last_error = "connection_id/provider required for renew_subscription"
                    await db.commit()
                    return {"ok": False, "sync_job_id": sync_job_id, "mode": "renew_invalid_payload"}
                conn_result = await db.execute(
                    select(CalendarConnection).where(
                        and_(
                            CalendarConnection.id == connection_id,
                            CalendarConnection.tenant_id == str(job.tenant_id),
                        )
                    ).limit(1)
                )
                conn_row = conn_result.scalar_one_or_none()
                if conn_row is None:
                    job.status = "failed"
                    job.retry_count = int(job.retry_count or 0) + 1
                    job.last_error = "connection not found"
                    await db.commit()
                    return {"ok": False, "sync_job_id": sync_job_id, "mode": "renew_connection_missing"}
                now_utc = datetime.now(timezone.utc)
                ttl_hours = 20 if provider == "google" else 46
                channel = (
                    await db.execute(
                        select(CalendarChannel)
                        .where(CalendarChannel.connection_id == connection_id)
                        .order_by(CalendarChannel.updated_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if channel is None:
                    channel = CalendarChannel(
                        tenant_id=str(job.tenant_id),
                        connection_id=connection_id,
                        provider=provider,
                        resource_id=f"{provider}-resource-{connection_id}",
                        channel_ref=f"{provider}-channel-{connection_id}",
                        expires_at=now_utc + timedelta(hours=ttl_hours),
                        renew_after=now_utc + timedelta(hours=max(ttl_hours - 2, 1)),
                        health_state="healthy",
                        payload={"renewed_by": "calendar_sync_ingest"},
                    )
                    db.add(channel)
                else:
                    channel.expires_at = now_utc + timedelta(hours=ttl_hours)
                    channel.renew_after = now_utc + timedelta(hours=max(ttl_hours - 2, 1))
                    channel.health_state = "healthy"
                    channel.payload = {
                        **dict(channel.payload or {}),
                        "renewed_by": "calendar_sync_ingest",
                        "renewed_at": now_utc.isoformat(),
                    }
                job.status = "done"
                job.completed_at = now_utc
                await db.commit()
                return {"ok": True, "sync_job_id": sync_job_id, "mode": "renewed"}

            if source_kind in {"slack_event", "teams_event"} and action in {"cancel", "cancel_item", "reschedule"}:
                item_id = str(payload.get("calendar_item_id") or payload.get("item_id") or event_data.get("calendar_item_id") or "").strip()
                if item_id:
                    item_row = await db.execute(
                        select(CalendarItem).where(and_(CalendarItem.id == item_id, CalendarItem.tenant_id == str(job.tenant_id))).limit(1)
                    )
                    item = item_row.scalar_one_or_none()
                    if item is not None:
                        expected_provider_version = str(
                            payload.get("expected_provider_version")
                            or event_data.get("expected_provider_version")
                            or ""
                        ).strip()
                        if expected_provider_version:
                            link_row = await db.execute(
                                select(CalendarItemLink)
                                .where(CalendarItemLink.calendar_item_id == str(item.id))
                                .order_by(CalendarItemLink.updated_at.desc())
                                .limit(1)
                            )
                            link = link_row.scalar_one_or_none()
                            actual_provider_version = str(getattr(link, "provider_version", "") or "").strip()
                            if actual_provider_version and actual_provider_version != expected_provider_version:
                                item.payload = {
                                    **dict(item.payload or {}),
                                    "last_action_source": source_kind,
                                    "last_action": "conflict_skipped",
                                    "conflict_expected_provider_version": expected_provider_version,
                                    "conflict_actual_provider_version": actual_provider_version,
                                }
                                job.status = "done"
                                job.completed_at = datetime.now(timezone.utc)
                                await db.commit()
                                return {
                                    "ok": True,
                                    "sync_job_id": sync_job_id,
                                    "mode": "action_conflict_skipped",
                                }
                        if action in {"cancel", "cancel_item"}:
                            item.status = "cancelled"
                        elif action == "reschedule":
                            new_start = _read_datetime(payload.get("starts_at") or payload.get("start") or event_data.get("starts_at"))
                            if new_start is not None:
                                item.starts_at = new_start
                                item.status = "scheduled"
                            new_end = _read_datetime(payload.get("ends_at") or payload.get("end") or event_data.get("ends_at"))
                            if new_end is not None:
                                item.ends_at = new_end
                        item.payload = {
                            **dict(item.payload or {}),
                            "last_action_source": source_kind,
                            "last_action": action,
                        }
                job.status = "done"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return {"ok": True, "sync_job_id": sync_job_id, "mode": "action"}

            if provider is not None:
                if operation == "reconcile":
                    events = payload.get("events")
                    if not isinstance(events, list) or not events:
                        connection_id = str(payload.get("connection_id") or "").strip()
                        conn_row = None
                        if connection_id:
                            conn_result = await db.execute(
                                select(CalendarConnection).where(
                                    and_(
                                        CalendarConnection.id == connection_id,
                                        CalendarConnection.tenant_id == str(job.tenant_id),
                                    )
                                ).limit(1)
                            )
                            conn_row = conn_result.scalar_one_or_none()
                        if conn_row is not None:
                            token_meta = dict(conn_row.token_meta_json or {})
                            access_token = str(token_meta.get("access_token") or "").strip()
                            cursor_val = str(payload.get("cursor") or "").strip() or None
                            cursor_meta = payload.get("cursor_meta")
                            if not isinstance(cursor_meta, dict):
                                cursor_meta = {}
                            calendar_ref = cursor_meta.get("calendar_ref")
                            try:
                                if provider == "google":
                                    sync_result = await fetch_google_events(
                                        access_token=access_token,
                                        calendar_ref=calendar_ref if isinstance(calendar_ref, str) else None,
                                        cursor=cursor_val,
                                        cursor_meta=cursor_meta,
                                    )
                                else:
                                    sync_result = await fetch_microsoft_events(
                                        access_token=access_token,
                                        calendar_ref=calendar_ref if isinstance(calendar_ref, str) else None,
                                        cursor=cursor_val,
                                        cursor_meta=cursor_meta,
                                    )
                            except CalendarProviderSyncError as exc:
                                job.status = "failed"
                                job.retry_count = int(job.retry_count or 0) + 1
                                job.last_error = str(exc)
                                await db.commit()
                                return {
                                    "ok": False,
                                    "sync_job_id": sync_job_id,
                                    "mode": "reconcile_provider_failed",
                                }
                            events = sync_result.events
                            payload = {
                                "events": events,
                                "cursor": sync_result.next_cursor,
                                "cursor_meta": sync_result.cursor_meta or {},
                            }
                            cursor_row = (
                                await db.execute(
                                    select(CalendarSyncCursor).where(
                                        and_(
                                            CalendarSyncCursor.connection_id == str(conn_row.id),
                                            CalendarSyncCursor.calendar_ref
                                            == str((sync_result.cursor_meta or {}).get("calendar_ref") or calendar_ref or "default"),
                                        )
                                    )
                                )
                            ).scalar_one_or_none()
                            if cursor_row is None:
                                cursor_row = CalendarSyncCursor(
                                    tenant_id=str(job.tenant_id),
                                    connection_id=str(conn_row.id),
                                    provider=provider,
                                    calendar_ref=str((sync_result.cursor_meta or {}).get("calendar_ref") or calendar_ref or "default"),
                                    cursor=sync_result.next_cursor,
                                    cursor_meta_json=dict(sync_result.cursor_meta or {}),
                                    last_synced_at=datetime.now(timezone.utc),
                                )
                                db.add(cursor_row)
                            else:
                                cursor_row.cursor = sync_result.next_cursor
                                cursor_row.cursor_meta_json = dict(sync_result.cursor_meta or {})
                                cursor_row.last_synced_at = datetime.now(timezone.utc)
                        if not isinstance(events, list) or not events:
                            job.status = "done"
                            job.completed_at = datetime.now(timezone.utc)
                            await db.commit()
                            return {
                                "ok": True,
                                "sync_job_id": sync_job_id,
                                "source_kind": job.source_kind,
                                "mode": "reconcile_noop",
                            }
                event_rows: list[dict[str, Any]] = []
                if operation == "reconcile":
                    raw_events = payload.get("events")
                    if isinstance(raw_events, list):
                        event_rows = [row for row in raw_events if isinstance(row, dict)]
                if not event_rows:
                    if isinstance(event_data, dict):
                        event_rows = [event_data]

                for provider_event in event_rows:
                    event_id = _read_event_id(provider_event)
                    is_deleted = _is_event_deleted(provider_event)
                    title = _extract_title(provider_event, fallback=f"{provider.title()} event")
                    description_text = _extract_description(provider_event)
                    enriched_payload = _extract_enriched_payload(provider_event)
                    start_dt = _read_datetime(
                        provider_event.get("starts_at")
                        or provider_event.get("start")
                        or provider_event.get("startDateTime")
                    ) or _utcnow_fallback()
                    end_dt = _read_datetime(
                        provider_event.get("ends_at")
                        or provider_event.get("end")
                        or provider_event.get("endDateTime")
                    )
                    timezone_name = str(provider_event.get("timezone") or provider_event.get("timeZone") or "UTC")

                    item: CalendarItem | None = None
                    if event_id:
                        link_row = await db.execute(
                            select(CalendarItemLink).where(
                                and_(
                                    CalendarItemLink.tenant_id == str(job.tenant_id),
                                    CalendarItemLink.provider == provider,
                                    CalendarItemLink.provider_event_id == event_id,
                                )
                            ).limit(1)
                        )
                        link = link_row.scalar_one_or_none()
                        if link is not None:
                            item_row = await db.execute(
                                select(CalendarItem).where(
                                    and_(
                                        CalendarItem.id == str(link.calendar_item_id),
                                        CalendarItem.tenant_id == str(job.tenant_id),
                                    )
                                ).limit(1)
                            )
                            item = item_row.scalar_one_or_none()
                            if item is not None:
                                item.title = title
                                item.starts_at = start_dt
                                item.ends_at = end_dt
                                item.description = description_text
                                item.timezone = timezone_name
                                item.source = provider
                                item.status = "cancelled" if is_deleted else "scheduled"
                                item.payload = {
                                    **dict(item.payload or {}),
                                    **enriched_payload,
                                    "provider_payload": provider_event,
                                }
                                link.provider_version = str(
                                    provider_event.get("etag")
                                    or provider_event.get("@odata.etag")
                                    or provider_event.get("updated")
                                    or ""
                                ) or None
                                link.sync_state = "cancelled" if is_deleted else "synced"
                                link.payload = {**dict(link.payload or {}), "source_kind": source_kind}

                    if item is None and not is_deleted:
                        item = CalendarItem(
                            tenant_id=str(job.tenant_id),
                            owner_id=None,
                            assignee_id=None,
                            kind="event",
                            status="scheduled",
                            title=title,
                            description=(
                                description_text
                            ),
                            timezone=timezone_name,
                            starts_at=start_dt,
                            ends_at=end_dt,
                            all_day=False,
                            linked_entity_type=None,
                            linked_entity_id=None,
                            source=provider,
                            payload={**enriched_payload, "provider_payload": provider_event},
                        )
                        db.add(item)
                        await db.flush()
                        if event_id:
                            db.add(
                                CalendarItemLink(
                                    tenant_id=str(job.tenant_id),
                                    calendar_item_id=item.id,
                                    connection_id=None,
                                    provider=provider,
                                    provider_calendar_id=(
                                        str(provider_event.get("calendar_id") or provider_event.get("calendarId") or "").strip() or None
                                    ),
                                    provider_event_id=event_id,
                                    provider_version=(
                                        str(provider_event.get("etag") or provider_event.get("@odata.etag") or "").strip() or None
                                    ),
                                    sync_state="synced",
                                    payload={"source_kind": source_kind},
                                )
                            )

            job.status = "done"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("[arq] calendar_sync_ingest processed sync_job_id=%s source=%s", sync_job_id, job.source_kind)
            return {"ok": True, "sync_job_id": sync_job_id, "source_kind": job.source_kind}
        except Exception as exc:
            await db.rollback()
            job_row = await db.execute(select(CalendarSyncJob).where(CalendarSyncJob.id == str(sync_job_id)).limit(1))
            job_retry = job_row.scalar_one_or_none()
            if job_retry is not None:
                job_retry.status = "failed"
                job_retry.retry_count = int(job_retry.retry_count or 0) + 1
                job_retry.last_error = str(exc)
                await db.commit()
            logger.exception("[arq] calendar_sync_ingest failed sync_job_id=%s: %s", sync_job_id, exc)
            raise


def _utcnow_fallback():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


# Registry of (name → callable) used both by ARQ (via WorkerSettings.functions)
# and by the in-process fallback in `app.core.queue`.
JOB_REGISTRY: Dict[str, Callable[..., Awaitable[Any]]] = {
    "stripe_webhook_process": job_stripe_webhook_process,
    "communications_dispatch_once": job_communications_dispatch_once,
    "automation_evaluate_trigger": job_automation_evaluate_trigger,
    "calendar_sync_ingest": job_calendar_sync_ingest,
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
