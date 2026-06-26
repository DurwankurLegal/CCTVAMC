from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CashCollectionBase(BaseModel):
    customer_name: str
    company_id: UUID
    service_ticket_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    amount: float = Field(..., gt=0)
    collected_at: datetime
    remarks: Optional[str] = None
    receipt_photo_url: Optional[str] = None

class CashCollectionCreate(CashCollectionBase):
    employee_id: Optional[UUID] = None

class CashCollectionUpdate(CashCollectionBase):
    employee_id: Optional[UUID] = None

class CashCollectionAction(BaseModel):
    action: str  # APPROVED, REJECTED
    notes: Optional[str] = None

class CashCollectionLogResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    action: str
    action_by: UUID
    action_at: datetime
    notes: Optional[str]

class CashCollectionResponse(CashCollectionBase):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    payment_mode: str
    status: str
    logs: List[CashCollectionLogResponse] = []
