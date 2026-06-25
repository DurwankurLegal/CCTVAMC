from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.base import TenantRepository
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.services.gst import compute_gst_totals, grand_total
from app.services.sequences import next_number


class InvoiceRepository(TenantRepository[Invoice]):
    model = Invoice


async def list_invoices(db, tenant_id, offset=0, limit=50):
    return await InvoiceRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_invoice(db, tenant_id, invoice_id):
    obj = await InvoiceRepository(db, tenant_id).get(invoice_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return obj


async def create_invoice(db: AsyncSession, tenant_id: UUID, payload: InvoiceCreate) -> Invoice:
    # Fetch tenant invoice prefix
    from sqlalchemy import select
    from app.models.tenant import Tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    prefix = (tenant.invoice_prefix or "") if tenant else ""
    prefix = prefix or str(tenant_id)[:4].upper()

    subtotal, cgst, sgst, igst = compute_gst_totals(
        payload.line_items or [],
        payload.supply_state_code,
        tenant.settings.get("state_code") if tenant else None,
    )

    inv = Invoice(
        customer_id=payload.customer_id,
        invoice_number=await next_number(db, tenant_id, "invoice", prefix),
        invoice_type=payload.invoice_type,
        amc_contract_id=payload.amc_contract_id,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        supply_state_code=payload.supply_state_code,
        line_items=payload.line_items or [],
        notes=payload.notes,
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_amount=grand_total(subtotal, cgst, sgst, igst),
    )
    return await InvoiceRepository(db, tenant_id).create(inv)


async def update_invoice(db, tenant_id, invoice_id, payload: InvoiceUpdate) -> Invoice:
    repo = InvoiceRepository(db, tenant_id)
    obj = await repo.get(invoice_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    return await repo.save(obj)


def render_pdf(invoice: Invoice, tenant_name: str = "") -> bytes:
    """Render a GST-compliant (or simplified) invoice PDF (SRS 4.13)."""
    from weasyprint import HTML
    rows = "".join(
        f"<tr><td>{li.get('description','')}</td><td>{li.get('quantity','')}</td>"
        f"<td>{li.get('unit_price','')}</td><td>{li.get('amount','')}</td></tr>"
        for li in (invoice.line_items or [])
    )
    is_simplified = str(invoice.invoice_type) == "simplified"
    tax_rows = "" if is_simplified else (
        f"<tr><td>CGST</td><td>{invoice.cgst_amount}</td></tr>"
        f"<tr><td>SGST</td><td>{invoice.sgst_amount}</td></tr>"
        f"<tr><td>IGST</td><td>{invoice.igst_amount}</td></tr>"
    )
    title = "INVOICE" if not is_simplified else "BILL OF SUPPLY"
    html = f"""<html><head><style>
      body{{font-family:sans-serif;font-size:12px}} h1{{font-size:18px}}
      table{{border-collapse:collapse;width:100%;margin-top:8px}}
      td,th{{border:1px solid #ccc;padding:5px;text-align:left}}</style></head>
      <body><h1>{title} — {invoice.invoice_number}</h1>
      <p>{tenant_name}</p>
      <table><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Amount</th></tr>{rows}</table>
      <table><tr><td>Subtotal</td><td>{invoice.subtotal}</td></tr>{tax_rows}
      <tr><td><b>Total</b></td><td><b>{invoice.total_amount}</b></td></tr></table>
      </body></html>"""
    return HTML(string=html).write_pdf()


async def generate_recurring_amc_invoices(db: AsyncSession) -> int:
    """Create AMC billing invoices for active contracts whose cycle is due (SRS 4.13).
    Idempotent within a period via a per-contract invoice-existence check."""
    from sqlalchemy import select, and_
    from datetime import date
    from app.models.amc import AMCContract, AMCStatus
    from app.models.tenant import Tenant
    from app.workers.tasks import set_celery_tenant_context

    count = 0
    # Fetch all active/trial tenants
    tenants = (await db.execute(
        select(Tenant.id).where(Tenant.status.in_(["active", "trial"]))
    )).scalars().all()
    
    today = date.today()
    for tid in tenants:
        # Dynamically set Postgres session parameter and structlog context variables
        await set_celery_tenant_context(db, tid)
        
        contracts = (await db.execute(
            select(AMCContract).where(AMCContract.status == AMCStatus.ACTIVE)
        )).scalars().all()
        
        for c in contracts:
            period_tag = today.strftime("%Y%m")
            exists = (await db.execute(
                select(Invoice).where(and_(
                    Invoice.tenant_id == c.tenant_id,
                    Invoice.amc_contract_id == c.id,
                    Invoice.notes == f"AMC billing {period_tag}",
                ))
            )).scalar_one_or_none()
            if exists:
                continue
            freq = (c.payment_frequency or "annual")
            divisor = {"monthly": 12, "quarterly": 4, "annual": 1}.get(freq, 1)
            amount = round(float(c.annual_amount or 0) / divisor, 2)
            inv = Invoice(
                tenant_id=c.tenant_id,
                customer_id=c.customer_id,
                invoice_number=await next_number(db, c.tenant_id, "invoice", str(c.tenant_id)[:4].upper()),
                amc_contract_id=c.id,
                invoice_date=today,
                line_items=[{"description": f"AMC {freq} billing", "amount": amount}],
                subtotal=amount, total_amount=amount,
                notes=f"AMC billing {period_tag}",
            )
            db.add(inv)
            await db.flush()
            count += 1
            
    await db.commit()
    return count



async def create_credit_note(db: AsyncSession, tenant_id: UUID, original_invoice_id: UUID) -> Invoice:
    """Create a credit note (reversal) for an existing invoice."""
    repo = InvoiceRepository(db, tenant_id)
    original = await repo.get(original_invoice_id)
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original invoice not found")

    from app.models.invoice import InvoiceStatus as IS, InvoiceType
    credit = Invoice(
        customer_id=original.customer_id,
        invoice_number=await next_number(db, tenant_id, "credit_note", "CN"),
        invoice_type=InvoiceType.TAX_INVOICE,
        reference_invoice_id=original_invoice_id,
        invoice_date=datetime.now(timezone.utc).date(),
        supply_state_code=original.supply_state_code,
        line_items=original.line_items,
        subtotal=-original.subtotal,
        cgst_amount=-original.cgst_amount,
        sgst_amount=-original.sgst_amount,
        igst_amount=-original.igst_amount,
        total_amount=-original.total_amount,
        status=IS.CREDIT_NOTE,
        notes=f"Credit note against {original.invoice_number}",
    )
    return await repo.create(credit)
