from fastapi import APIRouter, Depends
from app.api.v1 import auth, tenants, users, customers, leads, vendors, assets, products, rentals
from app.api.v1 import quotations, amc, service_tickets, engineer_visits
from app.api.v1 import inventory, sales_orders, invoices, payments, notifications, reports
from app.api.v1 import documents, installations, portal, tenant_admin, companies, company_templates, cash_collections, help
from app.core.deps import require_module, require_module_any

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(customers.router, prefix="/customers", tags=["customers"])
router.include_router(leads.router, prefix="/leads", tags=["leads"])
router.include_router(vendors.router, prefix="/vendors", tags=["vendors"], dependencies=[Depends(require_module("inventory"))])
router.include_router(assets.router, prefix="/assets", tags=["assets"], dependencies=[Depends(require_module("assets"))])
router.include_router(quotations.router, prefix="/quotations", tags=["quotations"], dependencies=[Depends(require_module_any(["sales", "rental", "amc"]))])
router.include_router(amc.router, prefix="/amc", tags=["amc"], dependencies=[Depends(require_module("amc"))])
router.include_router(service_tickets.router, prefix="/service-tickets", tags=["service-tickets"], dependencies=[Depends(require_module("amc"))])
router.include_router(engineer_visits.router, prefix="/engineer-visits", tags=["engineer-visits"], dependencies=[Depends(require_module("amc"))])
router.include_router(inventory.router, prefix="/inventory", tags=["inventory"], dependencies=[Depends(require_module("inventory"))])
router.include_router(sales_orders.router, prefix="/sales-orders", tags=["sales-orders"], dependencies=[Depends(require_module("sales"))])
router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(installations.router, prefix="/installations", tags=["installations"], dependencies=[Depends(require_module("amc"))])
router.include_router(portal.router, prefix="/portal", tags=["customer-portal"])
router.include_router(tenant_admin.router, prefix="/tenant-admin", tags=["tenant-admin"])
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(company_templates.router, prefix="/company-templates", tags=["company-templates"])
router.include_router(cash_collections.router, prefix="/cash-collections", tags=["cash-collections"])
router.include_router(products.router, prefix="/products", tags=["products"], dependencies=[Depends(require_module("rental"))])
router.include_router(rentals.router, prefix="/rentals", tags=["rentals"], dependencies=[Depends(require_module("rental"))])
router.include_router(help.router, prefix="/help", tags=["help"])

