import uuid
from enum import Enum
from sqlalchemy import UUID, String, ForeignKey, Text, Date
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    CONVERTED = "converted"
    LOST = "lost"


class LeadSource(str, Enum):
    REFERRAL = "referral"
    WALK_IN = "walk_in"
    SOCIAL_MEDIA = "social_media"
    WEBSITE = "website"
    COLD_CALL = "cold_call"
    OTHER = "other"


class Lead(Base, TenantMixin):
    __tablename__ = "leads"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default=LeadSource.OTHER)
    status: Mapped[str] = mapped_column(String(50), default=LeadStatus.NEW)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    follow_up_date: Mapped[str] = mapped_column(Date, nullable=True)
    converted_customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
