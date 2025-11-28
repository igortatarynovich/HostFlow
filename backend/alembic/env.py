from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path
import logging

from alembic import context
from sqlalchemy import create_engine, pool, String

# backend/alembic/env.py



# --- импорт приложения (для metadata) ---
# Добавляем корень проекта (родитель каталога `backend`) в sys.path,
# чтобы импорт по пути `backend.app...` работал при запуске Alembic
_path_candidates = [
    str(Path(__file__).resolve().parents[2]),  # project root (../../)
    str(Path(__file__).resolve().parents[1]),  # backend/ directory (../)
]
for candidate in _path_candidates:
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

# Alembic Config object
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Метаданные моделей приложения
try:  # noqa: F401
    from backend.app.db.base import Base  # type: ignore
except ModuleNotFoundError:
    from app.db.base import Base  # type: ignore


target_metadata = Base.metadata


def _include_object(object, name, type_, reflected, compare_to):
    """
    Prevent autogenerate from proposing DROP operations (table/index/column)
    when the object is missing from metadata due to partial imports, etc.
    """
    # If object absent in metadata (compare_to is None) and it's not reflected
    # Alembic would normally propose to DROP it. We skip such removals.
    if compare_to is None and not reflected:
        if type_ in {"table", "index", "column"}:
            return False
    return True


def _mask_url(url: str) -> str:
    try:
        # маскируем пароль, если есть, но не трогаем sqlite пути
        if url.startswith("sqlite:"):
            return url
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            creds_host = rest.split("@", 1)
            if len(creds_host) == 2:
                creds, hostpart = creds_host
                if ":" in creds:
                    user = creds.split(":", 1)[0]
                    return f"{scheme}://{user}:***@{hostpart}"
        return url
    except Exception:
        return url


def _effective_sync_url() -> str:
    """
    Return a *sync* PostgreSQL SQLAlchemy URL for Alembic.

    Priority (first non-empty wins):
      1) ALEMBIC_DATABASE_URL
      2) SYNC_DATABASE_URL
      3) DATABASE_URL

    Requirements:
      - Must be PostgreSQL. No SQLite fallback anymore.
      - If an async driver is provided (postgresql+asyncpg), convert it to a sync driver (postgresql+psycopg) for Alembic.
    """
    url = (
        os.getenv("ALEMBIC_DATABASE_URL")
        or os.getenv("SYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )

    if not url:
        raise RuntimeError(
            "[alembic.env] No database URL provided. "
            "Set ALEMBIC_DATABASE_URL or SYNC_DATABASE_URL or DATABASE_URL to a PostgreSQL DSN."
        )

    # Disallow SQLite or any non-Postgres DSN
    if url.startswith("sqlite:"):
        raise RuntimeError(
            "[alembic.env] SQLite DSN is not allowed in this project. Use PostgreSQL."
        )

    # Normalize Postgres drivers for Alembic (sync engine required)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    # Accept bare 'postgresql://' (let SQLAlchemy pick a default sync driver),
    # but prefer explicit psycopg when possible.
    return url


def run_migrations_offline():
    url = _effective_sync_url()
    logger.info("[env] offline migrations using DB: %s", _mask_url(url))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=_include_object,
        version_table_pk_column="version_num",
        version_table_pk_column_type=String(128),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    url = _effective_sync_url()
    logger.info("[env] online migrations using DB: %s", _mask_url(url))
    # создаём движок напрямую, БЕЗ engine_from_config/ini
    connectable = create_engine(url, poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=_include_object,
            version_table_pk_column="version_num",
            version_table_pk_column_type=String(128),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
