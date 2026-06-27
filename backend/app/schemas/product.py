from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class ProductCreate(BaseModel):
    sku: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    sale_price: Optional[float] = None
    rental_price: Optional[float] = None
    is_serial_tracked: bool = False
    warranty_months: int = 0
    inventory_item_id: Optional[UUID] = None
    is_sellable: bool = True
    is_rentable: bool = False


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    sale_price: Optional[float] = None
    rental_price: Optional[float] = None
    is_serial_tracked: Optional[bool] = None
    warranty_months: Optional[int] = None
    inventory_item_id: Optional[UUID] = None
    is_sellable: Optional[bool] = None
    is_rentable: Optional[bool] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    sku: str
    name: str
    brand: Optional[str]
    model: Optional[str]
    category: Optional[str]
    hsn_code: Optional[str]
    gst_rate: Optional[float]
    sale_price: Optional[float]
    rental_price: Optional[float]
    is_serial_tracked: bool
    warranty_months: int
    inventory_item_id: Optional[UUID]
    is_sellable: bool
    is_rentable: bool
    is_active: bool
