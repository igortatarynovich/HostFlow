"""Ensure ``hostflow_simple_tsvector`` exists on PostgreSQL (GIN-safe FTS helper).

Alembic migration ``202603291700`` creates the same function and indexes; this
lifespan hook keeps dev/test DBs aligned with code when migrations lag.

Uses the app's async engine (same URL as API queries), not a separate sync URL.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine.url import make_url

logger = logging.getLogger(__name__)

_CREATE_HOSTFLOW_SIMPLE_TSVECTOR = """
CREATE OR REPLACE FUNCTION hostflow_simple_tsvector(content text)
RETURNS tsvector
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $f$
  SELECT to_tsvector('pg_catalog.simple'::regconfig, COALESCE(content, ''));
$f$
"""


async def ensure_global_search_fts_function_async() -> None:
    try:
        from backend.app.db.session import engine
    except Exception as exc:
        logger.debug("ensure_global_search_fts_function_async: skip imports (%s)", exc)
        return

    try:
        url = make_url(engine.url)
        if not str(url.drivername).startswith("postgresql"):
            return
    except Exception:
        return

    try:
        async with engine.begin() as conn:
            await conn.execute(text(_CREATE_HOSTFLOW_SIMPLE_TSVECTOR))
        logger.info("[global_search_fts] ensured hostflow_simple_tsvector() on PostgreSQL")
    except Exception as exc:
        logger.warning("[global_search_fts] ensure hostflow_simple_tsvector skipped (%s)", exc)
