import uuid
from datetime import date
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Date, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class PMStatus(str, Enum):
    PLANNED = "planned"
    DONE = "done"
    SKIPPED = "skipped"
    RESCHEDULED = "rescheduled"


class PMSchedule(Base, TenantMixin):
    """A planned preventive-maintenance visit auto-generated from an AMC contract
    (SRS 4.9). Tracks completion against the contract's committed visit count."""
    __tablename__ = "pm_schedules"

    amc_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("amc_contracts.id"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=PMStatus.PLANNED)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=True)   # for skip/reschedule
    completed_visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
