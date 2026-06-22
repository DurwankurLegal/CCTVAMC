"""Customer Master completion + documents/media store (SRS 4.3, 4.17, 4.18).

Revision ID: 004
Revises: 003
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

NEW_TENANT_SCOPED = ["customer_contacts", "documents"]


def upgrade() -> None:
    # Customer: status + commercial fields
    op.add_column("customers", sa.Column("status", sa.String(50), nullable=False, server_default="active"))
    op.add_column("customers", sa.Column("billing_address", sa.Text, nullable=True))
    op.add_column("customers", sa.Column("shipping_address", sa.Text, nullable=True))
    op.add_column("customers", sa.Column("authorized_signatory", sa.String(255), nullable=True))

    # Customer sites: geo-coordinates
    op.add_column("customer_sites", sa.Column("latitude", sa.Float, nullable=True))
    op.add_column("customer_sites", sa.Column("longitude", sa.Float, nullable=True))

    # customer_contacts
    op.create_table(
        "customer_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="admin"),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("doc_type", sa.String(50), server_default="other"),
        sa.Column("file_name", sa.String(255)),
        sa.Column("content_type", sa.String(100)),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000)),
        sa.Column("notes", sa.Text),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True)),
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
    op.drop_table("documents")
    op.drop_table("customer_contacts")
    op.drop_column("customer_sites", "longitude")
    op.drop_column("customer_sites", "latitude")
    op.drop_column("customers", "authorized_signatory")
    op.drop_column("customers", "shipping_address")
    op.drop_column("customers", "billing_address")
    op.drop_column("customers", "status")
