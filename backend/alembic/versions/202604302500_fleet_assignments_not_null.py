"""Fleet: fleet_assignments NOT NULL alignment (legacy nullable adds from 202604302450).

Revision ID: 202604302500_fleet_assignments_not_null
Revises: 202604302490_workforce_linked_user
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302500_fleet_assignments_not_null"
down_revision: Union[str, None] = "202604302490_workforce_linked_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TBL = "fleet_assignments"

# Match FleetAssignment ORM + TimestampMixin — optional FKs / service_end / notes stay nullable.
_REQUIRED_NOT_NULL = (
    "tenant_id",
    "line_id",
    "vehicle_id",
    "status",
    "service_start",
    "created_at",
    "updated_at",
)


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _column_nullable(bind, table: str, column: str) -> bool | None:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return None
    for c in insp.get_columns(table):
        if c["name"] == column:
            return bool(c.get("nullable", True))
    return None


def upgrade() -> None:
    if not _is_postgres():
        return

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TBL):
        return

    op.execute(
        sa.text(
            f"""
            DELETE FROM {_TBL}
            WHERE tenant_id IS NULL
               OR line_id IS NULL
               OR vehicle_id IS NULL
               OR service_start IS NULL
            """
        )
    )
    op.execute(sa.text(f"UPDATE {_TBL} SET status = COALESCE(status, 'planned') WHERE status IS NULL"))
    op.execute(
        sa.text(f"UPDATE {_TBL} SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL")
    )
    op.execute(
        sa.text(f"UPDATE {_TBL} SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL")
    )

    for col in _REQUIRED_NOT_NULL:
        if _column_nullable(bind, _TBL, col) is not True:
            continue
        op.execute(sa.text(f'ALTER TABLE {_TBL} ALTER COLUMN "{col}" SET NOT NULL'))


def downgrade() -> None:
    if not _is_postgres():
        return

    bind = op.get_bind()
    if not sa.inspect(bind).has_table(_TBL):
        return

    for col in _REQUIRED_NOT_NULL:
        if _column_nullable(bind, _TBL, col) is not False:
            continue
        op.execute(sa.text(f'ALTER TABLE {_TBL} ALTER COLUMN "{col}" DROP NOT NULL'))
