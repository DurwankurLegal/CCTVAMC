"""New-installation work orders (SRS 4.5).

Revision ID: 006
Revises: 005
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("work_order_number", sa.String(100), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer_sites.id"), nullable=True),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotations.id"), nullable=True),
        sa.Column("status", sa.String(50), server_default="survey_pending"),
        sa.Column("survey_date", sa.Date),
        sa.Column("survey_notes", sa.Text),
        sa.Column("feasibility_notes", sa.Text),
        sa.Column("recommended_camera_count", sa.Integer),
        sa.Column("assigned_technician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("target_completion_date", sa.Date),
        sa.Column("handover_otp", sa.String(10)),
        sa.Column("handed_over_at", sa.DateTime(timezone=True)),
        sa.Column("amc_contract_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_installation_wo", "installations", ["tenant_id", "work_order_number"], unique=True)
    op.execute("ALTER TABLE installations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON installations "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    )
    op.execute("ALTER TABLE installations FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("installations")
