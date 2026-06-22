from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quotation import Quotation
from app.repositories.base import TenantRepository
from app.schemas.quotation import QuotationCreate, QuotationUpdate
from app.services.gst import compute_gst_totals, grand_total
from app.services.sequences import next_number


class QuotationRepository(TenantRepository[Quotation]):
    model = Quotation


# Backwards-compatible alias (GST logic now lives in app.services.gst).
_compute_gst_totals = compute_gst_totals


async def list_quotations(db, tenant_id, offset=0, limit=50):
    return await QuotationRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_quotation(db, tenant_id, qid):
    from fastapi import HTTPException, status
    obj = await QuotationRepository(db, tenant_id).get(qid)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    return obj


async def create_quotation(db: AsyncSession, tenant_id: UUID, payload: QuotationCreate) -> Quotation:
    items = [i.model_dump() for i in payload.line_items]
    subtotal, cgst, sgst, igst = compute_gst_totals(items, None, None)
    obj = Quotation(
        customer_id=payload.customer_id,
        lead_id=payload.lead_id,
        quotation_number=await next_number(db, tenant_id, "quotation", "QT"),
        line_items=items,
        terms=payload.terms,
        valid_until=payload.valid_until,
        notes=payload.notes,
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_amount=grand_total(subtotal, cgst, sgst, igst),
    )
    return await QuotationRepository(db, tenant_id).create(obj)


async def update_quotation(db, tenant_id, qid, payload: QuotationUpdate):
    repo = QuotationRepository(db, tenant_id)
    from fastapi import HTTPException, status
    obj = await repo.get(qid)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        if k == "line_items":
            items = [i.model_dump() for i in v]
            subtotal, cgst, sgst, igst = compute_gst_totals(items, None, None)
            obj.line_items = items
            obj.subtotal = subtotal
            obj.cgst_amount = cgst
            obj.sgst_amount = sgst
            obj.igst_amount = igst
            obj.total_amount = grand_total(subtotal, cgst, sgst, igst)
        else:
            setattr(obj, k, v)
    return await repo.save(obj)
