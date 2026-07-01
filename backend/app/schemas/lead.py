from uuid import UUID
from typing import Optional
from datetime import date
from pydantic import BaseModel, EmailStr
from app.models.lead import LeadStatus, LeadSource, LeadCategory, InterestType


class LeadCreate(BaseModel):
    company_id: Optional[UUID] = None
    name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    category: Optional[LeadCategory] = None
    interest_type: Optional[InterestType] = None
    source: LeadSource = LeadSource.OTHER
    notes: Optional[str] = None
    assigned_to: Optional[UUID] = None
    follow_up_date: Optional[date] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    category: Optional[LeadCategory] = None
    interest_type: Optional[InterestType] = None
    status: Optional[LeadStatus] = None
    lost_reason: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[UUID] = None
    follow_up_date: Optional[date] = None
    converted_customer_id: Optional[UUID] = None


class LeadResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    company_id: UUID
    name: str
    company_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    category: Optional[str]
    interest_type: Optional[str]
    source: str
    status: str
    notes: Optional[str]
    assigned_to: Optional[UUID]
    follow_up_date: Optional[date]
    converted_customer_id: Optional[UUID]
