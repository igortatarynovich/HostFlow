from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("SYNC_DATABASE_URL")
    or os.environ.get("ASYNC_DATABASE_URL")
)

if not DATABASE_URL:
    # fallback to local sqlite file at project root
    PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'app.db')}"

# if an async URL was provided, convert it to a sync driver for SQLAlchemy's create_engine
if DATABASE_URL.startswith("sqlite+aiosqlite:"):
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
