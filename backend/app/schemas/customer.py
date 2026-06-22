from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.customer import CustomerCategory


class CustomerCreate(BaseModel):
    name: str
    category: CustomerCategory
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    state_code: Optional[str] = None
    society_registration_no: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    state_code: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    name: str
    category: str
    phone: Optional[str]
    email: Optional[str]
    gstin: Optional[str]
    address: Optional[str]
    state_code: Optional[str]
    contact_person_name: Optional[str]
    is_active: bool
