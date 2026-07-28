"""Age-out for the ``notifications`` table.

The bell is a live work surface, not an archive: rows older than their retention
class carry no signal but are paid for on every poll. Without this sweep the table
only ever grows — it reached ~1M rows for a handful of real users in July 2026,
which pinned a CPU core on notification polling.

Three retention classes, matching the partial indexes that already exist on the
table (``ix_notifications_retention_{read,unread,critical}_created``) so each
delete is an index range scan rather than a seq scan:

* read, non-critical   — shortest TTL, the user has already seen them
* unread, non-critical — longer TTL, still unseen but stale
* critical             — longest TTL, audit-relevant

Deletes run in bounded batches so a large backlog is drained over several ticks
instead of locking the table in one long transaction.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except Exception:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def retention_enabled() -> bool:
    return _env_bool("NOTIFICATIONS_RETENTION_ENABLED", True)


def retention_interval_seconds() -> int:
    return _env_int("NOTIFICATIONS_RETENTION_INTERVAL_SECONDS", 3600)


def read_retention_days() -> int:
    return _env_int("NOTIFICATIONS_RETENTION_READ_DAYS", 30)


def unread_retention_days() -> int:
    return _env_int("NOTIFICATIONS_RETENTION_UNREAD_DAYS", 90)


def critical_retention_days() -> int:
    return _env_int("NOTIFICATIONS_RETENTION_CRITICAL_DAYS", 180)


def retention_batch_limit() -> int:
    return _env_int("NOTIFICATIONS_RETENTION_BATCH", 5000)


# Mirrors the partial-index predicates verbatim so the planner can use them.
_NON_CRITICAL = "(priority IS NULL OR priority <> 'critical')"

_CLASSES: tuple[tuple[str, str], ...] = (
    ("read", f"is_read = true AND {_NON_CRITICAL}"),
    ("unread", f"is_read = false AND {_NON_CRITICAL}"),
    ("critical", "priority = 'critical'"),
)


def _cutoffs(now: datetime) -> Dict[str, datetime]:
    return {
        "read": now - timedelta(days=read_retention_days()),
        "unread": now - timedelta(days=unread_retention_days()),
        "critical": now - timedelta(days=critical_retention_days()),
    }


async def purge_expired_notifications(
    db: AsyncSession,
    *,
    tenant_id: str,
    now: datetime | None = None,
    batch_limit: int | None = None,
) -> Dict[str, int]:
    """Delete notifications past their retention class for one tenant.

    Returns per-class delete counts plus a ``total``. Bounded by ``batch_limit``
    per class; leftovers are picked up on the next run.
    """
    now_utc = now or datetime.now(timezone.utc)
    limit = int(batch_limit or retention_batch_limit())
    cutoffs = _cutoffs(now_utc)
    stats: Dict[str, int] = {"total": 0}

    for label, predicate in _CLASSES:
        cutoff = cutoffs[label]
        # Select the victim ids first: DELETE ... LIMIT is not valid in Postgres,
        # and an unbounded DELETE on a large backlog would hold locks far too long.
        result = await db.execute(
            sa.text(
                f"""
                DELETE FROM notifications
                WHERE id IN (
                    SELECT id FROM notifications
                    WHERE tenant_id = :tenant_id
                      AND created_at < :cutoff
                      AND {predicate}
                    ORDER BY created_at
                    LIMIT :limit
                )
                """
            ),
            {"tenant_id": tenant_id, "cutoff": cutoff, "limit": limit},
        )
        deleted = int(result.rowcount or 0)
        stats[label] = deleted
        stats["total"] += deleted

    if stats["total"]:
        logger.info(
            "[notification-retention] tenant=%s purged=%s read=%s unread=%s critical=%s",
            tenant_id,
            stats["total"],
            stats.get("read", 0),
            stats.get("unread", 0),
            stats.get("critical", 0),
        )
    return stats
