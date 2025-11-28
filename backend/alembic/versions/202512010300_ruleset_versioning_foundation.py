"""Ruleset versioning foundation fields and metadata.

Revision ID: 202512010300_ruleset_versioning_foundation
Revises: 202512010200_admin_v2
Create Date: 2025-12-01 12:00:00.000000
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "202512010300_ruleset_versioning_foundation"
down_revision = "202512010200_admin_v2"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _table_exists(conn: Connection, name: str) -> bool:
    if conn.dialect.name == "sqlite":
        res = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        return res is not None
    insp = sa.inspect(conn)
    return insp.has_table(name)


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


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if _table_exists(conn, "document_ruleset_versions"):
        op.add_column(
            "document_ruleset_versions",
            sa.Column("signature", sa.String(length=128), nullable=True),
        )
        op.add_column(
            "document_ruleset_versions",
            sa.Column("origin_version_id", sa.String(length=36), nullable=True),
        )
        op.add_column(
            "document_ruleset_versions",
            sa.Column("rollback_comment", sa.Text(), nullable=True),
        )
        if dialect != "sqlite":
            op.create_foreign_key(
                "fk_document_ruleset_versions_origin",
                "document_ruleset_versions",
                "document_ruleset_versions",
                ["origin_version_id"],
                ["id"],
                ondelete="SET NULL",
            )

        metadata = sa.MetaData()
        versions = sa.Table(
            "document_ruleset_versions",
            metadata,
            autoload_with=conn,
        )
        rows = conn.execute(
            sa.select(
                versions.c.id,
                versions.c.tenant_id,
                versions.c.version,
                versions.c.json_data,
                versions.c.comment,
            )
        ).all()
        for row in rows:
            signature = _compute_signature(
                tenant_id=str(row.tenant_id),
                version=int(row.version),
                json_data=row.json_data,
                comment=row.comment,
            )
            conn.execute(
                versions.update()
                .where(versions.c.id == row.id)
                .values(signature=signature)
            )
        sig_default = sa.text("''")
        op.alter_column(
            "document_ruleset_versions",
            "signature",
            existing_type=sa.String(length=128),
            nullable=False,
            server_default=sig_default,
        )

    if _table_exists(conn, "document_ruleset_usage"):
        op.add_column(
            "document_ruleset_usage",
            sa.Column("metadata", sa.JSON(), nullable=True),
        )
        metadata = sa.MetaData()
        usage_table = sa.Table(
            "document_ruleset_usage",
            metadata,
            autoload_with=conn,
        )
        conn.execute(usage_table.update().values(metadata={}))
        json_default = sa.text("'{}'::jsonb") if dialect == "postgresql" else sa.text("'{}'")
        op.alter_column(
            "document_ruleset_usage",
            "metadata",
            existing_type=sa.JSON(),
            nullable=False,
            server_default=json_default,
        )

    if _table_exists(conn, "document_ruleset_diffs"):
        op.add_column(
            "document_ruleset_diffs",
            sa.Column("computed_with", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if _table_exists(conn, "document_ruleset_diffs"):
        op.drop_column("document_ruleset_diffs", "computed_with")

    if _table_exists(conn, "document_ruleset_usage"):
        op.drop_column("document_ruleset_usage", "metadata")

    if _table_exists(conn, "document_ruleset_versions"):
        if dialect != "sqlite":
            op.drop_constraint(
                "fk_document_ruleset_versions_origin",
                "document_ruleset_versions",
                type_="foreignkey",
            )
        op.drop_column("document_ruleset_versions", "rollback_comment")
        op.drop_column("document_ruleset_versions", "origin_version_id")
        op.drop_column("document_ruleset_versions", "signature")
