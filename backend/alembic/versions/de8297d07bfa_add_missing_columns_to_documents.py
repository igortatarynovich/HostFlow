# backend/alembic/versions/<your_new_rev>_add_missing_columns_to_documents.py
from alembic import op
import sqlalchemy as sa

revision = "de8297d07bfa"          # alembic сам подставит
down_revision = "4d006b7dd00e"       # <-- последняя успешная ревизия у тебя
branch_labels = None
depends_on = None

def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return any(col["name"] == column for col in insp.get_columns(table))

def upgrade():
    bind = op.get_bind()

    # список колонок, которых не хватает по логам
    to_add = [
        ("filename", sa.String(length=255)),
        ("path", sa.String(length=512)),
        ("issued_date", sa.Date()),
        ("expires_date", sa.Date()),
        ("extra", sa.Text()),
    ]

    for name, coltype in to_add:
        if not _has_column(bind, "documents", name):
            op.add_column("documents", sa.Column(name, coltype, nullable=True))

def downgrade():
    # Для SQLite безопасный даунгрейд колонки — лишняя возня (DROP COLUMN ограничен).
    # Если очень нужно, можно сделать batch_alter с пересозданием таблицы.
    pass