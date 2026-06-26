import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Numeric, JSON, Text, Boolean, Date
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class QuotationStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quotation(Base, TenantMixin):
    __tablename__ = "quotations"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quotation_number: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=QuotationStatus.DRAFT)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    terms: Mapped[str] = mapped_column(Text, nullable=True)
    valid_until: Mapped[date] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
