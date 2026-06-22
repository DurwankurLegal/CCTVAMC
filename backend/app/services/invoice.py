from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.base import TenantRepository
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.services.quotation import _compute_gst_totals

_INV_SEQ: dict[UUID, int] = {}


class InvoiceRepository(TenantRepository[Invoice]):
    model = Invoice


def _next_invoice_number(tenant_id: UUID, prefix: str = "") -> str:
    _INV_SEQ[tenant_id] = _INV_SEQ.get(tenant_id, 0) + 1
    year = datetime.now(timezone.utc).year
    pfx = prefix or str(tenant_id)[:4].upper()
    return f"{pfx}-{year}-{_INV_SEQ[tenant_id]:05d}"


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

    subtotal, cgst, sgst, igst = _compute_gst_totals(
        payload.line_items or [],
        payload.supply_state_code,
        tenant.settings.get("state_code") if tenant else None,
    )

    inv = Invoice(
        customer_id=payload.customer_id,
        invoice_number=_next_invoice_number(tenant_id, prefix),
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
        total_amount=round(subtotal + cgst + sgst + igst, 2),
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


async def create_credit_note(db: AsyncSession, tenant_id: UUID, original_invoice_id: UUID) -> Invoice:
    """Create a credit note (reversal) for an existing invoice."""
    repo = InvoiceRepository(db, tenant_id)
    original = await repo.get(original_invoice_id)
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original invoice not found")

    from app.models.invoice import InvoiceStatus as IS, InvoiceType
    credit = Invoice(
        customer_id=original.customer_id,
        invoice_number=_next_invoice_number(tenant_id, "CN"),
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
