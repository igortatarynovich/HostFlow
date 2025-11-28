from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "20251020_create_reminders_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # если таблица уже есть — выходим (PostgreSQL-safe)
    exists = conn.exec_driver_sql(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = %s
        """,
        ("user_memberships",),
    ).scalar()
    if exists:
        return

    op.create_table(
        "user_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_um_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_um_tenant", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_um_user_tenant"),
    )
    op.create_index("ix_user_memberships_user", "user_memberships", ["user_id"])
    op.create_index("ix_user_memberships_tenant", "user_memberships", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_user_memberships_tenant", table_name="user_memberships")
    op.drop_index("ix_user_memberships_user", table_name="user_memberships")
    op.drop_table("user_memberships")
