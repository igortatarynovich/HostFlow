"""Insert processing_by_hr into driver_ce_default / poltrakt_drivers funnels (profile parity).

Internal HR handoff sets candidate.stage = processing_by_hr; funnel stages must list it
so the card UI does not show stage_not_in_profile for Poltrakt Drivers et al.

Revision ID: 202605060004_funnel_processing_by_hr_stage
Revises: 202605060003_user_role_client_processor
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605060004_funnel_processing_by_hr_stage"
down_revision: Union[str, None] = "202605060003_user_role_client_processor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAGE_CODE = "processing_by_hr"
_LABEL = "Przekazany do działu HR"


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT cp.funnel_id
            FROM candidate_profiles cp
            WHERE cp.code IN ('driver_ce_default', 'poltrakt_drivers')
              AND cp.funnel_id IS NOT NULL
            """
        )
    ).fetchall()
    for (funnel_id,) in rows:
        if not funnel_id:
            continue
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM funnel_stages WHERE funnel_id = :fid AND code = :code LIMIT 1"
            ),
            {"fid": funnel_id, "code": _STAGE_CODE},
        ).scalar()
        if exists:
            continue
        anchor = conn.execute(
            sa.text(
                'SELECT "order" FROM funnel_stages WHERE funnel_id = :fid AND code = :code LIMIT 1'
            ),
            {"fid": funnel_id, "code": "ready_for_handoff"},
        ).fetchone()
        if anchor is None:
            anchor = conn.execute(
                sa.text(
                    'SELECT "order" FROM funnel_stages WHERE funnel_id = :fid AND code = :code LIMIT 1'
                ),
                {"fid": funnel_id, "code": "processing_by_client"},
            ).fetchone()
            if anchor is None:
                continue
            insert_after = max(0, int(anchor[0]) - 1)
        else:
            insert_after = int(anchor[0])
        conn.execute(
            sa.text(
                'UPDATE funnel_stages SET "order" = "order" + 1 WHERE funnel_id = :fid AND "order" > :o'
            ),
            {"fid": funnel_id, "o": insert_after},
        )
        new_id = str(uuid.uuid4())
        new_order = insert_after + 1
        conn.execute(
            sa.text(
                """
                INSERT INTO funnel_stages (
                    id, funnel_id, code, label, system_stage, "order", is_terminal
                )
                VALUES (
                    :id, :fid, :code, :label, 'in_progress', :ord, false
                )
                """
            ),
            {
                "id": new_id,
                "fid": funnel_id,
                "code": _STAGE_CODE,
                "label": _LABEL,
                "ord": new_order,
            },
        )


def downgrade() -> None:
    """No-op: removing a stage risks breaking candidates already at processing_by_hr."""
    pass
