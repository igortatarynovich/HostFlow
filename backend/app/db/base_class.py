# SQLAlchemy compatibility declarative base
try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Common declarative base for all models."""

except ImportError:  # pragma: no cover - SQLAlchemy < 2.0
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()
