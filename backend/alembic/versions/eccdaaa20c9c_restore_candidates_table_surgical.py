from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "eccdaaa20c9c"
down_revision = "20250912_companies_vacancies_mvp"
branch_labels = None
depends_on = None

def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        row = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:t",
            {"t": table_name},
        ).fetchone()
        return row is not None
    elif dialect == "postgresql":
        row = conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = :t
                """
            ),
            {"t": table_name},
        ).fetchone()
        return row is not None
    else:
        insp = sa.inspect(conn)
        return insp.has_table(table_name)

def upgrade() -> None:
    # Если таблица уже есть — выходим (диалект-агностично)
    if _table_exists("candidates"):
        return

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("short_id", sa.String(length=50), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("languages", sa.Text(), nullable=True),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("manager", sa.String(length=255), nullable=True),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("vacancy_id", sa.String(length=36), nullable=True),
        sa.Column("docs_progress", sa.String(length=32), nullable=True),
        sa.Column("extra", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Индексы, которые у тебя ранее были и которые использует код:
    op.create_index("ix_candidates_tenant_id", "candidates", ["tenant_id"])
    op.create_index("ix_candidates_stage", "candidates", ["stage"])
    op.create_index("ix_candidates_manager", "candidates", ["manager"])
    op.create_index("ix_candidates_company_id", "candidates", ["company_id"])
    op.create_index("ix_candidates_vacancy_id", "candidates", ["vacancy_id"])
    op.create_index("ix_candidates_email", "candidates", ["email"])
    op.create_index("ix_candidates_first_name", "candidates", ["first_name"])
    op.create_index("ix_candidates_last_name", "candidates", ["last_name"])
    op.create_index("ix_candidates_short_id", "candidates", ["short_id"])

def downgrade() -> None:
    op.drop_index("ix_candidates_short_id", table_name="candidates")
    op.drop_index("ix_candidates_last_name", table_name="candidates")
    op.drop_index("ix_candidates_first_name", table_name="candidates")
    op.drop_index("ix_candidates_email", table_name="candidates")
    op.drop_index("ix_candidates_vacancy_id", table_name="candidates")
    op.drop_index("ix_candidates_company_id", table_name="candidates")
    op.drop_index("ix_candidates_manager", table_name="candidates")
    op.drop_index("ix_candidates_stage", table_name="candidates")
    op.drop_index("ix_candidates_tenant_id", table_name="candidates")
    op.drop_table("candidates")