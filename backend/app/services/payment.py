from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select
from app.models.payment import Payment
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.base import TenantRepository
from app.schemas.payment import PaymentCreate, PaymentUpdate


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


async def get_payment(db: AsyncSession, tenant_id: UUID, payment_id: UUID) -> Payment:
    obj = await PaymentRepository(db, tenant_id).get(payment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return obj


def _recompute_invoice_status(invoice) -> None:
    paid = float(invoice.amount_paid or 0)
    if paid >= float(invoice.total_amount) and float(invoice.total_amount) > 0:
        invoice.status = InvoiceStatus.PAID
    elif paid > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = InvoiceStatus.ISSUED


async def update_payment(db: AsyncSession, tenant_id: UUID, payment_id: UUID, payload: PaymentUpdate) -> Payment:
    repo = PaymentRepository(db, tenant_id)
    payment = await repo.get(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    data = payload.model_dump(exclude_none=True)
    new_amount = data.get("amount")
    # If the amount changed, adjust the linked invoice's paid total + status by the delta.
    if new_amount is not None and float(new_amount) != float(payment.amount):
        invoice = await InvoiceRepository(db, tenant_id).get(payment.invoice_id)
        if invoice:
            delta = float(new_amount) - float(payment.amount)
            invoice.amount_paid = float(invoice.amount_paid or 0) + delta
            _recompute_invoice_status(invoice)
            await InvoiceRepository(db, tenant_id).save(invoice)

    for k, v in data.items():
        setattr(payment, k, v)
    return await repo.save(payment)


def render_receipt(payment: Payment) -> bytes:
    """Render a payment receipt PDF (SRS 4.14)."""
    from weasyprint import HTML
    html = f"""<html><head><style>
      body{{font-family:sans-serif;font-size:13px}} h1{{font-size:18px}}
      td{{padding:4px 8px}}</style></head>
      <body><h1>Payment Receipt</h1>
      <table>
        <tr><td>Receipt for invoice</td><td>{payment.invoice_id}</td></tr>
        <tr><td>Amount</td><td>{payment.amount}</td></tr>
        <tr><td>Method</td><td>{getattr(payment, 'method', '')}</td></tr>
        <tr><td>Date</td><td>{getattr(payment, 'payment_date', '')}</td></tr>
      </table></body></html>"""
    return HTML(string=html).write_pdf()


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
