"""funnels company_id + module_key (module-owned pipelines P0 / Recruitment).

Revision ID: 202606300001_funnels_company_module_scope_p0
Revises: 202608240001_document_expiry_notification_events_p2
Create Date: 2026-06-30

Adds nullable company_id and module_key, indexes, and backfills recruitment funnels
per company (reassign when single company; clone when multiple). Legacy tenant-scoped
rows remain for strangler fallback (company_id IS NULL).
"""

from __future__ import annotations

import uuid
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202606300001_funnels_company_module_scope_p0"
down_revision: Union[str, None] = "202608240001_document_expiry_notification_events_p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RECRUITMENT_FUNNEL_TYPES = ("candidate", "lead", "deal")
RECRUITMENT_MODULE_KEY = "recruitment"


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(conn).get_columns(table)}


def _stage_columns(conn: sa.Connection) -> list[str]:
    skip = frozenset({"id", "funnel_id"})
    return [
        c["name"]
        for c in sa.inspect(conn).get_columns("funnel_stages")
        if c["name"] not in skip
    ]


def _clone_funnel_stages(
    conn: sa.Connection,
    *,
    source_funnel_id: str,
    target_funnel_id: str,
) -> None:
    stage_cols = _stage_columns(conn)
    if not stage_cols:
        return
    select_cols = ", ".join(f'"{c}"' if c == "order" else c for c in stage_cols)
    rows = conn.execute(
        sa.text(
            f"""
            SELECT {select_cols}
            FROM funnel_stages
            WHERE funnel_id = :fid
            ORDER BY "order", code
            """
        ),
        {"fid": source_funnel_id},
    ).mappings().all()
    for row in rows:
        payload: dict[str, Any] = dict(row)
        insert_cols = ["id", "funnel_id"] + stage_cols
        placeholders = ", ".join(f":{c}" for c in insert_cols)
        col_list = ", ".join(f'"{c}"' if c == "order" else c for c in insert_cols)
        params: dict[str, Any] = {"id": str(uuid.uuid4()), "funnel_id": target_funnel_id}
        for c in stage_cols:
            params[c] = payload[c]
        conn.execute(
            sa.text(f"INSERT INTO funnel_stages ({col_list}) VALUES ({placeholders})"),
            params,
        )


def _backfill_recruitment_funnels(conn: sa.Connection) -> None:
    if not _has_table(conn, "funnels") or not _has_table(conn, "companies"):
        return

    conn.execute(
        sa.text(
            """
            UPDATE funnels
            SET module_key = :mk
            WHERE type IN ('candidate', 'lead', 'deal')
              AND (module_key IS NULL OR module_key = '')
            """
        ),
        {"mk": RECRUITMENT_MODULE_KEY},
    )

    tenant_rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT tenant_id
            FROM funnels
            WHERE tenant_id IS NOT NULL
              AND tenant_id != 'default'
              AND company_id IS NULL
              AND type IN ('candidate', 'lead', 'deal')
            """
        )
    ).fetchall()

    for (tenant_id,) in tenant_rows:
        if not tenant_id:
            continue
        company_rows = conn.execute(
            sa.text(
                """
                SELECT id
                FROM companies
                WHERE tenant_id = :tid
                  AND COALESCE(is_archived, false) = false
                ORDER BY created_at ASC NULLS LAST, id ASC
                """
            ),
            {"tid": tenant_id},
        ).fetchall()
        company_ids = [str(r[0]) for r in company_rows if r and r[0]]
        if not company_ids:
            continue

        legacy_funnels = conn.execute(
            sa.text(
                """
                SELECT id, type, name, is_default
                FROM funnels
                WHERE tenant_id = :tid
                  AND company_id IS NULL
                  AND type IN ('candidate', 'lead', 'deal')
                ORDER BY is_default DESC, name ASC, id ASC
                """
            ),
            {"tid": tenant_id},
        ).fetchall()

        if len(company_ids) == 1:
            cid = company_ids[0]
            conn.execute(
                sa.text(
                    """
                    UPDATE funnels
                    SET company_id = :cid,
                        module_key = COALESCE(module_key, :mk)
                    WHERE tenant_id = :tid
                      AND company_id IS NULL
                      AND type IN ('candidate', 'lead', 'deal')
                    """
                ),
                {"cid": cid, "tid": tenant_id, "mk": RECRUITMENT_MODULE_KEY},
            )
            continue

        for funnel_id, funnel_type, funnel_name, is_default in legacy_funnels:
            fid = str(funnel_id)
            ftype = str(funnel_type)
            fname = str(funnel_name or "Pipeline")
            for cid in company_ids:
                exists = conn.execute(
                    sa.text(
                        """
                        SELECT 1 FROM funnels
                        WHERE tenant_id = :tid
                          AND company_id = :cid
                          AND module_key = :mk
                          AND type = :ftype
                          AND name = :name
                        LIMIT 1
                        """
                    ),
                    {
                        "tid": tenant_id,
                        "cid": cid,
                        "mk": RECRUITMENT_MODULE_KEY,
                        "ftype": ftype,
                        "name": fname,
                    },
                ).scalar()
                if exists:
                    continue
                new_id = str(uuid.uuid4())
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO funnels (
                            id, tenant_id, company_id, module_key, type, name, is_default
                        ) VALUES (
                            :id, :tid, :cid, :mk, :ftype, :name, :is_default
                        )
                        """
                    ),
                    {
                        "id": new_id,
                        "tid": tenant_id,
                        "cid": cid,
                        "mk": RECRUITMENT_MODULE_KEY,
                        "ftype": ftype,
                        "name": fname,
                        "is_default": bool(is_default),
                    },
                )
                _clone_funnel_stages(conn, source_funnel_id=fid, target_funnel_id=new_id)


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "funnels"):
        return

    if not _has_column(conn, "funnels", "company_id"):
        op.add_column(
            "funnels",
            sa.Column(
                "company_id",
                sa.String(length=36),
                sa.ForeignKey("companies.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
    if not _has_column(conn, "funnels", "module_key"):
        op.add_column(
            "funnels",
            sa.Column("module_key", sa.String(length=32), nullable=True),
        )

    for idx_name, cols in (
        ("ix_funnels_tenant_company_module", ["tenant_id", "company_id", "module_key"]),
        ("ix_funnels_tenant_module_type", ["tenant_id", "module_key", "type"]),
        ("ix_funnels_company_id", ["company_id"]),
    ):
        try:
            op.create_index(idx_name, "funnels", cols, unique=False)
        except Exception:
            pass

    _backfill_recruitment_funnels(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "funnels"):
        return

    cloned = conn.execute(
        sa.text(
            """
            SELECT f1.id
            FROM funnels f1
            JOIN funnels f2
              ON f2.tenant_id = f1.tenant_id
             AND f2.type = f1.type
             AND f2.name = f1.name
             AND f2.company_id IS NULL
             AND f1.company_id IS NOT NULL
            """
        )
    ).fetchall()
    for (fid,) in cloned:
        conn.execute(sa.text("DELETE FROM funnels WHERE id = :id"), {"id": str(fid)})

    for idx in (
        "ix_funnels_company_id",
        "ix_funnels_tenant_module_type",
        "ix_funnels_tenant_company_module",
    ):
        try:
            op.drop_index(idx, table_name="funnels")
        except Exception:
            pass

    if _has_column(conn, "funnels", "module_key"):
        op.drop_column("funnels", "module_key")
    if _has_column(conn, "funnels", "company_id"):
        op.drop_column("funnels", "company_id")
