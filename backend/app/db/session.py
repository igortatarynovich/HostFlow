from __future__ import annotations

from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
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

# 2) Создаём движок на ЭТОМ URL (без каких-либо маскировок)
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    future=True,
    echo=False,
    pool_pre_ping=False,
    poolclass=NullPool,
)

# 3) Фабрика сессий
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# 4) Лог — только маскируем вывод, НЕ исходный URL
try:
    u = make_url(ASYNC_DATABASE_URL)
    safe = u.set(password="***") if u.password else u
    print(f"[db] Using async engine: {safe.render_as_string(hide_password=False)}")
except Exception:
    pass

__all__ = ["engine", "async_session_maker", "ASYNC_DATABASE_URL"]
