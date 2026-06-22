import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, DateTime, Text, Float, Boolean, JSON
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class VisitType(str, Enum):
    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"


class EngineerVisit(Base, TenantMixin):
    __tablename__ = "engineer_visits"

    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_tickets.id"), nullable=True)
    amc_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"), nullable=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visit_type: Mapped[str] = mapped_column(String(50), default=VisitType.CORRECTIVE)
    checkin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    checkout_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    checkin_lat: Mapped[float] = mapped_column(Float, nullable=True)
    checkin_lng: Mapped[float] = mapped_column(Float, nullable=True)
    checkout_lat: Mapped[float] = mapped_column(Float, nullable=True)
    checkout_lng: Mapped[float] = mapped_column(Float, nullable=True)
    work_performed: Mapped[str] = mapped_column(Text, nullable=True)
    parts_used: Mapped[list] = mapped_column(JSON, default=list)   # [{item_id, qty, description}]
    photo_urls: Mapped[list] = mapped_column(JSON, default=list)
    signature_url: Mapped[str] = mapped_column(String(500), nullable=True)
    customer_feedback: Mapped[str] = mapped_column(Text, nullable=True)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=True)  # False = created offline, pending sync
