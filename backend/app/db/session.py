from __future__ import annotations

import os

from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

try:
    from sqlalchemy.ext.asyncio import async_sessionmaker  # type: ignore
except ImportError:  # pragma: no cover - SQLAlchemy < 2.0 compatibility
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    def async_sessionmaker(*args, **kwargs):  # type: ignore[override]
        return _sessionmaker(*args, **kwargs)

from backend.app.core.settings import settings


def _force_async_driver(url_str: str) -> str:
    """
    Гарантируем async-драйвер, не трогая пароль.
    Никаких str(URL) — только render_as_string(hide_password=False).
    """
    u: URL = make_url(url_str)
    if u.drivername.startswith(("postgres", "postgresql")):
        u = u.set(drivername="postgresql+asyncpg")
    elif u.drivername.startswith("sqlite"):
        u = u.set(drivername="sqlite+aiosqlite")
    return u.render_as_string(hide_password=False)


# 1) Берём реальный async-URL из настроек и принудительно задаём async-драйвер
ASYNC_DATABASE_URL: str = _force_async_driver(settings.ASYNC_DATABASE_URL)

# 2) Создаём движок на ЭТОМ URL (без каких-либо маскировок).
# Для Postgres используем bounded queue pool, чтобы не взрывать число клиентов БД.
_db_url_obj: URL = make_url(ASYNC_DATABASE_URL)
_is_postgres = _db_url_obj.drivername.startswith("postgresql")

_null_pool = os.getenv("HOSTFLOW_SQLALCHEMY_NULL_POOL", "").strip().lower() in ("1", "true", "yes")

if _is_postgres:
    if _null_pool:
        # Pytest / multi-loop: queue pool keeps asyncpg conns tied to a closed loop (GC _cancel warnings).
        engine = create_async_engine(
            ASYNC_DATABASE_URL,
            future=True,
            echo=False,
            pool_pre_ping=False,
            poolclass=NullPool,
        )
    else:
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_POOL_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
        engine = create_async_engine(
            ASYNC_DATABASE_URL,
            future=True,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_use_lifo=True,
        )
else:
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        future=True,
        echo=False,
        pool_pre_ping=False,
        poolclass=NullPool,
    )

from backend.app.db.tenant_session import TenantEnforcingAsyncSession

# 3) Фабрика сессий
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=TenantEnforcingAsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


def _session_local_sync_url() -> str:
    """Bare ``postgresql://`` defaults to psycopg2 in SQLAlchemy; prefer psycopg (v3)."""
    raw = settings.SYNC_DATABASE_URL
    u: URL = make_url(raw)
    d = u.drivername
    if d in ("postgresql", "postgres"):
        return u.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    return raw


# Sync session factory for legacy/unit tests (e.g. TestClient + `.query()`).
# Application code should use ``async_session_maker``.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as _sync_sessionmaker

_sync_engine = create_engine(
    _session_local_sync_url(),
    future=True,
    pool_pre_ping=True,
)
SessionLocal = _sync_sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False, future=True)

# 4) Лог — только маскируем вывод, НЕ исходный URL
try:
    u = make_url(ASYNC_DATABASE_URL)
    safe = u.set(password="***") if u.password else u
    print(f"[db] Using async engine: {safe.render_as_string(hide_password=False)}")
except Exception:
    pass

__all__ = ["engine", "async_session_maker", "ASYNC_DATABASE_URL", "SessionLocal"]
