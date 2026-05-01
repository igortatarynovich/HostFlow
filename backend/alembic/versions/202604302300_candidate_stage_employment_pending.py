"""Candidate funnels: insert stage employment_pending immediately before employed.

Revision ID: 202604302300_candidate_stage_employment_pending
Revises: 202604301600_merge_doc_tpl
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302300_candidate_stage_employment_pending"
down_revision: Union[str, None] = "202604301600_merge_doc_tpl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DEFAULT_LABEL = "На трудоустройстве"


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("""
            SELECT fs.funnel_id, fs."order" AS emp_order
            FROM funnel_stages fs
            INNER JOIN funnels f ON f.id = fs.funnel_id
            WHERE f.type = 'candidate' AND lower(fs.code) = 'employed'
        """)
    ).fetchall()

    for funnel_id, emp_order in rows:
        exists = bind.execute(
            sa.text("""
                SELECT 1 FROM funnel_stages
                WHERE funnel_id = :fid AND lower(code) = 'employment_pending'
                LIMIT 1
            """),
            {"fid": funnel_id},
        ).scalar()
        if exists:
            continue

        bind.execute(
            sa.text("""
                UPDATE funnel_stages
                SET "order" = "order" + 1
                WHERE funnel_id = :fid AND "order" >= :o
            """),
            {"fid": funnel_id, "o": emp_order},
        )
        bind.execute(
            sa.text("""
                INSERT INTO funnel_stages (
                    id, funnel_id, code, label, system_stage, "order", is_terminal,
                    stage_contract_v1, conversion_root_v1
                )
                VALUES (
                    :id, :fid, 'employment_pending', :label, 'in_progress', :ord, false,
                    NULL, NULL
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "fid": funnel_id,
                "label": _DEFAULT_LABEL,
                "ord": emp_order,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    pending = bind.execute(
        sa.text(
            """
            SELECT funnel_id, "order" AS o
            FROM funnel_stages
            WHERE lower(code) = 'employment_pending'
            """
        )
    ).fetchall()

    for funnel_id, ord_val in pending:
        bind.execute(
            sa.text("DELETE FROM funnel_stages WHERE funnel_id = :fid AND lower(code) = 'employment_pending'"),
            {"fid": funnel_id},
        )
        bind.execute(
            sa.text("""
                UPDATE funnel_stages
                SET "order" = "order" - 1
                WHERE funnel_id = :fid AND "order" > :o
            """),
            {"fid": funnel_id, "o": ord_val},
        )
