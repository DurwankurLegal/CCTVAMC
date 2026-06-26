import uuid
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Numeric, JSON, Text, Boolean, Date
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    CANCELLED = "cancelled"
    CREDIT_NOTE = "credit_note"


class InvoiceType(str, Enum):
    TAX_INVOICE = "tax_invoice"
    SIMPLIFIED = "simplified"   # for unregistered small businesses


class Invoice(Base, TenantMixin):
    __tablename__ = "invoices"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_type: Mapped[str] = mapped_column(String(50), default=InvoiceType.TAX_INVOICE)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amc_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"), nullable=True)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)  # For credit notes
    status: Mapped[str] = mapped_column(String(50), default=InvoiceStatus.DRAFT)
    invoice_date: Mapped[str] = mapped_column(Date, nullable=False)
    due_date: Mapped[str] = mapped_column(Date, nullable=True)
    supply_state_code: Mapped[str] = mapped_column(String(2), nullable=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
