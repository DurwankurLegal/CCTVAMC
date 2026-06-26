import uuid
from sqlalchemy import UUID, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TenantMixin

class CompanyTemplate(Base, TenantMixin):
    __tablename__ = "company_templates"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    template_html: Mapped[str] = mapped_column(Text, nullable=False)
    header_html: Mapped[str] = mapped_column(Text, nullable=True)
    footer_html: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company: Mapped["Company"] = relationship("Company", back_populates="templates")
