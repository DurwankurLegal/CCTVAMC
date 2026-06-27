import asyncio
import os
import uuid
from datetime import date, datetime, timezone, timedelta
from sqlalchemy import select, text
import app.core.database as db
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.models.company import Company
from app.models.subscription import Module, SaasPlan, PlanModule, TenantSubscription, TenantModule
from app.models.customer import Customer, CustomerSite, CustomerCategory, CustomerStatus
from app.models.product import Product
from app.models.inventory import InventoryItem
from app.models.asset import CCTVAsset, AssetStatus
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.quotation import Quotation, QuotationStatus
from app.models.sales_order import SalesOrder, SalesOrderStatus
from app.models.rental import RentalUnit, RentalContract, RentalContractLine
from app.models.amc import AMCContract, AMCStatus
from app.models.service_ticket import ServiceTicket, TicketPriority, TicketStatus
from app.models.engineer_visit import EngineerVisit
from app.models.installation import Installation
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.payment import Payment, PaymentMode
from app.models.vendor import Vendor, VendorStatus, PurchaseOrder, VendorPayment, POStatus
from app.models.help import HelpCategory, HelpArticle, HelpFAQ, HelpAttachment
from app.models.customer_portal_user import CustomerPortalUser

TODAY = date.today()
DEFAULT_PASSWORD = "Passw0rd@123"

# Subscriptions definition for Company A, B, C, D, E
SUBSCRIPTION_COMBINATIONS = [
    {
        "slug": "company-a",
        "name": "Company A (Sales Only)",
        "modules": ["sales", "inventory"]
    },
    {
        "slug": "company-b",
        "name": "Company B (Rental Only)",
        "modules": ["rental", "assets"]
    },
    {
        "slug": "company-c",
        "name": "Company C (AMC Only)",
        "modules": ["amc", "assets"]
    },
    {
        "slug": "company-d",
        "name": "Company D (Sales and Rental)",
        "modules": ["sales", "rental", "inventory", "assets"]
    },
    {
        "slug": "company-e",
        "name": "Company E (Sales, Rental and AMC)",
        "modules": ["sales", "rental", "amc", "inventory", "assets"]
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

    # Introduction
    art_intro = HelpArticle(
        category_id=cat_gs.id, title="Introduction to CCTV ERP", slug="introduction",
        purpose="A high level overview of the CCTV & Computer Hardware SaaS ERP platform.",
        content_markdown="Welcome to the **SaaS ERP Help Center**!\n\nThis application is designed to help you manage your sales, device rentals, AMC service contracts, service tickets, and site installations seamlessly from a single dashboard.\n\n### Main Features\n- **CRM**: Track leads and manage customer directories.\n- **Sales**: Complete invoicing, quotations, and payments.\n- **Rentals**: Track serial-tracked items and monthly billing cycles.\n- **AMC**: Manage annual maintenance contracts and service ticket lifecycles.\n- **Inventory**: Stay updated on parts reorder warnings.\n\n> [!NOTE]\n> Ensure your profile configuration is complete before processing transactions.",
        applicable_module="core", required_permission=None, is_active=True, status="published"
    )

    # Login and 2FA
    art_login = HelpArticle(
        category_id=cat_gs.id, title="Login & 2FA Setup", slug="login-and-2fa",
        purpose="Instructions on logging in and setting up 2-Factor Authentication.",
        content_markdown="Secure access to the ERP is mandated using modern auth standards.\n\n### Login Steps\n1. Navigate to the login page.\n2. Input your email and password.\n3. Click **Login**.\n\n### Enabling 2FA\n- Click **2FA Security** in the top header.\n- Scan the QR code using your Authenticator App.\n- Input the active code to enable secure logins.\n\n> [!TIP]\n- Keep your backup codes safe.",
        applicable_module="core", required_permission=None, is_active=True, status="published"
    )

    # Lead Management
    art_leads = HelpArticle(
        category_id=cat_crm.id, title="Lead Management Guide", slug="lead-management",
        purpose="Track sales leads and follow-up activities.",
        content_markdown="Leads are critical for business growth.\n\n### How to Add a Lead\n1. Go to CRM -> Leads.\n2. Click **Add Lead**.\n3. Complete the name, contact, interest details, and lead source.\n4. Click **Save**.\n\n### Lead Conversion\n- Mark a lead as **Converted** when the customer approves a quotation. This automatically prompt to create a customer account.",
        applicable_module="core", required_permission="leads:read", is_active=True, status="published"
    )

    # Customer Directory
    art_customers = HelpArticle(
        category_id=cat_crm.id, title="Customer Directory Guide", slug="customer-directory",
        purpose="Managing customer categories, sites, and profiles.",
        content_markdown="The Customer Master screen allows directory organization.\n\n### Society Categories\n- **CHS (Housing Societies)**: Requires society registration number.\n- **Commercial**: Used for business offices.\n- **Single Shop**: For individual stores.\n\n> [!NOTE]\n> Create sites (e.g. Lobby, Main Gate) first before configuring CCTV Assets.",
        applicable_module="core", required_permission="customers:read", is_active=True, status="published"
    )

    # Quotations
    art_quotes = HelpArticle(
        category_id=cat_sales.id, title="Creating Quotations", slug="quotations",
        purpose="Generating quotes for potential hardware sales or AMC contracts.",
        content_markdown="Draft professional CCTV setup quotes for clients.\n\n### How to Create a Quote\n1. Go to Sales -> Quotations.\n2. Click **New Quotation**.\n3. Select Customer and Site.\n4. Add items from the catalog.\n5. Click **Submit**.\n\n> [!NOTE]\n> Quotes must be approved by a Manager before generating an Invoice.",
        applicable_module="sales", required_permission="quotations:read", is_active=True, status="published"
    )

    # Sales Orders
    art_sales_orders = HelpArticle(
        category_id=cat_sales.id, title="Sales Orders Processing", slug="sales-orders",
        purpose="Convert approved quotes into active sales orders.",
        content_markdown="Track order assembly and inventory allocation.\n\n### Steps\n1. Open Sales -> Sales Orders.\n2. View approved orders.\n3. Click **Fulfill Order** to allocate serial numbers and update stock levels.",
        applicable_module="sales", required_permission="sales_orders:read", is_active=True, status="published"
    )

    # Invoices
    art_invoices = HelpArticle(
        category_id=cat_sales.id, title="Generating Invoices", slug="invoices",
        purpose="Creating and emailing tax invoices to clients.",
        content_markdown="Invoices represent legal records of sales, rent, or service fees.\n\n### How to generate\n- Go to Sales -> Invoices.\n- Click **Create Tax Invoice**.\n- Choose sales order, rent cycle, or AMC contract.\n- Print or email directly.",
        applicable_module="core", required_permission="invoices:read", is_active=True, status="published"
    )

    # Rental Contracts
    art_rentals = HelpArticle(
        category_id=cat_rental.id, title="Rental Contracts Setup", slug="rental-contracts",
        purpose="Configure ongoing CCTV camera rentals and recurring monthly billings.",
        content_markdown="Rentals are structured around recurring billing schedules.\n\n### Key Steps\n1. Go to Rental -> Rental Contracts.\n2. Click **Create Contract**.\n3. Link serialized rental cameras.\n4. Save to generate monthly invoices automatically.",
        applicable_module="rental", required_permission="rentals:read", is_active=True, status="published"
    )

    # AMC Contracts
    art_amc_contracts = HelpArticle(
        category_id=cat_amc.id, title="AMC Service Contracts", slug="amc-contracts",
        purpose="Instructions on creating service contracts and scheduling visits.",
        content_markdown="Annual Maintenance Contracts (AMC) keep customer cameras operational.\n\n### Creating a Contract\n1. Go to AMC -> AMC Contracts.\n2. Click **Create Contract**.\n3. Set start/end dates, total annual fee, and number of visits.\n4. Add items to target assets list.",
        applicable_module="amc", required_permission="amc:read", is_active=True, status="published"
    )

    # Service Tickets
    art_tickets = HelpArticle(
        category_id=cat_amc.id, title="Service Tickets Guide", slug="service-tickets",
        purpose="Create, assign, and track progress of service tickets.",
        content_markdown="Service tickets are raised when client cameras report faults.\n\n### Lifecycle\n- **Open**: Created by staff or via the customer portal.\n- **Assigned**: Allocated to an engineer.\n- **Resolved**: Fix confirmed by the technician on-site.",
        applicable_module="amc", required_permission="service_tickets:read", is_active=True, status="published"
    )

    # Engineer Visits
    art_visits = HelpArticle(
        category_id=cat_amc.id, title="Technician Site Visits", slug="engineer-visits",
        purpose="Track technician on-site performance and location coordinates.",
        content_markdown="Technicians log visits to perform repairs or scheduled preventive maintenance.\n\n### Steps\n1. Open AMC -> Engineer Visits.\n2. Select assigned ticket.\n3. Click **Check-in** (captures GPS location).\n4. Record work notes and click **Check-out**.",
        applicable_module="amc", required_permission="engineer_visits:read", is_active=True, status="published"
    )

    # Installations
    art_installations = HelpArticle(
        category_id=cat_amc.id, title="Installations & Surveys", slug="installations",
        purpose="Process pre-installation surveys and handovers.",
        content_markdown="Manage complete physical hardware installations.\n\n### Flow\n- Perform site survey & record layout notes.\n- Allocate parts from inventory.\n- Capture OTP from client to complete handover.",
        applicable_module="amc", required_permission="installations:read", is_active=True, status="published"
    )

    session.add_all([
        art_intro, art_login, art_leads, art_customers, 
        art_quotes, art_sales_orders, art_invoices, 
        art_rentals, art_amc_contracts, art_tickets, 
        art_visits, art_installations
    ])
    await session.flush()

    # Seed some FAQs
    faq_1 = HelpFAQ(article_id=art_intro.id, question="What is core access?", answer="Core access represents pages like leads and customers, which are available to all tenants.", display_order=1)
    faq_2 = HelpFAQ(article_id=art_login.id, question="How can I reset 2FA?", answer="Contact your platform administrator to clear your registered secret.", display_order=1)
    faq_3 = HelpFAQ(article_id=art_tickets.id, question="How do customers track ticket status?", answer="Customers can log in to the Customer Self-Service Portal to view real-time ticket progress.", display_order=1)
    session.add_all([faq_1, faq_2, faq_3])
    await session.flush()

    await session.flush()
    return modules_map, plans_map


async def seed_tenant_data(session, tenant_config, plans_map):
    slug = tenant_config["slug"]
    name = tenant_config["name"]
    module_codes = tenant_config["modules"]

    print(f"\n🏢 Seeding Tenant: {name} (slug: {slug}) with modules: {module_codes}...")

    # 1. Create Tenant
    tenant = Tenant(
        name=name,
        slug=slug,
        plan="growth",
        status="active",
        invoice_prefix=slug[:3].upper()
    )
    session.add(tenant)
    await session.flush()

    # RLS bypass/context mapping
    conn = await session.connection()
    if conn.dialect.name == "postgresql":
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": str(tenant.id)}
        )

    # 2. Create TenantSubscription
    plan = plans_map["growth"]
    sub = TenantSubscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status="active",
        starts_at=datetime.now(timezone.utc)
    )
    session.add(sub)

    # 3. Create TenantModule records
    for m_code in module_codes:
        tm = TenantModule(
            tenant_id=tenant.id,
            module_code=m_code,
            status="active",
            starts_at=datetime.now(timezone.utc)
        )
        session.add(tm)

    # 4. Create Default Users (Admin, Accounts, Tech)
    pwd_hash = hash_password(DEFAULT_PASSWORD)
    admin = User(
        tenant_id=tenant.id,
        email=f"admin@{slug}.com",
        full_name=f"{name} Admin",
        hashed_password=pwd_hash,
        role=TenantRole.ADMIN,
        is_active=True
    )
    session.add(admin)

    tech = User(
        tenant_id=tenant.id,
        email=f"tech@{slug}.com",
        full_name=f"{name} Technician",
        hashed_password=pwd_hash,
        role=TenantRole.TECHNICIAN,
        is_active=True
    )
    session.add(tech)

    accounts = User(
        tenant_id=tenant.id,
        email=f"billing@{slug}.com",
        full_name=f"{name} Billing",
        hashed_password=pwd_hash,
        role="accounts",
        is_active=True
    )
    session.add(accounts)
    await session.flush()

    # 5. Create Default Company
    company = Company(
        tenant_id=tenant.id,
        name=f"{name} Operating Co",
        gst_status="GST",
        gstin="27AAACD1234F1Z1",
        address="123 Corporate Park, Mumbai",
        is_default=True,
        is_active=True
    )
    session.add(company)
    await session.flush()

    # 6. Create Customer & Site (Core modules)
    customer = Customer(
        tenant_id=tenant.id,
        name=f"Client of {name}",
        category=CustomerCategory.COMMERCIAL,
        status=CustomerStatus.ACTIVE,
        phone="9876543210",
        email=f"contact@client-{slug}.com",
        state_code="27",
        address="Bandra Kurla Complex, Mumbai",
        is_active=True
    )
    session.add(customer)
    await session.flush()

    site = CustomerSite(
        tenant_id=tenant.id,
        customer_id=customer.id,
        name="Main Office Site",
        address="Building 4, BKC, Mumbai",
        is_active=True
    )
    session.add(site)
    await session.flush()

    # 7. Create Lead (CRM module)
    lead = Lead(
        tenant_id=tenant.id,
        company_id=company.id,
        name=f"Lead for {name}",
        phone="9999888877",
        email=f"lead@client-{slug}.com",
        source=LeadSource.WEBSITE,
        status=LeadStatus.NEW,
        notes="Interested in full services"
    )
    session.add(lead)
    await session.flush()

    # Shared products setup if sales or rental is active
    product = None
    inventory_item = None
    vendor = None

    if "inventory" in module_codes or "sales" in module_codes or "rental" in module_codes:
        # Create Vendor master data
        vendor = Vendor(
            tenant_id=tenant.id,
            name="Global Security Supplies Ltd",
            vendor_type="supplier",
            status="active",
            phone="8887776665",
            email="orders@globalsecurity.com",
            gstin="27AAAGS1234E1Z0",
            address="Industrial Estate, Pune",
            is_active=True
        )
        session.add(vendor)
        await session.flush()

        # Create Inventory Item
        inventory_item = InventoryItem(
            tenant_id=tenant.id,
            name="CCTV Camera 4K Dome",
            part_number="CAM-4K-DOME",
            unit="pcs",
            current_stock=100,
            unit_cost=1500.0,
            vendor_id=vendor.id,
            is_active=True
        )
        session.add(inventory_item)
        await session.flush()

        # Create Product Catalog item
        product = Product(
            tenant_id=tenant.id,
            sku="CAM-4K-DOME",
            name="CCTV Dome Camera 4K Ultra",
            brand="Hikvision",
            category="camera",
            gst_rate=18.0,
            sale_price=2500.0,
            rental_price=150.0,
            is_serial_tracked=True,
            is_sellable="sales" in module_codes,
            is_rentable="rental" in module_codes,
            inventory_item_id=inventory_item.id,
            is_active=True
        )
        session.add(product)
        await session.flush()

    # 8. Seed Sales Modules Data
    if "sales" in module_codes:
        print(f"  💸 Seeding Sales Data for {slug}...")
        quote = Quotation(
            tenant_id=tenant.id,
            company_id=company.id,
            quotation_number=f"QT-{slug.upper()}-001",
            customer_id=customer.id,
            status=QuotationStatus.APPROVED,
            subtotal=2500.0,
            cgst_amount=225.0,
            sgst_amount=225.0,
            total_amount=2950.0,
            line_items=[{
                "product_id": str(product.id) if product else str(uuid.uuid4()),
                "name": "CCTV Dome Camera 4K Ultra",
                "quantity": 1,
                "unit_price": 2500.0,
                "gst_rate": 18.0,
                "total": 2950.0
            }]
        )
        session.add(quote)
        await session.flush()

        sales_order = SalesOrder(
            tenant_id=tenant.id,
            order_number=f"SO-{slug.upper()}-001",
            customer_id=customer.id,
            quotation_id=quote.id,
            status=SalesOrderStatus.CONFIRMED,
            order_date=TODAY,
            subtotal=2500.0,
            cgst_amount=225.0,
            sgst_amount=225.0,
            total_amount=2950.0,
            line_items=quote.line_items
        )
        session.add(sales_order)
        await session.flush()

        invoice = Invoice(
            tenant_id=tenant.id,
            company_id=company.id,
            invoice_number=f"INV-{slug.upper()}-001",
            invoice_type=InvoiceType.TAX_INVOICE,
            customer_id=customer.id,
            sales_order_id=sales_order.id,
            status=InvoiceStatus.ISSUED,
            invoice_date=TODAY,
            due_date=TODAY + timedelta(days=15),
            subtotal=2500.0,
            cgst_amount=225.0,
            sgst_amount=225.0,
            total_amount=2950.0,
            amount_paid=0.0,
            line_items=quote.line_items
        )
        session.add(invoice)
        await session.flush()

        payment = Payment(
            tenant_id=tenant.id,
            invoice_id=invoice.id,
            customer_id=customer.id,
            amount=2950.0,
            payment_date=TODAY,
            mode=PaymentMode.UPI,
            reference_number="TXN123456"
        )
        session.add(payment)
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = 2950.0
        await session.flush()

    # 9. Seed Rental Modules Data
    if "rental" in module_codes:
        print(f"  📦 Seeding Rental Data for {slug}...")
        rental_unit = RentalUnit(
            tenant_id=tenant.id,
            product_id=product.id if product else None,
            serial_number=f"SR-{slug.upper()}-0987",
            condition="new",
            status="on_rent",
            purchase_cost=1500.0,
            purchase_date=TODAY - timedelta(days=30),
            is_active=True
        )
        session.add(rental_unit)
        await session.flush()

        rental_contract = RentalContract(
            tenant_id=tenant.id,
            contract_number=f"RC-{slug.upper()}-001",
            customer_id=customer.id,
            site_id=site.id,
            company_id=company.id,
            status="active",
            start_date=TODAY - timedelta(days=10),
            end_date=TODAY + timedelta(days=355),
            billing_cycle="monthly",
            deposit_amount=500.0,
            deposit_status="paid",
            subtotal=150.0,
            cgst_amount=13.5,
            sgst_amount=13.5,
            total_amount=177.0
        )
        session.add(rental_contract)
        await session.flush()

        line = RentalContractLine(
            tenant_id=tenant.id,
            rental_contract_id=rental_contract.id,
            product_id=product.id,
            rental_unit_id=rental_unit.id,
            quantity=1,
            unit_price=150.0,
            gst_rate=18.0,
            cgst_amount=13.5,
            sgst_amount=13.5,
            total_amount=177.0
        )
        session.add(line)
        await session.flush()

        rental_invoice = Invoice(
            tenant_id=tenant.id,
            company_id=company.id,
            invoice_number=f"RINV-{slug.upper()}-001",
            invoice_type=InvoiceType.TAX_INVOICE,
            customer_id=customer.id,
            status=InvoiceStatus.ISSUED,
            invoice_date=TODAY - timedelta(days=10),
            due_date=TODAY + timedelta(days=5),
            subtotal=150.0,
            cgst_amount=13.5,
            sgst_amount=13.5,
            total_amount=177.0,
            amount_paid=177.0,
            line_items=[{
                "product_id": str(product.id),
                "name": product.name,
                "quantity": 1,
                "unit_price": 150.0,
                "gst_rate": 18.0,
                "total": 177.0
            }]
        )
        session.add(rental_invoice)
        await session.flush()

    # 10. Seed AMC Modules Data
    if "amc" in module_codes:
        print(f"  🔧 Seeding AMC Data for {slug}...")
        # Create Deployed CCTV Asset
        cctv_asset = CCTVAsset(
            tenant_id=tenant.id,
            site_id=site.id,
            serial_number=f"SERIAL-{slug.upper()}-AMC",
            make="Dahua",
            model="DH-IPC-HFW1230S",
            asset_type="Camera",
            installation_date=TODAY - timedelta(days=180),
            warranty_expiry=TODAY + timedelta(days=180),
            status=AssetStatus.ACTIVE,
            is_active=True
        )
        session.add(cctv_asset)
        await session.flush()

        amc_contract = AMCContract(
            tenant_id=tenant.id,
            company_id=company.id,
            customer_id=customer.id,
            contract_number=f"AMC-{slug.upper()}-2026",
            status=AMCStatus.ACTIVE,
            start_date=TODAY - timedelta(days=15),
            end_date=TODAY + timedelta(days=350),
            annual_amount=12000.0,
            payment_frequency="annual",
            preventive_visits_per_year=4
        )
        session.add(amc_contract)
        await session.flush()

        ticket = ServiceTicket(
            tenant_id=tenant.id,
            company_id=company.id,
            customer_id=customer.id,
            site_id=site.id,
            ticket_number=f"TKT-{slug.upper()}-001",
            complaint="Camera Feed Intermittent: BKC warehouse lobby is dropping frames frequently.",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.ASSIGNED,
            assigned_to=tech.id,
            amc_contract_id=amc_contract.id
        )
        session.add(ticket)
        await session.flush()

        visit = EngineerVisit(
            tenant_id=tenant.id,
            ticket_id=ticket.id,
            technician_id=tech.id,
            visit_type="corrective",
            work_performed="Check camera power supply. Replaced loose connector.",
            is_synced=True
        )
        session.add(visit)
        await session.flush()

        installation = Installation(
            tenant_id=tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            work_order_number=f"WO-{slug.upper()}-001",
            status="in_progress",
            assigned_technician_id=tech.id,
            target_completion_date=TODAY + timedelta(days=5),
            survey_notes="Survey completed. Layout approved.",
            feasibility_notes="BKC main lobby has direct power outlets."
        )
        session.add(installation)
        await session.flush()

        amc_invoice = Invoice(
            tenant_id=tenant.id,
            company_id=company.id,
            invoice_number=f"AINV-{slug.upper()}-001",
            invoice_type=InvoiceType.TAX_INVOICE,
            customer_id=customer.id,
            amc_contract_id=amc_contract.id,
            status=InvoiceStatus.ISSUED,
            invoice_date=TODAY - timedelta(days=15),
            due_date=TODAY,
            subtotal=12000.0,
            cgst_amount=1080.0,
            sgst_amount=1080.0,
            total_amount=14160.0,
            amount_paid=0.0,
            line_items=[{
                "name": "Annual Maintenance Service Fee",
                "quantity": 1,
                "unit_price": 12000.0,
                "gst_rate": 18.0,
                "total": 14160.0
            }]
        )
        session.add(amc_invoice)
        await session.flush()

        # --- RICH TEST DATA FOR COMPANY E ---
        if slug == "company-e":
            print("🌟 Seeding rich multi-record test data for Company E...")

            # 1. Additional Products
            prod_bullet = Product(
                tenant_id=tenant.id, sku="CAM-4K-BULLET", name="CCTV Bullet Camera 4K Pro", brand="Hikvision",
                category="camera", gst_rate=18.0, sale_price=3200.0, rental_price=180.0,
                is_serial_tracked=True, is_sellable=True, is_rentable=True, is_active=True
            )
            prod_nvr = Product(
                tenant_id=tenant.id, sku="NVR-8CH", name="8-Channel Network Video Recorder", brand="Dahua",
                category="NVR", gst_rate=18.0, sale_price=7500.0, rental_price=400.0,
                is_serial_tracked=True, is_sellable=True, is_rentable=True, is_active=True
            )
            prod_hdd = Product(
                tenant_id=tenant.id, sku="HDD-1TB", name="1TB Surveillance Hard Drive", brand="WD Purple",
                category="HDD", gst_rate=18.0, sale_price=3800.0, rental_price=0.0,
                is_serial_tracked=True, is_sellable=True, is_rentable=False, is_active=True
            )
            prod_switch = Product(
                tenant_id=tenant.id, sku="SW-8POE", name="8-Port Gigabit PoE Switch", brand="D-Link",
                category="switch", gst_rate=18.0, sale_price=4500.0, rental_price=0.0,
                is_serial_tracked=True, is_sellable=True, is_rentable=False, is_active=True
            )
            session.add_all([prod_bullet, prod_nvr, prod_hdd, prod_switch])
            await session.flush()

            # 2. Additional Inventory
            inv_bullet = InventoryItem(
                tenant_id=tenant.id, name="CCTV Camera 4K Bullet", part_number="CAM-4K-BULLET", unit="pcs",
                current_stock=50, unit_cost=1800.0, vendor_id=vendor.id, is_active=True
            )
            inv_nvr = InventoryItem(
                tenant_id=tenant.id, name="8-Channel NVR Hub", part_number="NVR-8CH", unit="pcs",
                current_stock=20, unit_cost=4500.0, vendor_id=vendor.id, is_active=True
            )
            inv_hdd = InventoryItem(
                tenant_id=tenant.id, name="1TB Surveillance HDD", part_number="HDD-1TB", unit="pcs",
                current_stock=35, unit_cost=2200.0, vendor_id=vendor.id, is_active=True
            )
            inv_switch = InventoryItem(
                tenant_id=tenant.id, name="8-Port PoE Switch", part_number="SW-8POE", unit="pcs",
                current_stock=15, unit_cost=2500.0, vendor_id=vendor.id, is_active=True
            )
            session.add_all([inv_bullet, inv_nvr, inv_hdd, inv_switch])
            await session.flush()

            # Link catalog items to inventory
            prod_bullet.inventory_item_id = inv_bullet.id
            prod_nvr.inventory_item_id = inv_nvr.id
            prod_hdd.inventory_item_id = inv_hdd.id
            prod_switch.inventory_item_id = inv_switch.id
            await session.flush()

            # 3. Additional Customers (CHS and Single Shop categories)
            cust_gokuldham = Customer(
                tenant_id=tenant.id, name="Gokuldham Co-operative Housing Society",
                category=CustomerCategory.CHS, status=CustomerStatus.ACTIVE, phone="9812345678",
                email="secretary@gokuldham.org", state_code="27", address="Powai, Mumbai",
                society_registration_no="MUM/HS/1234/2020", contact_person_name="A. Bhide",
                contact_person_phone="9812345678", is_active=True
            )
            cust_groceries = Customer(
                tenant_id=tenant.id, name="Corner Groceries Store",
                category=CustomerCategory.SINGLE_SHOP, status=CustomerStatus.ACTIVE, phone="9832109876",
                email="groceries@corner.com", state_code="27", address="Andheri East, Mumbai",
                is_active=True
            )
            session.add_all([cust_gokuldham, cust_groceries])
            await session.flush()

            # Customer Sites
            site_gokuldham_a = CustomerSite(
                tenant_id=tenant.id, customer_id=cust_gokuldham.id, name="Main Gate & Security Cabin",
                address="Powai Main Road, Mumbai", is_active=True
            )
            site_gokuldham_b = CustomerSite(
                tenant_id=tenant.id, customer_id=cust_gokuldham.id, name="Clubhouse & Gym Lobby",
                address="Powai Main Road, Mumbai", is_active=True
            )
            site_groceries = CustomerSite(
                tenant_id=tenant.id, customer_id=cust_groceries.id, name="Retail Billing Counter",
                address="Andheri Station Road, Mumbai", is_active=True
            )
            session.add_all([site_gokuldham_a, site_gokuldham_b, site_groceries])
            await session.flush()

            # 4. Additional CRM Leads
            lead_sunrise = Lead(
                tenant_id=tenant.id, company_id=company.id, name="Sunrise Apartments CHS", phone="9112233445",
                email="admin@sunrise-chs.in", source=LeadSource.REFERRAL, status=LeadStatus.CONTACTED,
                notes="Requires quote for 16-camera setup at building gate and staircases"
            )
            lead_dmart = Lead(
                tenant_id=tenant.id, company_id=company.id, name="D-Mart Supermarket", phone="9223344556",
                email="procurement@dmart.com", source=LeadSource.WEBSITE, status=LeadStatus.CONVERTED,
                notes="Converted into Corner Groceries customer account"
            )
            lead_bluestar = Lead(
                tenant_id=tenant.id, company_id=company.id, name="Blue Star Corporate Office", phone="9334455667",
                email="facilities@bluestar.co.in", source=LeadSource.COLD_CALL, status=LeadStatus.LOST,
                lost_reason="Competitor offered 15% discount on installation", notes="Follow-up closed"
            )
            session.add_all([lead_sunrise, lead_dmart, lead_bluestar])
            await session.flush()

            # 5. Purchase Orders & Vendor Payments (Inventory module)
            po = PurchaseOrder(
                tenant_id=tenant.id, po_number=f"PO-{slug.upper()}-001", vendor_id=vendor.id,
                status=POStatus.RECEIVED, order_date=TODAY - timedelta(days=12),
                line_items=[
                    {"item_id": str(inv_bullet.id), "qty": 10, "unit_cost": 1800.0},
                    {"item_id": str(inv_nvr.id), "qty": 2, "unit_cost": 4500.0}
                ],
                total_amount=27000.0
            )
            session.add(po)
            await session.flush()

            v_payment = VendorPayment(
                tenant_id=tenant.id, vendor_id=vendor.id, purchase_order_id=po.id,
                amount=20000.0, payment_date=TODAY - timedelta(days=10),
                method="neft", reference="NFT987654321", notes="Partial payment for PO-COMPANY-E-001"
            )
            session.add(v_payment)
            await session.flush()

            # 6. Additional Sales Quotations & Orders
            quote_gokuldham = Quotation(
                tenant_id=tenant.id, company_id=company.id, quotation_number=f"QT-{slug.upper()}-002",
                customer_id=cust_gokuldham.id, lead_id=lead_sunrise.id, status=QuotationStatus.DRAFT,
                subtotal=14400.0, cgst_amount=1296.0, sgst_amount=1296.0, total_amount=16992.0,
                line_items=[
                    {"product_id": str(prod_bullet.id), "name": prod_bullet.name, "quantity": 4, "unit_price": 3200.0, "gst_rate": 18.0, "total": 15104.0},
                    {"product_id": str(prod_switch.id), "name": prod_switch.name, "quantity": 1, "unit_price": 4500.0, "gst_rate": 18.0, "total": 5310.0}
                ]
            )
            quote_groceries = Quotation(
                tenant_id=tenant.id, company_id=company.id, quotation_number=f"QT-{slug.upper()}-003",
                customer_id=cust_groceries.id, lead_id=lead_dmart.id, status=QuotationStatus.APPROVED,
                subtotal=8000.0, cgst_amount=720.0, sgst_amount=720.0, total_amount=9440.0,
                line_items=[
                    {"product_id": str(prod_bullet.id), "name": prod_bullet.name, "quantity": 2, "unit_price": 3200.0, "gst_rate": 18.0, "total": 7552.0},
                    {"product_id": str(prod_switch.id), "name": prod_switch.name, "quantity": 1, "unit_price": 4500.0, "gst_rate": 18.0, "total": 5310.0}
                ]
            )
            session.add_all([quote_gokuldham, quote_groceries])
            await session.flush()

            so_groceries = SalesOrder(
                tenant_id=tenant.id, order_number=f"SO-{slug.upper()}-002", customer_id=cust_groceries.id,
                quotation_id=quote_groceries.id, status=SalesOrderStatus.FULFILLED, order_date=TODAY - timedelta(days=5),
                subtotal=8000.0, cgst_amount=720.0, sgst_amount=720.0, total_amount=9440.0,
                line_items=quote_groceries.line_items, fulfilled_at=TODAY - timedelta(days=4)
            )
            session.add(so_groceries)
            await session.flush()

            inv_groceries = Invoice(
                tenant_id=tenant.id, company_id=company.id, invoice_number=f"INV-{slug.upper()}-002",
                invoice_type=InvoiceType.TAX_INVOICE, customer_id=cust_groceries.id, sales_order_id=so_groceries.id,
                status=InvoiceStatus.ISSUED, invoice_date=TODAY - timedelta(days=4), due_date=TODAY + timedelta(days=10),
                subtotal=8000.0, cgst_amount=720.0, sgst_amount=720.0, total_amount=9440.0,
                amount_paid=0.0, line_items=quote_groceries.line_items
            )
            session.add(inv_groceries)
            await session.flush()

            pay_groceries = Payment(
                tenant_id=tenant.id, invoice_id=inv_groceries.id, customer_id=cust_groceries.id,
                amount=9440.0, payment_date=TODAY - timedelta(days=3), mode=PaymentMode.CARD,
                reference_number="CARD777888", notes="Full payment for Corner Groceries Dome/Switch setup"
            )
            session.add(pay_groceries)
            inv_groceries.status = InvoiceStatus.PAID
            inv_groceries.amount_paid = 9440.0
            await session.flush()

            # 7. Additional Rental Contracts
            rent_unit_nvr = RentalUnit(
                tenant_id=tenant.id, product_id=prod_nvr.id, serial_number=f"SR-{slug.upper()}-NVR-5555",
                condition="good", status="on_rent", purchase_cost=4500.0, purchase_date=TODAY - timedelta(days=60),
                is_active=True
            )
            session.add(rent_unit_nvr)
            await session.flush()

            rent_contract_groceries = RentalContract(
                tenant_id=tenant.id, contract_number=f"RC-{slug.upper()}-002", customer_id=cust_groceries.id,
                site_id=site_groceries.id, company_id=company.id, status="active",
                start_date=TODAY - timedelta(days=20), end_date=TODAY + timedelta(days=345),
                billing_cycle="monthly", deposit_amount=1000.0, deposit_status="paid",
                subtotal=400.0, cgst_amount=36.0, sgst_amount=36.0, total_amount=472.0
            )
            session.add(rent_contract_groceries)
            await session.flush()

            rent_line_groceries = RentalContractLine(
                tenant_id=tenant.id, rental_contract_id=rent_contract_groceries.id, product_id=prod_nvr.id,
                rental_unit_id=rent_unit_nvr.id, quantity=1, unit_price=400.0, gst_rate=18.0,
                cgst_amount=36.0, sgst_amount=36.0, total_amount=472.0
            )
            session.add(rent_line_groceries)
            await session.flush()

            # 8. Additional Deployed Site Assets & AMC Contracts
            asset_gokuldham_1 = CCTVAsset(
                tenant_id=tenant.id, site_id=site_gokuldham_a.id, serial_number=f"SR-{slug.upper()}-GOK-CAM1",
                make="Hikvision", model="Bullet 4K Pro", asset_type="Camera",
                installation_date=TODAY - timedelta(days=200), warranty_expiry=TODAY + timedelta(days=165),
                status=AssetStatus.ACTIVE, is_active=True
            )
            asset_gokuldham_2 = CCTVAsset(
                tenant_id=tenant.id, site_id=site_gokuldham_b.id, serial_number=f"SR-{slug.upper()}-GOK-NVR1",
                make="Dahua", model="8-Channel NVR Hub", asset_type="NVR",
                installation_date=TODAY - timedelta(days=200), warranty_expiry=TODAY + timedelta(days=165),
                status=AssetStatus.ACTIVE, is_active=True
            )
            session.add_all([asset_gokuldham_1, asset_gokuldham_2])
            await session.flush()

            amc_gokuldham = AMCContract(
                tenant_id=tenant.id, company_id=company.id, customer_id=cust_gokuldham.id,
                contract_number=f"AMC-{slug.upper()}-GOK-2026", status=AMCStatus.ACTIVE,
                start_date=TODAY - timedelta(days=30), end_date=TODAY + timedelta(days=335),
                annual_amount=24000.0, payment_frequency="quarterly", preventive_visits_per_year=4
            )
            session.add(amc_gokuldham)
            await session.flush()

            # 9. Additional Service Tickets & Engineer Visits
            ticket_gokuldham = ServiceTicket(
                tenant_id=tenant.id, company_id=company.id, customer_id=cust_gokuldham.id,
                site_id=site_gokuldham_b.id, asset_id=asset_gokuldham_2.id, amc_contract_id=amc_gokuldham.id,
                ticket_number=f"TKT-{slug.upper()}-002",
                complaint="NVR power supply fan is making grinding noise and shutting down frequently.",
                priority=TicketPriority.HIGH, status=TicketStatus.OPEN, assigned_to=tech.id
            )
            ticket_groceries_resolved = ServiceTicket(
                tenant_id=tenant.id, company_id=company.id, customer_id=cust_groceries.id,
                site_id=site_groceries.id, ticket_number=f"TKT-{slug.upper()}-003",
                complaint="Billing counter camera lens is dirty and blurred.",
                priority=TicketPriority.LOW, status=TicketStatus.RESOLVED, assigned_to=tech.id,
                resolved_at=datetime.now(timezone.utc) - timedelta(days=2),
                resolution_notes="Cleaned camera lens and adjusted angle."
            )
            session.add_all([ticket_gokuldham, ticket_groceries_resolved])
            await session.flush()

            visit_groceries_resolved = EngineerVisit(
                tenant_id=tenant.id, ticket_id=ticket_groceries_resolved.id, technician_id=tech.id,
                visit_type="corrective", checkin_at=datetime.now(timezone.utc) - timedelta(days=2, hours=3),
                checkout_at=datetime.now(timezone.utc) - timedelta(days=2, hours=2),
                work_performed="Cleaned camera lens and adjusted viewing angle.", is_synced=True
            )
            session.add(visit_groceries_resolved)
            await session.flush()

            # Seed customer portal user linked to Gokuldham CHS
            portal_user = CustomerPortalUser(
                tenant_id=tenant.id,
                customer_id=cust_gokuldham.id,
                email="portal@greenvalley.in",
                full_name="Gokuldham Portal User",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                is_active=True
            )
            session.add(portal_user)
            await session.flush()
            print("✔ Customer Portal user successfully seeded for Company E (portal@greenvalley.in).")

            print("✔ Rich test data successfully seeded for Company E.")

        print(f"✔ Successfully provisioned and seeded tenant: {slug}")


async def main():
    db._init_engine()
    async with db._AsyncSessionLocal() as session:
        # Seed Base Master
        modules_map, plans_map = await seed_base_metadata(session)
        await session.commit()

        # Seed Platform Admin Tenant & User
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

        # Seed each configuration
        for config in SUBSCRIPTION_COMBINATIONS:
            async with db._AsyncSessionLocal() as t_session:
                await seed_tenant_data(t_session, config, plans_map)
                await t_session.commit()
        
        print("\n🎉 Seed of all subscription combinations completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
