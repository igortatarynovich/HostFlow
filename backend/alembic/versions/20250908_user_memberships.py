import sqlalchemy as sa
from alembic import op

revision = "20250908_user_memberships"
down_revision = "20250906_users_ts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "tenant_id", name="uq_user_memberships_user_tenant"
        ),
    )
    op.create_index("ix_user_memberships_user", "user_memberships", ["user_id"])
    op.create_index("ix_user_memberships_tenant", "user_memberships", ["tenant_id"])


def downgrade():
    op.drop_index("ix_user_memberships_tenant", table_name="user_memberships")
    op.drop_index("ix_user_memberships_user", table_name="user_memberships")
    op.drop_table("user_memberships")
