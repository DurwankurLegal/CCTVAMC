from uuid import UUID
from typing import Optional, List
from datetime import date
from pydantic import BaseModel


class RentalUnitCreate(BaseModel):
    product_id: UUID
    serial_number: str
    condition: Optional[str] = None
    status: str = "available"
    purchase_cost: Optional[float] = None
    purchase_date: Optional[date] = None
    notes: Optional[str] = None


class RentalUnitUpdate(BaseModel):
    serial_number: Optional[str] = None
    condition: Optional[str] = None
    status: Optional[str] = None
    purchase_cost: Optional[float] = None
    purchase_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class RentalUnitResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    product_id: UUID
    serial_number: str
    condition: Optional[str]
    status: str
    purchase_cost: Optional[float]
    purchase_date: Optional[date]
    notes: Optional[str]
    is_active: bool


class RentalContractLineCreate(BaseModel):
    product_id: UUID
    rental_unit_id: Optional[UUID] = None
    quantity: int = 1
    unit_price: float = 0.0
    gst_rate: float = 18.0


class RentalContractLineResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    rental_contract_id: UUID
    product_id: UUID
    rental_unit_id: Optional[UUID]
    quantity: int
    unit_price: float
    gst_rate: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float


class RentalContractCreate(BaseModel):
    customer_id: UUID
    site_id: Optional[UUID] = None
    company_id: UUID
    start_date: date
    end_date: date
    billing_cycle: str = "monthly"
    deposit_amount: float = 0.0
    deposit_status: str = "pending"
    lines: List[RentalContractLineCreate]
    notes: Optional[str] = None


class RentalContractUpdate(BaseModel):
    status: Optional[str] = None
    end_date: Optional[date] = None
    deposit_status: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class RentalContractResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    contract_number: str
    customer_id: UUID
    site_id: Optional[UUID]
    company_id: UUID
    status: str
    start_date: date
    end_date: date
    billing_cycle: str
    deposit_amount: float
    deposit_status: str
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float
    notes: Optional[str]
    is_active: bool
    lines: List[RentalContractLineResponse] = []


class RentalMovementCreate(BaseModel):
    rental_contract_id: UUID
    rental_unit_id: UUID
    movement_type: str  # check_out, check_in
    movement_date: date
    condition: Optional[str] = None
    meter_reading: Optional[str] = None
    notes: Optional[str] = None
    charges: float = 0.0


class RentalMovementResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    rental_contract_id: UUID
    rental_unit_id: UUID
    movement_type: str
    movement_date: date
    condition: Optional[str]
    meter_reading: Optional[str]
    notes: Optional[str]
    charges: float
    recorded_by: UUID
