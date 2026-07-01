"""vacancy required_documents_template_id

Revision ID: 202602080001
Revises: c5b7faf744e5
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602080001"
down_revision: Union[str, Sequence[str], None] = "c5b7faf744e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        columns = [c["name"] for c in insp.get_columns(table)]
    except Exception:
        return False
    return column in columns


def upgrade() -> None:
    if _has_column("vacancies", "required_documents_template_id"):
        return
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    # SQLite: add column without FK (ALTER TABLE in SQLite has limited FK support)
    col = sa.Column("required_documents_template_id", sa.String(36), nullable=True)
    if not is_sqlite:
        col = sa.Column(
            "required_documents_template_id",
            sa.String(36),
            sa.ForeignKey("document_templates.id", ondelete="SET NULL"),
            nullable=True,
        )
    op.add_column("vacancies", col)
    op.create_index(
        op.f("ix_vacancies_required_documents_template_id"),
        "vacancies",
        ["required_documents_template_id"],
        unique=False,
    )


def downgrade() -> None:
    if _has_column("vacancies", "required_documents_template_id"):
        op.drop_index(
            op.f("ix_vacancies_required_documents_template_id"),
            table_name="vacancies",
        )
        op.drop_column("vacancies", "required_documents_template_id")
