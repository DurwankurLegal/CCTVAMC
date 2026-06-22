from uuid import UUID
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.models.installation import InstallationStatus


class InstallationCreate(BaseModel):
    customer_id: UUID
    site_id: Optional[UUID] = None
    quotation_id: Optional[UUID] = None
    target_completion_date: Optional[date] = None
    assigned_technician_id: Optional[UUID] = None


class SurveyUpdate(BaseModel):
    survey_date: Optional[date] = None
    survey_notes: Optional[str] = None
    feasibility_notes: Optional[str] = None
    recommended_camera_count: Optional[int] = None


class InstallationUpdate(BaseModel):
    status: Optional[InstallationStatus] = None
    assigned_technician_id: Optional[UUID] = None
    target_completion_date: Optional[date] = None


class HandoverRequest(BaseModel):
    otp: str
    # AMC terms to auto-create on handover
    amc_annual_amount: float = 0
    amc_months: int = 12
    preventive_visits_per_year: int = 2


class InstallationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    work_order_number: str
    customer_id: UUID
    site_id: Optional[UUID]
    status: str
    recommended_camera_count: Optional[int]
    target_completion_date: Optional[date]
    amc_contract_id: Optional[UUID]
