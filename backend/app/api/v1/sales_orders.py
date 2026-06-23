from typing import List, Optional, Any
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.models.sales_order import SalesOrder, SalesOrderStatus
from app.services.sequences import next_number

router = APIRouter()


class SalesOrderCreate(BaseModel):
    customer_id: UUID
    quotation_id: Optional[UUID] = None
    order_date: date
    delivery_date: Optional[date] = None
    line_items: List[Any] = []
    notes: Optional[str] = None


class SalesOrderResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    order_number: str
    customer_id: UUID
    status: str
    order_date: date
    total_amount: float
    is_active: bool


@router.get("", response_model=List[SalesOrderResponse])
async def list_orders(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.tenant_id == current_user.tenant_id)
        .offset(offset).limit(limit)
    )
    return list(result.scalars().all())


@router.post("", response_model=SalesOrderResponse, status_code=201)
async def create_order(
    payload: SalesOrderCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales_orders:write")),
):
    subtotal = sum(
        float(i.get("amount", i.get("unit_price", 0) * i.get("quantity", 1)))
        for i in payload.line_items
    )
    order = SalesOrder(
        tenant_id=current_user.tenant_id,
        order_number=await next_number(db, current_user.tenant_id, "sales_order", "SO"),
        customer_id=payload.customer_id,
        quotation_id=payload.quotation_id,
        order_date=payload.order_date,
        delivery_date=payload.delivery_date,
        line_items=payload.line_items,
        subtotal=subtotal,
        total_amount=subtotal,
        notes=payload.notes,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order
