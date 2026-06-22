from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quotation import Quotation
from app.repositories.base import TenantRepository
from app.schemas.quotation import QuotationCreate, QuotationUpdate


class QuotationRepository(TenantRepository[Quotation]):
    model = Quotation


def _compute_gst_totals(line_items: list, supply_state_code, tenant_state_code):
    """Compute CGST+SGST for intra-state, IGST for inter-state."""
    subtotal = 0.0
    cgst = sgst = igst = 0.0
    is_intra = (supply_state_code and tenant_state_code and supply_state_code == tenant_state_code)
    for item in line_items:
        amt = float(item.get("amount", item.get("unit_price", 0) * item.get("quantity", 1)))
        rate = float(item.get("gst_rate", 18.0)) / 100
        subtotal += amt
        tax = amt * rate
        if is_intra:
            cgst += tax / 2
            sgst += tax / 2
        else:
            igst += tax
    return round(subtotal, 2), round(cgst, 2), round(sgst, 2), round(igst, 2)


_QUOTATION_SEQ: dict[UUID, int] = {}


def _next_quotation_number(tenant_id: UUID) -> str:
    _QUOTATION_SEQ[tenant_id] = _QUOTATION_SEQ.get(tenant_id, 0) + 1
    return f"QT-{str(tenant_id)[:4].upper()}-{_QUOTATION_SEQ[tenant_id]:05d}"


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
    subtotal, cgst, sgst, igst = _compute_gst_totals(items, None, None)
    obj = Quotation(
        customer_id=payload.customer_id,
        lead_id=payload.lead_id,
        quotation_number=_next_quotation_number(tenant_id),
        line_items=items,
        terms=payload.terms,
        valid_until=payload.valid_until,
        notes=payload.notes,
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_amount=round(subtotal + cgst + sgst + igst, 2),
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
            subtotal, cgst, sgst, igst = _compute_gst_totals(items, None, None)
            obj.line_items = items
            obj.subtotal = subtotal
            obj.cgst_amount = cgst
            obj.sgst_amount = sgst
            obj.igst_amount = igst
            obj.total_amount = round(subtotal + cgst + sgst + igst, 2)
        else:
            setattr(obj, k, v)
    return await repo.save(obj)
