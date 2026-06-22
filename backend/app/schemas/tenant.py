from uuid import UUID
from typing import Optional
from pydantic import BaseModel
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
