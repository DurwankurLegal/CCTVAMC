from uuid import UUID
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vendor import Vendor, PurchaseOrder, VendorPayment, POStatus
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud
from app.services.sequences import next_number


class VendorRepository(TenantRepository[Vendor]):
    model = Vendor


class PORepository(TenantRepository[PurchaseOrder]):
    model = PurchaseOrder


class VendorPaymentRepository(TenantRepository[VendorPayment]):
    model = VendorPayment


list_vendors, get_vendor, create_vendor_raw, _update_vendor_raw = make_crud(VendorRepository, Vendor)


async def create_vendor(db, tenant_id, payload):
    from app.core.crypto import encrypt
    data = payload.model_dump()
    bank = data.pop("bank_account", None)
    vendor = Vendor(**data)
    if bank:
        vendor.bank_account_encrypted = encrypt(bank)
    return await VendorRepository(db, tenant_id).create(vendor)


async def update_vendor(db, tenant_id, vendor_id, payload):
    from app.core.crypto import encrypt
    repo = VendorRepository(db, tenant_id)
    obj = await repo.get(vendor_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    data = payload.model_dump(exclude_none=True)
    bank = data.pop("bank_account", None)
    for k, v in data.items():
        setattr(obj, k, v)
    if bank:
        obj.bank_account_encrypted = encrypt(bank)
    return await repo.save(obj)


async def create_purchase_order(db: AsyncSession, tenant_id: UUID, vendor_id: UUID,
                                line_items: list, notes: str = None) -> PurchaseOrder:
    if not await VendorRepository(db, tenant_id).get(vendor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    total = sum(float(i.get("qty", 0)) * float(i.get("unit_cost", 0)) for i in line_items)
    po = PurchaseOrder(
        po_number=await next_number(db, tenant_id, "purchase_order", "PO"),
        vendor_id=vendor_id, order_date=date.today(), line_items=line_items,
        total_amount=total, notes=notes, status=POStatus.DRAFT,
    )
    po = await PORepository(db, tenant_id).create(po)
    # Procuring increases the amount we owe the vendor.
    vendor = await VendorRepository(db, tenant_id).get(vendor_id)
    vendor.outstanding_payable = float(vendor.outstanding_payable or 0) + total
    await VendorRepository(db, tenant_id).save(vendor)

    # Record a notification so procurement activity is visible to staff.
    from app.services.notification import NotificationService
    from app.services.notification_events import PURCHASE_ORDER_CREATED
    from app.models.notification import NotificationChannel
    await NotificationService(db, tenant_id).send(
        PURCHASE_ORDER_CREATED, recipient="staff",
        context={"po_number": po.po_number, "vendor": vendor.name, "total": total},
        channel=NotificationChannel.IN_APP)
    return po


async def list_purchase_orders(db: AsyncSession, tenant_id: UUID):
    return list((await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
    )).scalars().all())


async def record_vendor_payment(db: AsyncSession, tenant_id: UUID, vendor_id: UUID,
                                amount: float, method: str = None, reference: str = None) -> VendorPayment:
    vendor = await VendorRepository(db, tenant_id).get(vendor_id)
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    payment = VendorPayment(vendor_id=vendor_id, amount=amount, payment_date=date.today(),
                            method=method, reference=reference)
    payment = await VendorPaymentRepository(db, tenant_id).create(payment)
    vendor.outstanding_payable = float(vendor.outstanding_payable or 0) - amount
    await VendorRepository(db, tenant_id).save(vendor)
    return payment


async def reorder_low_stock(db: AsyncSession, tenant_id: UUID) -> list:
    """Auto-create draft purchase orders for low-stock items, grouped by vendor (SRS 4.11)."""
    from app.services.inventory import list_low_stock
    items = await list_low_stock(db, tenant_id)
    by_vendor: dict = {}
    for it in items:
        if not it.vendor_id:
            continue
        qty = max(1, (it.reorder_level or 0) * 2 - (it.current_stock or 0))
        by_vendor.setdefault(it.vendor_id, []).append(
            {"item_id": str(it.id), "qty": qty, "unit_cost": float(it.unit_cost or 0)})
    created = []
    for vendor_id, line_items in by_vendor.items():
        created.append(await create_purchase_order(db, tenant_id, vendor_id, line_items,
                                                    notes="Auto reorder for low stock"))
    return created
