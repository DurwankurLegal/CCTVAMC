import asyncio
import os
import uuid
import pkgutil
import importlib
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import select, text
import app.core.database as db
from app.core.security import hash_password

# Import all models
from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.models.company import Company
from app.models.company_template import CompanyTemplate
from app.models.subscription import Module, SaasPlan, PlanModule, TenantSubscription, TenantModule
from app.models.customer import Customer, CustomerSite, CustomerCategory, CustomerStatus, CustomerContact, ContactRole
from app.models.product import Product
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.asset import CCTVAsset, AssetStatus
from app.models.lead import Lead, LeadSource, LeadStatus, LeadCategory, InterestType
from app.models.quotation import Quotation, QuotationStatus
from app.models.sales_order import SalesOrder, SalesOrderStatus
from app.models.rental import RentalUnit, RentalContract, RentalContractLine, RentalMovement
from app.models.amc import AMCContract, AMCStatus, AMCAsset
from app.models.service_ticket import ServiceTicket, TicketPriority, TicketStatus
from app.models.engineer_visit import EngineerVisit, VisitType
from app.models.installation import Installation, InstallationStatus
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.payment import Payment, PaymentMode
from app.models.vendor import Vendor, VendorStatus, PurchaseOrder, VendorPayment, POStatus
from app.models.help import HelpCategory, HelpArticle
from app.models.customer_portal_user import CustomerPortalUser
from app.models.ticket_comment import TicketComment
from app.models.pm_schedule import PMSchedule, PMStatus
from app.models.cash_collection import CashCollection, CashCollectionStatus
from app.models.cash_collection_log import CashCollectionLog

# Load every model module so SQLAlchemy can resolve all relationships
import app.models
for _m in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{_m.name}")

TODAY = date.today()
DEFAULT_PASSWORD = "Passw0rd@123"

# Subscriptions definition for 5 tenants
TENANTS_CONFIG = [
    {
        "slug": "tenant1",
        "name": "Redstar Automation",
        "plan": "enterprise",
        "custom_domain": "apex-cctv.com",
        "custom_email_sender": "billing@apex-cctv.com",
        "modules": ["sales", "rental", "amc", "inventory", "assets"],
        "companies": [
            {
                "name": "Apex CCTV Solutions Pvt Ltd",
                "gst_status": "GST",
                "gstin": "27AAAAA1111A1Z1",
                "address": "Apex Towers, Level 4, Bandra Kurla Complex, Mumbai, MH - 400051",
                "is_default": True
            },
            {
                "name": "Apex Services North",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "Plot 10, Sector 18, Gurugram, HR - 122015",
                "is_default": False
            },
            {
                "name": "Apex Services South",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "42, Richmond Road, Bengaluru, KA - 560025",
                "is_default": False
            },
            {
                "name": "Apex Installations East",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "SALT Lake Sector V, Block EP, Kolkata, WB - 700091",
                "is_default": False
            },
            {
                "name": "Apex Maintenance West",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "Kothrud Industrial Area, Pune, MH - 411038",
                "is_default": False
            }
        ]
    },
    {
        "slug": "tenant2",
        "name": "Durwankur Retail",
        "plan": "starter",
        "custom_domain": "durwankur-cctv.com",
        "custom_email_sender": "sales@durwankur-cctv.com",
        "modules": ["sales", "inventory"],
        "companies": [
            {
                "name": "Durwankur Retail CCTV",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "Ganesh Peth, Commercial Plaza Shop No. 12, Pune, MH - 411002",
                "is_default": True
            }
        ]
    },
    {
        "slug": "tenant3",
        "name": "Skyline Systems Group",
        "plan": "growth",
        "custom_domain": "skyline-systems.in",
        "custom_email_sender": "support@skyline-systems.in",
        "modules": ["sales", "amc", "assets"],
        "companies": [
            {
                "name": "Skyline Systems Pvt Ltd",
                "gst_status": "GST",
                "gstin": "27BBBBB2222B2Z2",
                "address": "Skyline Business Park, Hinjewadi Phase 3, Pune, MH - 411057",
                "is_default": True
            },
            {
                "name": "Skyline Support Services",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "MG Road, Skyline Arcade First Floor, Pune, MH - 411001",
                "is_default": False
            }
        ]
    },
    {
        "slug": "tenant4",
        "name": "Vanguard Industrial",
        "plan": "growth",
        "custom_domain": "vanguard-cctv.co.in",
        "custom_email_sender": "billing@vanguard-cctv.co.in",
        "modules": ["rental", "amc", "assets"],
        "companies": [
            {
                "name": "Vanguard Industrial CCTV Ltd",
                "gst_status": "GST",
                "gstin": "27CCCCC3333C3Z3",
                "address": "MIDC Area, Block G-12, Bhosari, Pune, MH - 411026",
                "is_default": True
            },
            {
                "name": "Vanguard Infrastructure Services",
                "gst_status": "GST",
                "gstin": "27DDDDD4444D4Z4",
                "address": "Chinchwad Station Link Road, Pune, MH - 411019",
                "is_default": False
            }
        ]
    },
    {
        "slug": "tenant5",
        "name": "Alpha Technologies",
        "plan": "enterprise",
        "custom_domain": "alpha-tech.io",
        "custom_email_sender": "accounts@alpha-tech.io",
        "modules": ["sales", "rental", "amc", "inventory", "assets"],
        "companies": [
            {
                "name": "Alpha Technologies Ltd",
                "gst_status": "GST",
                "gstin": "27EEEEE5555E5Z5",
                "address": "Alpha Tech Park, Block B-3, Viman Nagar, Pune, MH - 411014",
                "is_default": True
            },
            {
                "name": "Alpha Tech Rentals",
                "gst_status": "NON_GST",
                "gstin": None,
                "address": "Karve Road, Alpha House, Pune, MH - 411004",
                "is_default": False
            },
            {
                "name": "Alpha Service Logistics",
                "gst_status": "GST",
                "gstin": "27FFFFF6666F6Z6",
                "address": "Senapati Bapat Road, Alpha Logistics Hub, Pune, MH - 411016",
                "is_default": False
            }
        ]
    }
]

async def seed_base_metadata(session) -> tuple[dict, dict]:
    print("🌱 Seeding SaaS Modules and Plans Master...")

    # Seed Modules
    modules_data = [
        ("sales", "Sales Management", "Outright sales, quotations, invoices, payments", False),
        ("rental", "Rental Management", "Rental products, units, recurring contracts, and deployments", False),
        ("amc", "AMC Management", "Annual Maintenance Contracts, service tickets, preventive schedules, engineer visits", False),
        ("inventory", "Inventory Management", "Parts tracking, reorder levels, stock adjustments, purchase orders", False),
        ("assets", "Asset Tracking", "Deployed assets directory tracked at customer sites", False)
    ]
    modules_map = {}
    for code, name, desc, is_core in modules_data:
        m = Module(code=code, name=name, description=desc, is_core=is_core, is_active=True)
        session.add(m)
        modules_map[code] = m

    # Seed SaaS Plans
    plans_data = [
        ("starter", "Starter Package", 2999.0, 5, 25, 3),
        ("growth", "Growth Package", 9999.0, 25, 200, 15),
        ("enterprise", "Enterprise Package", 29999.0, 0, 0, 0)
    ]
    plans_map = {}
    for code, name, price, max_users, max_sites, max_techs in plans_data:
        p = SaasPlan(
            code=code, name=name, price_monthly=price,
            max_users=max_users, max_sites=max_sites, max_technicians=max_techs,
            is_active=True
        )
        session.add(p)
        plans_map[code] = p

    # --- SEED HELP CENTER CATEGORIES & ARTICLES ---
    print("📖 Seeding Help Center documentation...")
    cat_gs = HelpCategory(name="Getting Started", slug="getting-started", display_order=1, icon="BookOutlined")
    cat_crm = HelpCategory(name="CRM (Core)", slug="crm", display_order=2, icon="TeamOutlined")
    cat_sales = HelpCategory(name="Sales", slug="sales", display_order=3, icon="ShoppingCartOutlined")
    cat_rental = HelpCategory(name="Rental", slug="rental", display_order=4, icon="BuildOutlined")
    cat_amc = HelpCategory(name="AMC & Service", slug="amc", display_order=5, icon="ToolOutlined")
    session.add_all([cat_gs, cat_crm, cat_sales, cat_rental, cat_amc])
    await session.flush()

    art_intro = HelpArticle(
        category_id=cat_gs.id, title="Introduction to CCTV ERP", slug="introduction",
        purpose="A high level overview of the CCTV & Computer Hardware SaaS ERP platform.",
        content_markdown="Welcome to the **SaaS ERP Help Center**!\n\nThis application is designed to help you manage your sales, device rentals, AMC service contracts, service tickets, and site installations seamlessly from a single dashboard.\n\n### Main Features\n- **CRM**: Track leads and manage customer directories.\n- **Sales**: Complete invoicing, quotations, and payments.\n- **Rentals**: Track serial-tracked items and monthly billing cycles.\n- **AMC**: Manage annual maintenance contracts and service ticket lifecycles.\n- **Inventory**: Stay updated on parts reorder warnings.\n\n> [!NOTE]\n> Ensure your profile configuration is complete before processing transactions.",
        applicable_module="core", required_permission=None, is_active=True, status="published"
    )
    
    art_login = HelpArticle(
        category_id=cat_gs.id, title="Login & 2FA Setup", slug="login-and-2fa",
        purpose="Instructions on logging in and setting up two-factor authentication.",
        content_markdown="Details on how to log in and configure 2FA.",
        applicable_module="core", required_permission=None, is_active=True, status="published"
    )
    
    art_leads = HelpArticle(
        category_id=cat_crm.id, title="Lead Management Guide", slug="lead-management",
        purpose="Instructions on managing leads.",
        content_markdown="Details on tracking and managing leads.",
        applicable_module="core", required_permission=None, is_active=True, status="published"
    )
    
    art_quotes = HelpArticle(
        category_id=cat_sales.id, title="Creating Quotations", slug="creating-quotations",
        purpose="Instructions on creating quotations.",
        content_markdown="Details on generating quotations.",
        applicable_module="sales", required_permission=None, is_active=True, status="published"
    )
    
    art_orders = HelpArticle(
        category_id=cat_sales.id, title="Sales Orders", slug="sales-orders",
        purpose="Instructions on managing sales orders.",
        content_markdown="Details on sales orders processing.",
        applicable_module="sales", required_permission=None, is_active=True, status="published"
    )
    
    art_rental_ag = HelpArticle(
        category_id=cat_rental.id, title="Rental Agreements", slug="rental-agreements",
        purpose="Instructions on rental contracts.",
        content_markdown="Details on managing rentals.",
        applicable_module="rental", required_permission=None, is_active=True, status="published"
    )
    
    art_visits = HelpArticle(
        category_id=cat_amc.id, title="Technician Site Visits", slug="engineer-visits",
        purpose="Instructions on managing site visits.",
        content_markdown="Details on tracking technician site visits.",
        applicable_module="amc", required_permission=None, is_active=True, status="published"
    )
    
    session.add_all([art_intro, art_login, art_leads, art_quotes, art_orders, art_rental_ag, art_visits])
    return modules_map, plans_map

async def seed_templates(session, tenant_id) -> None:
    from app.models.notification import NotificationTemplate, NotificationChannel
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
    for event_type, (subject, body) in defaults.items():
        session.add(NotificationTemplate(
            tenant_id=tenant_id, event_type=event_type,
            channel=NotificationChannel.IN_APP, subject=subject, body=body, is_active=True))

async def seed_tenant_data(session, config: dict, plans_map: dict) -> None:
    slug = config["slug"]
    print(f"🏢 Seeding data for tenant: {slug}...")

    # 1. Create Tenant
    tenant = Tenant(
        name=config["name"],
        slug=slug,
        plan=config["plan"],
        status="active",
        invoice_prefix=slug[:3].upper(),
        registered_address=f"Registered Head Office, {config['name']}, BKC, Mumbai",
        custom_domain=config["custom_domain"],
        custom_email_sender=config["custom_email_sender"],
        branding={
            "primary_color": "#4f46e5",
            "secondary_color": "#10b981",
            "theme": "dark_mode"
        },
        settings={
            "quotation_settings": {
                "default_terms": "<p>1. Warranty: 12 months carry-in.<br/>2. Payment: 100% advance.<br/>3. Validity: 15 days.</p>"
            }
        },
        email_templates={
            "quote_sent": {
                "subject": "Quotation proposal {{quotation_number}} from " + config["name"],
                "body": "Dear customer, please find attached quotation {{quotation_number}} for {{total_amount}}."
            }
        }
    )
    session.add(tenant)
    await session.flush()

    # 2. Seed default notification templates
    await seed_templates(session, tenant.id)

    # 3. Enable subscribed modules and subscription
    plan = plans_map[config["plan"]]
    session.add(TenantSubscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status="active",
        starts_at=datetime.now(timezone.utc)
    ))
    for module_code in config["modules"]:
        session.add(TenantModule(
            tenant_id=tenant.id,
            module_code=module_code,
            status="active",
            starts_at=datetime.now(timezone.utc)
        ))
    await session.flush()

    # 4. Create Staff Directory (Full range of roles, filled completely)
    pwd_hash = hash_password(DEFAULT_PASSWORD)
    admin_user = User(
        tenant_id=tenant.id, email=f"admin@{slug}.com", full_name=f"{config['name']} Admin",
        hashed_password=pwd_hash, role=TenantRole.ADMIN, is_active=True, phone="9876543210"
    )
    tech_user = User(
        tenant_id=tenant.id, email=f"tech@{slug}.com", full_name=f"{config['name']} Technician",
        hashed_password=pwd_hash, role=TenantRole.TECHNICIAN, is_active=True, phone="9876543211",
        skills=["CCTV installation", "IP networking", "DVR configuration"],
        certifications=["Hikvision Certified Professional"], territory="West Pune", availability="available"
    )
    billing_user = User(
        tenant_id=tenant.id, email=f"billing@{slug}.com", full_name=f"{config['name']} Accountant",
        hashed_password=pwd_hash, role=TenantRole.ACCOUNTS, is_active=True, phone="9876543212"
    )
    manager_user = User(
        tenant_id=tenant.id, email=f"manager@{slug}.com", full_name=f"{config['name']} Manager",
        hashed_password=pwd_hash, role=TenantRole.MANAGER, is_active=True, phone="9876543213"
    )
    coord_user = User(
        tenant_id=tenant.id, email=f"coordinator@{slug}.com", full_name=f"{config['name']} Coordinator",
        hashed_password=pwd_hash, role=TenantRole.COORDINATOR, is_active=True, phone="9876543214"
    )
    viewer_user = User(
        tenant_id=tenant.id, email=f"viewer@{slug}.com", full_name=f"{config['name']} Auditor",
        hashed_password=pwd_hash, role=TenantRole.VIEWER, is_active=True, phone="9876543215"
    )
    session.add_all([admin_user, tech_user, billing_user, manager_user, coord_user, viewer_user])
    await session.flush()

    # Set context tenant_id for SQLAlchemy row gating (RLS)
    await session.execute(text("SELECT set_config('app.tenant_id', :val, false)"), {"val": str(tenant.id)})

    # 5. Create Companies (GST/Non-GST setup)
    created_companies = []
    for c_idx, c_conf in enumerate(config["companies"]):
        c = Company(
            tenant_id=tenant.id,
            name=c_conf["name"],
            gst_status=c_conf["gst_status"],
            gstin=c_conf["gstin"],
            address=c_conf["address"],
            contact_details={
                "email": f"contact@{slug}{c_idx+1}.com",
                "phone": f"98765432{c_idx:02d}",
                "website": f"www.{slug}{c_idx+1}.com"
            },
            bank_details={
                "bank_name": "State Bank of India" if c_idx % 2 == 0 else "HDFC Bank Ltd",
                "account_number": f"10020030040{c_idx}",
                "ifsc_code": "SBIN0000123" if c_idx % 2 == 0 else "HDFC0000111",
                "branch": "BKC Corporate Branch"
            },
            authorized_signatory={
                "name": f"Signatory {c_idx+1}",
                "designation": "Authorized Partner" if c_conf["gst_status"] == "NON_GST" else "Managing Director",
                "signature_url": f"/signatures/sign_{slug}_{c_idx+1}.png"
            },
            logo_url=f"/logos/logo_{slug}_{c_idx+1}.png",
            is_default=c_conf["is_default"],
            is_active=True
        )
        session.add(c)
        await session.flush()
        created_companies.append(c)

        # Seed company document templates
        t_html = "<html><body><h1>Quotation from {{company_name}}</h1><p>Quote Number: {{quotation_number}}</p></body></html>"
        session.add(CompanyTemplate(
            tenant_id=tenant.id, company_id=c.id, document_type="quotation",
            template_html=t_html, header_html="Header", footer_html="Footer",
            selected_style="style1", is_active=True
        ))
        session.add(CompanyTemplate(
            tenant_id=tenant.id, company_id=c.id, document_type="invoice",
            template_html=t_html, header_html="Header", footer_html="Footer",
            selected_style="style2", is_active=True
        ))
        session.add(CompanyTemplate(
            tenant_id=tenant.id, company_id=c.id, document_type="amc_contract",
            template_html=t_html, header_html="Header", footer_html="Footer",
            selected_style="style1", is_active=True
        ))
        await session.flush()

    # 6. Seed Vendors (Procurement)
    vendors = []
    v1 = Vendor(
        tenant_id=tenant.id,
        name=f"SecureDistributors {slug.upper()}",
        vendor_type="supplier",
        status=VendorStatus.ACTIVE,
        phone=f"9922110001",
        email=f"sales@securedistributors-{slug}.com",
        gstin="27VND1111A1Z1",
        address="101, Industrial Area, Phase II, Pune, MH",
        contact_person="Ramesh Kumar",
        payment_terms="Net 30",
        outstanding_payable=50000.0,
        is_active=True
    )
    v2 = Vendor(
        tenant_id=tenant.id,
        name=f"TechParts India {slug.upper()}",
        vendor_type="supplier",
        status=VendorStatus.ACTIVE,
        phone=f"9922110002",
        email=f"support@techparts-{slug}.com",
        gstin="27VND2222B2Z2",
        address="Bandra West, Link Road, Mumbai, MH",
        contact_person="Anita Deshmukh",
        payment_terms="Immediate",
        outstanding_payable=0.0,
        is_active=True
    )
    session.add_all([v1, v2])
    await session.flush()
    vendors.extend([v1, v2])

    # 7. Seed Products and Inventory Items
    products = []
    inv_items = []
    p_configs = [
        ("DOM-CAM-101", "Dome Camera 2MP", "Hikvision", "HK-D2", "camera", 2500.0, 250.0, True, 12, True, True),
        ("BUL-CAM-102", "Bullet Camera 4MP", "Hikvision", "HK-B4", "camera", 3000.0, 300.0, True, 12, True, True),
        ("NVR-08-H2", "NVR 8-Channel Hub", "Hikvision", "HK-N8", "NVR", 8000.0, 800.0, True, 24, True, True),
        ("DVR-08-C1", "DVR 8-Channel Classic", "CP Plus", "CP-D8", "DVR", 6000.0, 600.0, True, 24, True, True),
        ("POE-SW-8P", "PoE Switch 8-Port", "TP-Link", "TP-P8", "switch", 4000.0, 400.0, False, 12, True, True),
        ("HDD-2TB-S", "Surveillance HDD 2TB", "Seagate", "ST-2T", "HDD", 5500.0, 0.0, True, 36, True, False),
        ("CAT6-CABLE", "Cat6 Network Cable 305m", "D-Link", "DL-C6", "accessory", 4500.0, 0.0, False, 0, True, False),
        ("BNC-CONN", "BNC Connector Box 100pcs", "Generic", "GN-BNC", "accessory", 500.0, 0.0, False, 0, True, False)
    ]
    for idx, (sku, name, brand, model, cat, sale_p, rent_p, is_ser, warranty, is_sell, is_rent) in enumerate(p_configs):
        inv = InventoryItem(
            tenant_id=tenant.id,
            part_number=f"PART-{sku}",
            name=name,
            description=f"High-quality {name} for surveillance installations.",
            unit="rolls" if "CABLE" in sku else "box" if "CONN" in sku else "pcs",
            hsn_code="85258900" if "CAM" in sku or "NVR" in sku or "DVR" in sku else "84717020" if "HDD" in sku else "85176200",
            gst_rate=18.0,
            reorder_level=5,
            current_stock=50 if idx % 2 == 0 else 12,
            van_stock=5,
            unit_cost=sale_p * 0.6,
            vendor_id=v1.id if idx % 2 == 0 else v2.id,
            is_active=True
        )
        session.add(inv)
        await session.flush()
        inv_items.append(inv)

        p = Product(
            tenant_id=tenant.id,
            sku=sku,
            name=name,
            brand=brand,
            model=model,
            category=cat,
            hsn_code=inv.hsn_code,
            gst_rate=18.0,
            sale_price=sale_p,
            rental_price=rent_p if is_rent else None,
            is_serial_tracked=is_ser,
            warranty_months=warranty,
            inventory_item_id=inv.id,
            is_sellable=is_sell,
            is_rentable=is_rent,
            is_active=True
        )
        session.add(p)
        await session.flush()
        products.append(p)

    # 8. Seed Purchase Orders & Vendor Payments
    po1 = PurchaseOrder(
        tenant_id=tenant.id,
        po_number=f"PO-{slug.upper()}-2026-00001",
        vendor_id=v1.id,
        status=POStatus.RECEIVED,
        order_date=TODAY - timedelta(days=20),
        line_items=[
            {"item_id": str(inv_items[0].id), "qty": 10, "unit_cost": float(inv_items[0].unit_cost)},
            {"item_id": str(inv_items[1].id), "qty": 10, "unit_cost": float(inv_items[1].unit_cost)}
        ],
        total_amount=10 * float(inv_items[0].unit_cost) + 10 * float(inv_items[1].unit_cost),
        notes="Urgent inventory replenishment"
    )
    po2 = PurchaseOrder(
        tenant_id=tenant.id,
        po_number=f"PO-{slug.upper()}-2026-00002",
        vendor_id=v2.id,
        status=POStatus.SENT,
        order_date=TODAY - timedelta(days=5),
        line_items=[
            {"item_id": str(inv_items[2].id), "qty": 5, "unit_cost": float(inv_items[2].unit_cost)}
        ],
        total_amount=5 * float(inv_items[2].unit_cost),
        notes="Regular restocking order"
    )
    session.add_all([po1, po2])
    await session.flush()

    # Inventory movements for PO1 (received)
    session.add(InventoryMovement(
        tenant_id=tenant.id, item_id=inv_items[0].id, movement_type="purchase",
        quantity=10, reference_type="purchase_order", reference_id=po1.id,
        notes="Received stock from PO"
    ))
    session.add(InventoryMovement(
        tenant_id=tenant.id, item_id=inv_items[1].id, movement_type="purchase",
        quantity=10, reference_type="purchase_order", reference_id=po1.id,
        notes="Received stock from PO"
    ))
    await session.flush()

    # Vendor Payment
    vp = VendorPayment(
        tenant_id=tenant.id,
        vendor_id=v1.id,
        purchase_order_id=po1.id,
        amount=po1.total_amount * 0.5,
        payment_date=TODAY - timedelta(days=15),
        method="neft",
        reference="NEFT-PO1-P1",
        notes="Advance token payment"
    )
    session.add(vp)
    await session.flush()

    # 9. Seed 10 Leads
    leads_list = []
    sources = [LeadSource.WEBSITE, LeadSource.REFERRAL, LeadSource.COLD_CALL, LeadSource.SOCIAL_MEDIA]
    statuses = [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUOTED, LeadStatus.CONVERTED, LeadStatus.LOST]
    categories = [LeadCategory.CHS, LeadCategory.COMMERCIAL, LeadCategory.SINGLE_SHOP]
    interests = [InterestType.NEW_INSTALLATION, InterestType.AMC, InterestType.UPGRADE]
    
    for idx in range(1, 11):
        lead = Lead(
            tenant_id=tenant.id,
            company_id=created_companies[idx % len(created_companies)].id,
            name=f"Lead Prospect {idx}",
            email=f"prospect{idx}@{slug}.com",
            phone=f"90000000{idx:02d}",
            address=f"Prospect Site Address {idx}, Highway Road, Pune",
            category=categories[idx % len(categories)],
            interest_type=interests[idx % len(interests)],
            source=sources[idx % len(sources)],
            status=statuses[idx % len(statuses)],
            notes=f"Detailed evaluation notes for CCTV installation at Prospect site {idx}.",
            assigned_to=tech_user.id if idx % 2 == 0 else admin_user.id,
            follow_up_date=TODAY + timedelta(days=idx),
            lost_reason="Price too high" if statuses[idx % len(statuses)] == LeadStatus.LOST else None
        )
        session.add(lead)
        await session.flush()
        leads_list.append(lead)

    # 10. Seed 10 Customers (CHS Housing and Business Categories)
    cats = [CustomerCategory.CHS, CustomerCategory.COMMERCIAL, CustomerCategory.SINGLE_SHOP]
    cust_list = []
    for idx in range(1, 11):
        cat = cats[idx % len(cats)]
        cust = Customer(
            tenant_id=tenant.id,
            name=f"Customer Enterprise {idx}",
            email=f"customer{idx}@{slug}.com",
            phone=f"91111111{idx:02d}",
            category=cat,
            status=CustomerStatus.ACTIVE,
            billing_address=f"Commercial Arcade Road, Building {idx}, Pune, MH - 4110{idx:02d}",
            shipping_address=f"Commercial Arcade Road, Building {idx}, Pune, MH - 4110{idx:02d}",
            gstin=f"27CUSTM1111A{idx}Z{idx}",
            state_code="27",
            contact_person_name=f"Contact Person {idx}",
            contact_person_phone=f"90000001{idx:02d}",
            authorized_signatory=f"Authorized Signatory {idx}",
            is_active=True
        )
        if cat == CustomerCategory.CHS:
            cust.society_registration_no = f"CHS-REG-{idx:04d}"
        session.add(cust)
        await session.flush()
        cust_list.append(cust)

        # Create Customer Site
        site = CustomerSite(
            tenant_id=tenant.id,
            customer_id=cust.id,
            name="Main Gate Lobby" if idx % 2 == 0 else "Server Room Hub",
            address=f"Site Address {idx}, Ground floor, Building {idx}, Pune",
            latitude=18.5204 + (idx * 0.005),
            longitude=73.8567 + (idx * 0.005),
            contact_person=f"Site Contact {idx}",
            contact_phone=f"90000002{idx:02d}",
            is_active=True
        )
        session.add(site)
        await session.flush()

        # Create Customer Contact
        roles_arr = [ContactRole.ADMIN, ContactRole.ACCOUNTS, ContactRole.TECHNICAL]
        contact = CustomerContact(
            tenant_id=tenant.id,
            customer_id=cust.id,
            name=f"Contact {idx}",
            role=roles_arr[idx % len(roles_arr)],
            phone=f"90000003{idx:02d}",
            email=f"contact{idx}@{slug}.com"
        )
        session.add(contact)
        await session.flush()

        # Map converted leads
        if idx <= len(leads_list):
            lead = leads_list[idx - 1]
            if lead.status == LeadStatus.CONVERTED:
                lead.converted_customer_id = cust.id
                session.add(lead)
                await session.flush()

    # 11. Seed CCTV Assets (Map created assets in memory to avoid greenlet/lazy-load error)
    assets_list = []
    customer_assets_map = {}
    for idx, cust in enumerate(cust_list):
        site = (await session.execute(
            select(CustomerSite).where(CustomerSite.customer_id == cust.id)
        )).scalars().first()
        
        a1 = CCTVAsset(
            tenant_id=tenant.id,
            site_id=site.id,
            serial_number=f"ASSET-{slug.upper()}-CAM-{1000+idx}",
            make="Hikvision",
            model="HK-DOME-2MP",
            asset_type="Camera",
            installation_date=TODAY - timedelta(days=120),
            warranty_expiry=TODAY + timedelta(days=245),
            status=AssetStatus.ACTIVE,
            location_description="Main Lobby Entrance ceiling",
            is_active=True
        )
        a2 = CCTVAsset(
            tenant_id=tenant.id,
            site_id=site.id,
            serial_number=f"ASSET-{slug.upper()}-DVR-{1000+idx}",
            make="CP Plus",
            model="CP-DVR-08",
            asset_type="DVR",
            installation_date=TODAY - timedelta(days=120),
            warranty_expiry=TODAY + timedelta(days=245),
            status=AssetStatus.ACTIVE if idx % 3 != 0 else AssetStatus.FAULTY,
            location_description="Server Rack Room 1",
            is_active=True
        )
        session.add_all([a1, a2])
        await session.flush()
        assets_list.extend([a1, a2])
        customer_assets_map[cust.id] = [a1, a2]

    # 12. Seed Serialized Rental Units
    rental_units = []
    for idx in range(1, 6):
        prod = products[idx % 4]
        ru = RentalUnit(
            tenant_id=tenant.id,
            product_id=prod.id,
            serial_number=f"SR-{slug.upper()}-{prod.sku}-{1000+idx}",
            condition="new" if idx % 2 == 0 else "good",
            status="available",
            purchase_cost=prod.sale_price * 0.5,
            purchase_date=TODAY - timedelta(days=180),
            notes="Ready for deployment",
            is_active=True
        )
        session.add(ru)
        await session.flush()
        rental_units.append(ru)

    # 13. Seed Rental Contracts (if rental is in modules)
    if "rental" in config["modules"] and len(rental_units) > 0:
        for idx in range(2):
            cust = cust_list[idx + 5]
            comp = created_companies[idx % len(created_companies)]
            site = (await session.execute(
                select(CustomerSite).where(CustomerSite.customer_id == cust.id)
            )).scalars().first()
            
            ru = rental_units[idx]
            ru.status = "on_rent"
            session.add(ru)
            await session.flush()
            
            sub = 1500.0
            if comp.gst_status == "GST":
                cgst = round(sub * 0.09, 2)
                sgst = round(sub * 0.09, 2)
                igst = 0.0
                tot = sub + cgst + sgst
            else:
                cgst = 0.0
                sgst = 0.0
                igst = 0.0
                tot = sub
                
            rc = RentalContract(
                tenant_id=tenant.id,
                contract_number=f"RC-{comp.name[:3].upper()}-2026-{idx+1:05d}",
                customer_id=cust.id,
                site_id=site.id,
                company_id=comp.id,
                status="active",
                start_date=TODAY - timedelta(days=30),
                end_date=TODAY + timedelta(days=335),
                billing_cycle="monthly",
                deposit_amount=sub * 2.0,
                deposit_status="paid",
                subtotal=sub,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                total_amount=tot,
                notes="Standard camera rental contract",
                is_active=True
            )
            session.add(rc)
            await session.flush()
            
            line = RentalContractLine(
                tenant_id=tenant.id,
                rental_contract_id=rc.id,
                product_id=ru.product_id,
                rental_unit_id=ru.id,
                quantity=1,
                unit_price=sub,
                gst_rate=18.0,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                total_amount=tot
            )
            session.add(line)
            await session.flush()

            session.add(RentalMovement(
                tenant_id=tenant.id,
                rental_contract_id=rc.id,
                rental_unit_id=ru.id,
                movement_type="check_out",
                movement_date=TODAY - timedelta(days=30),
                condition="new",
                notes="Delivered and tested successfully.",
                charges=0.0,
                recorded_by=tech_user.id
            ))
            await session.flush()

    # 14. Seed Quotations
    quotes_list = []
    for idx in range(5):
        cust = cust_list[idx]
        lead = leads_list[idx]
        comp = created_companies[idx % len(created_companies)]
        
        sub = 15000.0 + (idx * 5000.0)
        if comp.gst_status == "GST":
            cgst = round(sub * 0.09, 2)
            sgst = round(sub * 0.09, 2)
            igst = 0.0
            tot = sub + cgst + sgst
        else:
            cgst = 0.0
            sgst = 0.0
            igst = 0.0
            tot = sub
            
        status_arr = [QuotationStatus.DRAFT, QuotationStatus.SENT, QuotationStatus.APPROVED, QuotationStatus.REJECTED, QuotationStatus.EXPIRED]
        q = Quotation(
            tenant_id=tenant.id,
            company_id=comp.id,
            quotation_number=f"QT-{comp.name[:3].upper()}-2026-{idx+1:05d}",
            customer_id=cust.id,
            lead_id=lead.id,
            status=status_arr[idx],
            line_items=[
                {"description": "CCTV Setup Camera Package", "qty": 4, "rate": sub / 4, "amount": sub}
            ],
            subtotal=sub,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            total_amount=tot,
            terms=tenant.settings.get("quotation_settings", {}).get("default_terms", "Standard terms apply."),
            valid_until=TODAY + timedelta(days=15),
            notes="Discount quote",
            is_active=True
        )
        session.add(q)
        await session.flush()
        quotes_list.append(q)

    # 15. Seed Sales Orders (for approved quotes)
    sales_orders = []
    approved_q = quotes_list[2]
    comp = created_companies[2 % len(created_companies)]
    so = SalesOrder(
        tenant_id=tenant.id,
        order_number=f"SO-{comp.name[:3].upper()}-2026-00001",
        customer_id=approved_q.customer_id,
        quotation_id=approved_q.id,
        status=SalesOrderStatus.CONFIRMED,
        order_date=TODAY - timedelta(days=10),
        delivery_date=TODAY + timedelta(days=5),
        line_items=approved_q.line_items,
        subtotal=approved_q.subtotal,
        cgst_amount=approved_q.cgst_amount,
        sgst_amount=approved_q.sgst_amount,
        igst_amount=approved_q.igst_amount,
        total_amount=approved_q.total_amount,
        supply_state_code="27",
        notes="Delivery scheduled.",
        is_active=True
    )
    session.add(so)
    await session.flush()
    sales_orders.append(so)

    # 16. Seed Invoices
    invoices_list = []
    for idx in range(6):
        cust = cust_list[idx % len(cust_list)]
        comp = created_companies[idx % len(created_companies)]
        
        sub = 10000.0 + (idx * 3000.0)
        if comp.gst_status == "GST":
            cgst = round(sub * 0.09, 2)
            sgst = round(sub * 0.09, 2)
            igst = 0.0
            tot = sub + cgst + sgst
            inv_type = InvoiceType.TAX_INVOICE
        else:
            cgst = 0.0
            sgst = 0.0
            igst = 0.0
            tot = sub
            inv_type = InvoiceType.SIMPLIFIED
            
        status_arr = [
            InvoiceStatus.PAID,
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.CANCELLED,
            InvoiceStatus.DRAFT,
            InvoiceStatus.ISSUED
        ]
        
        inv_date = TODAY - timedelta(days=45) if idx == 5 else TODAY - timedelta(days=15)
        due_date = TODAY - timedelta(days=15) if idx == 5 else TODAY + timedelta(days=15)
        
        paid = tot if idx == 0 else (tot * 0.4) if idx == 2 else 0.0
        
        inv = Invoice(
            tenant_id=tenant.id,
            company_id=comp.id,
            invoice_number=f"INV-{comp.name[:3].upper()}-2026-{idx+1:05d}",
            invoice_type=inv_type,
            customer_id=cust.id,
            status=status_arr[idx],
            invoice_date=inv_date,
            due_date=due_date,
            supply_state_code="27",
            line_items=[
                {"description": "CCTV Hardware and Installation Service", "qty": 1, "rate": sub, "amount": sub}
            ],
            subtotal=sub,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            total_amount=tot,
            amount_paid=paid,
            notes="Thank you for your business." if idx != 5 else "OVERDUE: Payment reminders sent.",
            is_active=True
        )
        session.add(inv)
        await session.flush()
        invoices_list.append(inv)

    # 17. Seed Payments
    p1 = Payment(
        tenant_id=tenant.id,
        invoice_id=invoices_list[0].id,
        customer_id=invoices_list[0].customer_id,
        amount=invoices_list[0].total_amount,
        payment_date=TODAY - timedelta(days=10),
        mode=PaymentMode.UPI,
        reference_number="UPI-PAYMENT-REF-1001",
        notes="UPI payment complete."
    )
    p2 = Payment(
        tenant_id=tenant.id,
        invoice_id=invoices_list[2].id,
        customer_id=invoices_list[2].customer_id,
        amount=invoices_list[2].amount_paid,
        payment_date=TODAY - timedelta(days=5),
        mode=PaymentMode.CHEQUE,
        reference_number="CHQ-778811",
        notes="Cheque deposit."
    )
    session.add_all([p1, p2])
    await session.flush()

    # 18. Seed AMC Contracts
    amc_contracts = []
    for idx in range(5):
        cust = cust_list[idx]
        comp = created_companies[idx % len(created_companies)]
        status_arr = [AMCStatus.ACTIVE, AMCStatus.EXPIRING, AMCStatus.DRAFT, AMCStatus.TERMINATED, AMCStatus.RENEWED]
        
        start_d = TODAY - timedelta(days=90) if idx != 1 else TODAY - timedelta(days=350)
        end_d = TODAY + timedelta(days=275) if idx != 1 else TODAY + timedelta(days=15)
        
        c = AMCContract(
            tenant_id=tenant.id,
            company_id=comp.id,
            customer_id=cust.id,
            contract_number=f"AMC-{comp.name[:3].upper()}-2026-{idx+1:04d}",
            status=status_arr[idx],
            start_date=start_d,
            end_date=end_d,
            annual_amount=24000.0 + (idx * 6000.0),
            payment_frequency="quarterly" if idx != 2 else "annual",
            preventive_visits_per_year=4 if idx != 2 else 2,
            terms="Preventive visits quarterly. Response within 24 hours of ticket logging.",
            is_active=True
        )
        session.add(c)
        await session.flush()
        amc_contracts.append(c)
        
        # Link some assets to contract (using in-memory map to avoid lazy load issues)
        cust_assets = customer_assets_map.get(cust.id, [])
        for asset in cust_assets:
            session.add(AMCAsset(
                tenant_id=tenant.id,
                contract_id=c.id,
                asset_id=asset.id
            ))
        await session.flush()

        # Seed PM Schedules for Active/Expiring contracts (idx=0 and idx=1)
        if idx in (0, 1):
            visits_count = c.preventive_visits_per_year
            for v_idx in range(1, visits_count + 1):
                offset_days = (365 // visits_count) * (v_idx - 1)
                sch_date = start_d + timedelta(days=offset_days)
                status_val = PMStatus.DONE if sch_date <= TODAY else PMStatus.PLANNED
                
                session.add(PMSchedule(
                    tenant_id=tenant.id,
                    amc_contract_id=c.id,
                    sequence_no=v_idx,
                    scheduled_date=sch_date,
                    status=status_val,
                    notes=f"Preventive maintenance visit sequence {v_idx}"
                ))
            await session.flush()

    # 19. Seed Service Tickets & Comments
    tickets_list = []
    for idx in range(5):
        cust = cust_list[idx]
        comp = created_companies[idx % len(created_companies)]
        contract = amc_contracts[idx]
        cust_assets = customer_assets_map.get(cust.id, [])
        asset_id = cust_assets[0].id if cust_assets else None
        site = (await session.execute(
            select(CustomerSite).where(CustomerSite.customer_id == cust.id)
        )).scalars().first()
        
        status_arr = [TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED]
        priority_arr = [TicketPriority.HIGH, TicketPriority.CRITICAL, TicketPriority.MEDIUM, TicketPriority.LOW, TicketPriority.HIGH]
        complaints = [
            "Camera 1 at main entrance shows black screen",
            "NVR beep sound constantly and no recording disk error",
            "Camera view in lobby is blurry / out of focus",
            "Preventive checkup ticket: clear dust and adjust bracket",
            "Technician visit request: camera 3 network link flapping"
        ]
        
        t = ServiceTicket(
            tenant_id=tenant.id,
            company_id=comp.id,
            ticket_number=f"TKT-{comp.name[:3].upper()}-2026-{idx+1:05d}",
            customer_id=cust.id,
            site_id=site.id,
            asset_id=asset_id,
            amc_contract_id=contract.id if idx != 4 else None,
            status=status_arr[idx],
            priority=priority_arr[idx],
            complaint=complaints[idx],
            assigned_to=tech_user.id if idx > 0 else None,
            sla_due_at=datetime.combine(TODAY + timedelta(days=2), datetime.min.time(), timezone.utc),
            sla_breached=False,
            resolved_at=datetime.combine(TODAY - timedelta(days=2), datetime.min.time(), timezone.utc) if idx in (3, 4) else None,
            closed_at=datetime.combine(TODAY - timedelta(days=1), datetime.min.time(), timezone.utc) if idx == 4 else None,
            resolution_notes="Cleaned dome, re-aligned mount." if idx in (3, 4) else None
        )
        session.add(t)
        await session.flush()
        tickets_list.append(t)

        # Add ticket comments
        if idx in (1, 2):
            session.add(TicketComment(
                tenant_id=tenant.id,
                ticket_id=t.id,
                author_id=tech_user.id,
                body="I have reviewed the camera status. Will visit site tomorrow morning."
            ))
            session.add(TicketComment(
                tenant_id=tenant.id,
                ticket_id=t.id,
                author_id=admin_user.id,
                body="Customer requested callback before technician arrival."
            ))
            await session.flush()

    # 20. Seed Engineer Visits
    for idx in [2, 3, 4]:
        t = tickets_list[idx]
        visit = EngineerVisit(
            tenant_id=tenant.id,
            ticket_id=t.id,
            amc_contract_id=t.amc_contract_id,
            technician_id=tech_user.id,
            visit_type=VisitType.CORRECTIVE,
            checkin_at=datetime.combine(TODAY - timedelta(days=idx), datetime.min.time(), timezone.utc),
            checkout_at=datetime.combine(TODAY - timedelta(days=idx), datetime.min.time(), timezone.utc) + timedelta(hours=2),
            checkin_lat=18.5204,
            checkin_lng=73.8567,
            checkout_lat=18.5205,
            checkout_lng=73.8568,
            work_performed="Tightened BNC cable connections and cleaned camera sensor.",
            parts_used=[{"item_id": str(inv_items[7].id), "qty": 2, "description": "BNC Connector"}],
            photo_urls=["/visits/visit_photo_1.jpg"],
            signature_url=f"/visits/signature_{t.ticket_number}.png",
            customer_feedback="Excellent and prompt resolution.",
            is_synced=True
        )
        session.add(visit)
        await session.flush()

    # 21. Seed Installations
    for idx in range(3):
        cust = cust_list[idx + 7]
        comp = created_companies[idx % len(created_companies)]
        site = (await session.execute(
            select(CustomerSite).where(CustomerSite.customer_id == cust.id)
        )).scalars().first()
        
        status_arr = [InstallationStatus.SURVEY_PENDING, InstallationStatus.IN_PROGRESS, InstallationStatus.HANDED_OVER]
        
        inst = Installation(
            tenant_id=tenant.id,
            work_order_number=f"WO-{comp.name[:3].upper()}-2026-{idx+1:05d}",
            customer_id=cust.id,
            site_id=site.id,
            quotation_id=None,
            status=status_arr[idx],
            survey_date=TODAY - timedelta(days=15) if idx > 0 else None,
            survey_notes="Site surveyed. 4 cameras needed." if idx > 0 else None,
            feasibility_notes="Feasible, standard mounting heights." if idx > 0 else None,
            recommended_camera_count=4 if idx > 0 else None,
            assigned_technician_id=tech_user.id if idx > 0 else None,
            target_completion_date=TODAY + timedelta(days=5) if idx == 1 else TODAY - timedelta(days=2) if idx == 2 else None,
            handover_otp="123456" if idx == 2 else None,
            handed_over_at=datetime.combine(TODAY - timedelta(days=2), datetime.min.time(), timezone.utc) if idx == 2 else None,
            amc_contract_id=amc_contracts[idx].id if idx == 2 else None
        )
        session.add(inst)
        await session.flush()

    # 22. Seed Cash Collections & Logs
    for idx in range(3):
        cust = cust_list[idx]
        comp = created_companies[idx % len(created_companies)]
        status_arr = [CashCollectionStatus.PENDING, CashCollectionStatus.RECEIVED, CashCollectionStatus.REJECTED]
        
        cc = CashCollection(
            tenant_id=tenant.id,
            employee_id=tech_user.id,
            customer_name=cust.name,
            company_id=comp.id,
            service_ticket_id=tickets_list[idx].id,
            invoice_id=invoices_list[idx].id,
            amount=1500.0 + (idx * 1000.0),
            collected_at=datetime.combine(TODAY - timedelta(days=idx+1), datetime.min.time(), timezone.utc),
            payment_mode="CASH",
            remarks=f"Cash payment collected by technician {idx+1}",
            receipt_photo_url=f"/receipts/cc_{idx+1}.jpg",
            status=status_arr[idx]
        )
        session.add(cc)
        await session.flush()
        
        if status_arr[idx] in [CashCollectionStatus.RECEIVED, CashCollectionStatus.REJECTED]:
            log_action = "APPROVED" if status_arr[idx] == CashCollectionStatus.RECEIVED else "REJECTED"
            session.add(CashCollectionLog(
                tenant_id=tenant.id,
                cash_collection_id=cc.id,
                action=log_action,
                action_by=admin_user.id,
                action_at=datetime.now(timezone.utc),
                notes="Cleared by Admin" if log_action == "APPROVED" else "Mismatch in cash amount, rejected."
            ))
            await session.flush()

    # 23. Seed Portal Users
    portal_email = f"portal@{slug}.com"
    session.add(CustomerPortalUser(
        tenant_id=tenant.id,
        customer_id=cust_list[0].id,
        email=portal_email,
        full_name=f"{cust_list[0].name} Portal User",
        hashed_password=pwd_hash
    ))
    await session.flush()

    print(f"✔ Successfully provisioned and seeded tenant: {slug} with {len(created_companies)} companies, 10 leads, and 10 customers.")

async def main():
    db._init_engine()
    
    # 1. Create Base Modules & Plans
    async with db._AsyncSessionLocal() as session:
        modules_map, plans_map = await seed_base_metadata(session)
        await session.commit()

    # 2. Seed Platform Superadmin
    async with db._AsyncSessionLocal() as p_session:
        durwankur = Tenant(
            name="Durwankur Platform",
            slug="durwankur",
            plan="enterprise",
            status="active",
            invoice_prefix="DUR"
        )
        p_session.add(durwankur)
        await p_session.flush()
        
        pwd_hash = hash_password("Platform@1234")
        plat_admin = User(
            tenant_id=durwankur.id,
            email="platform@durwankur.ai",
            full_name="Platform Superadmin",
            hashed_password=pwd_hash,
            role=TenantRole.ADMIN,
            is_active=True,
            is_platform_admin=True
        )
        p_session.add(plat_admin)
        await p_session.commit()
        print("✔ Seeded platform superadmin: platform@durwankur.ai (password: Platform@1234)")

    # 3. Seed the 5 tenants & multi-company combinations
    for config in TENANTS_CONFIG:
        async with db._AsyncSessionLocal() as t_session:
            await seed_tenant_data(t_session, config, plans_map)
            await t_session.commit()
    
    print("\n🎉 Seed of all UAT combinations completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
