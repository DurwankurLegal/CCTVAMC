from uuid import UUID
from typing import Optional, List, Any
from datetime import date
from pydantic import BaseModel


class SalesOrderCreate(BaseModel):
    customer_id: UUID
    quotation_id: Optional[UUID] = None
    order_date: date
    delivery_date: Optional[date] = None
    line_items: List[Any] = []
    notes: Optional[str] = None
    supply_state_code: Optional[str] = None


class SalesOrderUpdate(BaseModel):
    status: Optional[str] = None
    delivery_date: Optional[date] = None
    notes: Optional[str] = None
    line_items: Optional[List[Any]] = None


class SalesOrderResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    order_number: str
    customer_id: UUID
    quotation_id: Optional[UUID]
    status: str
    order_date: date
    delivery_date: Optional[date]
    line_items: List[Any]
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float
    supply_state_code: Optional[str]
    fulfilled_at: Optional[date]
    invoice_id: Optional[UUID]
    notes: Optional[str]
    is_active: bool
