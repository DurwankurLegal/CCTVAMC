"""Enforce status/category enums at the DB layer via CHECK constraints
(addresses the review's "enums stored as unconstrained strings" tech debt).

Revision ID: 010
Revises: 009
Create Date: 2026-06-22
"""
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

# (constraint_name, table, column, allowed values)
CHECKS = [
    ("ck_customers_status", "customers", "status", ["active", "inactive", "amc_expired", "prospect"]),
    ("ck_customers_category", "customers", "category", ["chs", "commercial", "single_shop"]),
    ("ck_tenants_status", "tenants", "status", ["trial", "active", "suspended", "cancelled"]),
    ("ck_leads_status", "leads", "status", ["new", "contacted", "quoted", "converted", "lost"]),
    ("ck_assets_status", "cctv_assets", "status", ["active", "faulty", "under_repair", "replaced", "decommissioned"]),
    ("ck_amc_status", "amc_contracts", "status", ["draft", "active", "expiring", "renewed", "terminated"]),
    ("ck_ticket_status", "service_tickets", "status",
     ["open", "assigned", "in_progress", "pending_parts", "resolved", "closed"]),
    ("ck_ticket_priority", "service_tickets", "priority", ["low", "medium", "high", "critical"]),
    ("ck_invoice_status", "invoices", "status",
     ["draft", "issued", "paid", "partially_paid", "cancelled", "credit_note"]),
    ("ck_quotation_status", "quotations", "status", ["draft", "sent", "approved", "rejected", "expired"]),
    ("ck_vendor_status", "vendors", "status", ["active", "inactive", "blacklisted"]),
    ("ck_installation_status", "installations", "status",
     ["survey_pending", "survey_done", "material_allocated", "in_progress", "completed", "handed_over"]),
    ("ck_pm_status", "pm_schedules", "status", ["planned", "done", "skipped", "rescheduled"]),
]


def upgrade() -> None:
    for name, table, column, values in CHECKS:
        allowed = ", ".join(f"'{v}'" for v in values)
        op.create_check_constraint(name, table, f"{column} IN ({allowed})")


def downgrade() -> None:
    for name, table, _, _ in CHECKS:
        op.drop_constraint(name, table, type_="check")
