from uuid import UUID
from typing import Optional, Dict, Any
from pydantic import BaseModel

class CompanyBase(BaseModel):
    name: str
    gst_status: str = "NON_GST"
    gstin: Optional[str] = None
    address: Optional[str] = None
    contact_details: Dict[str, Any] = {}
    bank_details: Dict[str, Any] = {}
    logo_url: Optional[str] = None
    authorized_signatory: Dict[str, Any] = {}
    is_default: bool = False
    is_active: bool = True

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    gst_status: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    contact_details: Optional[Dict[str, Any]] = None
    bank_details: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    authorized_signatory: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

class CompanyResponse(CompanyBase):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
