"""Initial schema with RLS policies

Revision ID: 001
Revises:
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

TENANT_SCOPED_TABLES = [
    "users", "customers", "customer_sites", "cctv_assets",
    "leads", "vendors", "amc_contracts", "amc_assets",
    "service_tickets", "engineer_visits",
    "inventory_items", "inventory_movements",
    "quotations", "sales_orders", "invoices", "payments",
    "notification_templates", "notification_logs",
    "audit_logs",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── tenants (no RLS — platform-level table) ───────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("status", sa.String(50), nullable=False, server_default="trial"),
        sa.Column("branding", postgresql.JSONB, server_default="{}"),
        sa.Column("settings", postgresql.JSONB, server_default="{}"),
        sa.Column("gstin", sa.String(20)),
        sa.Column("registered_address", sa.Text),
        sa.Column("invoice_prefix", sa.String(20)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_platform_admin", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email_tenant", "users", ["tenant_id", "email"], unique=True)

    # ── customers ─────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("gstin", sa.String(20)),
        sa.Column("address", sa.Text),
        sa.Column("state_code", sa.String(2)),
        sa.Column("society_registration_no", sa.String(100)),
        sa.Column("contact_person_name", sa.String(255)),
        sa.Column("contact_person_phone", sa.String(20)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── customer_sites ────────────────────────────────────────
    op.create_table(
        "customer_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("contact_person", sa.String(255)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── cctv_assets ───────────────────────────────────────────
    op.create_table(
        "cctv_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer_sites.id"), nullable=False),
        sa.Column("serial_number", sa.String(100)),
        sa.Column("make", sa.String(100)),
        sa.Column("model", sa.String(100)),
        sa.Column("asset_type", sa.String(100)),
        sa.Column("installation_date", sa.Date),
        sa.Column("warranty_expiry", sa.Date),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("location_description", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── leads ─────────────────────────────────────────────────
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("address", sa.Text),
        sa.Column("source", sa.String(50)),
        sa.Column("status", sa.String(50), server_default="new"),
        sa.Column("notes", sa.Text),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("follow_up_date", sa.Date),
        sa.Column("converted_customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── vendors ───────────────────────────────────────────────
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vendor_type", sa.String(50)),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("gstin", sa.String(20)),
        sa.Column("address", sa.Text),
        sa.Column("contact_person", sa.String(255)),
        sa.Column("payment_terms", sa.String(100)),
        sa.Column("bank_account_encrypted", sa.String(500)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── amc_contracts ─────────────────────────────────────────
    op.create_table(
        "amc_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("contract_number", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("annual_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_frequency", sa.String(50)),
        sa.Column("terms", sa.Text),
        sa.Column("preventive_visits_per_year", sa.Integer),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── amc_assets (junction) ────────────────────────────────
    op.create_table(
        "amc_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("amc_contracts.id"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cctv_assets.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── service_tickets ───────────────────────────────────────
    op.create_table(
        "service_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("ticket_number", sa.String(100), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer_sites.id")),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cctv_assets.id")),
        sa.Column("amc_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("amc_contracts.id")),
        sa.Column("status", sa.String(50), server_default="open"),
        sa.Column("priority", sa.String(50), server_default="medium"),
        sa.Column("complaint", sa.Text, nullable=False),
        sa.Column("resolution_notes", sa.Text),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("sla_due_at", sa.DateTime(timezone=True)),
        sa.Column("sla_breached", sa.Boolean, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── engineer_visits ───────────────────────────────────────
    op.create_table(
        "engineer_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_tickets.id")),
        sa.Column("amc_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("amc_contracts.id")),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("visit_type", sa.String(50), server_default="corrective"),
        sa.Column("checkin_at", sa.DateTime(timezone=True)),
        sa.Column("checkout_at", sa.DateTime(timezone=True)),
        sa.Column("checkin_lat", sa.Float),
        sa.Column("checkin_lng", sa.Float),
        sa.Column("checkout_lat", sa.Float),
        sa.Column("checkout_lng", sa.Float),
        sa.Column("work_performed", sa.Text),
        sa.Column("parts_used", postgresql.JSONB, server_default="[]"),
        sa.Column("photo_urls", postgresql.JSONB, server_default="[]"),
        sa.Column("signature_url", sa.String(500)),
        sa.Column("customer_feedback", sa.Text),
        sa.Column("is_synced", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── inventory_items ───────────────────────────────────────
    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("part_number", sa.String(100)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("unit", sa.String(50)),
        sa.Column("hsn_code", sa.String(20)),
        sa.Column("gst_rate", sa.Numeric(5, 2)),
        sa.Column("reorder_level", sa.Integer, server_default="0"),
        sa.Column("current_stock", sa.Integer, server_default="0"),
        sa.Column("van_stock", sa.Integer, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 2)),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id")),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── inventory_movements ───────────────────────────────────
    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("movement_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── quotations ────────────────────────────────────────────
    op.create_table(
        "quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("quotation_number", sa.String(100), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id")),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("line_items", postgresql.JSONB, server_default="[]"),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"),
        sa.Column("cgst_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("sgst_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("igst_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("terms", sa.Text),
        sa.Column("valid_until", sa.Date),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── invoices ──────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("invoice_type", sa.String(50), server_default="tax_invoice"),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("amc_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("amc_contracts.id")),
        sa.Column("sales_order_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reference_invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id")),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("invoice_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date),
        sa.Column("supply_state_code", sa.String(2)),
        sa.Column("line_items", postgresql.JSONB, server_default="[]"),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"),
        sa.Column("cgst_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("sgst_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("igst_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("amount_paid", sa.Numeric(12, 2), server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("pdf_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── payments ──────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("mode", sa.String(50), server_default="cash"),
        sa.Column("reference_number", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── notification_templates ────────────────────────────────
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(255)),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── notification_logs ─────────────────────────────────────
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255)),
        sa.Column("body", sa.Text),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_detail", sa.Text),
        sa.Column("context_data", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── sales_orders ──────────────────────────────────────────
    op.create_table(
        "sales_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("order_number", sa.String(100), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotations.id")),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("delivery_date", sa.Date),
        sa.Column("line_items", postgresql.JSONB, server_default="[]"),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── audit_logs ────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("before_state", postgresql.JSONB),
        sa.Column("after_state", postgresql.JSONB),
        sa.Column("chain_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Row-Level Security policies ───────────────────────────
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            """
        )
        # Allow superuser (migrations, platform admin) to bypass RLS
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    tables = [
        "audit_logs", "notification_logs", "notification_templates",
        "payments", "invoices", "quotations",
        "inventory_movements", "inventory_items",
        "engineer_visits", "service_tickets",
        "sales_orders",
        "amc_assets", "amc_contracts",
        "leads", "vendors",
        "cctv_assets", "customer_sites", "customers",
        "users", "tenants",
    ]
    for table in tables:
        op.drop_table(table)
