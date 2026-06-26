"""add multi company and cash collection

Revision ID: 016
Revises: 015
Create Date: 2026-06-26 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None

NEW_RLS_TABLES = ["companies", "company_templates", "cash_collections", "cash_collection_logs"]

def upgrade() -> None:
    # 1. Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('gst_status', sa.String(length=50), server_default='NON_GST', nullable=False),
        sa.Column('gstin', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('contact_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('bank_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('authorized_signatory', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_companies_tenant_id', 'companies', ['tenant_id'])
    op.create_index('ix_companies_name', 'companies', ['name'])

    # 2. Create company_templates table
    op.create_table(
        'company_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('template_html', sa.Text(), nullable=False),
        sa.Column('header_html', sa.Text(), nullable=True),
        sa.Column('footer_html', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE')
    )
    op.create_index('ix_company_templates_tenant_id', 'company_templates', ['tenant_id'])
    op.create_index('ix_company_templates_document_type', 'company_templates', ['document_type'])

    # 3. Create cash_collections table
    op.create_table(
        'cash_collections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('employee_id', sa.UUID(), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('service_ticket_id', sa.UUID(), nullable=True),
        sa.Column('invoice_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payment_mode', sa.String(length=50), server_default='CASH', nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('receipt_photo_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id']),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['service_ticket_id'], ['service_tickets.id'])
    )
    op.create_index('ix_cash_collections_tenant_id', 'cash_collections', ['tenant_id'])
    op.create_index('ix_cash_collections_employee_id', 'cash_collections', ['employee_id'])
    op.create_index('ix_cash_collections_customer_name', 'cash_collections', ['customer_name'])
    op.create_index('ix_cash_collections_status', 'cash_collections', ['status'])

    # 4. Create cash_collection_logs table
    op.create_table(
        'cash_collection_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('cash_collection_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('action_by', sa.UUID(), nullable=False),
        sa.Column('action_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cash_collection_id'], ['cash_collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['action_by'], ['users.id'])
    )
    op.create_index('ix_cash_collection_logs_tenant_id', 'cash_collection_logs', ['tenant_id'])
    op.create_index('ix_cash_collection_logs_cash_collection_id', 'cash_collection_logs', ['cash_collection_id'])

    # 5. Populate default companies for existing tenants
    op.execute(
        """
        INSERT INTO companies (id, tenant_id, name, gst_status, gstin, address, contact_details, bank_details, logo_url, authorized_signatory, is_default, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), id, name, CASE WHEN gstin IS NOT NULL AND gstin != '' THEN 'GST' ELSE 'NON_GST' END, gstin, registered_address, '{}'::json, '{}'::json, NULL, '{}'::json, true, true, now(), now()
        FROM tenants;
        """
    )

    # 6. Add company_id reference columns to existing transactional tables
    transactional_tables = ['leads', 'quotations', 'invoices', 'amc_contracts', 'service_tickets']
    for table in transactional_tables:
        op.add_column(table, sa.Column('company_id', sa.UUID(), nullable=True))
        
        # Link existing records to the default company of their respective tenant
        op.execute(
            f"""
            UPDATE {table} t
            SET company_id = c.id
            FROM companies c
            WHERE t.tenant_id = c.tenant_id AND c.is_default = true;
            """
        )
        
        # Enforce foreign key and non-nullable constraint
        op.alter_column(table, 'company_id', nullable=False)
        op.create_foreign_key(f'fk_{table}_company_id', table, 'companies', ['company_id'], ['id'])

    # 7. Enable RLS on the new tables
    for table in NEW_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            """
        )
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

def downgrade() -> None:
    # 1. Disable RLS and drop policies
    for table in NEW_RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # 2. Remove company_id from existing tables
    transactional_tables = ['leads', 'quotations', 'invoices', 'amc_contracts', 'service_tickets']
    for table in transactional_tables:
        op.drop_constraint(f'fk_{table}_company_id', table, type_='foreignkey')
        op.drop_column(table, 'company_id')

    # 3. Drop new tables
    op.drop_table('cash_collection_logs')
    op.drop_table('cash_collections')
    op.drop_table('company_templates')
    op.drop_table('companies')
