try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Базовый класс для всех моделей."""

except ImportError:  # pragma: no cover - SQLAlchemy < 2.0 compatibility
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()
