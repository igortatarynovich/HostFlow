"""Add candidate profiles and process templates.

Revision ID: 202501030000_add_candidate_profiles_and_process_templates
Revises: 202501020000_add_requirements_and_gates
Create Date: 2025-01-03 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '202501030000_add_candidate_profiles_and_process_templates'
down_revision: Union[str, None] = '202501020000_add_requirements_and_gates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == 'postgresql'


def upgrade() -> None:
    # 1. Create candidate_profiles table
    op.create_table('candidate_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('client_id', sa.String(length=36), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('owner_user_id', sa.String(length=36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_candidate_profile_tenant_code')
    )
    op.create_index(op.f('ix_candidate_profiles_tenant_id'), 'candidate_profiles', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_candidate_profiles_client_id'), 'candidate_profiles', ['client_id'], unique=False)

    # 2. Create process_templates table
    op.create_table('process_templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status_model', sa.Enum('EVIDENCE', 'PROCESS_WP_A', 'PROCESS_OSWIADCZENIE', 'PROCESS_RESIDENCE', name='document_status_model_enum', native_enum=False), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_process_template_tenant_code')
    )
    op.create_index(op.f('ix_process_templates_tenant_id'), 'process_templates', ['tenant_id'], unique=False)

    # 3. Add candidate_profile_id to vacancies
    with op.batch_alter_table('vacancies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('candidate_profile_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_vacancies_candidate_profile_id',
            'candidate_profiles',
            ['candidate_profile_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_vacancies_candidate_profile_id', ['candidate_profile_id'], unique=False)

    # 4. Enable RLS for new tables
    if _is_postgres():
        for table in ['candidate_profiles', 'process_templates']:
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
        for table in ['process_templates', 'candidate_profiles']:
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")

    # Remove candidate_profile_id from vacancies
    with op.batch_alter_table('vacancies', schema=None) as batch_op:
        batch_op.drop_constraint('fk_vacancies_candidate_profile_id', type_='foreignkey')
        batch_op.drop_index('ix_vacancies_candidate_profile_id')
        batch_op.drop_column('candidate_profile_id')

    # Drop tables
    op.drop_index(op.f('ix_process_templates_tenant_id'), table_name='process_templates')
    op.drop_table('process_templates')
    op.drop_index(op.f('ix_candidate_profiles_client_id'), table_name='candidate_profiles')
    op.drop_index(op.f('ix_candidate_profiles_tenant_id'), table_name='candidate_profiles')
    op.drop_table('candidate_profiles')

