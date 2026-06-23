import uuid
from enum import Enum
from sqlalchemy import UUID, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class DocumentType(str, Enum):
    PHOTO = "photo"
    SIGNATURE = "signature"
    WARRANTY_CARD = "warranty_card"
    AMC_AGREEMENT = "amc_agreement"
    SIGNED_REPORT = "signed_report"
    INVOICE = "invoice"
    OTHER = "other"


class Document(Base, TenantMixin):
    """Polymorphic document/media store (SRS 4.17). Files live in S3; the row
    holds the object key + metadata and the entity it is attached to."""
    __tablename__ = "documents"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)   # customer, site, asset, visit, ticket, invoice
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(50), default=DocumentType.OTHER)
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
