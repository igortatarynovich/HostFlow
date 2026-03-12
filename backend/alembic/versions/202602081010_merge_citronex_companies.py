"""Merge duplicate Citronex companies into a single canonical company.

We keep the company named like 'Citronex Trans Logistic Sp. z o.o.%'
and reattach all data from 'Citronex Trans Logistic' to this company.

This removes future confusion in analytics where two rows appeared:
  - Citronex Trans Logistic
  - Citronex Trans Logistic Sp. z o.o.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "202602081010"
down_revision: Union[str, Sequence[str], None] = "202602081002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    conn = op.get_bind()

    # 1) Найдём каноническую компанию (с полным названием) и дубликат
    canonical_row = conn.exec_driver_sql(
        """
        SELECT id, tenant_id, name
        FROM companies
        WHERE name ILIKE %s
        ORDER BY id
        LIMIT 1
        """,
        ("Citronex Trans Logistic Sp. z o.o.%",),
    ).fetchone()

    if not canonical_row:
        # Нет канонической компании — выходим без изменений, чтобы не ломать другие БД.
        return

    canonical_id = canonical_row[0]

    # Дубликаты: все компании с похожим именем, но другим id
    duplicate_rows = conn.exec_driver_sql(
        """
        SELECT id
        FROM companies
        WHERE name ILIKE %s
          AND id <> %s
        """,
        ("Citronex Trans Logistic%", canonical_id),
    ).fetchall()

    if not duplicate_rows:
        return

    duplicate_ids = [row[0] for row in duplicate_rows]

    # 2) Перевесим все ссылки на дубликаты на каноническую компанию.
    # Vacancy.company_id
    conn.exec_driver_sql(
        """
        UPDATE vacancies
        SET company_id = %s
        WHERE company_id = ANY(%s)
        """,
        (canonical_id, duplicate_ids),
    )

    # Candidate.company_id (если используется)
    conn.exec_driver_sql(
        """
        UPDATE candidates
        SET company_id = %s
        WHERE company_id = ANY(%s)
        """,
        (canonical_id, duplicate_ids),
    )

    # TenantLink.client_company_id / handoff_include_company_id
    conn.exec_driver_sql(
        """
        UPDATE tenant_links
        SET client_company_id = %s
        WHERE client_company_id = ANY(%s)
        """,
        (canonical_id, duplicate_ids),
    )
    conn.exec_driver_sql(
        """
        UPDATE tenant_links
        SET handoff_include_company_id = %s
        WHERE handoff_include_company_id = ANY(%s)
        """,
        (canonical_id, duplicate_ids),
    )

    # CandidateHandoff.client_company_id
    conn.exec_driver_sql(
        """
        UPDATE candidate_handoffs
        SET client_company_id = %s
        WHERE client_company_id = ANY(%s)
        """,
        (canonical_id, duplicate_ids),
    )

    # Leads / invoices / other references where company_id is used.
    # Эти таблицы могут отсутствовать в старых БД, поэтому проверяем наличие через to_regclass.
    row = conn.exec_driver_sql("SELECT to_regclass('public.leads')").fetchone()
    if row and row[0]:
        conn.exec_driver_sql(
            """
            UPDATE leads
            SET company_id = %s
            WHERE company_id = ANY(%s)
            """,
            (canonical_id, duplicate_ids),
        )

    row = conn.exec_driver_sql("SELECT to_regclass('public.lead_sources')").fetchone()
    if row and row[0]:
        conn.exec_driver_sql(
            """
            UPDATE lead_sources
            SET company_id = %s
            WHERE company_id = ANY(%s)
            """,
            (canonical_id, duplicate_ids),
        )

    row = conn.exec_driver_sql("SELECT to_regclass('public.invoices')").fetchone()
    if row and row[0]:
        conn.exec_driver_sql(
            """
            UPDATE invoices
            SET company_id = %s
            WHERE company_id = ANY(%s)
            """,
            (canonical_id, duplicate_ids),
        )

    # 3) Заархивируем/удалим дубликаты, чтобы они не появлялись в списках и аналитике.
    conn.exec_driver_sql(
        """
        UPDATE companies
        SET is_archived = TRUE
        WHERE id = ANY(%s)
        """,
        (duplicate_ids,),
    )


def downgrade() -> None:
    # Невозможно безопасно разнести компании обратно
    pass

