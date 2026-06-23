"""Seed the database with a starter tenant, an admin user, and sample data.

Idempotent: running it multiple times will not create duplicates.

Usage (from the backend/ directory, with venv active):

    python -m scripts.seed

Or via the running API container:

    docker compose exec api python -m scripts.seed

Default admin credentials (override with env vars):
    SEED_ADMIN_EMAIL    (default: admin@durwankur.ai)
    SEED_ADMIN_PASSWORD (default: Admin@1234)
    SEED_TENANT_NAME    (default: Durwankur)

Set SEED_SAMPLE_DATA=false to seed only the tenant + admin user.
"""

import asyncio
import os
from datetime import date, timedelta

from sqlalchemy import select, text

import importlib
import pkgutil

import app.core.database as db
import app.models
from app.core.security import hash_password
from app.models.amc import AMCContract, AMCStatus

# Load every model module so SQLAlchemy can resolve all relationships
for _m in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{_m.name}")
from app.models.customer import Customer, CustomerCategory
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.payment import Payment, PaymentMode
from app.models.service_ticket import ServiceTicket, TicketPriority, TicketStatus
from app.models.tenant import Tenant
from app.models.user import TenantRole, User

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@durwankur.ai")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@1234")
ADMIN_NAME = os.getenv("SEED_ADMIN_NAME", "Admin")
TENANT_NAME = os.getenv("SEED_TENANT_NAME", "Durwankur")
TENANT_SLUG = os.getenv("SEED_TENANT_SLUG", "durwankur")
SAMPLE_DATA = os.getenv("SEED_SAMPLE_DATA", "true").lower() != "false"

# Platform admin (Durwankur operator) — manages tenants/subscriptions via the
# platform-admin console. Distinct from a tenant admin.
PLATFORM_ADMIN_EMAIL = os.getenv("SEED_PLATFORM_ADMIN_EMAIL", "platform@durwankur.ai")
PLATFORM_ADMIN_PASSWORD = os.getenv("SEED_PLATFORM_ADMIN_PASSWORD", "Platform@1234")

# Second tenant so isolation / acceptance scenarios have at least two tenants.
TENANT2_NAME = os.getenv("SEED_TENANT2_NAME", "Skyline Security")
TENANT2_SLUG = os.getenv("SEED_TENANT2_SLUG", "skyline")
TENANT2_ADMIN_EMAIL = os.getenv("SEED_TENANT2_ADMIN_EMAIL", "admin@skyline.in")

DEFAULT_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD", "Passw0rd@123")

TODAY = date.today()


async def seed_templates(session, tenant_id) -> None:
    """Seed default in-app notification templates per tenant (SRS 4.17)."""
    from app.models.notification import NotificationTemplate, NotificationChannel
    # Bodies use the engine's Handlebars-style {{placeholder}} syntax.
    defaults = {
        "ticket_assigned": ("Ticket assigned", "Ticket {{ticket_number}} ({{priority}}) assigned to you."),
        "customer_ticket_created": ("New customer ticket", "Customer raised {{ticket_number}} ({{priority}}): {{complaint}}"),
        "customer_ticket_comment": ("Customer replied", "New customer comment on ticket {{ticket_id}}."),
        "sla_breach": ("SLA breached", "Ticket {{ticket_number}} has breached its SLA."),
        "quote_approved": ("Quotation approved", "Quotation {{quotation_number}} was approved."),
        "quote_rejected": ("Quotation rejected", "Quotation {{quotation_number}} was rejected."),
        "low_stock": ("Low stock alert", "{{item}} is low: {{current_stock}} (reorder at {{reorder_level}})."),
        "purchase_order_created": ("Purchase order created", "PO {{po_number}} for {{vendor}} (₹{{total}})."),
        "installation_handover": ("Installation handover", "Installation handover completed."),
        "amc_expiry": ("AMC expiring", "AMC contract is expiring soon."),
        "payment_due": ("Payment due", "Invoice payment is due."),
    }
    existing = (await session.execute(
        select(NotificationTemplate).where(NotificationTemplate.tenant_id == tenant_id).limit(1)
    )).scalar_one_or_none()
    if existing is not None:
        return
    for event_type, (subject, body) in defaults.items():
        session.add(NotificationTemplate(
            tenant_id=tenant_id, event_type=event_type,
            channel=NotificationChannel.IN_APP, subject=subject, body=body, is_active=True))
    print(f"✔ Seeded {len(defaults)} notification templates")


async def ensure_user(session, tenant_id, email, full_name, role,
                      password=DEFAULT_PASSWORD, is_platform_admin=False):
    """Idempotently create a user (by email). Returns the user."""
    from app.models.user import User
    existing = (await session.execute(
        select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        print(f"• User already exists: {email}")
        return existing
    user = User(
        tenant_id=tenant_id, email=email, full_name=full_name,
        hashed_password=hash_password(password), role=role, is_active=True,
        is_platform_admin=is_platform_admin,
    )
    session.add(user)
    await session.flush()
    flag = " [platform-admin]" if is_platform_admin else ""
    print(f"✔ Created user: {email} ({role}){flag}")
    return user


def gst_split(subtotal: float) -> dict:
    """Compute 18% GST (9% CGST + 9% SGST) for an intra-state supply."""
    cgst = round(subtotal * 0.09, 2)
    sgst = round(subtotal * 0.09, 2)
    return {
        "subtotal": subtotal,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": 0,
        "total_amount": round(subtotal + cgst + sgst, 2),
    }


async def seed_sample_data(session, tenant_id) -> None:
    """Create customers, leads, AMC contracts, invoices, payments, tickets."""

    # Skip if customers already exist (idempotency guard for sample data)
    existing = (
        await session.execute(select(Customer).limit(1))
    ).scalar_one_or_none()
    if existing is not None:
        print("• Sample data already present — skipping")
        return

    # ── 5 Customers ───────────────────────────────────────────
    customers = [
        Customer(tenant_id=tenant_id, name="Green Valley CHS", category=CustomerCategory.CHS,
                 phone="9820011001", email="office@greenvalley.in", state_code="27",
                 address="Andheri West, Mumbai", contact_person_name="Mr. Rao"),
        Customer(tenant_id=tenant_id, name="Sunrise Apartments", category=CustomerCategory.CHS,
                 phone="9820011002", email="admin@sunrise.in", state_code="27",
                 address="Powai, Mumbai", contact_person_name="Mrs. Iyer"),
        Customer(tenant_id=tenant_id, name="MegaMart Retail", category=CustomerCategory.COMMERCIAL,
                 phone="9820011003", email="facilities@megamart.in", state_code="27",
                 address="Lower Parel, Mumbai", contact_person_name="Mr. Shah"),
        Customer(tenant_id=tenant_id, name="TechPark Offices", category=CustomerCategory.COMMERCIAL,
                 phone="9820011004", email="security@techpark.in", state_code="27",
                 address="BKC, Mumbai", contact_person_name="Ms. Nair"),
        Customer(tenant_id=tenant_id, name="Corner Electronics", category=CustomerCategory.SINGLE_SHOP,
                 phone="9820011005", email="owner@cornerelec.in", state_code="27",
                 address="Dadar, Mumbai", contact_person_name="Mr. Khan"),
    ]
    session.add_all(customers)
    await session.flush()
    print(f"✔ Created {len(customers)} customers")

    # ── 10 Leads (5 converted to the customers above) ─────────
    leads = []
    for i, cust in enumerate(customers):
        leads.append(Lead(
            tenant_id=tenant_id, name=cust.name, phone=cust.phone, email=cust.email,
            source=LeadSource.REFERRAL, status=LeadStatus.CONVERTED,
            converted_customer_id=cust.id, notes="Converted to customer",
        ))
    pending_leads = [
        ("Riverside Mall", LeadSource.WEBSITE, LeadStatus.QUOTED),
        ("City Hospital", LeadSource.COLD_CALL, LeadStatus.CONTACTED),
        ("Lotus School", LeadSource.WALK_IN, LeadStatus.NEW),
        ("Star Hotel", LeadSource.SOCIAL_MEDIA, LeadStatus.QUOTED),
        ("Metro Warehouse", LeadSource.REFERRAL, LeadStatus.LOST),
    ]
    for name, src, st in pending_leads:
        leads.append(Lead(
            tenant_id=tenant_id, name=name, phone="98200200" + str(len(leads)),
            source=src, status=st, follow_up_date=TODAY + timedelta(days=7),
        ))
    session.add_all(leads)
    await session.flush()
    print(f"✔ Created {len(leads)} leads (5 converted)")

    # ── 5 AMC Contracts (4 active, 1 draft/pending) ───────────
    contracts = [
        AMCContract(tenant_id=tenant_id, customer_id=customers[0].id, contract_number="AMC-2026-0001",
                    status=AMCStatus.ACTIVE, start_date=TODAY - timedelta(days=60),
                    end_date=TODAY + timedelta(days=305), annual_amount=24000,
                    payment_frequency="quarterly", preventive_visits_per_year=4),
        AMCContract(tenant_id=tenant_id, customer_id=customers[1].id, contract_number="AMC-2026-0002",
                    status=AMCStatus.ACTIVE, start_date=TODAY - timedelta(days=30),
                    end_date=TODAY + timedelta(days=335), annual_amount=18000,
                    payment_frequency="annual", preventive_visits_per_year=2),
        AMCContract(tenant_id=tenant_id, customer_id=customers[2].id, contract_number="AMC-2026-0003",
                    status=AMCStatus.ACTIVE, start_date=TODAY - timedelta(days=90),
                    end_date=TODAY + timedelta(days=275), annual_amount=48000,
                    payment_frequency="quarterly", preventive_visits_per_year=4),
        AMCContract(tenant_id=tenant_id, customer_id=customers[3].id, contract_number="AMC-2026-0004",
                    status=AMCStatus.ACTIVE, start_date=TODAY - timedelta(days=15),
                    end_date=TODAY + timedelta(days=350), annual_amount=60000,
                    payment_frequency="monthly", preventive_visits_per_year=6),
        AMCContract(tenant_id=tenant_id, customer_id=customers[4].id, contract_number="AMC-2026-0005",
                    status=AMCStatus.DRAFT, start_date=TODAY,
                    end_date=TODAY + timedelta(days=365), annual_amount=12000,
                    payment_frequency="annual", preventive_visits_per_year=2),
    ]
    session.add_all(contracts)
    await session.flush()
    print(f"✔ Created {len(contracts)} AMC contracts (4 active, 1 draft)")

    # ── 6 Invoices (3 paid on time, 2 follow-up, 1 default) ───
    def make_invoice(num, cust, amc, subtotal, status, inv_date, due_date, paid, notes=""):
        g = gst_split(subtotal)
        return Invoice(
            tenant_id=tenant_id, invoice_number=num, invoice_type=InvoiceType.TAX_INVOICE,
            customer_id=cust.id, amc_contract_id=amc.id if amc else None, status=status,
            invoice_date=inv_date, due_date=due_date, supply_state_code="27",
            line_items=[{"description": "CCTV AMC Service", "qty": 1, "rate": subtotal, "amount": subtotal}],
            amount_paid=paid, notes=notes, **g,
        )

    invoices = [
        # 3 paid on time
        make_invoice("INV-2026-001", customers[0], contracts[0], 6000, InvoiceStatus.PAID,
                     TODAY - timedelta(days=50), TODAY - timedelta(days=35), gst_split(6000)["total_amount"]),
        make_invoice("INV-2026-002", customers[1], contracts[1], 18000, InvoiceStatus.PAID,
                     TODAY - timedelta(days=25), TODAY - timedelta(days=10), gst_split(18000)["total_amount"]),
        make_invoice("INV-2026-003", customers[2], contracts[2], 12000, InvoiceStatus.PAID,
                     TODAY - timedelta(days=80), TODAY - timedelta(days=65), gst_split(12000)["total_amount"]),
        # 2 needs follow-up (issued, due soon / recently overdue, unpaid)
        make_invoice("INV-2026-004", customers[3], contracts[3], 5000, InvoiceStatus.ISSUED,
                     TODAY - timedelta(days=20), TODAY - timedelta(days=5), 0,
                     notes="Follow-up: payment reminder sent"),
        make_invoice("INV-2026-005", customers[2], contracts[2], 12000, InvoiceStatus.ISSUED,
                     TODAY - timedelta(days=15), TODAY + timedelta(days=10), 0,
                     notes="Follow-up: awaiting PO confirmation"),
        # 1 in default (very overdue, unpaid)
        make_invoice("INV-2026-006", customers[4], None, 9000, InvoiceStatus.ISSUED,
                     TODAY - timedelta(days=90), TODAY - timedelta(days=60), 0,
                     notes="DEFAULTER: no response after multiple reminders"),
    ]
    session.add_all(invoices)
    await session.flush()
    print(f"✔ Created {len(invoices)} invoices (3 paid, 2 follow-up, 1 default)")

    # ── 4 Payments (one per paid invoice + a partial) ─────────
    payments = [
        Payment(tenant_id=tenant_id, invoice_id=invoices[0].id, customer_id=customers[0].id,
                amount=invoices[0].total_amount, payment_date=TODAY - timedelta(days=40),
                mode=PaymentMode.UPI, reference_number="UPI-7781"),
        Payment(tenant_id=tenant_id, invoice_id=invoices[1].id, customer_id=customers[1].id,
                amount=invoices[1].total_amount, payment_date=TODAY - timedelta(days=12),
                mode=PaymentMode.NEFT, reference_number="NEFT-4421"),
        Payment(tenant_id=tenant_id, invoice_id=invoices[2].id, customer_id=customers[2].id,
                amount=invoices[2].total_amount, payment_date=TODAY - timedelta(days=70),
                mode=PaymentMode.CHEQUE, reference_number="CHQ-009812"),
        Payment(tenant_id=tenant_id, invoice_id=invoices[2].id, customer_id=customers[2].id,
                amount=1000, payment_date=TODAY - timedelta(days=68),
                mode=PaymentMode.CASH, reference_number=None, notes="Adjustment"),
    ]
    session.add_all(payments)
    print(f"✔ Created {len(payments)} payments")

    # ── 3 Service Tickets ─────────────────────────────────────
    tickets = [
        ServiceTicket(tenant_id=tenant_id, ticket_number="TKT-2026-001", customer_id=customers[0].id,
                      amc_contract_id=contracts[0].id, status=TicketStatus.OPEN,
                      priority=TicketPriority.HIGH, complaint="Camera 3 in lobby not recording"),
        ServiceTicket(tenant_id=tenant_id, ticket_number="TKT-2026-002", customer_id=customers[2].id,
                      amc_contract_id=contracts[2].id, status=TicketStatus.IN_PROGRESS,
                      priority=TicketPriority.MEDIUM, complaint="DVR storage full, footage overwriting early"),
        ServiceTicket(tenant_id=tenant_id, ticket_number="TKT-2026-003", customer_id=customers[3].id,
                      amc_contract_id=contracts[3].id, status=TicketStatus.RESOLVED,
                      priority=TicketPriority.LOW, complaint="Night vision blurry on gate camera",
                      resolution_notes="Cleaned lens and adjusted IR settings"),
    ]
    session.add_all(tickets)
    print(f"✔ Created {len(tickets)} service tickets")

    # ── Customer portal user (self-service) — linked to first customer ──
    from app.models.customer_portal_user import CustomerPortalUser
    portal_email = "portal@greenvalley.in"
    existing_portal = (await session.execute(
        select(CustomerPortalUser).where(CustomerPortalUser.email == portal_email)
    )).scalar_one_or_none()
    if existing_portal is None:
        session.add(CustomerPortalUser(
            tenant_id=tenant_id, customer_id=customers[0].id, email=portal_email,
            full_name="Green Valley Portal", hashed_password=hash_password(DEFAULT_PASSWORD),
        ))
        print(f"✔ Created portal user: {portal_email} (customer: {customers[0].name})")

    await session.commit()


async def seed() -> None:
    db._init_engine()
    async with db._AsyncSessionLocal() as session:
        # ── Tenant ────────────────────────────────────────────
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                plan="starter",
                status="active",
                invoice_prefix="INV",
            )
            session.add(tenant)
            await session.flush()
            print(f"✔ Created tenant: {TENANT_NAME} ({tenant.id})")
        else:
            print(f"• Tenant already exists: {TENANT_NAME} ({tenant.id})")

        # RLS requires app.tenant_id to be set before touching tenant-scoped tables
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": str(tenant.id)},
        )

        # ── Users (platform admin, tenant admin, technician, accounts) ──
        await ensure_user(session, tenant.id, ADMIN_EMAIL, ADMIN_NAME,
                          TenantRole.ADMIN, password=ADMIN_PASSWORD)
        await ensure_user(session, tenant.id, PLATFORM_ADMIN_EMAIL, "Platform Admin",
                          TenantRole.ADMIN, password=PLATFORM_ADMIN_PASSWORD,
                          is_platform_admin=True)
        await ensure_user(session, tenant.id, "tech@durwankur.ai", "Ravi Technician",
                          TenantRole.TECHNICIAN)
        # "accounts" is a custom RBAC role string (billing user) — see permissions matrix.
        await ensure_user(session, tenant.id, "billing@durwankur.ai", "Billing User", "accounts")
        await seed_templates(session, tenant.id)

        await session.commit()

        # ── Second tenant (isolation / acceptance scenarios) ──
        tenant2 = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT2_SLUG))
        ).scalar_one_or_none()
        if tenant2 is None:
            tenant2 = Tenant(name=TENANT2_NAME, slug=TENANT2_SLUG, plan="growth",
                             status="active", invoice_prefix="SKY")
            session.add(tenant2)
            await session.flush()
            print(f"✔ Created tenant: {TENANT2_NAME} ({tenant2.id})")
        else:
            print(f"• Tenant already exists: {TENANT2_NAME} ({tenant2.id})")
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": str(tenant2.id)},
        )
        await ensure_user(session, tenant2.id, TENANT2_ADMIN_EMAIL, "Skyline Admin",
                          TenantRole.ADMIN)
        await ensure_user(session, tenant2.id, "tech@skyline.in", "Skyline Technician",
                          TenantRole.TECHNICIAN)
        await seed_templates(session, tenant2.id)
        await session.commit()

        # ── Sample data (primary tenant) ──────────────────────
        if SAMPLE_DATA:
            # Re-assert RLS context for the new transaction
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, false)"),
                {"tid": str(tenant.id)},
            )
            await seed_sample_data(session, tenant.id)

    print("\nSeed complete.")
    print(f"  Platform admin: {PLATFORM_ADMIN_EMAIL} / {PLATFORM_ADMIN_PASSWORD}")
    print(f"  Tenant admin:   {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Technician:     tech@durwankur.ai / {DEFAULT_PASSWORD}")
    print(f"  Accounts:       billing@durwankur.ai / {DEFAULT_PASSWORD}")
    print(f"  Tenant 2 admin: {TENANT2_ADMIN_EMAIL} / {DEFAULT_PASSWORD}")
    if SAMPLE_DATA:
        print(f"  Portal user:    portal@greenvalley.in / {DEFAULT_PASSWORD} (tenant_slug: {TENANT_SLUG})")


if __name__ == "__main__":
    asyncio.run(seed())
