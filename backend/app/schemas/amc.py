from uuid import UUID
from typing import Optional, List
from datetime import date
from pydantic import BaseModel
from app.models.amc import AMCStatus


class AMCContractCreate(BaseModel):
    company_id: Optional[UUID] = None
    customer_id: UUID
    start_date: date
    end_date: date
    annual_amount: float
    payment_frequency: Optional[str] = None   # monthly | quarterly | annual
    terms: Optional[str] = None
    preventive_visits_per_year: Optional[int] = None
    asset_ids: List[UUID] = []


class AMCContractUpdate(BaseModel):
    status: Optional[AMCStatus] = None
    end_date: Optional[date] = None
    annual_amount: Optional[float] = None
    payment_frequency: Optional[str] = None
    terms: Optional[str] = None
    preventive_visits_per_year: Optional[int] = None


class AMCContractResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    company_id: UUID
    customer_id: UUID
    contract_number: str
    status: str
    start_date: date
    end_date: date
    annual_amount: float
    payment_frequency: Optional[str]
    preventive_visits_per_year: Optional[int]
    is_active: bool
