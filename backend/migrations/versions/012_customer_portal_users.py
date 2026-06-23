"""Customer self-service portal identity (SRS 4.2).

Separate identity table for portal users, tenant-scoped with RLS. Portal users
are additionally scoped to a single ``customer_id`` at the application layer.

Revision ID: 012
Revises: 011
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Tenant isolation via RLS, mirroring every other tenant-scoped table.
    op.execute("ALTER TABLE customer_portal_users ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON customer_portal_users "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    )
    op.execute("ALTER TABLE customer_portal_users FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("customer_portal_users")
