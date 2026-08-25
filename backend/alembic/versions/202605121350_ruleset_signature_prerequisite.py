"""Ensure document_ruleset_versions.signature exists before baseline backfill.

Revision ID: 202605121350_ruleset_signature_prerequisite
Revises: 202605140900_ch_snap
Create Date: 2026-07-13

Parallel migration branch (candidate-handoff / HR) forked before
202512010300_ruleset_versioning_foundation. Baseline backfill requires
signature column; this revision restores the canonical column order:
    create signature → backfill existing rows → NOT NULL constraint.

Idempotent: if the column already exists, still backfills NULL/empty/mismatched
signatures and enforces NOT NULL when the column remains nullable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "202605121350_ruleset_signature_prerequisite"
down_revision: Union[str, None] = "202605140900_ch_snap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn: Connection, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _column_nullable(conn: Connection, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return True
    for col in insp.get_columns(table):
        if col["name"] == column:
            return bool(col.get("nullable", True))
    return True


def _fk_exists(conn: Connection, table: str, fk_name: str) -> bool:
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return False
    return any(fk.get("name") == fk_name for fk in insp.get_foreign_keys(table))


def _normalize_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {"__raw__": raw}
    return {}


def _compute_signature(tenant_id: str, version: int, json_data: Any, comment: str | None) -> str:
    payload = {
        "tenant_id": tenant_id,
        "version": version,
        "ruleset": _normalize_payload(json_data),
    }
    if comment:
        payload["comment"] = comment
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _ensure_auxiliary_columns(conn: Connection, dialect: str) -> None:
    if not _column_exists(conn, "document_ruleset_versions", "origin_version_id"):
        op.add_column(
            "document_ruleset_versions",
            sa.Column("origin_version_id", sa.String(length=36), nullable=True),
        )
    if not _column_exists(conn, "document_ruleset_versions", "rollback_comment"):
        op.add_column(
            "document_ruleset_versions",
            sa.Column("rollback_comment", sa.Text(), nullable=True),
        )
    if dialect != "sqlite" and not _fk_exists(
        conn, "document_ruleset_versions", "fk_document_ruleset_versions_origin"
    ):
        op.create_foreign_key(
            "fk_document_ruleset_versions_origin",
            "document_ruleset_versions",
            "document_ruleset_versions",
            ["origin_version_id"],
            ["id"],
            ondelete="SET NULL",
        )


def _backfill_signatures(conn: Connection) -> None:
    metadata = sa.MetaData()
    versions = sa.Table("document_ruleset_versions", metadata, autoload_with=conn)
    rows = conn.execute(
        sa.select(
            versions.c.id,
            versions.c.tenant_id,
            versions.c.version,
            versions.c.json_data,
            versions.c.comment,
            versions.c.signature,
        )
    ).all()
    for row in rows:
        expected = _compute_signature(
            tenant_id=str(row.tenant_id),
            version=int(row.version),
            json_data=row.json_data,
            comment=row.comment,
        )
        current = str(row.signature or "").strip()
        if not current or current != expected:
            conn.execute(
                versions.update().where(versions.c.id == row.id).values(signature=expected)
            )


def _ensure_signature_not_null(conn: Connection) -> None:
    if not _column_exists(conn, "document_ruleset_versions", "signature"):
        return
    if not _column_nullable(conn, "document_ruleset_versions", "signature"):
        return
    op.alter_column(
        "document_ruleset_versions",
        "signature",
        existing_type=sa.String(length=128),
        nullable=False,
        server_default=sa.text("''"),
    )


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if not sa.inspect(conn).has_table("document_ruleset_versions"):
        return

    if not _column_exists(conn, "document_ruleset_versions", "signature"):
        op.add_column(
            "document_ruleset_versions",
            sa.Column("signature", sa.String(length=128), nullable=True),
        )

    _ensure_auxiliary_columns(conn, dialect)
    _backfill_signatures(conn)
    _ensure_signature_not_null(conn)


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if not sa.inspect(conn).has_table("document_ruleset_versions"):
        return
    if not _column_exists(conn, "document_ruleset_versions", "signature"):
        return
    if dialect != "sqlite":
        op.drop_constraint(
            "fk_document_ruleset_versions_origin",
            "document_ruleset_versions",
            type_="foreignkey",
        )
    if _column_exists(conn, "document_ruleset_versions", "rollback_comment"):
        op.drop_column("document_ruleset_versions", "rollback_comment")
    if _column_exists(conn, "document_ruleset_versions", "origin_version_id"):
        op.drop_column("document_ruleset_versions", "origin_version_id")
    op.drop_column("document_ruleset_versions", "signature")
