import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base
from app.models.base import TenantMixin


class TicketStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_PARTS = "pending_parts"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ServiceTicket(Base, TenantMixin):
    __tablename__ = "service_tickets"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    ticket_number: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_sites.id"), nullable=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cctv_assets.id"), nullable=True)
    amc_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=TicketStatus.OPEN)
    priority: Mapped[str] = mapped_column(String(50), default=TicketPriority.MEDIUM)
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def resolution_time_hours(self) -> float:
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            return round(delta.total_seconds() / 3600.0, 2)
        return 0.0

