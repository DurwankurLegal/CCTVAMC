import asyncio
import pkgutil
import importlib
from sqlalchemy import select, func
import app.core.database as db

# Import all models
from app.models.tenant import Tenant
from app.models.user import User
from app.models.company import Company
from app.models.company_template import CompanyTemplate
from app.models.subscription import Module, SaasPlan, TenantSubscription, TenantModule
from app.models.customer import Customer, CustomerSite, CustomerContact
from app.models.product import Product
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.asset import CCTVAsset
from app.models.lead import Lead
from app.models.quotation import Quotation
from app.models.sales_order import SalesOrder
from app.models.rental import RentalUnit, RentalContract, RentalContractLine, RentalMovement
from app.models.amc import AMCContract, AMCAsset
from app.models.service_ticket import ServiceTicket
from app.models.engineer_visit import EngineerVisit
from app.models.installation import Installation
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.vendor import Vendor, PurchaseOrder, VendorPayment
from app.models.help import HelpCategory, HelpArticle
from app.models.customer_portal_user import CustomerPortalUser
from app.models.ticket_comment import TicketComment
from app.models.pm_schedule import PMSchedule
from app.models.cash_collection import CashCollection
from app.models.cash_collection_log import CashCollectionLog

# Load every model module so SQLAlchemy can resolve all relationships
import app.models
for _m in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{_m.name}")

async def count_table(session, model) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar() or 0

async def main():
    db._init_engine()
    async with db._AsyncSessionLocal() as session:
        # Check counts
        tenants = await count_table(session, Tenant)
        users = await count_table(session, User)
        companies = await count_table(session, Company)
        templates = await count_table(session, CompanyTemplate)
        modules = await count_table(session, Module)
        plans = await count_table(session, SaasPlan)
        tenant_subs = await count_table(session, TenantSubscription)
        tenant_mods = await count_table(session, TenantModule)
        leads = await count_table(session, Lead)
        customers = await count_table(session, Customer)
        sites = await count_table(session, CustomerSite)
        contacts = await count_table(session, CustomerContact)
        assets = await count_table(session, CCTVAsset)
        products = await count_table(session, Product)
        inv_items = await count_table(session, InventoryItem)
        inv_movements = await count_table(session, InventoryMovement)
        vendors = await count_table(session, Vendor)
        pos = await count_table(session, PurchaseOrder)
        v_payments = await count_table(session, VendorPayment)
        rental_units = await count_table(session, RentalUnit)
        rental_contracts = await count_table(session, RentalContract)
        rental_lines = await count_table(session, RentalContractLine)
        rental_movements = await count_table(session, RentalMovement)
        quotations = await count_table(session, Quotation)
        sales_orders = await count_table(session, SalesOrder)
        invoices = await count_table(session, Invoice)
        payments = await count_table(session, Payment)
        amc_contracts = await count_table(session, AMCContract)
        amc_assets = await count_table(session, AMCAsset)
        pm_schedules = await count_table(session, PMSchedule)
        tickets = await count_table(session, ServiceTicket)
        comments = await count_table(session, TicketComment)
        visits = await count_table(session, EngineerVisit)
        installations = await count_table(session, Installation)
        cash_col = await count_table(session, CashCollection)
        cash_log = await count_table(session, CashCollectionLog)
        portal_users = await count_table(session, CustomerPortalUser)
        help_cats = await count_table(session, HelpCategory)
        help_arts = await count_table(session, HelpArticle)

        print("\n==================================================")
        print("📊 SEEDED DATABASE COUNT SUMMARY")
        print("==================================================")
        print(f"Tenants:                     {tenants}")
        print(f"Users (Staff Directory):     {users}")
        print(f"Companies:                   {companies}")
        print(f"Company templates:           {templates}")
        print(f"Modules (Platform Master):   {modules}")
        print(f"SaaS Plans (Platform Master): {plans}")
        print(f"Tenant subscriptions:        {tenant_subs}")
        print(f"Tenant modules enabled:      {tenant_mods}")
        print(f"Leads:                       {leads}")
        print(f"Customers:                   {customers}")
        print(f"Customer sites:              {sites}")
        print(f"Customer contacts:           {contacts}")
        print(f"CCTV Assets:                 {assets}")
        print(f"Products:                    {products}")
        print(f"Inventory items:             {inv_items}")
        print(f"Inventory movements:         {inv_movements}")
        print(f"Vendors:                     {vendors}")
        print(f"Purchase orders:             {pos}")
        print(f"Vendor payments:             {v_payments}")
        print(f"Rental units:                {rental_units}")
        print(f"Rental contracts:            {rental_contracts}")
        print(f"Rental contract lines:       {rental_lines}")
        print(f"Rental movements:            {rental_movements}")
        print(f"Quotations:                  {quotations}")
        print(f"Sales orders:                {sales_orders}")
        print(f"Invoices:                    {invoices}")
        print(f"Payments:                    {payments}")
        print(f"AMC contracts:               {amc_contracts}")
        print(f"AMC assets:                  {amc_assets}")
        print(f"PM schedules:                {pm_schedules}")
        print(f"Service tickets:             {tickets}")
        print(f"Ticket comments:             {comments}")
        print(f"Engineer visits:             {visits}")
        print(f"Installations:               {installations}")
        print(f"Cash collections:            {cash_col}")
        print(f"Cash collection logs:        {cash_log}")
        print(f"Customer portal users:       {portal_users}")
        print(f"Help Categories:             {help_cats}")
        print(f"Help Articles:               {help_arts}")
        print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
