from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.customer import CustomerCategory, CustomerStatus, ContactRole


class CustomerCreate(BaseModel):
    name: str
    category: CustomerCategory
    status: CustomerStatus = CustomerStatus.ACTIVE
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    state_code: Optional[str] = None
    society_registration_no: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    authorized_signatory: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[CustomerStatus] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    state_code: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    authorized_signatory: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    name: str
    category: str
    status: str
    phone: Optional[str]
    email: Optional[str]
    gstin: Optional[str]
    address: Optional[str]
    state_code: Optional[str]
    contact_person_name: Optional[str]
    billing_address: Optional[str]
    shipping_address: Optional[str]
    authorized_signatory: Optional[str]
    is_active: bool


class ContactCreate(BaseModel):
    name: str
    role: ContactRole = ContactRole.ADMIN
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class ContactResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    customer_id: UUID
    name: str
    role: str
    phone: Optional[str]
    email: Optional[str]
