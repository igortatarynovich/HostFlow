"""fix counters: docs_progress (documents) + vacancies.candidates_count) [PostgreSQL version]

This migration replaces SQLite-style JSON/trigger logic with PostgreSQL JSONB + plpgsql trigger functions.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e88ddd40f226"
down_revision: Union[str, None] = "12f82a6782cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1) колонка-счётчик у вакансий (если ещё нет)
    try:
        cols = [c["name"] for c in insp.get_columns("vacancies")]
    except Exception:
        cols = []
    if "candidates_count" not in cols:
        op.add_column("vacancies", sa.Column("candidates_count", sa.Integer(), nullable=True))

    # 2) удалить старые триггеры (PostgreSQL требует указать таблицу)
    if insp.has_table("documents"):
        for trg in [
            "trg_docs_after_insert",
            "trg_docs_after_update",
            "trg_docs_after_delete",
        ]:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON documents")

    if insp.has_table("candidates"):
        for trg in [
            "trg_vac_after_candidate_insert",
            "trg_vac_after_candidate_update",
            "trg_vac_after_candidate_delete",
        ]:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON candidates")

    # 3) Разовый backfill docs_progress из таблицы documents (JSONB)
    conn.exec_driver_sql(
        """
        UPDATE candidates
        SET docs_progress = jsonb_build_object(
            'total',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.deleted_at IS NULL), 0),
            'uploaded',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
            'ready',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.status='ready' AND d.deleted_at IS NULL), 0),
            'submitted',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.status='submitted' AND d.deleted_at IS NULL), 0),
            'planned',    COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.status='planned' AND d.deleted_at IS NULL), 0)
        ),
        updated_at = CURRENT_TIMESTAMP
        """
    )

    # 4) Функция и триггеры для поддержки docs_progress (plpgsql)
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE FUNCTION fn_recalc_candidate_docs_progress() RETURNS trigger AS $$
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                UPDATE candidates
                SET docs_progress = jsonb_build_object(
                    'total',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.deleted_at IS NULL), 0),
                    'uploaded',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
                    'ready',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.status='ready' AND d.deleted_at IS NULL), 0),
                    'submitted',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.status='submitted' AND d.deleted_at IS NULL), 0),
                    'planned',    COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.status='planned' AND d.deleted_at IS NULL), 0)
                ),
                updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.candidate_id;

            ELSIF (TG_OP = 'UPDATE') THEN
                -- пересчитать для нового кандидата
                UPDATE candidates
                SET docs_progress = jsonb_build_object(
                    'total',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.deleted_at IS NULL), 0),
                    'uploaded',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
                    'ready',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.status='ready' AND d.deleted_at IS NULL), 0),
                    'submitted',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.status='submitted' AND d.deleted_at IS NULL), 0),
                    'planned',    COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = NEW.candidate_id AND d.status='planned' AND d.deleted_at IS NULL), 0)
                ),
                updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.candidate_id;

                -- если кандидат поменялся, пересчитаем и для старого
                IF (NEW.candidate_id IS DISTINCT FROM OLD.candidate_id) THEN
                    UPDATE candidates
                    SET docs_progress = jsonb_build_object(
                        'total',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.deleted_at IS NULL), 0),
                        'uploaded',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
                        'ready',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.status='ready' AND d.deleted_at IS NULL), 0),
                        'submitted',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.status='submitted' AND d.deleted_at IS NULL), 0),
                        'planned',    COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.status='planned' AND d.deleted_at IS NULL), 0)
                    ),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = OLD.candidate_id;
                END IF;

            ELSIF (TG_OP = 'DELETE') THEN
                UPDATE candidates
                SET docs_progress = jsonb_build_object(
                    'total',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.deleted_at IS NULL), 0),
                    'uploaded',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
                    'ready',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.status='ready' AND d.deleted_at IS NULL), 0),
                    'submitted',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.status='submitted' AND d.deleted_at IS NULL), 0),
                    'planned',    COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = OLD.candidate_id AND d.status='planned' AND d.deleted_at IS NULL), 0)
                ),
                updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.candidate_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    conn.exec_driver_sql(
        """
        CREATE TRIGGER trg_docs_after_insert
        AFTER INSERT ON documents
        FOR EACH ROW
        EXECUTE FUNCTION fn_recalc_candidate_docs_progress();
        """
    )

    conn.exec_driver_sql(
        """
        CREATE TRIGGER trg_docs_after_update
        AFTER UPDATE OF status, filename, deleted_at, candidate_id ON documents
        FOR EACH ROW
        EXECUTE FUNCTION fn_recalc_candidate_docs_progress();
        """
    )

    conn.exec_driver_sql(
        """
        CREATE TRIGGER trg_docs_after_delete
        AFTER DELETE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION fn_recalc_candidate_docs_progress();
        """
    )

    # 5) Разовый пересчёт vacancies.candidates_count
    conn.exec_driver_sql(
        """
        UPDATE vacancies
        SET candidates_count = COALESCE((
            SELECT COUNT(*) FROM candidates c
            WHERE c.vacancy_id = vacancies.id
              AND c.tenant_id  = vacancies.tenant_id
              AND c.deleted_at IS NULL
        ), 0)
        """
    )

    # 6) Функция и триггеры для поддержки vacancies.candidates_count
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE FUNCTION fn_recalc_vacancy_candidates_count() RETURNS trigger AS $$
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                IF NEW.vacancy_id IS NOT NULL THEN
                    UPDATE vacancies
                    SET candidates_count = COALESCE((
                        SELECT COUNT(*) FROM candidates c
                        WHERE c.vacancy_id = NEW.vacancy_id
                          AND c.tenant_id  = NEW.tenant_id
                          AND c.deleted_at IS NULL
                    ), 0)
                    WHERE vacancies.id = NEW.vacancy_id AND vacancies.tenant_id = NEW.tenant_id;
                END IF;

            ELSIF (TG_OP = 'UPDATE') THEN
                -- пересчитать для нового vacancy_id
                IF NEW.vacancy_id IS NOT NULL THEN
                    UPDATE vacancies
                    SET candidates_count = COALESCE((
                        SELECT COUNT(*) FROM candidates c
                        WHERE c.vacancy_id = NEW.vacancy_id
                          AND c.tenant_id  = NEW.tenant_id
                          AND c.deleted_at IS NULL
                    ), 0)
                    WHERE vacancies.id = NEW.vacancy_id AND vacancies.tenant_id = NEW.tenant_id;
                END IF;
                -- если вакансия/тенант поменялись, пересчитаем и для старых значений
                IF (NEW.vacancy_id IS DISTINCT FROM OLD.vacancy_id) OR (NEW.tenant_id IS DISTINCT FROM OLD.tenant_id) OR (NEW.deleted_at IS DISTINCT FROM OLD.deleted_at) THEN
                    IF OLD.vacancy_id IS NOT NULL THEN
                        UPDATE vacancies
                        SET candidates_count = COALESCE((
                            SELECT COUNT(*) FROM candidates c
                            WHERE c.vacancy_id = OLD.vacancy_id
                              AND c.tenant_id  = OLD.tenant_id
                              AND c.deleted_at IS NULL
                        ), 0)
                        WHERE vacancies.id = OLD.vacancy_id AND vacancies.tenant_id = OLD.tenant_id;
                    END IF;
                END IF;

            ELSIF (TG_OP = 'DELETE') THEN
                IF OLD.vacancy_id IS NOT NULL THEN
                    UPDATE vacancies
                    SET candidates_count = COALESCE((
                        SELECT COUNT(*) FROM candidates c
                        WHERE c.vacancy_id = OLD.vacancy_id
                          AND c.tenant_id  = OLD.tenant_id
                          AND c.deleted_at IS NULL
                    ), 0)
                    WHERE vacancies.id = OLD.vacancy_id AND vacancies.tenant_id = OLD.tenant_id;
                END IF;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    conn.exec_driver_sql(
        """
        CREATE TRIGGER trg_vac_after_candidate_insert
        AFTER INSERT ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION fn_recalc_vacancy_candidates_count();
        """
    )

    conn.exec_driver_sql(
        """
        CREATE TRIGGER trg_vac_after_candidate_update
        AFTER UPDATE OF vacancy_id, tenant_id, deleted_at ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION fn_recalc_vacancy_candidates_count();
        """
    )

    conn.exec_driver_sql(
        """
        CREATE TRIGGER trg_vac_after_candidate_delete
        AFTER DELETE ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION fn_recalc_vacancy_candidates_count();
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table("documents"):
        for trg in [
            "trg_docs_after_insert",
            "trg_docs_after_update",
            "trg_docs_after_delete",
        ]:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON documents")
    conn.exec_driver_sql("DROP FUNCTION IF EXISTS fn_recalc_candidate_docs_progress()")

    if insp.has_table("candidates"):
        for trg in [
            "trg_vac_after_candidate_insert",
            "trg_vac_after_candidate_update",
            "trg_vac_after_candidate_delete",
        ]:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON candidates")
    conn.exec_driver_sql("DROP FUNCTION IF EXISTS fn_recalc_vacancy_candidates_count()")

    try:
        op.drop_column("vacancies", "candidates_count")
    except Exception:
        pass