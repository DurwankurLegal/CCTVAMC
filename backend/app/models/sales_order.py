import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Numeric, JSON, Text, Boolean, Date
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class SalesOrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class SalesOrder(Base, TenantMixin):
    __tablename__ = "sales_orders"

    order_number: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=SalesOrderStatus.DRAFT)
    order_date: Mapped[str] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[str] = mapped_column(Date, nullable=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    supply_state_code: Mapped[str] = mapped_column(String(2), nullable=True)
    fulfilled_at: Mapped[date] = mapped_column(Date, nullable=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

