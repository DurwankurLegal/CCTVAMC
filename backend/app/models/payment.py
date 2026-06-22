import uuid
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Numeric, Text, Date
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class PaymentMode(str, Enum):
    CASH = "cash"
    CHEQUE = "cheque"
    NEFT = "neft"
    UPI = "upi"
    CARD = "card"
    OTHER = "other"


class Payment(Base, TenantMixin):
    __tablename__ = "payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[str] = mapped_column(Date, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default=PaymentMode.CASH)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
