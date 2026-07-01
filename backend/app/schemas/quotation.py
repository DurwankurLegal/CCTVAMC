from uuid import UUID
from typing import Optional, List, Any
from datetime import date
from pydantic import BaseModel, model_validator
from app.models.quotation import QuotationStatus


class LineItem(BaseModel):
    description: str
    hsn_sac: Optional[str] = None
    quantity: float
    unit: Optional[str] = None
    unit_price: float
    gst_rate: float = 18.0
    amount: float


class QuotationCreate(BaseModel):
    company_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    line_items: List[LineItem] = []
    terms: Optional[str] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_customer_or_lead(self) -> "QuotationCreate":
        if not self.customer_id and not self.lead_id:
            raise ValueError("Either customer_id or lead_id must be provided")
        return self


class QuotationUpdate(BaseModel):
    status: Optional[QuotationStatus] = None
    line_items: Optional[List[LineItem]] = None
    terms: Optional[str] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None


class QuotationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    company_id: UUID
    quotation_number: str
    customer_id: Optional[UUID]
    lead_id: Optional[UUID]
    status: str
    line_items: List[Any]
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float
    terms: Optional[str]
    valid_until: Optional[date]
    is_active: bool
