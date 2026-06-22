from uuid import UUID
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.models.asset import AssetStatus


class AssetCreate(BaseModel):
    site_id: UUID
    serial_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    asset_type: Optional[str] = None
    installation_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    location_description: Optional[str] = None


class AssetUpdate(BaseModel):
    serial_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    asset_type: Optional[str] = None
    warranty_expiry: Optional[date] = None
    status: Optional[AssetStatus] = None
    location_description: Optional[str] = None
    is_active: Optional[bool] = None


class AssetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    site_id: UUID
    serial_number: Optional[str]
    make: Optional[str]
    model: Optional[str]
    asset_type: Optional[str]
    installation_date: Optional[date]
    warranty_expiry: Optional[date]
    status: str
    location_description: Optional[str]
    is_active: bool
