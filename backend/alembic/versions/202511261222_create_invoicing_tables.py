"""Create invoicing tables (invoices, invoice_items, payments, refunds)

Revision ID: 202511261222
Revises: 202511261202
Create Date: 2025-11-26 12:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '202511261222'
down_revision: Union[str, None] = '202511261202'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == 'postgresql'


def _has_column(table: str, column: str) -> bool:
    """Check if column exists in table."""
    if not _is_postgres():
        return False
    bind = op.get_bind()
    result = bind.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = :column_name
            )
        """),
        {"table_name": table, "column_name": column}
    )
    return bool(result.scalar())


def _has_table(table: str) -> bool:
    """Check if table exists."""
    if not _is_postgres():
        return False
    bind = op.get_bind()
    result = bind.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
        """),
        {"table_name": table}
    )
    return bool(result.scalar())


def upgrade() -> None:
    """Create invoicing tables."""
    if not _is_postgres():
        # SQLite doesn't support all features, skip for now
        return
    
    # Create invoices table
    if not _has_table("invoices"):
        op.create_table(
            'invoices',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), nullable=False),
            sa.Column('company_id', sa.String(36), nullable=True),
            sa.Column('candidate_id', sa.String(36), nullable=True),
            sa.Column('contract_id', sa.String(36), nullable=True),
            sa.Column('order_id', sa.String(36), nullable=True),
            sa.Column('service_order_id', sa.String(36), nullable=True),
            sa.Column('invoice_number', sa.String(64), nullable=False, unique=True),
            sa.Column('issue_date', sa.Date(), nullable=False),
            sa.Column('due_date', sa.Date(), nullable=False),
            sa.Column('currency', sa.String(10), nullable=False, server_default='PLN'),
            sa.Column('subtotal', sa.Numeric(14, 2), nullable=False, server_default='0'),
            sa.Column('vat_total', sa.Numeric(14, 2), nullable=False, server_default='0'),
            sa.Column('total_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
            sa.Column('paid_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
            sa.Column('status', sa.String(16), nullable=False, server_default='draft'),
            sa.Column('payment_date', sa.Date(), nullable=True),
            sa.Column('pdf_file_id', sa.String(36), nullable=True),
            sa.Column('billing_details', postgresql.JSONB(), nullable=True),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='SET NULL'),
            sa.CheckConstraint(
                "status IN ('draft','issued','sent','paid','overdue','cancelled')",
                name='chk_invoice_status'
            ),
            sa.CheckConstraint(
                "subtotal >= 0 AND vat_total >= 0 AND total_amount = subtotal + vat_total AND paid_amount >= 0",
                name='chk_invoice_amounts'
            ),
        )
        op.create_index('idx_invoices_tenant', 'invoices', ['tenant_id'])
        op.create_index('idx_invoices_company', 'invoices', ['company_id'])
        op.create_index('idx_invoices_candidate', 'invoices', ['candidate_id'])
        op.create_index('idx_invoices_status', 'invoices', ['status'])
        op.create_index('idx_invoices_due', 'invoices', ['due_date'])
    
    # Create invoice_items table with GENERATED columns
    if not _has_table("invoice_items"):
        # Create table via raw SQL to support GENERATED ALWAYS AS columns
        op.execute("""
            CREATE TABLE invoice_items (
                id VARCHAR(36) PRIMARY KEY,
                invoice_id VARCHAR(36) NOT NULL,
                line_no INTEGER NOT NULL DEFAULT 1,
                description TEXT NOT NULL,
                qty NUMERIC(12,2) NOT NULL DEFAULT 1,
                unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
                vat_rate NUMERIC(5,2) NOT NULL DEFAULT 23.00,
                net_total NUMERIC(14,2) GENERATED ALWAYS AS (qty * unit_price) STORED NOT NULL,
                vat_amount NUMERIC(14,2) GENERATED ALWAYS AS (ROUND((qty * unit_price) * (vat_rate/100.0), 2)) STORED NOT NULL,
                gross_total NUMERIC(14,2) GENERATED ALWAYS AS (ROUND((qty * unit_price) * (1 + vat_rate/100.0), 2)) STORED NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT fk_item_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                CONSTRAINT chk_qty CHECK (qty > 0),
                CONSTRAINT chk_price CHECK (unit_price >= 0)
            );
        """)
        op.create_index('idx_invoice_items_invoice', 'invoice_items', ['invoice_id'])
    
    # Create payments table
    if not _has_table("payments"):
        op.create_table(
            'payments',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), nullable=False),
            sa.Column('invoice_id', sa.String(36), nullable=False),
            sa.Column('amount', sa.Numeric(14, 2), nullable=False),
            sa.Column('currency', sa.String(10), nullable=False, server_default='PLN'),
            sa.Column('payment_date', sa.Date(), nullable=False),
            sa.Column('method', sa.String(24), nullable=False),
            sa.Column('provider', sa.String(32), nullable=True),
            sa.Column('provider_reference', sa.String(128), nullable=True),
            sa.Column('reference_number', sa.String(128), nullable=True),
            sa.Column('status', sa.String(16), nullable=False, server_default='confirmed'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
            sa.CheckConstraint(
                "status IN ('pending','confirmed','failed')",
                name='chk_payment_status'
            ),
            sa.CheckConstraint('amount > 0', name='chk_payment_amount'),
        )
        op.create_index('idx_payments_invoice', 'payments', ['invoice_id'])
        op.create_index('idx_payments_tenant', 'payments', ['tenant_id'])
        op.create_index('idx_payments_status', 'payments', ['status'])
    
    # Create refunds table
    if not _has_table("refunds"):
        op.create_table(
            'refunds',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), nullable=False),
            sa.Column('payment_id', sa.String(36), nullable=False),
            sa.Column('amount', sa.Numeric(14, 2), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('refund_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
            sa.Column('status', sa.String(16), nullable=False, server_default='initiated'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
            sa.CheckConstraint(
                "status IN ('initiated','completed','cancelled')",
                name='chk_refund_status'
            ),
            sa.CheckConstraint('amount > 0', name='chk_refund_amount'),
        )
        op.create_index('idx_refunds_payment', 'refunds', ['payment_id'])
        op.create_index('idx_refunds_tenant', 'refunds', ['tenant_id'])
    
    # Enable RLS
    for table in ['invoices', 'invoice_items', 'payments', 'refunds']:
        if _has_table(table):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            
            if table == 'invoices':
                op.execute("""
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies 
                            WHERE tablename = 'invoices' 
                            AND policyname = 'rls_invoices_tenant'
                        ) THEN
                            CREATE POLICY rls_invoices_tenant ON invoices
                            USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
                        END IF;
                    END $$;
                """)
            elif table == 'invoice_items':
                op.execute("""
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies 
                            WHERE tablename = 'invoice_items' 
                            AND policyname = 'rls_invoice_items_parent'
                        ) THEN
                            CREATE POLICY rls_invoice_items_parent ON invoice_items
                            USING (
                                EXISTS (
                                    SELECT 1 FROM invoices i 
                                    WHERE i.id = invoice_items.invoice_id 
                                    AND i.tenant_id::uuid = current_setting('app.tenant_id')::uuid
                                )
                            );
                        END IF;
                    END $$;
                """)
            elif table == 'payments':
                op.execute("""
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies 
                            WHERE tablename = 'payments' 
                            AND policyname = 'rls_payments_tenant'
                        ) THEN
                            CREATE POLICY rls_payments_tenant ON payments
                            USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
                        END IF;
                    END $$;
                """)
            elif table == 'refunds':
                op.execute("""
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies 
                            WHERE tablename = 'refunds' 
                            AND policyname = 'rls_refunds_tenant'
                        ) THEN
                            CREATE POLICY rls_refunds_tenant ON refunds
                            USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
                        END IF;
                    END $$;
                """)


def downgrade() -> None:
    """Drop invoicing tables."""
    if not _is_postgres():
        return
    
    # Drop RLS policies
    for table in ['refunds', 'payments', 'invoice_items', 'invoices']:
        if _has_table(table):
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
            if table == 'invoices':
                op.execute("DROP POLICY IF EXISTS rls_invoices_tenant ON invoices;")
            elif table == 'invoice_items':
                op.execute("DROP POLICY IF EXISTS rls_invoice_items_parent ON invoice_items;")
            elif table == 'payments':
                op.execute("DROP POLICY IF EXISTS rls_payments_tenant ON payments;")
            elif table == 'refunds':
                op.execute("DROP POLICY IF EXISTS rls_refunds_tenant ON refunds;")
    
    # Drop tables in reverse order
    for table in ['refunds', 'payments', 'invoice_items', 'invoices']:
        if _has_table(table):
            op.drop_table(table)

