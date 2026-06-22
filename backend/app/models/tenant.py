import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, Boolean, JSON, Numeric, Date, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TimestampMixin


class SubscriptionPlan(str, Enum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


# Plan limits applied by enforce_limit() (SRS 4.1 / NFR 5.3).
PLAN_LIMITS = {
    "starter":    {"max_users": 5,  "max_sites": 25,   "max_technicians": 3},
    "growth":     {"max_users": 25, "max_sites": 200,  "max_technicians": 15},
    "enterprise": {"max_users": 0,  "max_sites": 0,    "max_technicians": 0},  # 0 = unlimited
}


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default=SubscriptionPlan.STARTER, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=TenantStatus.TRIAL, nullable=False)
    branding: Mapped[dict] = mapped_column(JSON, default=dict)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    gstin: Mapped[str] = mapped_column(String(20), nullable=True)
    registered_address: Mapped[str] = mapped_column(String(500), nullable=True)
    invoice_prefix: Mapped[str] = mapped_column(String(20), nullable=True)
    billing_contact_name: Mapped[str] = mapped_column(String(255), nullable=True)
    billing_contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SubscriptionInvoice(Base, TimestampMixin):
    """Platform-level invoice issued by Durwankur to a Tenant for its subscription
    (distinct from a Tenant's own customer invoicing) — SRS 4.1."""
    __tablename__ = "subscription_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="issued")
