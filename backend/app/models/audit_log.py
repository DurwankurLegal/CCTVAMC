import uuid
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import UUID, String, DateTime, JSON, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, APPROVE
    before_state: Mapped[dict] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict] = mapped_column(JSON, nullable=True)
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @staticmethod
    def compute_hash(previous_hash: str, payload: dict) -> str:
        content = previous_hash + json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
