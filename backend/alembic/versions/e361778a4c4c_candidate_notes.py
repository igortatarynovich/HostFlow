from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

# revision identifiers, used by Alembic.
revision = "e361778a4c4c"
down_revision = "fe5d16892956"  # поставь свой предыдущий head, если другой
branch_labels = None
depends_on = None

def _is_sqlite() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", "") == "sqlite"

def upgrade():
    if _is_sqlite():
        # SQLite: без EXTENSION/RLS, UUID v4 как TEXT по выражению
        op.create_table(
            "candidate_notes",
            sa.Column("id", sa.String(36), primary_key=True),
            # NOTE: SQLite не поддерживает сложные DEFAULT‑выражения; UUID генерируется на уровне приложения
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("candidate_id", sa.String(36), nullable=False),
            sa.Column("author_id", sa.String(36), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("visibility", sa.String(16), nullable=False, server_default="internal"),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("idx_notes_candidate", "candidate_notes", ["candidate_id"])
    else:
        # PostgreSQL: расширение и RLS
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        bind = op.get_bind()
        insp = sa.inspect(bind)

        def _sa_type_for(table: str, column: str):
            cols = {c["name"]: c for c in insp.get_columns(table)}
            col = cols.get(column)
            if not col:
                # Fallback to UUID if not found
                return psql.UUID(as_uuid=False)
            t = col["type"]
            t_str = str(t).lower()
            # UUID
            if "uuid" in t_str:
                return psql.UUID(as_uuid=False)
            # character varying / varchar
            if hasattr(t, "length"):
                return sa.String(getattr(t, "length", None))
            if "character varying" in t_str or "varchar" in t_str:
                return sa.String(getattr(t, "length", None))
            # text
            if "text" in t_str:
                return sa.Text()
            # default fallback
            return sa.String(getattr(t, "length", None))

        # Determine types to match referenced tables
        candidate_id_type = _sa_type_for("candidates", "id")
        author_id_type = _sa_type_for("users", "id")
        # tenant_id may come from tenants table; if missing, keep UUID fallback
        try:
            tenant_id_type = _sa_type_for("tenants", "id")
        except Exception:
            tenant_id_type = psql.UUID(as_uuid=False)
        op.create_table(
            "candidate_notes",
            sa.Column("id", psql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", tenant_id_type, nullable=False),
            sa.Column("candidate_id", candidate_id_type, nullable=False),
            sa.Column("author_id", author_id_type, nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("visibility", sa.String(16), nullable=False, server_default="internal"),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        )
        op.create_index("idx_notes_candidate", "candidate_notes", ["candidate_id"])
        op.execute("ALTER TABLE candidate_notes ENABLE ROW LEVEL SECURITY;")
        # Build policy condition that matches the actual tenant_id column type
        is_tenant_uuid = "uuid" in str(tenant_id_type).lower()
        policy_using = (
            "tenant_id = current_setting('app.tenant_id')::uuid"
            if is_tenant_uuid
            else "tenant_id = current_setting('app.tenant_id')"
        )

        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = current_schema()
                      AND tablename = 'candidate_notes'
                      AND policyname = 'rls_notes_tenant'
                ) THEN
                    CREATE POLICY rls_notes_tenant ON candidate_notes
                    USING ({policy_using});
                END IF;
            END $$;
            """
        )

def downgrade():
    if not _is_sqlite():
        op.execute("DROP POLICY IF EXISTS rls_notes_tenant ON candidate_notes;")
        op.execute("ALTER TABLE candidate_notes DISABLE ROW LEVEL SECURITY;")
    op.drop_index("idx_notes_candidate", table_name="candidate_notes")
    op.drop_table("candidate_notes")