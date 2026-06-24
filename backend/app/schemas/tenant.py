from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.tenant import SubscriptionPlan, TenantStatus


class TenantCreate(BaseModel):
    name: str
    slug: str
    plan: SubscriptionPlan = SubscriptionPlan.STARTER
    gstin: Optional[str] = None
    registered_address: Optional[str] = None
    invoice_prefix: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[SubscriptionPlan] = None
    status: Optional[TenantStatus] = None
    gstin: Optional[str] = None
    registered_address: Optional[str] = None
    invoice_prefix: Optional[str] = None
    branding: Optional[dict] = None
    settings: Optional[dict] = None
    trial_ends_at: Optional[datetime] = None
    custom_domain: Optional[str] = None
    custom_email_sender: Optional[str] = None
    email_templates: Optional[dict] = None


class TenantResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    slug: str
    plan: str
    status: str
    gstin: Optional[str]
    invoice_prefix: Optional[str]
    branding: dict
    settings: dict
    is_active: bool
    trial_ends_at: Optional[datetime] = None
    custom_domain: Optional[str] = None
    custom_email_sender: Optional[str] = None
    email_templates: Optional[dict] = None


class TenantProvisionRequest(BaseModel):
    """Onboard a company in one shot: tenant + optional first admin (sales-led)."""
    tenant: TenantCreate
    admin_email: Optional[EmailStr] = None
    admin_full_name: Optional[str] = None
    admin_password: Optional[str] = None   # omit → a temp password is generated


class ProvisionedAdmin(BaseModel):
    id: UUID
    email: str
    must_change_password: bool


class TenantProvisionResponse(BaseModel):
    tenant: TenantResponse
    first_admin: Optional[ProvisionedAdmin] = None
    temp_password: Optional[str] = None     # shown ONCE in the UI; not retrievable later
