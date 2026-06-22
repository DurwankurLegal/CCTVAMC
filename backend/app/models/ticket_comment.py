import uuid
from sqlalchemy import UUID, String, ForeignKey, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class TicketComment(Base, TenantMixin):
    """Comment / status-change note on a service ticket (SRS 4.8 audit trail)."""
    __tablename__ = "ticket_comments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_tickets.id"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class TicketAttachment(Base, TenantMixin):
    """File attached to a service ticket (stored as a Document reference)."""
    __tablename__ = "ticket_attachments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_tickets.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
