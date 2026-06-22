import uuid
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Numeric, Integer, Boolean, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base
from app.models.base import TenantMixin


class MovementType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    CONSUMPTION = "consumption"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    RETURN = "return"


class InventoryItem(Base, TenantMixin):
    __tablename__ = "inventory_items"

    part_number: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=True)
    gst_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    van_stock: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    movements: Mapped[list["InventoryMovement"]] = relationship("InventoryMovement", back_populates="item")


class InventoryMovement(Base, TenantMixin):
    __tablename__ = "inventory_movements"

    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=True)  # visit, purchase_order
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="movements")
