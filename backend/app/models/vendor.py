import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, Boolean, Text, ForeignKey, Numeric, Date, JSON
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


class POStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class Vendor(Base, TenantMixin):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_type: Mapped[str] = mapped_column(String(50), nullable=True)  # supplier, service_partner
    status: Mapped[str] = mapped_column(String(50), default=VendorStatus.ACTIVE, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(100), nullable=True)
    bank_account_encrypted: Mapped[str] = mapped_column(String(500), nullable=True)
    outstanding_payable: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PurchaseOrder(Base, TenantMixin):
    """Procurement PO linked to a vendor (SRS 4.4/4.11)."""
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(String(100), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=POStatus.DRAFT)
    order_date: Mapped[date] = mapped_column(Date, nullable=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)   # [{item_id, qty, unit_cost}]
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class VendorPayment(Base, TenantMixin):
    """Payment made against a vendor — drives outstanding payable balance (SRS 4.14)."""
    __tablename__ = "vendor_payments"

    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=True)
    method: Mapped[str] = mapped_column(String(50), nullable=True)
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
