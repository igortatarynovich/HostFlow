from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f0babdeb1fc7"
down_revision = "26fdae625994"  # если текущий head другой — подставь его
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("candidates")}
    if "phone_country_code" in columns:
        return
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.add_column(sa.Column("phone_country_code", sa.String(length=8), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("candidates")}
    if "phone_country_code" not in columns:
        return
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_column("phone_country_code")
