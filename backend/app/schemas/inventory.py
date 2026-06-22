from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from app.models.inventory import MovementType


class InventoryItemCreate(BaseModel):
    name: str
    part_number: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    reorder_level: int = 0
    unit_cost: Optional[float] = None
    vendor_id: Optional[UUID] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    reorder_level: Optional[int] = None
    unit_cost: Optional[float] = None
    vendor_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class InventoryItemResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    name: str
    part_number: Optional[str]
    unit: Optional[str]
    hsn_code: Optional[str]
    gst_rate: Optional[float]
    reorder_level: int
    current_stock: int
    van_stock: int
    unit_cost: Optional[float]
    vendor_id: Optional[UUID]
    is_active: bool


class StockAdjustment(BaseModel):
    item_id: UUID
    quantity: int                  # positive = in, negative = out
    movement_type: MovementType
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    notes: Optional[str] = None
