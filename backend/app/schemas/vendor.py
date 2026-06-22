from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.vendor import VendorStatus


class VendorCreate(BaseModel):
    name: str
    vendor_type: Optional[str] = None   # supplier | service_partner
    status: VendorStatus = VendorStatus.ACTIVE
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[VendorStatus] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: Optional[bool] = None


class VendorResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    name: str
    vendor_type: Optional[str]
    status: str
    phone: Optional[str]
    email: Optional[str]
    gstin: Optional[str]
    address: Optional[str]
    contact_person: Optional[str]
    payment_terms: Optional[str]
    outstanding_payable: float
    is_active: bool
