"""tenant_lead_forms.public_slug — public intake binding (optional per form).

Revision ID: 202603301301_tlf_public_slug
Revises: 202603301200_tenant_lead_forms
Create Date: 2026-03-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "202603301301_tlf_public_slug"
down_revision: Union[str, None] = "202603301200_tenant_lead_forms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "tenant_lead_forms" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tenant_lead_forms")}
    if "public_slug" not in cols:
        op.add_column("tenant_lead_forms", sa.Column("public_slug", sa.String(length=64), nullable=True))
    existing_uq = {c["name"] for c in insp.get_unique_constraints("tenant_lead_forms")}
    if "uq_tenant_lead_forms_tenant_public_slug" not in existing_uq:
        op.create_unique_constraint(
            "uq_tenant_lead_forms_tenant_public_slug",
            "tenant_lead_forms",
            ["tenant_id", "public_slug"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "tenant_lead_forms" not in insp.get_table_names():
        return
    existing_uq = {c["name"] for c in insp.get_unique_constraints("tenant_lead_forms")}
    if "uq_tenant_lead_forms_tenant_public_slug" in existing_uq:
        op.drop_constraint("uq_tenant_lead_forms_tenant_public_slug", "tenant_lead_forms", type_="unique")
    cols = {c["name"] for c in insp.get_columns("tenant_lead_forms")}
    if "public_slug" in cols:
        op.drop_column("tenant_lead_forms", "public_slug")
