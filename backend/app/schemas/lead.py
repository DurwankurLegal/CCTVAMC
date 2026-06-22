from uuid import UUID
from typing import Optional
from datetime import date
from pydantic import BaseModel, EmailStr
from app.models.lead import LeadStatus, LeadSource


class LeadCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    source: LeadSource = LeadSource.OTHER
    notes: Optional[str] = None
    assigned_to: Optional[UUID] = None
    follow_up_date: Optional[date] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    assigned_to: Optional[UUID] = None
    follow_up_date: Optional[date] = None
    converted_customer_id: Optional[UUID] = None


class LeadResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    name: str
    phone: Optional[str]
    email: Optional[str]
    source: str
    status: str
    notes: Optional[str]
    assigned_to: Optional[UUID]
    follow_up_date: Optional[date]
    converted_customer_id: Optional[UUID]
