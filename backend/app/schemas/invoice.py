from uuid import UUID
from typing import Optional, List, Any
from datetime import date
from pydantic import BaseModel
from app.models.invoice import InvoiceStatus, InvoiceType


class InvoiceCreate(BaseModel):
    customer_id: UUID
    invoice_date: date
    due_date: Optional[date] = None
    invoice_type: InvoiceType = InvoiceType.TAX_INVOICE
    amc_contract_id: Optional[UUID] = None
    supply_state_code: Optional[str] = None   # 2-digit GST state code
    line_items: List[Any] = []
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    invoice_number: str
    invoice_type: str
    customer_id: UUID
    amc_contract_id: Optional[UUID]
    status: str
    invoice_date: date
    due_date: Optional[date]
    supply_state_code: Optional[str]
    line_items: List[Any]
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float
    amount_paid: float
    notes: Optional[str]
    pdf_url: Optional[str]
    is_active: bool
