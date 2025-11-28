from __future__ import annotations

import sqlalchemy.orm as sa_orm

if not hasattr(sa_orm, "Mapped"):  # pragma: no cover - SQLAlchemy < 1.4.30
    from typing import Any

    sa_orm.Mapped = Any  # type: ignore[attr-defined]

if not hasattr(sa_orm, "mapped_column"):  # pragma: no cover
    from sqlalchemy import Column as _LegacyColumn

    def _mapped_column(*args, **kwargs):
        return _LegacyColumn(*args, **kwargs)

    sa_orm.mapped_column = _mapped_column  # type: ignore[attr-defined]

try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """База для всех моделей."""

except ImportError:  # pragma: no cover - SQLAlchemy < 2.0 compatibility
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()



# Подтягиваем модели, чтобы Alembic видел таблицы через Base.metadata
try:
    # Если модели разложены по пакету app/models, не трогаем
    from app import models  # noqa: F401
except Exception:
    # На раннем этапе можно игнорировать; когда модели появятся — импорт пройдёт
    pass
