"""
PostgreSQL full-text search helpers for GET /search slices.

Uses config ``simple`` (locale-agnostic tokenization) + ``websearch_to_tsquery``
so multi-word queries match across non-adjacent text (e.g. JSON keys), support
quoted phrases, and ``-token`` exclusions — unlike a single ILIKE substring.
Combined with existing ILIKE clauses for IDs and codes.
"""
from __future__ import annotations

from sqlalchemy import Text, bindparam, cast, func
from sqlalchemy.sql.elements import ColumnElement

FTS_CONFIG = "simple"
BIND_GS_FTS_Q = "gs_fts_q"


def fts_vector_from_concat(*parts: ColumnElement) -> ColumnElement:
    """Same tokens as ``to_tsvector('simple', …)`` via DB IMMUTABLE wrapper (GIN-safe)."""
    hay = func.concat_ws(" ", *parts)
    return func.hostflow_simple_tsvector(hay)


def fts_match_and_rank(vec: ColumnElement) -> tuple[ColumnElement, ColumnElement]:
    """``vec @@ websearch_to_tsquery`` and ``ts_rank_cd`` for ordering."""
    tsq = func.websearch_to_tsquery(FTS_CONFIG, bindparam(BIND_GS_FTS_Q))
    return vec.op("@@")(tsq), func.ts_rank_cd(vec, tsq)


def as_text(value: ColumnElement) -> ColumnElement:
    return cast(value, Text)
