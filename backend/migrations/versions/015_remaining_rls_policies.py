"""remaining rls policies and scheduled hard delete column

Revision ID: 015
Revises: 243eb39c8756
Create Date: 2026-06-24 23:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "243eb39c8756"
branch_labels = None
depends_on = None

NEW_RLS_STRICT = ["dashboard_snapshots", "subscription_invoices"]
NEW_RLS_SYSTEM_ALLOWED = ["auth_sessions", "roles"]


def upgrade() -> None:
    # 1. Add scheduled_hard_delete_at to tenants
    op.add_column(
        "tenants",
        sa.Column("scheduled_hard_delete_at", sa.DateTime(timezone=True), nullable=True)
    )

    # 2. Enable RLS on strict tables (where tenant_id must match app.tenant_id)
    for table in NEW_RLS_STRICT:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            """
        )
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # 3. Enable RLS on tables allowing system rows (where tenant_id IS NULL is allowed)
    for table in NEW_RLS_SYSTEM_ALLOWED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id IS NULL OR tenant_id = current_setting('app.tenant_id', true)::uuid)
            """
        )
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # 1. Drop policies and disable RLS
    for table in NEW_RLS_STRICT + NEW_RLS_SYSTEM_ALLOWED:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # 2. Drop column from tenants
    op.drop_column("tenants", "scheduled_hard_delete_at")
