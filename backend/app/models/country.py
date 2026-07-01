"""Countries reference (ISO2) for normalization."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Country(Base):
    __tablename__ = "countries"

    iso2: Mapped[str] = mapped_column(String(8), primary_key=True)
    name_pl: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    aliases: Mapped[Optional[dict]] = mapped_column(
        SQLiteJSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
