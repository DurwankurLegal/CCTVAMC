import uuid
from sqlalchemy import UUID, String, ForeignKey, Numeric, Integer, Boolean
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class Product(Base, TenantMixin):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)  # camera, DVR, NVR, switch, HDD, accessory
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=True)
    gst_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    sale_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    rental_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    is_serial_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    warranty_months: Mapped[int] = mapped_column(Integer, default=0)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=True)
    is_sellable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_rentable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
