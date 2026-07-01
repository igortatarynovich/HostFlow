"""Add cost basis fields to services and service items.

Revision ID: 202608110004_services_cost_basis
Revises: 202608110003_company_ownership_fields
Create Date: 2026-08-11 00:04:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202608110004_services_cost_basis"
down_revision: Union[str, Sequence[str], None] = "202608110003_company_ownership_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("services", sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("services", sa.Column("cost_currency", sa.String(length=3), nullable=False, server_default="PLN"))
    op.add_column("service_items", sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("service_items", sa.Column("actual_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("service_items", sa.Column("cost_currency", sa.String(length=3), nullable=False, server_default="PLN"))
    op.add_column("service_items", sa.Column("cost_source", sa.String(length=64), nullable=True))
    op.add_column("service_items", sa.Column("cost_status", sa.String(length=16), nullable=False, server_default="missing"))

    op.alter_column("services", "estimated_cost", server_default=None)
    op.alter_column("services", "cost_currency", server_default=None)
    op.alter_column("service_items", "estimated_cost", server_default=None)
    op.alter_column("service_items", "cost_currency", server_default=None)
    op.alter_column("service_items", "cost_status", server_default=None)


def downgrade() -> None:
    op.drop_column("service_items", "cost_status")
    op.drop_column("service_items", "cost_source")
    op.drop_column("service_items", "cost_currency")
    op.drop_column("service_items", "actual_cost")
    op.drop_column("service_items", "estimated_cost")
    op.drop_column("services", "cost_currency")
    op.drop_column("services", "estimated_cost")
