"""add_sales_and_rental_modules

Revision ID: 039dd3484da6
Revises: f20df19f65f5
Create Date: 2026-06-27 09:33:02.308416

"""
from alembic import op
import sqlalchemy as sa

revision = '039dd3484da6'
down_revision = 'f20df19f65f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create products
    op.create_table('products',
    sa.Column('sku', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('brand', sa.String(length=100), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('hsn_code', sa.String(length=20), nullable=True),
    sa.Column('gst_rate', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('sale_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('rental_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('is_serial_tracked', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('warranty_months', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('inventory_item_id', sa.UUID(), nullable=True),
    sa.Column('is_sellable', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('is_rentable', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_tenant_id'), 'products', ['tenant_id'], unique=False)

    # 2. Create rental_units
    op.create_table('rental_units',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('serial_number', sa.String(length=100), nullable=False),
    sa.Column('condition', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False, server_default='available'),
    sa.Column('purchase_cost', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('purchase_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rental_units_tenant_id'), 'rental_units', ['tenant_id'], unique=False)

    # 3. Create rental_contracts
    op.create_table('rental_contracts',
    sa.Column('contract_number', sa.String(length=100), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=True),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False, server_default='booked'),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('billing_cycle', sa.String(length=50), nullable=False, server_default='monthly'),
    sa.Column('deposit_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('deposit_status', sa.String(length=50), nullable=False, server_default='pending'),
    sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('cgst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('sgst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('igst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    sa.ForeignKeyConstraint(['site_id'], ['customer_sites.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rental_contracts_tenant_id'), 'rental_contracts', ['tenant_id'], unique=False)

    # 4. Create rental_contract_lines
    op.create_table('rental_contract_lines',
    sa.Column('rental_contract_id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('rental_unit_id', sa.UUID(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
    sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('gst_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='18'),
    sa.Column('cgst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('sgst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('igst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['rental_contract_id'], ['rental_contracts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rental_unit_id'], ['rental_units.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rental_contract_lines_tenant_id'), 'rental_contract_lines', ['tenant_id'], unique=False)

    # 5. Create rental_movements
    op.create_table('rental_movements',
    sa.Column('rental_contract_id', sa.UUID(), nullable=False),
    sa.Column('rental_unit_id', sa.UUID(), nullable=False),
    sa.Column('movement_type', sa.String(length=50), nullable=False),
    sa.Column('movement_date', sa.Date(), nullable=False),
    sa.Column('condition', sa.String(length=100), nullable=True),
    sa.Column('meter_reading', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('charges', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    sa.Column('recorded_by', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['rental_contract_id'], ['rental_contracts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rental_unit_id'], ['rental_units.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rental_movements_tenant_id'), 'rental_movements', ['tenant_id'], unique=False)

    # 6. Alter sales_orders
    op.add_column('sales_orders', sa.Column('cgst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))
    op.add_column('sales_orders', sa.Column('sgst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))
    op.add_column('sales_orders', sa.Column('igst_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))
    op.add_column('sales_orders', sa.Column('supply_state_code', sa.String(length=2), nullable=True))
    op.add_column('sales_orders', sa.Column('fulfilled_at', sa.Date(), nullable=True))
    op.add_column('sales_orders', sa.Column('invoice_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_sales_orders_invoice_id', 'sales_orders', 'invoices', ['invoice_id'], ['id'])

    # 7. Enable RLS and create isolation policy for new tables
    NEW_RLS_TABLES = ["products", "rental_units", "rental_contracts", "rental_contract_lines", "rental_movements"]
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
    # 1. Disable RLS and drop policy
    NEW_RLS_TABLES = ["products", "rental_units", "rental_contracts", "rental_contract_lines", "rental_movements"]
    for table in NEW_RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # 2. Drop sales_orders columns
    op.drop_constraint('fk_sales_orders_invoice_id', 'sales_orders', type_='foreignkey')
    op.drop_column('sales_orders', 'invoice_id')
    op.drop_column('sales_orders', 'fulfilled_at')
    op.drop_column('sales_orders', 'supply_state_code')
    op.drop_column('sales_orders', 'igst_amount')
    op.drop_column('sales_orders', 'sgst_amount')
    op.drop_column('sales_orders', 'cgst_amount')

    # 3. Drop tables
    op.drop_index(op.f('ix_rental_movements_tenant_id'), table_name='rental_movements')
    op.drop_table('rental_movements')
    op.drop_index(op.f('ix_rental_contract_lines_tenant_id'), table_name='rental_contract_lines')
    op.drop_table('rental_contract_lines')
    op.drop_index(op.f('ix_rental_units_tenant_id'), table_name='rental_units')
    op.drop_table('rental_units')
    op.drop_index(op.f('ix_rental_contracts_tenant_id'), table_name='rental_contracts')
    op.drop_table('rental_contracts')
    op.drop_index(op.f('ix_products_tenant_id'), table_name='products')
    op.drop_table('products')
