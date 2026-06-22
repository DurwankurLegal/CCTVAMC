import uuid
from enum import Enum
from sqlalchemy import UUID, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base
from app.models.base import TenantMixin


class CustomerCategory(str, Enum):
    CHS = "chs"                    # Cooperative Housing Society
    COMMERCIAL = "commercial"
    SINGLE_SHOP = "single_shop"


class Customer(Base, TenantMixin):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    state_code: Mapped[str] = mapped_column(String(2), nullable=True)  # For GST intra/inter state
    # CHS-specific
    society_registration_no: Mapped[str] = mapped_column(String(100), nullable=True)
    contact_person_name: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_person_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sites: Mapped[list["CustomerSite"]] = relationship("CustomerSite", back_populates="customer")


class CustomerSite(Base, TenantMixin):
    __tablename__ = "customer_sites"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="sites")
    assets: Mapped[list["CCTVAsset"]] = relationship("CCTVAsset", back_populates="site")
