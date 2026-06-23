"""Vendor status/payables + purchase orders + vendor payments + ticket comments
(SRS 4.4, 4.8, 4.11).

Revision ID: 008
Revises: 007
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

NEW_TENANT_SCOPED = ["purchase_orders", "vendor_payments", "ticket_comments", "ticket_attachments"]


def upgrade() -> None:
    op.add_column("vendors", sa.Column("status", sa.String(50), nullable=False, server_default="active"))
    op.add_column("vendors", sa.Column("outstanding_payable", sa.Numeric(12, 2), server_default="0"))

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("po_number", sa.String(100), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("order_date", sa.Date),
        sa.Column("line_items", postgresql.JSONB, server_default="[]"),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "vendor_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.Date),
        sa.Column("method", sa.String(50)),
        sa.Column("reference", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_tickets.id"), nullable=False, index=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True)),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ticket_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_tickets.id"), nullable=False, index=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("url", sa.String(1000)),
        sa.Column("file_name", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    for table in NEW_TENANT_SCOPED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for t in NEW_TENANT_SCOPED:
        op.drop_table(t)
    op.drop_column("vendors", "outstanding_payable")
    op.drop_column("vendors", "status")
