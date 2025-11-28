"""Enable RLS for all tenant-scoped tables

Revision ID: 202511261201
Revises: 
Create Date: 2025-11-26 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202511261201'
down_revision: Union[str, None] = '202512210001_documents_type_dedup'  # Latest before merge
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == 'postgresql'


def _get_tenant_id_type(table_name: str) -> str:
    """Determine tenant_id column type for a table."""
    if not _is_postgres():
        return "text"
    
    # Query the actual column type
    bind = op.get_bind()
    result = bind.execute(sa.text(f"""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        AND column_name = 'tenant_id'
    """), {"table_name": table_name})
    
    row = result.fetchone()
    if row:
        dtype = row[0].lower()
        if 'uuid' in dtype:
            return "uuid"
    return "text"


# List of tables that should have RLS enabled
# Based on audit_rls.py results
TENANT_SCOPED_TABLES = [
    "activity_log",
    "auth_refresh_tokens",
    "bulk_operation_items",
    "bulk_operations",
    "candidate_consents",
    "candidate_delete_requests",
    "candidate_documents",
    "candidate_employments",
    "candidate_permits",
    "candidate_services",
    "candidate_stage_dict",
    "candidate_stage_history",
    "candidate_tasks",
    "candidate_vacancies",
    "candidate_vacancy",
    "candidate_visas",
    "candidates",
    "companies",
    "document_checks",
    "document_metrics_daily",
    "document_ruleset_diffs",
    "document_ruleset_usage",
    "document_ruleset_versions",
    "document_templates",
    "document_types",
    "documents",
    "documents_compliance_log",
    "lead_import_jobs",
    "leads",
    "magic_links",
    "meta_ads_map",
    "meta_lead_credentials",
    "meta_lead_settings",
    "reminders",
    "report_exports",
    "report_summaries",
    "scan_sessions",
    "service_attachments",
    "service_catalog",
    "services",
    "tenant_licenses",
    "tenant_seat_requests",
    "tenant_vacancy_access",
    "user_audit_log",
    "user_company_access",
    "user_invites",
    "user_notifications",
    "user_sessions",
    "vacancies",
    "vacancy_recruiters",
]


def upgrade() -> None:
    """Enable RLS and create policies for all tenant-scoped tables."""
    if not _is_postgres():
        # SQLite doesn't support RLS
        return
    
    for table_name in TENANT_SCOPED_TABLES:
        # Check if table exists
        bind = op.get_bind()
        result = bind.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
        """), {"table_name": table_name})
        
        if not result.scalar():
            # Table doesn't exist, skip
            continue
        
        # Check if tenant_id column exists
        result = bind.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = 'tenant_id'
            )
        """), {"table_name": table_name})
        
        if not result.scalar():
            # tenant_id column doesn't exist, skip
            continue
        
        # Determine tenant_id type
        tenant_id_type = _get_tenant_id_type(table_name)
        policy_condition = (
            "tenant_id = current_setting('app.tenant_id')::uuid"
            if tenant_id_type == "uuid"
            else "tenant_id = current_setting('app.tenant_id')"
        )
        
        policy_name = f"rls_{table_name}_tenant"
        
        # Enable RLS
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
        
        # Create policy if it doesn't exist
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = current_schema()
                      AND tablename = '{table_name}'
                      AND policyname = '{policy_name}'
                ) THEN
                    CREATE POLICY {policy_name} ON {table_name}
                    USING ({policy_condition});
                END IF;
            END $$;
        """)


def downgrade() -> None:
    """Disable RLS and drop policies for all tenant-scoped tables."""
    if not _is_postgres():
        return
    
    for table_name in TENANT_SCOPED_TABLES:
        policy_name = f"rls_{table_name}_tenant"
        
        # Check if table exists
        bind = op.get_bind()
        result = bind.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
        """), {"table_name": table_name})
        
        if not result.scalar():
            continue
        
        # Drop policy
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};")
        
        # Disable RLS
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

