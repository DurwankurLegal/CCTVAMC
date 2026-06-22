from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select
from app.models.payment import Payment
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.base import TenantRepository
from app.schemas.payment import PaymentCreate


class PaymentRepository(TenantRepository[Payment]):
    model = Payment


class InvoiceRepository(TenantRepository[Invoice]):
    model = Invoice


async def list_payments(db, tenant_id, offset=0, limit=50):
    return await PaymentRepository(db, tenant_id).list(offset=offset, limit=limit)


async def record_payment(db: AsyncSession, tenant_id: UUID, payload: PaymentCreate) -> Payment:
    inv_repo = InvoiceRepository(db, tenant_id)
    invoice = await inv_repo.get(payload.invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    payment = Payment(**payload.model_dump())
    payment = await PaymentRepository(db, tenant_id).create(payment)

    # Update invoice amount_paid and status
    invoice.amount_paid = float(invoice.amount_paid or 0) + payload.amount
    if invoice.amount_paid >= float(invoice.total_amount):
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    await inv_repo.save(invoice)

    return payment


async def get_payment_ageing(db: AsyncSession, tenant_id: UUID) -> list:
    """Return unpaid invoice ageing buckets: current, 30d, 60d, 90d+"""
    from datetime import date, timedelta
    result = await db.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
            Invoice.is_active == True,
        )
    )
    invoices = result.scalars().all()
    today = date.today()
    buckets = {"current": [], "30d": [], "60d": [], "90d_plus": []}
    for inv in invoices:
        if not inv.due_date:
            buckets["current"].append(inv)
            continue
        overdue_days = (today - inv.due_date).days
        if overdue_days <= 0:
            buckets["current"].append(inv)
        elif overdue_days <= 30:
            buckets["30d"].append(inv)
        elif overdue_days <= 60:
            buckets["60d"].append(inv)
        else:
            buckets["90d_plus"].append(inv)
    return [{"bucket": k, "count": len(v), "amount": sum(float(i.total_amount - i.amount_paid) for i in v)}
            for k, v in buckets.items()]
