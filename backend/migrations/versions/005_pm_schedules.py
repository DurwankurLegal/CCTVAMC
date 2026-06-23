"""Preventive-maintenance schedules (SRS 4.9).

Revision ID: 005
Revises: 004
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pm_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("amc_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("amc_contracts.id"), nullable=False, index=True),
        sa.Column("sequence_no", sa.Integer, nullable=False),
        sa.Column("scheduled_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(50), server_default="planned"),
        sa.Column("reason_code", sa.String(100)),
        sa.Column("completed_visit_id", postgresql.UUID(as_uuid=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pm_tenant_date", "pm_schedules", ["tenant_id", "scheduled_date"])
    op.execute("ALTER TABLE pm_schedules ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON pm_schedules "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    )
    op.execute("ALTER TABLE pm_schedules FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("pm_schedules")
