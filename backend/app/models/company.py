import uuid
from typing import Dict, Any
from sqlalchemy import UUID, String, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TenantMixin

class Company(Base, TenantMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gst_status: Mapped[str] = mapped_column(String(50), default="NON_GST", nullable=False)
    gstin: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    bank_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    authorized_signatory: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    templates: Mapped[list["CompanyTemplate"]] = relationship("CompanyTemplate", back_populates="company", cascade="all, delete-orphan")
