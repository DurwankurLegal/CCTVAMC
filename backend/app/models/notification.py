import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import UUID, String, Text, Boolean, JSON, DateTime
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationTemplate(Base, TenantMixin):
    __tablename__ = "notification_templates"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class NotificationLog(Base, TenantMixin):
    __tablename__ = "notification_logs"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=NotificationStatus.PENDING)
    retry_count: Mapped[int] = mapped_column(default=0)
    error_detail: Mapped[str] = mapped_column(Text, nullable=True)
    context_data: Mapped[dict] = mapped_column(JSON, default=dict)
    # In-app notification center: target user + read tracking.
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
