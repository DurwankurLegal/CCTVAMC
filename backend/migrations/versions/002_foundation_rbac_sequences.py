"""Foundation: document sequences, auth sessions, RBAC tables + seed,
per-tenant unique document numbers, hot-path indexes.

Revision ID: 002
Revises: 001
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

# New tenant-scoped tables that need RLS.
NEW_TENANT_SCOPED = ["document_sequences", "user_roles"]

PERMISSION_MODULES = [
    "customers", "leads", "vendors", "assets", "quotations", "amc",
    "service_tickets", "engineer_visits", "inventory", "sales_orders",
    "invoices", "payments", "notifications", "reports", "users", "tenants",
    "installations", "documents",
]


def upgrade() -> None:
    # ── document_sequences ────────────────────────────────────
    op.create_table(
        "document_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("last_value", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "doc_type", "year", name="uq_document_sequence"),
    )

    # ── auth_sessions ─────────────────────────────────────────
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("jti", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── RBAC ──────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("description", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "role_id", "site_id", name="uq_user_role_site"),
    )

    # ── Seed permission catalogue ─────────────────────────────
    for module in PERMISSION_MODULES:
        for action in ("read", "write"):
            op.execute(
                f"INSERT INTO permissions (id, code, description) "
                f"VALUES (gen_random_uuid(), '{module}:{action}', '{action} {module}')"
            )

    # ── RLS on new tenant-scoped tables ───────────────────────
    for table in NEW_TENANT_SCOPED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # ── Per-tenant unique document numbers + hot-path indexes ──
    op.create_index("uq_invoice_number", "invoices", ["tenant_id", "invoice_number"], unique=True)
    op.create_index("uq_quotation_number", "quotations", ["tenant_id", "quotation_number"], unique=True)
    op.create_index("uq_contract_number", "amc_contracts", ["tenant_id", "contract_number"], unique=True)
    op.create_index("uq_ticket_number", "service_tickets", ["tenant_id", "ticket_number"], unique=True)

    op.create_index("ix_tickets_tenant_status", "service_tickets", ["tenant_id", "status"])
    op.create_index("ix_tickets_tenant_sla", "service_tickets", ["tenant_id", "sla_due_at"])
    op.create_index("ix_invoices_tenant_status", "invoices", ["tenant_id", "status"])
    op.create_index("ix_invoices_tenant_due", "invoices", ["tenant_id", "due_date"])
    op.create_index("ix_amc_tenant_status", "amc_contracts", ["tenant_id", "status"])

    # ── In-app notification center columns ────────────────────
    op.add_column("notification_logs", sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notification_logs", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_notif_recipient_user", "notification_logs", ["recipient_user_id"])


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notif_recipient_user")
    op.drop_column("notification_logs", "read_at")
    op.drop_column("notification_logs", "recipient_user_id")
    for ix in [
        "ix_amc_tenant_status", "ix_invoices_tenant_due", "ix_invoices_tenant_status",
        "ix_tickets_tenant_sla", "ix_tickets_tenant_status",
        "uq_ticket_number", "uq_contract_number", "uq_quotation_number", "uq_invoice_number",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {ix}")
    for table in ["user_roles", "role_permissions", "roles", "permissions", "auth_sessions", "document_sequences"]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
