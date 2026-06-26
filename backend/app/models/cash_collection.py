import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import UUID, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TenantMixin

class CashCollectionStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    REJECTED = "rejected"

class CashCollection(Base, TenantMixin):
    __tablename__ = "cash_collections"

    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    service_ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_tickets.id"), nullable=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(50), default="CASH", nullable=False)
    remarks: Mapped[str] = mapped_column(Text, nullable=True)
    receipt_photo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=CashCollectionStatus.PENDING, nullable=False, index=True)

    employee: Mapped["User"] = relationship("User")
    company: Mapped["Company"] = relationship("Company")
    logs: Mapped[list["CashCollectionLog"]] = relationship("CashCollectionLog", back_populates="collection", cascade="all, delete-orphan", lazy="selectin")
