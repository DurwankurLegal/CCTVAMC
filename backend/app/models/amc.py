import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Date, Numeric, Text, Boolean
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base
from app.models.base import TenantMixin


class AMCStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRING = "expiring"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class AMCContract(Base, TenantMixin):
    __tablename__ = "amc_contracts"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=AMCStatus.DRAFT)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    annual_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_frequency: Mapped[str] = mapped_column(String(50), nullable=True)  # monthly, quarterly, annual
    terms: Mapped[str] = mapped_column(Text, nullable=True)
    preventive_visits_per_year: Mapped[int] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    assets: Mapped[list["AMCAsset"]] = relationship("AMCAsset", back_populates="contract")


class AMCAsset(Base, TenantMixin):
    """Junction: which CCTV assets are covered under an AMC contract."""
    __tablename__ = "amc_assets"

    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cctv_assets.id"), nullable=False)

    contract: Mapped["AMCContract"] = relationship("AMCContract", back_populates="assets")
