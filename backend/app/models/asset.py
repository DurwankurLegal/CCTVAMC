import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, Boolean, ForeignKey, Date, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base
from app.models.base import TenantMixin


class AssetStatus(str, Enum):
    ACTIVE = "active"
    FAULTY = "faulty"
    UNDER_REPAIR = "under_repair"
    REPLACED = "replaced"
    DECOMMISSIONED = "decommissioned"


class CCTVAsset(Base, TenantMixin):
    __tablename__ = "cctv_assets"

    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_sites.id"), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=True)
    make: Mapped[str] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=True)  # DVR, NVR, Camera, etc.
    installation_date: Mapped[date] = mapped_column(Date, nullable=True)
    warranty_expiry: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=AssetStatus.ACTIVE)
    location_description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    site: Mapped["CustomerSite"] = relationship("CustomerSite", back_populates="assets")
