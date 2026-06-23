from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from app.services import vendor as vendor_service

router = APIRouter()


class POCreate(BaseModel):
    vendor_id: UUID
    line_items: list = []
    notes: Optional[str] = None


class VendorPaymentCreate(BaseModel):
    vendor_id: UUID
    amount: float
    method: Optional[str] = None
    reference: Optional[str] = None


@router.get("", response_model=List[VendorResponse])
async def list_vendors(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await vendor_service.list_vendors(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=VendorResponse, status_code=201)
async def create_vendor(
    payload: VendorCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("vendors:write")),
):
    return await vendor_service.create_vendor(db, current_user.tenant_id, payload)


# ── Procurement (static paths declared before /{vendor_id}) ───
@router.post("/purchase-orders", status_code=201)
async def create_purchase_order(
    payload: POCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("vendors:write")),
):
    po = await vendor_service.create_purchase_order(
        db, current_user.tenant_id, payload.vendor_id, payload.line_items, payload.notes)
    return {"id": str(po.id), "po_number": po.po_number, "total_amount": float(po.total_amount)}


@router.get("/purchase-orders")
async def list_purchase_orders(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    pos = await vendor_service.list_purchase_orders(db, current_user.tenant_id)
    return [{"id": str(p.id), "po_number": p.po_number, "vendor_id": str(p.vendor_id),
             "status": p.status, "total_amount": float(p.total_amount)} for p in pos]


@router.post("/reorder", status_code=201)
async def reorder_low_stock(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("vendors:write")),
):
    pos = await vendor_service.reorder_low_stock(db, current_user.tenant_id)
    return {"created_pos": [{"id": str(p.id), "po_number": p.po_number} for p in pos]}


@router.post("/payments", status_code=201)
async def record_vendor_payment(
    payload: VendorPaymentCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("vendors:write")),
):
    p = await vendor_service.record_vendor_payment(
        db, current_user.tenant_id, payload.vendor_id, payload.amount, payload.method, payload.reference)
    return {"id": str(p.id), "amount": float(p.amount)}


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await vendor_service.get_vendor(db, current_user.tenant_id, vendor_id)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID, payload: VendorUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("vendors:write")),
):
    return await vendor_service.update_vendor(db, current_user.tenant_id, vendor_id, payload)
