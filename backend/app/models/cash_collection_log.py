import uuid
from datetime import datetime
from sqlalchemy import UUID, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TenantMixin

class CashCollectionLog(Base, TenantMixin):
    __tablename__ = "cash_collection_logs"

    cash_collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cash_collections.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # APPROVED, REJECTED
    action_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    collection: Mapped["CashCollection"] = relationship("CashCollection", back_populates="logs")
    actor: Mapped["User"] = relationship("User")
