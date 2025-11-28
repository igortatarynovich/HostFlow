"""Add missing company columns for enriched schema

Revision ID: 20251015_companies_extend_schema
Revises: 0e741c3987f5
Create Date: 2025-10-15 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "20251015_companies_extend_schema"
down_revision = "0e741c3987f5"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    try:
        cols = {col["name"] for col in inspector.get_columns(table)}
    except Exception:
        return False
    return column in cols


def _boolean_default(bind) -> sa.sql.elements.TextClause:
    if bind.dialect.name == "postgresql":
        return sa.text("false")
    return sa.text("0")


def upgrade() -> None:
    bind = op.get_bind()

    columns = [
        ("legal_name", sa.String(length=255), None),
        ("tax_id", sa.String(length=64), None),
        ("phone", sa.String(length=64), None),
        ("email", sa.String(length=255), None),
        ("website", sa.String(length=255), None),
        ("notes", sa.String(length=2000), None),
        ("is_archived", sa.Boolean(), _boolean_default(bind)),
        ("country_code", sa.String(length=2), None),
    ]

    for name, col_type, default in columns:
        if not _has_column(bind, "companies", name):
            nullable = False if name == "is_archived" else True
            op.add_column(
                "companies",
                sa.Column(name, col_type, nullable=nullable, server_default=default),
            )


def downgrade() -> None:
    bind = op.get_bind()
    for name in [
        "country_code",
        "is_archived",
        "notes",
        "website",
        "email",
        "phone",
        "tax_id",
        "legal_name",
    ]:
        if _has_column(bind, "companies", name):
            op.drop_column("companies", name)
