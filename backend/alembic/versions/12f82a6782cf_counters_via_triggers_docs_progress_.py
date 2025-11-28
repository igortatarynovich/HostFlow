"""counters via triggers: docs_progress + vacancy.candidates_count

Revision ID: 12f82a6782cf
Revises: f0babdeb1fc7
Create Date: 2025-09-19 11:11:04.998888+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "12f82a6782cf"  # можешь оставить авто-ID, это не критично
down_revision = "f0babdeb1fc7"      # подставь текущий head, если другой
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1) колонка для кандидатов у вакансии (если ещё нет)
    try:
        op.add_column("vacancies", sa.Column("candidates_count", sa.Integer(), nullable=True))
    except Exception:
        pass  # если уже добавлена — ок

    # 2) Разовый бэкофилл docs_progress у кандидатов (JSON) и candidates_count у вакансий
    # docs_progress = {"total": n, "uploaded": n, "ready": n, "submitted": n, "planned": n}
    conn.exec_driver_sql("""
        UPDATE candidates
        SET docs_progress = jsonb_build_object(
            'total',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.deleted_at IS NULL), 0),
            'uploaded',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
            'ready',      COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.status='ready' AND d.deleted_at IS NULL), 0),
            'submitted',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.status='submitted' AND d.deleted_at IS NULL), 0),
            'planned',    COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = candidates.id AND d.status='planned' AND d.deleted_at IS NULL), 0)
        ),
        updated_at = CURRENT_TIMESTAMP
    """)

    conn.exec_driver_sql("""
    UPDATE vacancies
    SET candidates_count = COALESCE((
        SELECT COUNT(*)
        FROM candidate_vacancies cv
        JOIN candidates c ON c.id = cv.candidate_id
        WHERE cv.vacancy_id = vacancies.id
          AND cv.tenant_id  = vacancies.tenant_id
          AND c.deleted_at IS NULL
    ), 0)
    """)

    # 3) Триггеры, поддерживающие docs_progress на изменениях таблицы documents
    # drop old (SQLite-style) triggers if they accidentally exist; in Postgres we must specify the table
    for trg in [
        "trg_docs_after_insert",
        "trg_docs_after_update",
        "trg_docs_after_delete",
    ]:
        try:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON documents")
        except Exception:
            pass

    # Postgres: create helper function to recalc candidate docs_progress
    conn.exec_driver_sql("""
    CREATE OR REPLACE FUNCTION fn_recalc_candidate_docs_progress()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_candidate_id uuid;
    BEGIN
        v_candidate_id := COALESCE(NEW.candidate_id, OLD.candidate_id);

        UPDATE candidates c
        SET docs_progress = jsonb_build_object(
                'total',     COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = v_candidate_id AND d.deleted_at IS NULL), 0),
                'uploaded',  COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = v_candidate_id AND d.filename IS NOT NULL AND d.deleted_at IS NULL), 0),
                'ready',     COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = v_candidate_id AND d.status = 'ready'     AND d.deleted_at IS NULL), 0),
                'submitted', COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = v_candidate_id AND d.status = 'submitted' AND d.deleted_at IS NULL), 0),
                'planned',   COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = v_candidate_id AND d.status = 'planned'   AND d.deleted_at IS NULL), 0)
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE c.id = v_candidate_id;

        RETURN NULL;
    END;
    $$;
    """)

    # Triggers on documents
    conn.exec_driver_sql("""
    DROP TRIGGER IF EXISTS trg_docs_after_insert ON documents;
    CREATE TRIGGER trg_docs_after_insert
    AFTER INSERT ON documents
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalc_candidate_docs_progress();
    """)

    conn.exec_driver_sql("""
    DROP TRIGGER IF EXISTS trg_docs_after_update ON documents;
    CREATE TRIGGER trg_docs_after_update
    AFTER UPDATE OF status, filename, deleted_at, candidate_id ON documents
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalc_candidate_docs_progress();
    """)

    conn.exec_driver_sql("""
    DROP TRIGGER IF EXISTS trg_docs_after_delete ON documents;
    CREATE TRIGGER trg_docs_after_delete
    AFTER DELETE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalc_candidate_docs_progress();
    """)

    # 4) Триггеры для vacancies.candidates_count (таблица candidate_vacancies — источник истины)
    # drop old (SQLite-style) cv triggers with table specified
    for trg in [
        "trg_cv_after_insert",
        "trg_cv_after_update",
        "trg_cv_after_delete",
    ]:
        try:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON candidate_vacancies")
        except Exception:
            pass

    # Postgres: function to recalc vacancies.candidates_count
    conn.exec_driver_sql("""
    CREATE OR REPLACE FUNCTION fn_recalc_vacancy_candidates_count()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_new_vac uuid;
        v_new_tenant uuid;
        v_old_vac uuid;
        v_old_tenant uuid;
    BEGIN
        v_new_vac := COALESCE(NEW.vacancy_id, NULL);
        v_new_tenant := COALESCE(NEW.tenant_id, NULL);
        v_old_vac := COALESCE(OLD.vacancy_id, NULL);
        v_old_tenant := COALESCE(OLD.tenant_id, NULL);

        IF v_new_vac IS NOT NULL AND v_new_tenant IS NOT NULL THEN
            UPDATE vacancies v
            SET candidates_count = COALESCE((
                SELECT COUNT(*)
                FROM candidate_vacancies cv
                JOIN candidates c ON c.id = cv.candidate_id
                WHERE cv.vacancy_id = v.id
                  AND cv.tenant_id  = v.tenant_id
                  AND c.deleted_at IS NULL
            ), 0)
            WHERE v.id = v_new_vac AND v.tenant_id = v_new_tenant;
        END IF;

        IF (TG_OP <> 'INSERT') AND v_old_vac IS NOT NULL AND v_old_tenant IS NOT NULL THEN
            UPDATE vacancies v
            SET candidates_count = COALESCE((
                SELECT COUNT(*)
                FROM candidate_vacancies cv
                JOIN candidates c ON c.id = cv.candidate_id
                WHERE cv.vacancy_id = v.id
                  AND cv.tenant_id  = v.tenant_id
                  AND c.deleted_at IS NULL
            ), 0)
            WHERE v.id = v_old_vac AND v.tenant_id = v_old_tenant;
        END IF;

        RETURN NULL;
    END;
    $$;
    """)

    conn.exec_driver_sql("""
    DROP TRIGGER IF EXISTS trg_cv_after_insert ON candidate_vacancies;
    CREATE TRIGGER trg_cv_after_insert
    AFTER INSERT ON candidate_vacancies
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalc_vacancy_candidates_count();
    """)

    conn.exec_driver_sql("""
    DROP TRIGGER IF EXISTS trg_cv_after_update ON candidate_vacancies;
    CREATE TRIGGER trg_cv_after_update
    AFTER UPDATE OF vacancy_id, tenant_id ON candidate_vacancies
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalc_vacancy_candidates_count();
    """)

    conn.exec_driver_sql("""
    DROP TRIGGER IF EXISTS trg_cv_after_delete ON candidate_vacancies;
    CREATE TRIGGER trg_cv_after_delete
    AFTER DELETE ON candidate_vacancies
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalc_vacancy_candidates_count();
    """)


def downgrade():
    conn = op.get_bind()

    # drop document triggers
    for trg in [
        "trg_docs_after_insert",
        "trg_docs_after_update",
        "trg_docs_after_delete",
    ]:
        try:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON documents")
        except Exception:
            pass

    # drop candidate_vacancies triggers
    for trg in [
        "trg_cv_after_insert",
        "trg_cv_after_update",
        "trg_cv_after_delete",
    ]:
        try:
            conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trg} ON candidate_vacancies")
        except Exception:
            pass

    # drop helper functions
    try:
        conn.exec_driver_sql("DROP FUNCTION IF EXISTS fn_recalc_candidate_docs_progress()")
    except Exception:
        pass
    try:
        conn.exec_driver_sql("DROP FUNCTION IF EXISTS fn_recalc_vacancy_candidates_count()")
    except Exception:
        pass

    # optional: drop the counter column
    try:
        op.drop_column("vacancies", "candidates_count")
    except Exception:
        pass