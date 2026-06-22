import uuid
from datetime import date, datetime
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Date, DateTime, Integer, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class InstallationStatus(str, Enum):
    SURVEY_PENDING = "survey_pending"
    SURVEY_DONE = "survey_done"
    MATERIAL_ALLOCATED = "material_allocated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    HANDED_OVER = "handed_over"


class Installation(Base, TenantMixin):
    """New-installation work order (SRS 4.5): survey -> install -> handover, with
    auto-AMC + warranty registration on handover."""
    __tablename__ = "installations"

    work_order_number: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_sites.id"), nullable=True)
    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=InstallationStatus.SURVEY_PENDING)
    survey_date: Mapped[date] = mapped_column(Date, nullable=True)
    survey_notes: Mapped[str] = mapped_column(Text, nullable=True)
    feasibility_notes: Mapped[str] = mapped_column(Text, nullable=True)
    recommended_camera_count: Mapped[int] = mapped_column(Integer, nullable=True)
    assigned_technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_completion_date: Mapped[date] = mapped_column(Date, nullable=True)
    handover_otp: Mapped[str] = mapped_column(String(10), nullable=True)
    handed_over_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    amc_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
