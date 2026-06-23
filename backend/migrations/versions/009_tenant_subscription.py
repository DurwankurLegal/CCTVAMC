"""Tenant billing contact + platform subscription invoices (SRS 4.1).

Revision ID: 009
Revises: 008
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("billing_contact_name", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("billing_contact_email", sa.String(255), nullable=True))

    op.create_table(
        "subscription_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date),
        sa.Column("amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("status", sa.String(50), server_default="issued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Platform-level table (keyed by tenant_id FK) — no RLS; only platform admin
    # reaches it, and the API filters by tenant_id explicitly.


def downgrade() -> None:
    op.drop_table("subscription_invoices")
    op.drop_column("tenants", "billing_contact_email")
    op.drop_column("tenants", "billing_contact_name")
