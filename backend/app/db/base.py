from __future__ import annotations

import sys as _sys

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


# Under the uvicorn /app/backend → /app symlink, `app.db.base` and
# `backend.app.db.base` can otherwise become two module objects (two Bases).
# Collapse them BEFORE any model import so FKs across absolute/relative imports
# resolve (e.g. lead_questionnaire_invites.lead_id → leads).
_this_base_module = _sys.modules[__name__]
_db_pkg = _sys.modules.get(__name__.rsplit(".", 1)[0])  # app.db or backend.app.db
if __name__ == "app.db.base":
    if _db_pkg is not None:
        _sys.modules.setdefault("backend.app.db", _db_pkg)
    _sys.modules.setdefault("backend.app.db.base", _this_base_module)
elif __name__ == "backend.app.db.base":
    if _db_pkg is not None:
        _sys.modules.setdefault("app.db", _db_pkg)
    _sys.modules.setdefault("app.db.base", _this_base_module)


# Подтягиваем модели, чтобы Alembic видел таблицы через Base.metadata
try:
    # Если модели разложены по пакету app/models, не трогаем
    from app import models  # noqa: F401
except Exception:
    # На раннем этапе можно игнорировать; когда модели появятся — импорт пройдёт
    pass
