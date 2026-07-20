"""In-app notification retention: TTL purge + per-user unread cap.

Notifications are an attention queue, not an audit/history store.
Policy (HostFlow defaults, overridable via settings):

* read, non-critical  → delete after ``notifications_retention_read_hours`` (24h)
* unread, non-critical → delete after ``notifications_retention_unread_days`` (7d)
* critical (any read state) → delete after ``notifications_retention_critical_days`` (30d)
* max unread per user → ``notifications_max_unread_per_user`` (100);
  excess drops oldest **non-critical** unread rows

Deletes use SQL Core/text against ``notifications`` so the retention worker
does not depend on unrelated ORM mapper configuration.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings

logger = logging.getLogger("hostflow.notifications.retention")

_CRITICAL = "critical"
_LOCK_KEY = "hostflow:lock:notifications_retention_purge"


def _as_utc(now: Optional[datetime]) -> datetime:
    ts = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


async def count_unread_for_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    row = await db.execute(
        text(
            "SELECT COUNT(*) FROM notifications "
            "WHERE tenant_id = :tenant_id AND user_id = :user_id AND is_read = false"
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    return int(row.scalar_one() or 0)


async def enforce_unread_cap_for_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    max_unread: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> int:
    """Delete oldest non-critical unread rows until count <= max_unread."""
    cap = int(max_unread if max_unread is not None else settings.notifications_max_unread_per_user)
    if cap <= 0:
        return 0
    batch = int(batch_size if batch_size is not None else settings.notifications_retention_batch_size)
    batch = max(1, min(batch, 5000))

    deleted_total = 0
    while True:
        unread = await count_unread_for_user(db, tenant_id=tenant_id, user_id=user_id)
        excess = unread - cap
        if excess <= 0:
            break
        take = min(excess, batch)
        ids = (
            await db.execute(
                text(
                    """
                    SELECT id FROM notifications
                    WHERE tenant_id = :tenant_id
                      AND user_id = :user_id
                      AND is_read = false
                      AND (priority IS NULL OR priority <> :critical)
                    ORDER BY created_at ASC
                    LIMIT :take
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "critical": _CRITICAL,
                    "take": take,
                },
            )
        ).scalars().all()
        if not ids:
            break
        deleted = await _delete_ids(db, ids)
        deleted_total += deleted
        if deleted == 0:
            break
    return deleted_total


async def _delete_ids(db: AsyncSession, ids: Sequence[Any]) -> int:
    if not ids:
        return 0
    # Expand bind params for broad dialect support (incl. asyncpg).
    params = {f"id{i}": str(v) for i, v in enumerate(ids)}
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    result = await db.execute(
        text(f"DELETE FROM notifications WHERE id IN ({placeholders})"),
        params,
    )
    return int(result.rowcount or 0)


async def _delete_matching_batch(
    db: AsyncSession,
    *,
    sql_where: str,
    params: Dict[str, Any],
    batch_size: int,
) -> int:
    ids = (
        await db.execute(
            text(
                f"""
                SELECT id FROM notifications
                WHERE {sql_where}
                ORDER BY created_at ASC
                LIMIT :batch_size
                """
            ),
            {**params, "batch_size": batch_size},
        )
    ).scalars().all()
    return await _delete_ids(db, ids)


async def purge_expired_notifications(
    db: AsyncSession,
    *,
    now: Optional[datetime] = None,
    batch_size: Optional[int] = None,
    max_batches: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, int]:
    """Purge expired notifications in small batches. Returns per-bucket deletes."""
    if not settings.notifications_retention_enabled:
        return {"read": 0, "unread": 0, "critical": 0, "batches": 0}

    ts = _as_utc(now)
    batch = int(batch_size if batch_size is not None else settings.notifications_retention_batch_size)
    batch = max(1, min(batch, 5000))
    limit_batches = int(
        max_batches
        if max_batches is not None
        else settings.notifications_retention_max_batches_per_run
    )
    limit_batches = max(1, limit_batches)

    read_cutoff = ts - timedelta(hours=max(1, int(settings.notifications_retention_read_hours)))
    unread_cutoff = ts - timedelta(days=max(1, int(settings.notifications_retention_unread_days)))
    critical_cutoff = ts - timedelta(days=max(1, int(settings.notifications_retention_critical_days)))

    tenant_clause = " AND tenant_id = :tenant_id" if tenant_id else ""
    base_params: Dict[str, Any] = {"critical": _CRITICAL}
    if tenant_id:
        base_params["tenant_id"] = tenant_id

    scopes: list[tuple[str, str, Dict[str, Any]]] = [
        (
            "read",
            f"is_read = true AND (priority IS NULL OR priority <> :critical) "
            f"AND created_at < :cutoff{tenant_clause}",
            {**base_params, "cutoff": read_cutoff},
        ),
        (
            "unread",
            f"is_read = false AND (priority IS NULL OR priority <> :critical) "
            f"AND created_at < :cutoff{tenant_clause}",
            {**base_params, "cutoff": unread_cutoff},
        ),
        (
            "critical",
            f"priority = :critical AND created_at < :cutoff{tenant_clause}",
            {**base_params, "cutoff": critical_cutoff},
        ),
    ]

    tallies = {"read": 0, "unread": 0, "critical": 0, "batches": 0}
    batches_used = 0

    for name, where_sql, params in scopes:
        while batches_used < limit_batches:
            deleted = await _delete_matching_batch(
                db, sql_where=where_sql, params=params, batch_size=batch
            )
            if deleted == 0:
                break
            tallies[name] += deleted
            batches_used += 1
            await db.commit()

    tallies["batches"] = batches_used
    return tallies


async def collapse_entity_unread_duplicates(
    db: AsyncSession,
    *,
    batch_size: int = 5000,
    max_batches: int = 2000,
    tenant_id: Optional[str] = None,
) -> Dict[str, int]:
    """Keep newest unread row per (tenant,user,type,channel,entity); delete older dupes."""
    batch = max(1, min(int(batch_size), 20000))
    limit_batches = max(1, int(max_batches))
    deleted_total = 0
    batches_used = 0
    tenant_clause = " AND tenant_id = :tenant_id" if tenant_id else ""
    params: Dict[str, Any] = {"batch_size": batch}
    if tenant_id:
        params["tenant_id"] = tenant_id

    for _ in range(limit_batches):
        result = await db.execute(
            text(
                f"""
                WITH ranked AS (
                  SELECT id,
                         ROW_NUMBER() OVER (
                           PARTITION BY tenant_id, user_id, type, channel,
                                        related_entity_type, related_entity_id
                           ORDER BY created_at DESC, id DESC
                         ) AS rn
                  FROM notifications
                  WHERE is_read = false
                    AND related_entity_id IS NOT NULL
                    {tenant_clause}
                ),
                doomed AS (
                  SELECT id FROM ranked WHERE rn > 1 LIMIT :batch_size
                )
                DELETE FROM notifications n
                USING doomed d
                WHERE n.id = d.id
                """
            ),
            params,
        )
        deleted = int(result.rowcount or 0)
        await db.commit()
        if deleted == 0:
            break
        deleted_total += deleted
        batches_used += 1
        await asyncio.sleep(0.05)

    return {"deleted": deleted_total, "batches": batches_used}


async def enforce_unread_caps_all_users(
    db: AsyncSession,
    *,
    max_unread: Optional[int] = None,
    limit_users: int = 500,
) -> Dict[str, int]:
    """Apply per-user unread cap for users currently over the limit."""
    cap = int(max_unread if max_unread is not None else settings.notifications_max_unread_per_user)
    if cap <= 0:
        return {"users": 0, "deleted": 0}
    rows = (
        await db.execute(
            text(
                """
                SELECT tenant_id, user_id, COUNT(*) AS n
                FROM notifications
                WHERE is_read = false
                GROUP BY tenant_id, user_id
                HAVING COUNT(*) > :cap
                ORDER BY n DESC
                LIMIT :limit_users
                """
            ),
            {"cap": cap, "limit_users": max(1, int(limit_users))},
        )
    ).mappings().all()
    deleted = 0
    for row in rows:
        deleted += await enforce_unread_cap_for_user(
            db,
            tenant_id=str(row["tenant_id"]),
            user_id=str(row["user_id"]),
            max_unread=cap,
        )
        await db.commit()
    return {"users": len(rows), "deleted": deleted}


@asynccontextmanager
async def redis_lock(ttl_sec: int = 3500):
    """Redis SET NX lock. Yields True if acquired (or Redis unavailable)."""
    client = None
    token = None
    acquired = True
    try:
        import redis.asyncio as redis_async

        url = (
            (settings.job_queue_redis_url or "").strip()
            or os.environ.get("REDIS_URL", "").strip()
        )
        if url:
            client = redis_async.from_url(url, encoding="utf-8", decode_responses=True)
            token = f"{os.getpid()}:{id(object())}"
            acquired = bool(await client.set(_LOCK_KEY, token, nx=True, ex=max(60, int(ttl_sec))))
    except Exception:
        logger.exception("[notifications_retention] redis lock unavailable; proceeding without lock")
        acquired = True
        client = None

    try:
        yield acquired
    finally:
        if client is not None and token is not None and acquired:
            try:
                await client.eval(
                    "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
                    1,
                    _LOCK_KEY,
                    token,
                )
            except Exception:
                pass
            try:
                await client.aclose()
            except Exception:
                pass


async def run_notifications_retention_once(
    *,
    tenant_id: Optional[str] = None,
    max_batches: Optional[int] = None,
    collapse_duplicates: bool = True,
    enforce_caps: bool = True,
    use_lock: bool = True,
) -> Dict[str, Any]:
    """Open a session and run one retention pass (ARQ / CLI only — not API loop)."""
    from backend.app.db.session import async_session_maker

    async with redis_lock(
        ttl_sec=max(600, int(settings.job_queue_default_timeout_sec or 120) * 10)
    ) as acquired:
        if use_lock and not acquired:
            logger.info("[notifications_retention] skipped — lock held by another worker")
            return {"skipped": 1, "read": 0, "unread": 0, "critical": 0, "batches": 0}

        out: Dict[str, Any] = {"skipped": 0}
        async with async_session_maker() as db:
            if collapse_duplicates:
                collapsed = await collapse_entity_unread_duplicates(
                    db,
                    batch_size=max(1000, int(settings.notifications_retention_batch_size)),
                    max_batches=max(50, int(settings.notifications_retention_max_batches_per_run)),
                    tenant_id=tenant_id,
                )
                out["collapsed"] = collapsed
            result = await purge_expired_notifications(
                db, tenant_id=tenant_id, max_batches=max_batches
            )
            out.update(result)
            if enforce_caps:
                caps = await enforce_unread_caps_all_users(db)
                out["caps"] = caps
            try:
                await db.commit()
            except Exception:
                await db.rollback()
        return out
