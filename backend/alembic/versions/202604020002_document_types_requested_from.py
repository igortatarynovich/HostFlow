"""Add requested_from to document_types

Revision ID: 202604020002_document_types_requested_from
Revises: 202604020001_document_type_structured_fields
Create Date: 2026-04-02 13:15:00.000000
"""

from __future__ import annotations

from typing import Dict

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202604020002_document_types_requested_from"
down_revision = "202604020001_document_type_structured_fields"
branch_labels = None
depends_on = None


REQUESTED_FROM_VALUES = ("driver", "employer", "agency")
REQUESTED_FROM_BY_CODE: Dict[str, str] = {
    "work_permit": "agency",
    "driver_certificate": "agency",
}


def _enum_type(dialect_name: str):
    if dialect_name == "postgresql":
        return postgresql.ENUM(
            *REQUESTED_FROM_VALUES,
            name="document_requested_from_enum",
            create_type=False,
        )
    return sa.Enum(
        *REQUESTED_FROM_VALUES,
        name="document_requested_from_enum",
    )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind else "postgresql"
    enum_type = _enum_type(dialect)
    server_default = (
        sa.text("'driver'::document_requested_from_enum")
        if dialect == "postgresql"
        else "driver"
    )

    op.add_column(
        "document_types",
        sa.Column(
            "requested_from",
            enum_type,
            nullable=False,
            server_default=server_default,
        ),
    )

    for code, requested in REQUESTED_FROM_BY_CODE.items():
        bind.execute(
            sa.text(
                "UPDATE document_types SET requested_from = :requested WHERE lower(code) = :code"
            ),
            {"requested": requested, "code": code},
        )

    bind.execute(
        sa.text(
            "UPDATE document_types SET requested_from = 'driver' WHERE requested_from IS NULL"
        )
    )

    op.alter_column("document_types", "requested_from", server_default=None)


def downgrade() -> None:
    op.drop_column("document_types", "requested_from")
