"""Startup invariant for the Activity & Notification Operating Layer.

Verifies — at FastAPI lifespan startup — that the database is in **one
of two consistent states**:

    A) Pre-Phase-1.3 (legacy):
       - ``reminders`` is a TABLE
       - ``activities`` does not exist (or is also a TABLE during a
         Phase 1.3 rollout in progress, which is briefly possible
         between transactions A and B of the migration; we accept it
         and let the migration finish on the next deploy).
       The ORM is currently mapped to ``__tablename__ = "activities"``,
       so when running on a legacy DB the app would 500-fail every
       query — we abort startup loudly with an actionable error.

    B) Post-Phase-1.3 (canonical):
       - ``activities`` is a TABLE
       - ``reminders`` is a VIEW (or absent — the compat-view drop in
         Phase 4 cleanup is a follow-up).
       This is the steady state. The ORM works.

Anything else (``activities`` is a VIEW, both ``reminders`` and
``activities`` are tables, schema half-renamed) is flagged as a fatal
inconsistency. The check exits the container with a clear error rather
than serving traffic against an incoherent schema.

See ``docs/specs/architecture/phase-1-3-activity-layer-v1-migration-plan.md``
§15.1 *Deploy mechanics — startup-check*.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text

logger = logging.getLogger(__name__)


def _async_url_to_sync(url: str) -> str:
    """Best-effort conversion of an async DSN to its sync counterpart."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    return url


def _classify_object(conn, name: str) -> str:
    """Return one of ``'table' | 'view' | 'absent'`` for ``name``."""
    dialect = conn.dialect.name
    if dialect == "postgresql":
        row = conn.execute(
            text(
                "SELECT relkind FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = :n AND n.nspname = 'public'"
            ),
            {"n": name},
        ).first()
        if row is None:
            return "absent"
        kind = row[0]
        if kind in ("r", "p"):
            return "table"
        if kind == "v":
            return "view"
        return "other"
    if dialect == "sqlite":
        row = conn.execute(
            text("SELECT type FROM sqlite_master WHERE name = :n"),
            {"n": name},
        ).first()
        if row is None:
            return "absent"
        return row[0]
    insp = inspect(conn)
    if name in set(insp.get_table_names()):
        return "table"
    if name in set(insp.get_view_names()):
        return "view"
    return "absent"


def _is_canonical(states: dict[str, str]) -> bool:
    return (
        states["activities"] == "table"
        and states["activity_events"] == "table"
        and states["notifications"] == "table"
        and states["reminders"] in ("view", "absent")
        and states["reminder_events"] in ("view", "absent")
        and states["user_notifications"] in ("view", "absent")
    )


def _is_legacy(states: dict[str, str]) -> bool:
    return (
        states["reminders"] == "table"
        and states["reminder_events"] == "table"
        and states["user_notifications"] == "table"
        and states["activities"] == "absent"
        and states["activity_events"] == "absent"
        and states["notifications"] == "absent"
    )


_ACTIVITY_OBJECTS = (
    "activities",
    "activity_events",
    "notifications",
    "reminders",
    "reminder_events",
    "user_notifications",
)


def check_activity_layer_v1_state(strict: bool | None = None) -> dict[str, str]:
    """Inspect the DB and return the state map (also logs at INFO).

    When ``strict=True`` (or when ``ENFORCE_ACTIVITY_LAYER_V1_INVARIANT=1``
    is set in the environment), an inconsistent intermediate state
    raises :class:`RuntimeError` so the container exits before serving
    traffic. The default ``strict=None`` reads the environment.
    """

    if strict is None:
        strict = bool(int(os.environ.get("ENFORCE_ACTIVITY_LAYER_V1_INVARIANT", "0")))

    try:
        from backend.app.core.settings import settings
    except Exception as exc:
        logger.warning("[startup:activity_layer_v1] settings unavailable (%s)", exc)
        return {}

    sync_url = (
        os.environ.get("ALEMBIC_DATABASE_URL")
        or os.environ.get("SYNC_DATABASE_URL")
        or _async_url_to_sync(str(getattr(settings, "ASYNC_DATABASE_URL", "") or ""))
    )
    if not sync_url:
        logger.warning("[startup:activity_layer_v1] no DB URL — skipping check")
        return {}

    states: dict[str, str] = {}
    try:
        engine = create_engine(sync_url, future=True)
        with engine.connect() as conn:
            for name in _ACTIVITY_OBJECTS:
                states[name] = _classify_object(conn, name)
        engine.dispose()
    except Exception as exc:
        logger.warning(
            "[startup:activity_layer_v1] state probe failed (%s) — assuming pre-Phase-1.0",
            exc,
        )
        return {}

    logger.info("[startup:activity_layer_v1] state map: %s", states)

    if _is_canonical(states):
        logger.info("[startup:activity_layer_v1] canonical schema — OK (Phase 1.3 applied)")
        return states

    if _is_legacy(states):
        msg = (
            "[startup:activity_layer_v1] legacy schema detected (reminders/user_notifications "
            "as TABLE, activities/notifications absent). The current code runs against the "
            "canonical schema (`__tablename__ = 'activities'`). Apply the "
            "`activity_layer_v1` Alembic revision before serving traffic. See "
            "docs/specs/architecture/phase-1-3-activity-layer-v1-migration-plan.md §15.1."
        )
        logger.error(msg)
        if strict:
            raise RuntimeError(msg)
        return states

    msg = (
        f"[startup:activity_layer_v1] inconsistent schema state: {states}. "
        "Neither pre-Phase-1.3 (legacy) nor canonical. This typically means a "
        "previous migration crashed half-way. Inspect manually before serving "
        "traffic. See docs/specs/architecture/phase-1-3-activity-layer-v1-migration-plan.md §15.1."
    )
    logger.error(msg)
    if strict:
        raise RuntimeError(msg)
    return states


__all__ = ["check_activity_layer_v1_state"]
