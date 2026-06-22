from fastapi import APIRouter
from app.api.v1 import auth, tenants, users, customers, leads, vendors, assets
from app.api.v1 import quotations, amc, service_tickets, engineer_visits
from app.api.v1 import inventory, sales_orders, invoices, payments, notifications, reports
from app.api.v1 import documents

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(customers.router, prefix="/customers", tags=["customers"])
router.include_router(leads.router, prefix="/leads", tags=["leads"])
router.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
router.include_router(assets.router, prefix="/assets", tags=["assets"])
router.include_router(quotations.router, prefix="/quotations", tags=["quotations"])
router.include_router(amc.router, prefix="/amc", tags=["amc"])
router.include_router(service_tickets.router, prefix="/service-tickets", tags=["service-tickets"])
router.include_router(engineer_visits.router, prefix="/engineer-visits", tags=["engineer-visits"])
router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
router.include_router(sales_orders.router, prefix="/sales-orders", tags=["sales-orders"])
router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
