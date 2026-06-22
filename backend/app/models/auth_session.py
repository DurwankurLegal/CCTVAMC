import uuid
from datetime import datetime
from sqlalchemy import UUID, String, Boolean, DateTime
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TimestampMixin


class AuthSession(Base, TimestampMixin):
    """Server-side record of an issued refresh token, enabling rotation and
    revocation. On refresh the current jti is revoked and a new one issued; a
    reused (already-revoked) jti is rejected.
    """
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
