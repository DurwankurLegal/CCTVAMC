import uuid
from sqlalchemy import UUID, JSON
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TimestampMixin


class DashboardSnapshot(Base, TimestampMixin):
    """Pre-aggregated per-tenant KPI metrics for fast dashboard loads (TAD 13.4).
    Refreshed periodically by a Celery task."""
    __tablename__ = "dashboard_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
