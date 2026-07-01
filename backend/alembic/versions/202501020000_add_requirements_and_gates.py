"""Add requirements, gates, and update document policies.

Revision ID: 202501020000_add_requirements_and_gates
Revises: 202501010000_add_tenant_limits_and_document_policies
Create Date: 2025-01-02 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '202501020000_add_requirements_and_gates'
down_revision: Union[str, None] = '202501010000_add_tenant_limits_and_document_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == 'postgresql'


def upgrade() -> None:
    # 1. Create enums (используем верхний регистр для соответствия Python enum)
    if _is_postgres():
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE document_status_model_enum AS ENUM ('EVIDENCE', 'PROCESS_WP_A', 'PROCESS_OSWIADCZENIE', 'PROCESS_RESIDENCE');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE requirement_type_enum AS ENUM ('ID_EVIDENCE', 'CODE95_EVIDENCE', 'RIGHT_TO_WORK_BASIS', 'CORE_PRO_DRIVER_SET', 'DRIVERS_CERTIFICATE_IF_REQUIRED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE gate_code_enum AS ENUM ('GATE_DOCS_RECEIVED', 'GATE_PLAN_ARRIVAL', 'GATE_ON_CLIENT_BASE', 'GATE_ON_ROUTE');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE requirement_level_enum AS ENUM ('DISABLED', 'OPTIONAL', 'REQUIRED', 'BLOCKING');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)

    # 2. Add status_model to document_types
    with op.batch_alter_table('document_types', schema=None) as batch_op:
        if _is_postgres():
            batch_op.add_column(sa.Column('status_model', sa.Enum('EVIDENCE', 'PROCESS_WP_A', 'PROCESS_OSWIADCZENIE', 'PROCESS_RESIDENCE', name='document_status_model_enum', native_enum=False), nullable=True, server_default='EVIDENCE'))
        else:
            batch_op.add_column(sa.Column('status_model', sa.String(64), nullable=True, server_default='EVIDENCE'))

    # 3. Create requirement_type_definitions table
    op.create_table('requirement_type_definitions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('requirement_code', sa.Enum('id_evidence', 'code95_evidence', 'right_to_work_basis', 'core_pro_driver_set', 'drivers_certificate_if_required', name='requirement_type_enum', native_enum=False), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('satisfaction_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'requirement_code', name='uq_requirement_type_tenant_code')
    )
    op.create_index(op.f('ix_requirement_type_definitions_tenant_id'), 'requirement_type_definitions', ['tenant_id'], unique=False)

    # 4. Create gates table
    op.create_table('gates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('gate_code', sa.Enum('GATE_DOCS_RECEIVED', 'GATE_PLAN_ARRIVAL', 'GATE_ON_CLIENT_BASE', 'GATE_ON_ROUTE', name='gate_code_enum', native_enum=False), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('blocks_stage', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'gate_code', name='uq_gate_tenant_code')
    )
    op.create_index(op.f('ix_gates_tenant_id'), 'gates', ['tenant_id'], unique=False)

    # 5. Update document_policies table
    with op.batch_alter_table('document_policies', schema=None) as batch_op:
        # Drop old unique constraint
        batch_op.drop_constraint('uq_document_policy_scope', type_='unique')
        
        # Add new columns
        if _is_postgres():
            batch_op.add_column(sa.Column('requirement_code', sa.Enum('ID_EVIDENCE', 'CODE95_EVIDENCE', 'RIGHT_TO_WORK_BASIS', 'CORE_PRO_DRIVER_SET', 'DRIVERS_CERTIFICATE_IF_REQUIRED', name='requirement_type_enum', native_enum=False), nullable=True))
            batch_op.add_column(sa.Column('required_level', sa.Enum('DISABLED', 'OPTIONAL', 'REQUIRED', 'BLOCKING', name='requirement_level_enum', native_enum=False), nullable=False, server_default='REQUIRED'))
        else:
            batch_op.add_column(sa.Column('requirement_code', sa.String(64), nullable=True))
            batch_op.add_column(sa.Column('required_level', sa.String(32), nullable=False, server_default='required'))
        
        batch_op.add_column(sa.Column('gates', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
        
        # Make document_type_id nullable (since requirement_code can be used instead)
        batch_op.alter_column('document_type_id', nullable=True)
        
        # Add check constraint
        batch_op.create_check_constraint(
            'ck_document_policy_type_or_requirement',
            "(document_type_id IS NOT NULL AND requirement_code IS NULL) OR (document_type_id IS NULL AND requirement_code IS NOT NULL)"
        )

    # 6. Create partial unique indexes for document_policies (PostgreSQL only)
    if _is_postgres():
        op.execute("""
            CREATE UNIQUE INDEX uq_document_policy_doc_type 
            ON document_policies (tenant_id, scope, scope_id, document_type_id) 
            WHERE requirement_code IS NULL;
        """)
        op.execute("""
            CREATE UNIQUE INDEX uq_document_policy_requirement 
            ON document_policies (tenant_id, scope, scope_id, requirement_code) 
            WHERE document_type_id IS NULL;
        """)
    else:
        # SQLite: create regular unique constraints (less strict)
        op.create_unique_constraint('uq_document_policy_doc_type', 'document_policies', ['tenant_id', 'scope', 'scope_id', 'document_type_id'])
        op.create_unique_constraint('uq_document_policy_requirement', 'document_policies', ['tenant_id', 'scope', 'scope_id', 'requirement_code'])

    # 7. Add indexes
    op.create_index(op.f('ix_document_policies_requirement_code'), 'document_policies', ['requirement_code'], unique=False)

    # 8. Enable RLS for new tables
    if _is_postgres():
        for table in ['requirement_type_definitions', 'gates']:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"""
                DO $$ BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_policies
                        WHERE tablename = '{table}'
                        AND policyname = 'rls_{table}_tenant'
                    ) THEN
                        CREATE POLICY rls_{table}_tenant ON {table}
                        USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
                    END IF;
                END $$;
            """)


def downgrade() -> None:
    # Disable RLS
    if _is_postgres():
        for table in ['gates', 'requirement_type_definitions']:
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")

    # Drop indexes
    op.drop_index(op.f('ix_document_policies_requirement_code'), table_name='document_policies')

    # Drop partial unique indexes (PostgreSQL)
    if _is_postgres():
        op.execute("DROP INDEX IF EXISTS uq_document_policy_requirement;")
        op.execute("DROP INDEX IF EXISTS uq_document_policy_doc_type;")
    else:
        op.drop_constraint('uq_document_policy_requirement', 'document_policies', type_='unique')
        op.drop_constraint('uq_document_policy_doc_type', 'document_policies', type_='unique')

    # Revert document_policies changes
    with op.batch_alter_table('document_policies', schema=None) as batch_op:
        batch_op.drop_constraint('ck_document_policy_type_or_requirement', type_='check')
        batch_op.drop_column('gates')
        batch_op.drop_column('required_level')
        batch_op.drop_column('requirement_code')
        batch_op.alter_column('document_type_id', nullable=False)
        # Restore old unique constraint
        batch_op.create_unique_constraint('uq_document_policy_scope', ['tenant_id', 'scope', 'scope_id', 'document_type_id'])

    # Drop tables
    op.drop_index(op.f('ix_gates_tenant_id'), table_name='gates')
    op.drop_table('gates')
    op.drop_index(op.f('ix_requirement_type_definitions_tenant_id'), table_name='requirement_type_definitions')
    op.drop_table('requirement_type_definitions')

    # Remove status_model from document_types
    with op.batch_alter_table('document_types', schema=None) as batch_op:
        batch_op.drop_column('status_model')

    # Drop enums (PostgreSQL only)
    if _is_postgres():
        op.execute("DROP TYPE IF EXISTS requirement_level_enum;")
        op.execute("DROP TYPE IF EXISTS gate_code_enum;")
        op.execute("DROP TYPE IF EXISTS requirement_type_enum;")
        op.execute("DROP TYPE IF EXISTS document_status_model_enum;")

