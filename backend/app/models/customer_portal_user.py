import uuid
from sqlalchemy import UUID, String, Boolean, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class CustomerPortalUser(Base, TenantMixin):
    """Self-service portal identity (SRS 4.2). Deliberately separate from the
    staff ``User`` table: portal users authenticate through a distinct flow and
    their JWTs carry a ``scope="portal"`` marker so they can never reach staff
    APIs (and staff tokens can never reach portal APIs). Scoped by both
    ``tenant_id`` (RLS) and ``customer_id`` (application layer)."""
    __tablename__ = "customer_portal_users"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
