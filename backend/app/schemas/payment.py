from uuid import UUID
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.models.payment import PaymentMode


class PaymentCreate(BaseModel):
    invoice_id: UUID
    customer_id: UUID
    amount: float
    payment_date: date
    mode: PaymentMode = PaymentMode.CASH
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    customer_id: UUID
    amount: float
    payment_date: date
    mode: str
    reference_number: Optional[str]
    notes: Optional[str]
