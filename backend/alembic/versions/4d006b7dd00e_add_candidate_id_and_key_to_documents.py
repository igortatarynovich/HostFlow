from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4d006b7dd00e"
down_revision = "eb65e8e273bf"  # <-- проверьте, что совпадает с вашей предыдущей ревизией
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("documents")}

    if "candidate_id" not in existing_columns:
        op.add_column("documents", sa.Column("candidate_id", sa.String(length=36), nullable=True))
    if "key" not in existing_columns:
        op.add_column("documents", sa.Column("key", sa.String(length=128), nullable=True))

    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("documents")}
    if "ix_documents_key" not in existing_indexes and any(col["name"] == "key" for col in inspector.get_columns("documents")):
        op.create_index("ix_documents_key", "documents", ["key"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("documents")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("documents")}

    if "ix_documents_key" in existing_indexes:
        op.drop_index("ix_documents_key", table_name="documents")
    if "key" in columns:
        op.drop_column("documents", "key")
    if "candidate_id" in columns:
        op.drop_column("documents", "candidate_id")
