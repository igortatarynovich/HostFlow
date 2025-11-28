"""Normalize candidate_vacancy.status to new pipeline + indexes"""

import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision: str = "20250902_pipeline_scale"
down_revision: str = "cd530c0f2042"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _ensure_index(conn, table: str, name: str, columns: list[str]) -> None:
    insp = sa.inspect(conn)
    # SQLite умеет IF NOT EXISTS, для остальных — проверяем по списку индексов
    if conn.dialect.name == "sqlite":
        cols_sql = ", ".join(columns)
        conn.execute(
            sa.text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols_sql})")
        )
    else:
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, columns)


def upgrade() -> None:
    conn = op.get_bind()

    # Если таблицы нет (например, чистая БД) — выходим тихо
    if not _table_exists(conn, "candidate_vacancy"):
        return

    # Нормализация старых статусов в новую шкалу
    conn.execute(
        sa.text(
            """
            UPDATE candidate_vacancy
            SET status = CASE lower(status)
              WHEN 'applied'   THEN 'new'
              WHEN 'screening' THEN 'interview'
              WHEN 'interview' THEN 'interview'
              WHEN 'offer'     THEN 'hiring'
              WHEN 'hired'     THEN 'employed'
              WHEN 'rejected'  THEN 'rejected'
              ELSE 'new'
            END
            """
        )
    )

    # Индексы под пайплайн и выборки
    _ensure_index(
        conn,
        "candidate_vacancy",
        "ix_cv_tenant_vacancy_status",
        ["tenant_id", "vacancy_id", "status"],
    )
    _ensure_index(
        conn,
        "candidate_vacancy",
        "ix_cv_tenant_candidate",
        ["tenant_id", "candidate_id"],
    )
    _ensure_index(conn, "candidate_vacancy", "ix_cv_updated_at", ["updated_at"])


def downgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "candidate_vacancy"):
        return

    # Откатываем к ближайшему «старому» виду (минимально необходимо)
    conn.execute(
        sa.text(
            """
            UPDATE candidate_vacancy
            SET status = CASE lower(status)
              WHEN 'new'        THEN 'applied'
              WHEN 'interview'  THEN 'interview'
              WHEN 'hiring'     THEN 'offer'
              WHEN 'employed'   THEN 'hired'
              WHEN 'rejected'   THEN 'rejected'
              WHEN 'probation'  THEN 'hired'
              ELSE 'applied'
            END
            """
        )
    )

    # Индексы можно не трогать — они безвредны. Если нужно — раскомментируй:
    # for name in ("ix_cv_tenant_vacancy_status", "ix_cv_tenant_candidate", "ix_cv_updated_at"):
    #     try:
    #         op.drop_index(name, table_name="candidate_vacancy")
    #     except Exception:
    #         pass
