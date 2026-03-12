"""RLS: let client tenant see vacancies of linked companies and candidates on those vacancies.

So the client can see all candidates that belong to their vacancies (vacancies of
companies in tenant_links.handoff_include_company_id), not only 6 with handoffs.

Revision ID: 202602080004
Revises: 202602080003
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602080004"
down_revision: Union[str, Sequence[str], None] = "202602080003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    # Vacancies: client can read vacancies of companies linked via handoff_include_company_id
    # Cast to uuid so varchar company_id compares with handoff_include_company_id::uuid
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = 'vacancies'
                  AND policyname = 'rls_vacancies_client_linked_company'
            ) THEN
                CREATE POLICY rls_vacancies_client_linked_company ON vacancies
                USING (
                    company_id::uuid IN (
                        SELECT tl.handoff_include_company_id::uuid
                        FROM tenant_links tl
                        WHERE tl.client_tenant_id::uuid = current_setting('app.tenant_id')::uuid
                          AND tl.handoff_include_company_id IS NOT NULL
                    )
                );
            END IF;
        END $$;
    """)

    # Candidates: client can read candidates whose vacancy is in linked companies
    # Cast varchar to uuid for company_id / handoff_include_company_id comparison
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = 'candidates'
                  AND policyname = 'rls_candidates_client_vacancy'
            ) THEN
                CREATE POLICY rls_candidates_client_vacancy ON candidates
                USING (
                    vacancy_id IN (
                        SELECT v.id
                        FROM vacancies v
                        INNER JOIN tenant_links tl
                          ON tl.handoff_include_company_id IS NOT NULL
                          AND tl.handoff_include_company_id::uuid = v.company_id::uuid
                          AND tl.client_tenant_id::uuid = current_setting('app.tenant_id')::uuid
                    )
                );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute("DROP POLICY IF EXISTS rls_candidates_client_vacancy ON candidates;")
    op.execute("DROP POLICY IF EXISTS rls_vacancies_client_linked_company ON vacancies;")
