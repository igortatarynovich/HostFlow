"""Cross-dialect ``tsvector``: real TSVECTOR on PostgreSQL, TEXT elsewhere."""
from __future__ import annotations

from sqlalchemy import Text, TypeDecorator
from sqlalchemy.dialects.postgresql import TSVECTOR


class TsVector(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())
