import uuid
from sqlalchemy import UUID, String, Integer, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TimestampMixin


class DocumentSequence(Base, TimestampMixin):
    """Per-tenant, per-doc-type, per-year monotonic counter for document
    numbers (invoices, quotations, AMC contracts, tickets). Incremented under a
    row lock so numbers are unique, gapless and survive restarts/multiple
    workers — required for GST-compliant sequential invoicing.
    """
    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "doc_type", "year", name="uq_document_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
