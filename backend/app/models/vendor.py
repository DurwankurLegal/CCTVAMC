import uuid
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class Vendor(Base, TenantMixin):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_type: Mapped[str] = mapped_column(String(50), nullable=True)  # supplier, service_partner
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(100), nullable=True)
    bank_account_encrypted: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
